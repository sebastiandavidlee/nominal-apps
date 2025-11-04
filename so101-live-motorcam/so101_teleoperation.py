"""
SO-101 Robot Arm Teleoperation

Reads motor positions from Arm 1 (ACM1) and commands them to Arm 2 (ACM0).
This creates a leader-follower setup where moving Arm 1 causes Arm 2 to mirror.

Current mapping: 1:1 (Motor 1 → Motor 1, Motor 2 → Motor 2, etc.)
"""

import serial
import time
import traceback
import connect_python

# --- Configuration ---
LEADER_PORT = "/dev/ttyACM1"    # Arm 1 - we READ from this
FOLLOWER_PORT = "/dev/ttyACM0"  # Arm 2 - we WRITE to this
BAUD_RATE = 1_000_000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
TIMEOUT = 0.05

UPDATE_RATE = 50.0  # Hz - how often to read leader and update follower

# Feetech Protocol
SCS_WRITE = 0x03
SCS_READ = 0x02
SCS_GOAL_POSITION_L = 42
SCS_PRESENT_POSITION_L = 56
SCS_MODE = 33
SCS_GOAL_SPEED_L = 46
SCS_TORQUE_ENABLE = 40

logger = connect_python.get_logger(__name__)


def calculate_checksum(packet):
    total = sum(packet[2:])
    return ~total & 0xFF


def set_motor_position(ser, motor_id, position):
    """Send position command to a motor."""
    position = max(0, min(4095, int(position)))
    pos_low = position & 0xFF
    pos_high = (position >> 8) & 0xFF
    
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 5, SCS_WRITE, 
        SCS_GOAL_POSITION_L, pos_low, pos_high
    ]
    
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.001)  # Brief delay
    if ser.in_waiting > 0:
        ser.read(ser.in_waiting)  # Clear response
    return True


def read_motor_register(ser, motor_id, register_address, num_bytes=2):
    """Read a register from a motor."""
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 4, SCS_READ, register_address, num_bytes
    ]
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    
    ser.write(packet)
    time.sleep(0.001)
    response = ser.read(5 + num_bytes + 1)
    
    if len(response) >= (5 + num_bytes) and response[0] == 0xFF and response[1] == 0xFF:
        if num_bytes == 2:
            return response[5] | (response[6] << 8)
        else:
            return response[5]
    return None


def get_motor_position(ser, motor_id):
    """Read current position from a motor."""
    return read_motor_register(ser, motor_id, SCS_PRESENT_POSITION_L, 2)


def set_motor_mode(ser, motor_id, mode=0):
    """Set motor control mode (0=position)."""
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 4, SCS_WRITE, SCS_MODE, mode
    ]
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.01)
    return True


def set_motor_speed(ser, motor_id, speed=500):
    """Set motor movement speed."""
    speed_low = speed & 0xFF
    speed_high = (speed >> 8) & 0xFF
    
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 5, SCS_WRITE, 
        SCS_GOAL_SPEED_L, speed_low, speed_high
    ]
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.005)
    return True


def enable_motor_torque(ser, motor_id):
    """Enable motor torque."""
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 4, SCS_WRITE, SCS_TORQUE_ENABLE, 1
    ]
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.005)
    return True


@connect_python.main
def main(connect_client: connect_python.Client):
    """
    Main teleoperation loop.
    
    Continuously reads positions from leader arm and commands follower arm to match.
    """
    ser_leader = None
    ser_follower = None
    
    try:
        # Connect to both arms
        logger.info(f"Connecting to LEADER arm at {LEADER_PORT}...")
        ser_leader = serial.Serial(LEADER_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Leader connected!")
        
        logger.info(f"Connecting to FOLLOWER arm at {FOLLOWER_PORT}...")
        ser_follower = serial.Serial(FOLLOWER_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Follower connected!")
        
        # Configure follower motors for position control
        logger.info("\nConfiguring follower arm motors...")
        for motor_id in MOTOR_IDS:
            set_motor_mode(ser_follower, motor_id, mode=0)
            set_motor_speed(ser_follower, motor_id, speed=0)  # 0 = maximum speed!
            enable_motor_torque(ser_follower, motor_id)
        logger.info("Follower arm ready!")
        
        # Clear streams
        connect_client.clear_stream("teleoperation")
        
        logger.info("\n🤖 Teleoperation ACTIVE! Move the leader arm (ACM1)...")
        logger.info("Press Ctrl+C to stop.\n")
        
        loop_count = 0
        
        # Main teleoperation loop
        while True:
            timestamp = time.time()
            loop_count += 1
            
            # Read all positions from leader arm
            leader_positions = {}
            for motor_id in MOTOR_IDS:
                pos = get_motor_position(ser_leader, motor_id)
                if pos is not None:
                    leader_positions[motor_id] = pos
            
            # Command follower arm to match leader positions
            for motor_id in MOTOR_IDS:
                if motor_id in leader_positions:
                    target_position = leader_positions[motor_id]
                    set_motor_position(ser_follower, motor_id, target_position)
            
            # Log status every 2 seconds
            if loop_count % (int(UPDATE_RATE) * 2) == 0:
                logger.info(f"Teleoperation active - Leader positions: {leader_positions}")
            
            # Stream data for visualization
            for motor_id in MOTOR_IDS:
                if motor_id in leader_positions:
                    connect_client.stream(
                        "teleoperation",
                        timestamp,
                        names=[f"leader_motor_{motor_id}", f"follower_cmd_{motor_id}"],
                        values=[leader_positions[motor_id], leader_positions[motor_id]]
                    )
            
            # Wait for next update
            time.sleep(1.0 / UPDATE_RATE)
        
    except serial.SerialException as e:
        logger.error(f"Serial connection error: {e}")
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Teleoperation stopped by user.")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        
    finally:
        if ser_leader and ser_leader.is_open:
            ser_leader.close()
            logger.info("Leader connection closed.")
        if ser_follower and ser_follower.is_open:
            ser_follower.close()
            logger.info("Follower connection closed.")


if __name__ == "__main__":
    main()

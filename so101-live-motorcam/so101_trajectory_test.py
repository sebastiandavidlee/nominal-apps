"""
SO-101 Robot Arm Motor Control - Trajectory Testing

This script sends position commands to the SO-101 robot motors to execute
a controlled trajectory. It moves each motor through a range of positions
at a safe speed to test motor control capabilities.

Hardware: SO-101 Robot with Feetech servo motors
Protocol: Feetech SCS (Serial Command System)
"""

import serial
import time
import traceback
import connect_python

# --- Configuration ---
SERIAL_PORT = "/dev/ttyACM0"  # Serial port for SO-101 connection
BAUD_RATE = 1_000_000          # Communication speed (1 Mbps)
MOTOR_IDS = [1, 2, 3, 4, 5, 6] # IDs of motors to control
TIMEOUT = 0.05                  # Serial read timeout in seconds

# Reference positions (measured from Arm 2 at rest)
HOME_POSITIONS = {
    1: 2054,
    2: 1703,
    3: 1311,
    4: 2524,
    5: 2103,
    6: 2162
}

# Trajectory parameters
POSITION_RANGE = 100           # +/- range from home position
STEP_SIZE = 20                 # Position change per update (encoder steps)
UPDATE_RATE = 1.0              # Updates per second (Hz)

# Feetech Protocol Constants
SCS_WRITE = 0x03               # Write command instruction
SCS_GOAL_POSITION_L = 42       # Register address for goal position (lower byte)
SCS_READ = 0x02                # Read command instruction
SCS_PRESENT_POSITION_L = 56    # Register address for current position (lower byte)

logger = connect_python.get_logger(__name__)


def calculate_checksum(packet):
    """
    Calculate the checksum for a Feetech SCS protocol packet.
    
    Args:
        packet: List of bytes representing the packet (without checksum)
        
    Returns:
        Checksum byte (inverted sum of ID through parameters)
    """
    total = sum(packet[2:])  # Sum from ID onwards (skip two 0xFF headers)
    return ~total & 0xFF


def set_motor_position(ser, motor_id, position):
    """
    Set the goal position for a Feetech servo motor.
    
    Args:
        ser: Serial connection object
        motor_id: Motor ID to control (1-6)
        position: Target position (0-4095)
        
    Returns:
        True if command was sent successfully, False otherwise
    """
    # Clamp position to valid range
    position = max(0, min(4095, int(position)))
    
    # Construct write command packet
    # Format: [0xFF, 0xFF, ID, Length, Instruction, Address, PosL, PosH, Checksum]
    length = 5  # Instruction + Address + PosL + PosH + Checksum
    pos_low = position & 0xFF
    pos_high = (position >> 8) & 0xFF
    
    packet_without_checksum = [
        0xFF, 0xFF,                    # Header bytes
        motor_id,                      # Target motor ID
        length,                        # Packet length
        SCS_WRITE,                     # Write instruction
        SCS_GOAL_POSITION_L,           # Goal position register address
        pos_low,                       # Position low byte
        pos_high                       # Position high byte
    ]
    
    checksum = calculate_checksum(packet_without_checksum)
    packet = bytes(packet_without_checksum + [checksum])

    try:
        ser.write(packet)
        time.sleep(0.002)  # Brief delay for motor to process command
        return True
        
    except Exception as e:
        logger.error(f"Motor {motor_id}: Error setting position - {e}")
        return False


def get_motor_position(ser, motor_id):
    """
    Read the current position from a Feetech servo motor.
    
    Args:
        ser: Serial connection object
        motor_id: Motor ID to query (1-6)
        
    Returns:
        Motor position as integer (0-4095), or None if read fails
    """
    # Construct read command packet
    length = 4
    packet_without_checksum = [
        0xFF, 0xFF,
        motor_id,
        length,
        SCS_READ,
        SCS_PRESENT_POSITION_L,
        2
    ]
    
    checksum = calculate_checksum(packet_without_checksum)
    packet = bytes(packet_without_checksum + [checksum])

    try:
        ser.write(packet)
        time.sleep(0.001)
        
        response = ser.read(8)
        
        if len(response) >= 8 and response[0] == 0xFF and response[1] == 0xFF:
            position = response[5] | (response[6] << 8)
            return position
        
        return None
        
    except Exception as e:
        logger.error(f"Motor {motor_id}: Error reading position - {e}")
        return None


@connect_python.main
def main(connect_client: connect_python.Client):
    """
    Main trajectory execution loop.
    
    Moves each motor through a controlled trajectory from home position
    -100 to +100 steps and back, at a safe speed.
    """
    ser = None
    
    try:
        # Open serial connection
        logger.info(f"Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Connection established successfully.")
        
        # Clear stream for trajectory data
        connect_client.clear_stream("motor_trajectory")
        
        # Verify we can read all motors first
        logger.info("Reading current motor positions...")
        current_positions = {}
        for motor_id in MOTOR_IDS:
            pos = get_motor_position(ser, motor_id)
            if pos is not None:
                current_positions[motor_id] = pos
                logger.info(f"Motor {motor_id}: Current position = {pos}, Home = {HOME_POSITIONS[motor_id]}")
            else:
                logger.error(f"Motor {motor_id}: Failed to read position!")
                return
        
        logger.info("All motors responding. Starting trajectory in 3 seconds...")
        time.sleep(3)
        
        # Execute trajectory: Home -> Home-100 -> Home+100 -> Home
        waypoints = [-POSITION_RANGE, POSITION_RANGE, 0]
        
        for waypoint_idx, target_offset in enumerate(waypoints):
            waypoint_name = ["MIN", "MAX", "HOME"][waypoint_idx]
            logger.info(f"\n=== Moving to waypoint: {waypoint_name} (offset: {target_offset:+d}) ===")
            
            # Calculate target positions for all motors
            targets = {
                motor_id: HOME_POSITIONS[motor_id] + target_offset
                for motor_id in MOTOR_IDS
            }
            
            # Move incrementally until all motors reach target
            while True:
                timestamp = time.time()
                all_reached = True
                
                for motor_id in MOTOR_IDS:
                    current = get_motor_position(ser, motor_id)
                    if current is None:
                        continue
                    
                    target = targets[motor_id]
                    error = target - current
                    
                    # Check if motor has reached target (within tolerance)
                    if abs(error) <= STEP_SIZE:
                        set_motor_position(ser, motor_id, target)
                    else:
                        # Move one step toward target
                        if error > 0:
                            next_pos = current + STEP_SIZE
                        else:
                            next_pos = current - STEP_SIZE
                        
                        set_motor_position(ser, motor_id, next_pos)
                        all_reached = False
                    
                    # Stream current position for visualization
                    connect_client.stream(
                        "motor_trajectory",
                        timestamp,
                        names=[f"motor_{motor_id}"],
                        values=[current]
                    )
                
                # Check if all motors reached waypoint
                if all_reached:
                    logger.info(f"Waypoint {waypoint_name} reached!")
                    time.sleep(0.5)  # Brief pause at waypoint
                    break
                
                time.sleep(1.0 / UPDATE_RATE)
        
        logger.info("\n=== Trajectory complete! ===")
        
    except serial.SerialException as e:
        logger.error(f"Failed to open serial port {SERIAL_PORT}: {e}")
        
    except KeyboardInterrupt:
        logger.info("Trajectory stopped by user.")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        
    finally:
        if ser and ser.is_open:
            ser.close()
            logger.info("Serial connection closed.")


if __name__ == "__main__":
    main()

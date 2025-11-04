"""
SO-101 Robot Arm - Simple Home Position Command

Sends each motor to its home position and exits.
Update HOME_POSITIONS dict to test different positions.
"""

import serial
import time
import connect_python

# --- Configuration ---
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 1_000_000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
TIMEOUT = 0.05

# UPDATE THESE VALUES:
HOME_POSITIONS = {
    1: 1700,
    2: 1200,
    3: 2600,
    4: 2500,
    5: 2100,
    6: 2100
}

# 1: 2000 centered
# 2: 2000 straight up
# 2: 1400 backed off
# 3: 2000 right angle
# 3: 2400 elbow tucking
# 4: 2500 wrist down
# 4: 2200 wrist straight
# 5: 2060 wrist neutral
# 5: 2200 CCW
# 6: 2000 closed
# 6: 2300 open

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
    position = max(0, min(4095, int(position)))
    pos_low = position & 0xFF
    pos_high = (position >> 8) & 0xFF
    
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 5, SCS_WRITE, 
        SCS_GOAL_POSITION_L, pos_low, pos_high
    ]
    
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.002)
    if ser.in_waiting > 0:
        ser.read(ser.in_waiting)
    return True


def read_motor_register(ser, motor_id, register_address, num_bytes=2):
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
    return read_motor_register(ser, motor_id, SCS_PRESENT_POSITION_L, 2)


def set_motor_mode(ser, motor_id, mode=0):
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 4, SCS_WRITE, SCS_MODE, mode
    ]
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.01)
    return True


def set_motor_speed(ser, motor_id, speed=200):
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
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 4, SCS_WRITE, SCS_TORQUE_ENABLE, 1
    ]
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.005)
    return True


@connect_python.main
def main(connect_client: connect_python.Client):
    ser = None
    
    try:
        # Connect
        logger.info(f"Connecting to {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        
        # Read current positions
        logger.info("\nCurrent positions:")
        for motor_id in MOTOR_IDS:
            pos = get_motor_position(ser, motor_id)
            if pos is not None:
                logger.info(f"  Motor {motor_id}: {pos}")
        
        # Configure motors
        logger.info("\nConfiguring motors...")
        for motor_id in MOTOR_IDS:
            set_motor_mode(ser, motor_id, mode=0)
            set_motor_speed(ser, motor_id, speed=100)  # Fast movement
            enable_motor_torque(ser, motor_id)
        
        # Send home commands
        logger.info("\nMoving to HOME positions...")
        for motor_id in MOTOR_IDS:
            target = HOME_POSITIONS[motor_id]
            logger.info(f"  Motor {motor_id} → {target}")
            set_motor_position(ser, motor_id, target)
        
        # Wait for movement to complete
        time.sleep(2.0)
        
        # Verify final positions
        logger.info("\nFinal positions:")
        for motor_id in MOTOR_IDS:
            pos = get_motor_position(ser, motor_id)
            target = HOME_POSITIONS[motor_id]
            error = abs(target - pos) if pos is not None else None
            if pos is not None:
                logger.info(f"  Motor {motor_id}: {pos} (target: {target}, error: {error})")
        
        logger.info("\n✓ Done!")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        
    finally:
        if ser and ser.is_open:
            ser.close()


if __name__ == "__main__":
    main()

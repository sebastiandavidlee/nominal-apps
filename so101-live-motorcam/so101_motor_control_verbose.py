"""
SO-101 Robot Arm Motor Control - New Control Script

This is a copy of the working trajectory test script.
Ready for new functionality to be added.

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
    1: 1950,
    2: 1626,
    3: 1807,
    4: 2495,
    5: 2060,
    6: 2300
}

# Trajectory parameters
POSITION_RANGE = 100          # +/- range from home position
STEP_SIZE = 10                 # Position change per update (encoder steps)
UPDATE_RATE = 2.0             # Updates per second (Hz)
TEST_MOTOR_ONLY = [1,2,3]     # Only move these motors [1, 2, ...], single motor like 1, or None to move all

# Feetech Protocol Constants
SCS_WRITE = 0x03               # Write command instruction
SCS_GOAL_POSITION_L = 42       # Register address for goal position (lower byte)
SCS_READ = 0x02                # Read command instruction
SCS_PRESENT_POSITION_L = 56    # Register address for current position (lower byte)
SCS_MIN_POSITION_L = 9         # Register address for minimum position limit (lower byte)
SCS_MAX_POSITION_L = 11        # Register address for maximum position limit (lower byte)
SCS_TORQUE_ENABLE = 40         # Register address for torque enable (1=on, 0=off)
SCS_LOCK = 48                  # Register address for EEPROM lock (0=unlock, 1=lock)
SCS_MODE = 33                  # Register address for control mode (0=servo/position, 1=motor/speed, 3=step)
SCS_GOAL_SPEED_L = 46          # Register address for goal speed (lower byte)

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


def set_motor_position(ser, motor_id, position, debug=False):
    """
    Set the goal position for a Feetech servo motor.
    
    Args:
        ser: Serial connection object
        motor_id: Motor ID to control (1-6)
        position: Target position (0-4095)
        debug: Print detailed packet information
        
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

    if debug:
        logger.info(f"Motor {motor_id}: Setting position to {position}")
        logger.info(f"  Packet: {' '.join([f'{b:02X}' for b in packet])}")
        logger.info(f"  Position bytes: Low={pos_low:02X} ({pos_low}), High={pos_high:02X} ({pos_high})")

    try:
        ser.write(packet)
        time.sleep(0.002)  # Brief delay for motor to process command
        
        # Try to read response (some servos send acknowledgment)
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            if debug:
                logger.info(f"  Response: {' '.join([f'{b:02X}' for b in response])}")
        
        return True
        
    except Exception as e:
        logger.error(f"Motor {motor_id}: Error setting position - {e}")
        return False


def read_motor_register(ser, motor_id, register_address, num_bytes=2):
    """
    Read a register from a Feetech servo motor.
    
    Args:
        ser: Serial connection object
        motor_id: Motor ID to query (1-6)
        register_address: Register address to read
        num_bytes: Number of bytes to read (default 2 for 16-bit values)
        
    Returns:
        Register value as integer, or None if read fails
    """
    length = 4
    packet_without_checksum = [
        0xFF, 0xFF,
        motor_id,
        length,
        SCS_READ,
        register_address,
        num_bytes
    ]
    
    checksum = calculate_checksum(packet_without_checksum)
    packet = bytes(packet_without_checksum + [checksum])

    try:
        ser.write(packet)
        time.sleep(0.001)
        
        response = ser.read(5 + num_bytes + 1)  # Header(2) + ID + Len + Error + Data + Checksum
        
        if len(response) >= (5 + num_bytes) and response[0] == 0xFF and response[1] == 0xFF:
            if num_bytes == 2:
                value = response[5] | (response[6] << 8)
            else:
                value = response[5]
            return value
        
        return None
        
    except Exception as e:
        logger.error(f"Motor {motor_id}: Error reading register {register_address} - {e}")
        return None


def get_motor_position(ser, motor_id):
    """
    Read the current position from a Feetech servo motor.
    
    Args:
        ser: Serial connection object
        motor_id: Motor ID to query (1-6)
        
    Returns:
        Motor position as integer (0-4095), or None if read fails
    """
    return read_motor_register(ser, motor_id, SCS_PRESENT_POSITION_L, 2)


def get_motor_limits(ser, motor_id):
    """
    Read the position limits from a Feetech servo motor.
    
    Args:
        ser: Serial connection object
        motor_id: Motor ID to query (1-6)
        
    Returns:
        Tuple of (min_position, max_position), or (None, None) if read fails
    """
    min_pos = read_motor_register(ser, motor_id, SCS_MIN_POSITION_L, 2)
    time.sleep(0.005)
    max_pos = read_motor_register(ser, motor_id, SCS_MAX_POSITION_L, 2)
    return (min_pos, max_pos)


def set_motor_mode(ser, motor_id, mode=0):
    """
    Set the control mode for a Feetech servo motor.
    
    Args:
        ser: Serial connection object
        motor_id: Motor ID to configure (1-6)
        mode: 0=servo/position mode, 1=motor/speed mode, 3=step mode
        
    Returns:
        True if successful, False otherwise
    """
    length = 4
    packet_without_checksum = [
        0xFF, 0xFF,
        motor_id,
        length,
        SCS_WRITE,
        SCS_MODE,
        mode
    ]
    
    checksum = calculate_checksum(packet_without_checksum)
    packet = bytes(packet_without_checksum + [checksum])
    
    try:
        ser.write(packet)
        time.sleep(0.01)
        mode_name = {0: "Position", 1: "Speed", 3: "Step"}
        logger.info(f"Motor {motor_id}: Set to {mode_name.get(mode, 'Unknown')} mode")
        return True
    except Exception as e:
        logger.error(f"Motor {motor_id}: Error setting mode - {e}")
        return False


def set_motor_speed(ser, motor_id, speed=100):
    """
    Set the movement speed for a Feetech servo motor (0-4095).
    Lower = slower, 0 = maximum speed.
    
    Args:
        ser: Serial connection object
        motor_id: Motor ID to configure (1-6)
        speed: Speed value (0-4095), recommend 100-500 for smooth motion
        
    Returns:
        True if successful, False otherwise
    """
    speed_low = speed & 0xFF
    speed_high = (speed >> 8) & 0xFF
    
    length = 5
    packet_without_checksum = [
        0xFF, 0xFF,
        motor_id,
        length,
        SCS_WRITE,
        SCS_GOAL_SPEED_L,
        speed_low,
        speed_high
    ]
    
    checksum = calculate_checksum(packet_without_checksum)
    packet = bytes(packet_without_checksum + [checksum])
    
    try:
        ser.write(packet)
        time.sleep(0.005)
        logger.info(f"Motor {motor_id}: Speed set to {speed}")
        return True
    except Exception as e:
        logger.error(f"Motor {motor_id}: Error setting speed - {e}")
        return False


def enable_motor_torque(ser, motor_id):
    """
    Enable torque on a Feetech servo motor so it can move.
    
    Args:
        ser: Serial connection object
        motor_id: Motor ID to enable (1-6)
        
    Returns:
        True if successful, False otherwise
    """
    # Construct write command to enable torque
    length = 4  # Instruction + Address + Value + Checksum
    packet_without_checksum = [
        0xFF, 0xFF,
        motor_id,
        length,
        SCS_WRITE,
        SCS_TORQUE_ENABLE,
        1  # 1 = enable torque
    ]
    
    checksum = calculate_checksum(packet_without_checksum)
    packet = bytes(packet_without_checksum + [checksum])
    
    try:
        ser.write(packet)
        time.sleep(0.005)
        logger.info(f"Motor {motor_id}: Torque enabled")
        return True
    except Exception as e:
        logger.error(f"Motor {motor_id}: Error enabling torque - {e}")
        return False


@connect_python.main
def main(connect_client: connect_python.Client):
    """
    Main control loop - ready for new functionality.
    """
    ser = None
    
    try:
        # Open serial connection
        logger.info(f"Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Connection established successfully.")
        
        # TODO: Add your new control logic here
        logger.info("Ready for new functionality!")
        
    except serial.SerialException as e:
        logger.error(f"Failed to open serial port {SERIAL_PORT}: {e}")
        
    except KeyboardInterrupt:
        logger.info("Script stopped by user.")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        
    finally:
        if ser and ser.is_open:
            ser.close()
            logger.info("Serial connection closed.")


if __name__ == "__main__":
    main()

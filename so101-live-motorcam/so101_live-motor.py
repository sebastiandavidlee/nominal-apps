"""
SO-101 Robot Live Data Stream

This script connects to a SO-101 robot via serial communication using the Feetech
servo bus protocol. It continuously reads motor positions and streams them to the
Nominal Connect application for real-time visualization.

Hardware: SO-101 Robot with Feetech servo motors
Protocol: Feetech SCS (Serial Command System)
"""

import serial
import time
import traceback
import connect_python

# --- Configuration ---
SERIAL_PORT = "/dev/ttyACM1"  # Serial port for SO-101 connection
BAUD_RATE = 1_000_000          # Communication speed (1 Mbps)
MOTOR_IDS = [1, 2, 3, 4, 5, 6] # IDs of motors to monitor
TIMEOUT = 0.05                  # Serial read timeout in seconds
SAMPLE_RATE = 50                # Target sampling rate in Hz

# Feetech Protocol Constants
SCS_READ = 0x02                 # Read command instruction
SCS_PRESENT_POSITION_L = 56     # Register address for position (lower byte)

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
    # Format: [0xFF, 0xFF, ID, Length, Instruction, Address, ReadLength, Checksum]
    length = 4  # Instruction + Address + ReadLength + Checksum
    packet_without_checksum = [
        0xFF, 0xFF,                    # Header bytes
        motor_id,                      # Target motor ID
        length,                        # Packet length
        SCS_READ,                      # Read instruction
        SCS_PRESENT_POSITION_L,        # Position register address
        2                              # Number of bytes to read (16-bit position)
    ]
    
    checksum = calculate_checksum(packet_without_checksum)
    packet = bytes(packet_without_checksum + [checksum])

    try:
        ser.write(packet)
        time.sleep(0.001)  # Brief delay for motor to process and respond
        
        # Expected response: [0xFF, 0xFF, ID, Length, Error, PosL, PosH, Checksum]
        response = ser.read(8)
        
        if len(response) >= 8 and response[0] == 0xFF and response[1] == 0xFF:
            # Position is 16-bit little-endian (low byte first)
            position = response[5] | (response[6] << 8)
            return position
        
        # Invalid or incomplete response
        return None
        
    except Exception as e:
        logger.error(f"Motor {motor_id}: Error reading position - {e}")
        return None

@connect_python.main
def main(connect_client: connect_python.Client):
    """
    Main streaming loop.
    
    Connects to the SO-101 robot, reads motor positions at regular intervals,
    and streams the data to the Nominal Connect application for visualization.
    Runs continuously until stopped by the user or an error occurs.
    """
    ser = None
    
    try:
        # Open serial connection to SO-101
        logger.info(f"Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Connection established successfully.")
        
        # Clear any existing data in the stream
        connect_client.clear_stream("so101_motors")

        # Main data acquisition loop
        logger.info(f"Starting data acquisition loop at {SAMPLE_RATE} Hz...")
        loop_count = 0
        while True:
            timestamp = time.time()
            
            # Query all motors for their current positions
            positions = {
                f"motor_{motor_id}": get_motor_position(ser, motor_id) 
                for motor_id in MOTOR_IDS
            }
            
            # Filter out any motors that failed to respond
            valid_positions = {
                name: pos for name, pos in positions.items() 
                if pos is not None
            }

            # Log status every 50 iterations (~1 second at 50Hz)
            loop_count += 1
            if loop_count % 50 == 0:
                logger.info(f"Loop {loop_count}: Read {len(valid_positions)}/{len(MOTOR_IDS)} motors successfully")
                if valid_positions:
                    logger.debug(f"Positions: {valid_positions}")

            # Stream the data to the UI
            if valid_positions:
                channel_names = list(valid_positions.keys())
                channel_values = list(valid_positions.values())
                connect_client.stream(
                    "so101_motors", 
                    timestamp, 
                    names=channel_names, 
                    values=channel_values
                )
            else:
                logger.warning(f"No valid motor positions read at loop {loop_count}")
            
            # Maintain consistent sampling rate
            time.sleep(1.0 / SAMPLE_RATE)

    except serial.SerialException as e:
        logger.error(f"Failed to open serial port {SERIAL_PORT}: {e}")
        logger.error("Check that the device is connected and not in use by another program.")
        
    except KeyboardInterrupt:
        logger.info("Script stopped by user.")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        
    finally:
        # Clean up serial connection
        if ser and ser.is_open:
            ser.close()
            logger.info("Serial connection closed.")

if __name__ == "__main__":
    main()

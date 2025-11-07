"""
SO-101 Arm 1 Reading Check

Simple script to verify reading from Arm 1 motors.
Reads and displays motor positions continuously.
"""

import serial
import time
import connect_python
from feetech_interface import get_motor_position

# --- Configuration ---
SERIAL_PORT = "/dev/ttyACM1"  # Arm 1
BAUD_RATE = 1_000_000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
TIMEOUT = 0.05
UPDATE_RATE = 30.0  # Hz

logger = connect_python.get_logger(__name__)


@connect_python.main
def main(connect_client: connect_python.Client):
    """Read and stream motor positions from Arm 1."""
    ser = None
    
    try:
        # Connect
        logger.info(f"Connecting to Arm 1 at {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Connected!")
        
        # Clear stream
        connect_client.clear_stream("arm1_positions")
        
        logger.info("\nReading Arm 1 motor positions...")
        logger.info("Press Ctrl+C to stop.\n")
        
        iteration = 0
        
        while True:
            timestamp = time.time()
            
            # Read all motor positions
            positions = {}
            for motor_id in MOTOR_IDS:
                pos = get_motor_position(ser, motor_id)
                if pos is not None:
                    positions[motor_id] = pos
            
            # Stream data
            if len(positions) == len(MOTOR_IDS):
                connect_client.stream(
                    "arm1_positions",
                    timestamp,
                    names=[f"motor_{i}" for i in MOTOR_IDS],
                    values=[positions[i] for i in MOTOR_IDS]
                )
            
            # Log every second
            iteration += 1
            if iteration % int(UPDATE_RATE) == 0:
                logger.info(f"Arm 1 positions: {positions}")
            
            time.sleep(1.0 / UPDATE_RATE)
        
    except serial.SerialException as e:
        logger.error(f"Serial connection error: {e}")
        
    except KeyboardInterrupt:
        logger.info("\nStopped by user.")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        if ser and ser.is_open:
            ser.close()
            logger.info("Serial connection closed.")


if __name__ == "__main__":
    main()

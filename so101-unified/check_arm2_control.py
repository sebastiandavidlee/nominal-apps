"""
SO-101 Arm 2 Control Check

Simple script to verify commanding Arm 2 motors.
Sends hardcoded positions to test control functionality.
"""

import serial
import time
import connect_python
from feetech_interface import (
    get_motor_position,
    set_motor_position,
    set_motor_mode,
    set_motor_speed,
    enable_motor_torque
)

# --- Configuration ---
SERIAL_PORT = "/dev/ttyACM0"  # Arm 2
BAUD_RATE = 1_000_000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
TIMEOUT = 0.05

# Test positions - UPDATE THESE to test different configurations
TEST_POSITIONS = {
    1: 1700,
    2: 1200,
    3: 2600,
    4: 2500,
    5: 2100,
    6: 2100
}

logger = connect_python.get_logger(__name__)


@connect_python.main
def main(connect_client: connect_python.Client):
    """Test commanding Arm 2 with hardcoded positions."""
    ser = None
    
    try:
        # Connect
        logger.info(f"Connecting to Arm 2 at {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Connected!")
        
        # Read current positions
        logger.info("\nCurrent positions:")
        for motor_id in MOTOR_IDS:
            pos = get_motor_position(ser, motor_id)
            if pos is not None:
                logger.info(f"  Motor {motor_id}: {pos}")
        
        # Configure motors
        logger.info("\nConfiguring motors for position control...")
        for motor_id in MOTOR_IDS:
            set_motor_mode(ser, motor_id, mode=0)  # Position control
            set_motor_speed(ser, motor_id, speed=100)  # Fast movement
            enable_motor_torque(ser, motor_id)
        
        # Send test positions
        logger.info("\nMoving to TEST positions...")
        for motor_id in MOTOR_IDS:
            target = TEST_POSITIONS[motor_id]
            logger.info(f"  Motor {motor_id} → {target}")
            set_motor_position(ser, motor_id, target)
        
        # Wait for movement
        logger.info("\nWaiting for movement to complete...")
        time.sleep(2.0)
        
        # Verify final positions
        logger.info("\nFinal positions:")
        for motor_id in MOTOR_IDS:
            pos = get_motor_position(ser, motor_id)
            target = TEST_POSITIONS[motor_id]
            error = abs(target - pos) if pos is not None else None
            if pos is not None:
                logger.info(f"  Motor {motor_id}: {pos} (target: {target}, error: {error})")
        
        logger.info("\n✓ Control check complete!")
        
    except serial.SerialException as e:
        logger.error(f"Serial connection error: {e}")
        
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

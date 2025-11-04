"""
SO-101 Motor Position Finder

This script helps you find and set safe home positions for each motor.
It reads the current positions and lets you manually adjust them to find
good reference points.

Usage:
1. Position your robot arm in a safe, comfortable pose
2. Run this script
3. It will show you the current positions - save these as HOME_POSITIONS
"""

import serial
import time
import connect_python

# --- Configuration ---
SERIAL_PORT = "/dev/ttyACM0"  # Serial port for SO-101 connection
BAUD_RATE = 1_000_000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
TIMEOUT = 0.05

# Feetech Protocol Constants
SCS_READ = 0x02
SCS_PRESENT_POSITION_L = 56

logger = connect_python.get_logger(__name__)


def calculate_checksum(packet):
    total = sum(packet[2:])
    return ~total & 0xFF


def get_motor_position(ser, motor_id):
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
    Continuously read and display motor positions to help find home positions.
    """
    ser = None
    
    try:
        logger.info(f"Connecting to {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Connection established.\n")
        
        logger.info("=" * 60)
        logger.info("MOTOR POSITION FINDER")
        logger.info("=" * 60)
        logger.info("Position your robot in a safe, comfortable pose.")
        logger.info("The current positions will be displayed continuously.")
        logger.info("Press Ctrl+C when ready to use these as HOME_POSITIONS.\n")
        
        time.sleep(2)
        
        # Read positions continuously
        count = 0
        while True:
            count += 1
            
            # Read all motor positions
            positions = {}
            all_valid = True
            for motor_id in MOTOR_IDS:
                pos = get_motor_position(ser, motor_id)
                if pos is not None:
                    positions[motor_id] = pos
                else:
                    all_valid = False
                    break
            
            # Display every 10th reading (2 times per second at 20Hz)
            if all_valid and count % 10 == 0:
                logger.info(f"\n--- Current Positions (reading #{count}) ---")
                for motor_id in MOTOR_IDS:
                    logger.info(f"Motor {motor_id}: {positions[motor_id]}")
                
                # Show as Python dict format
                logger.info("\nCopy this to your script as HOME_POSITIONS:")
                logger.info("HOME_POSITIONS = {")
                for motor_id in MOTOR_IDS:
                    logger.info(f"    {motor_id}: {positions[motor_id]},")
                logger.info("}")
            
            time.sleep(0.05)  # 20Hz update rate
            
    except KeyboardInterrupt:
        logger.info("\n\n" + "=" * 60)
        logger.info("FINAL HOME POSITIONS:")
        logger.info("=" * 60)
        
        # Read one final time
        final_positions = {}
        for motor_id in MOTOR_IDS:
            pos = get_motor_position(ser, motor_id)
            if pos is not None:
                final_positions[motor_id] = pos
        
        logger.info("\nHOME_POSITIONS = {")
        for motor_id in MOTOR_IDS:
            if motor_id in final_positions:
                logger.info(f"    {motor_id}: {final_positions[motor_id]},")
        logger.info("}")
        logger.info("\n✅ Copy the above dictionary into your trajectory script!")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        
    finally:
        if ser and ser.is_open:
            ser.close()
            logger.info("\nSerial connection closed.")


if __name__ == "__main__":
    main()

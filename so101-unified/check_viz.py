"""
SO-101 3D Visualization Check

Simple script to verify 3D visualization of arm.
Reads motor positions and displays in 3D using URDF model.
Converts encoder values (0-4095) to joint angles (radians).
"""

import serial
import time
import math
import connect_python
from feetech_interface import get_motor_position, ENCODER_MAX

# --- Configuration ---
SERIAL_PORT = "/dev/ttyACM0"  # Change to ACM0 (Arm 2) or ACM1 (Arm 1)
BAUD_RATE = 1_000_000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
TIMEOUT = 0.05
UPDATE_RATE = 30.0  # Hz

TWO_PI = 2 * math.pi

# Home positions (center points for each motor) - encoder values 0-4095
HOME_POSITIONS = {
    1: 2048,
    2: 2048,
    3: 2048,
    4: 2048,
    5: 2048,
    6: 2048,
}

# Joint encoder offsets (tune these to match simulation)
JOINT_ENCODER_OFFSETS = {
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0,
}

# Joint angle multipliers (use -1 to invert direction)
JOINT_MULTIPLIERS = {
    1: 1.0,
    2: 1.0,
    3: 1.0,
    4: 1.0,
    5: 1.0,
    6: 1.0,
}

logger = connect_python.get_logger(__name__)


def encoder_to_radians(encoder_value, home_position, motor_id):
    """Convert encoder position (0-4095) to radians relative to home."""
    # Apply encoder offset
    adjusted_encoder = encoder_value + JOINT_ENCODER_OFFSETS[motor_id]
    
    # Wrap to 0-4095 range
    adjusted_encoder = adjusted_encoder % ENCODER_MAX
    
    # Calculate offset from home
    offset = adjusted_encoder - home_position
    
    # Wrap to -2048 to +2047 range
    if offset > ENCODER_MAX / 2:
        offset -= ENCODER_MAX
    elif offset < -ENCODER_MAX / 2:
        offset += ENCODER_MAX
    
    # Convert to radians
    radians = (offset / ENCODER_MAX) * TWO_PI
    
    # Apply multiplier
    radians = radians * JOINT_MULTIPLIERS[motor_id]
    
    return radians


@connect_python.main
def main(connect_client: connect_python.Client):
    """Read motor positions and stream for 3D visualization."""
    ser = None
    
    try:
        # Connect
        logger.info(f"Connecting to arm at {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Connected!")
        
        # Clear streams
        connect_client.clear_stream("pose")
        connect_client.clear_stream("motor_positions")
        
        # Joint names matching URDF
        joint_names = [
            "shoulder_pan_joint",
            "shoulder_lift_joint",
            "elbow_joint",
            "wrist_1_joint",
            "wrist_2_joint",
            "wrist_3_joint"
        ]
        
        motor_channels = ["motor_1", "motor_2", "motor_3", "motor_4", "motor_5", "motor_6"]
        
        logger.info("\nStreaming 3D visualization...")
        logger.info("Press Ctrl+C to stop.\n")
        
        iteration = 0
        
        while True:
            timestamp = time.time()
            
            # Read all motor positions
            motor_positions = []
            joint_angles = []
            
            for motor_id in MOTOR_IDS:
                pos = get_motor_position(ser, motor_id)
                if pos is not None:
                    motor_positions.append(pos)
                    angle = encoder_to_radians(pos, HOME_POSITIONS[motor_id], motor_id)
                    joint_angles.append(angle)
                else:
                    motor_positions.append(0)
                    joint_angles.append(0.0)
            
            # Stream joint angles for URDF visualization
            connect_client.stream(
                "pose",
                timestamp,
                names=joint_names,
                values=joint_angles
            )
            
            # Stream motor positions (encoder values)
            connect_client.stream(
                "motor_positions",
                timestamp,
                names=motor_channels,
                values=motor_positions
            )
            
            # Log every second
            iteration += 1
            if iteration % int(UPDATE_RATE) == 0:
                logger.info("Motor positions:")
                for i, (name, angle, enc_pos) in enumerate(zip(joint_names, joint_angles, motor_positions), 1):
                    logger.info(f"  Motor {i} ({name}): encoder={enc_pos}, angle={angle:+.3f} rad")
            
            time.sleep(1.0 / UPDATE_RATE)
        
    except serial.SerialException as e:
        logger.error(f"Serial connection error: {e}")
        
    except KeyboardInterrupt:
        logger.info("\nVisualization stopped by user.")
        
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

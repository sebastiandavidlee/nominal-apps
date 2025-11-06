"""
SO-101 Robot Arm 3D Visualization

Reads motor positions from SO-101 arm and visualizes in 3D using URDF model.
Converts motor encoder values (0-4095) to joint angles (radians).
"""

import serial
import time
import math
import connect_python

# --- Configuration ---
SERIAL_PORT = "/dev/ttyACM1"  # Change to ACM0 or ACM1 depending on which arm
BAUD_RATE = 1_000_000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
TIMEOUT = 0.05
UPDATE_RATE = 30.0  # Hz

# Encoder to radian conversion (12-bit encoder: 0-4095 maps to 0-2π)
ENCODER_MAX = 4095
TWO_PI = 2 * math.pi

# Home positions (center points for each motor) - encoder values 0-4095
# These define the "zero" position for each joint
HOME_POSITIONS = {
    1: 2048,  # shoulder_pan_joint - update with actual home position
    2: 2048,  # shoulder_lift_joint
    3: 2048,  # elbow_joint
    4: 2048,  # wrist_1_joint
    5: 2048,  # wrist_2_joint
    6: 2048,  # wrist_3_joint
}

# Joint encoder offsets (0-4095) - tune these to match simulation
# Add these to the encoder reading before converting to radians
# Example: if joint is 500 ticks off, set offset to 500 or -500
JOINT_ENCODER_OFFSETS = {
    1: 0,  # shoulder_pan_joint
    2: 0,  # shoulder_lift_joint
    3: 0,  # elbow_joint
    4: 0,  # wrist_1_joint
    5: 0,  # wrist_2_joint
    6: 0,  # wrist_3_joint
}

# Joint angle multipliers - flip direction if needed (-1 to invert)
JOINT_MULTIPLIERS = {
    1: 1.0,  # shoulder_pan_joint
    2: 1.0,  # shoulder_lift_joint
    3: 1.0,  # elbow_joint
    4: 1.0,  # wrist_1_joint
    5: 1.0,  # wrist_2_joint
    6: 1.0,  # wrist_3_joint
}

# Feetech Protocol
SCS_READ = 0x02
SCS_PRESENT_POSITION_L = 56

logger = connect_python.get_logger(__name__)


def calculate_checksum(packet):
    total = sum(packet[2:])
    return ~total & 0xFF


def read_motor_register(ser, motor_id, register_address, num_bytes=2):
    """Read a register from a Feetech servo motor."""
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


def encoder_to_radians(encoder_value, home_position, motor_id):
    """
    Convert encoder position (0-4095) to radians relative to home.
    Centers the range around home position and applies offset/multiplier.
    """
    # Apply encoder offset first (before any conversion)
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
    
    # Convert to radians: offset / max_range * 2π
    radians = (offset / ENCODER_MAX) * TWO_PI
    
    # Apply multiplier (for direction inversion)
    radians = radians * JOINT_MULTIPLIERS[motor_id]
    
    return radians


@connect_python.main
def main(connect_client: connect_python.Client):
    """
    Main visualization loop.
    Reads motor positions and streams as joint angles for URDF visualization.
    """
    ser = None
    
    try:
        # Connect to robot
        logger.info(f"Connecting to SO-101 at {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Connected!")
        
        # Clear stream
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
        
        # Motor position channel names
        motor_channels = ["motor_1", "motor_2", "motor_3", "motor_4", "motor_5", "motor_6"]
        
        logger.info("Streaming SO-101 visualization...")
        logger.info("Press Ctrl+C to stop.\n")
        
        # Log offset configuration
        logger.info("=== Joint Configuration ===")
        for i, joint_name in enumerate(joint_names, 1):
            logger.info(f"Motor {i} ({joint_name}):")
            logger.info(f"  Home: {HOME_POSITIONS[i]}, Encoder Offset: {JOINT_ENCODER_OFFSETS[i]}, Multiplier: {JOINT_MULTIPLIERS[i]}")
        logger.info("")
        
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
                    # Convert to radians with offset and multiplier
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
            
            # Print debug info every 30 iterations (~1 second)
            iteration += 1
            if iteration % 30 == 0:
                logger.info("Current motor positions:")
                for i, (name, angle, enc_pos) in enumerate(zip(joint_names, joint_angles, motor_positions), 1):
                    logger.info(f"  Motor {i} ({name}): encoder={enc_pos}, angle={angle:+.3f} rad")
            
            time.sleep(1.0 / UPDATE_RATE)
        
    except serial.SerialException as e:
        logger.error(f"Serial connection error: {e}")
        
    except KeyboardInterrupt:
        logger.info("\nVisualization stopped by user.")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        if ser and ser.is_open:
            ser.close()
            logger.info("Serial connection closed.")


if __name__ == "__main__":
    main()

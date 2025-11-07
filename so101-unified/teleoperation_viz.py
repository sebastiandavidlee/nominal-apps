"""
SO-101 Robot Arm Teleoperation with Full Visualization

Complete teleoperation system with:
- Leader-follower motor control (Arm 1 → Arm 2)
- 3D URDF visualization of follower arm
- Motor position plots
- Dual camera feeds

This is the all-in-one script for full teleoperation experience.
"""

import serial
import cv2
import time
import math
import traceback
import connect_python
from feetech_interface import (
    get_motor_position,
    set_motor_position,
    set_motor_mode,
    set_motor_speed,
    enable_motor_torque,
    ENCODER_MAX
)

# --- Serial Configuration ---
LEADER_PORT = "/dev/ttyACM1"    # Arm 1 - we READ from this
FOLLOWER_PORT = "/dev/ttyACM0"  # Arm 2 - we WRITE to this
BAUD_RATE = 1_000_000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
SERIAL_TIMEOUT = 0.05

# --- Camera Configuration ---
CAMERA_1_INDEX = 0
CAMERA_2_INDEX = 2
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# --- Update Rates ---
CONTROL_RATE = 50.0  # Hz - teleoperation control loop
CAMERA_RATE = 30.0   # Hz - camera streaming

# --- Visualization Configuration ---
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


def initialize_camera(camera_index, width, height):
    """Initialize a camera with specified resolution."""
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logger.error(f"Failed to open camera {camera_index}")
            return None
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
        
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f"Camera {camera_index} initialized: {actual_width}x{actual_height}")
        
        return cap
        
    except Exception as e:
        logger.error(f"Error initializing camera {camera_index}: {e}")
        return None


def encoder_to_radians(encoder_value, home_position, motor_id):
    """Convert encoder position (0-4095) to radians relative to home."""
    adjusted_encoder = encoder_value + JOINT_ENCODER_OFFSETS[motor_id]
    adjusted_encoder = adjusted_encoder % ENCODER_MAX
    
    offset = adjusted_encoder - home_position
    
    if offset > ENCODER_MAX / 2:
        offset -= ENCODER_MAX
    elif offset < -ENCODER_MAX / 2:
        offset += ENCODER_MAX
    
    radians = (offset / ENCODER_MAX) * TWO_PI
    radians = radians * JOINT_MULTIPLIERS[motor_id]
    
    return radians


@connect_python.main
def main(connect_client: connect_python.Client):
    """
    Main teleoperation loop with full visualization.
    
    Combines motor control, 3D visualization, and camera feeds.
    """
    ser_leader = None
    ser_follower = None
    cap1 = None
    cap2 = None
    
    try:
        # ========== SERIAL CONNECTION ==========
        logger.info(f"Connecting to LEADER arm at {LEADER_PORT}...")
        ser_leader = serial.Serial(LEADER_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
        logger.info("Leader connected!")
        
        logger.info(f"Connecting to FOLLOWER arm at {FOLLOWER_PORT}...")
        ser_follower = serial.Serial(FOLLOWER_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
        logger.info("Follower connected!")
        
        # Configure follower motors
        logger.info("\nConfiguring follower arm motors...")
        for motor_id in MOTOR_IDS:
            set_motor_mode(ser_follower, motor_id, mode=0)
            set_motor_speed(ser_follower, motor_id, speed=0)
            enable_motor_torque(ser_follower, motor_id)
        logger.info("Follower arm ready!")
        
        # ========== CAMERA INITIALIZATION ==========
        logger.info("\nInitializing cameras...")
        cap1 = initialize_camera(CAMERA_1_INDEX, FRAME_WIDTH, FRAME_HEIGHT)
        cap2 = initialize_camera(CAMERA_2_INDEX, FRAME_WIDTH, FRAME_HEIGHT)
        
        if cap1 is None:
            logger.warning(f"Camera {CAMERA_1_INDEX} unavailable")
        if cap2 is None:
            logger.warning(f"Camera {CAMERA_2_INDEX} unavailable")
        
        # ========== CLEAR STREAMS ==========
        connect_client.clear_stream("leader_positions")
        connect_client.clear_stream("follower_commands")
        connect_client.clear_stream("pose")
        
        # Joint names matching URDF
        joint_names = [
            "shoulder_pan_joint",
            "shoulder_lift_joint",
            "elbow_joint",
            "wrist_1_joint",
            "wrist_2_joint",
            "wrist_3_joint"
        ]
        
        logger.info("\n🤖 FULL TELEOPERATION ACTIVE!")
        logger.info("Move the leader arm (ACM1) to control follower (ACM0)")
        logger.info("Press Ctrl+C to stop.\n")
        
        loop_count = 0
        camera_frame_count = 0
        last_camera_time = time.time()
        
        # ========== MAIN LOOP ==========
        while True:
            timestamp = time.time()
            loop_count += 1
            
            # --- MOTOR CONTROL ---
            leader_positions = {}
            for motor_id in MOTOR_IDS:
                pos = get_motor_position(ser_leader, motor_id)
                if pos is not None:
                    leader_positions[motor_id] = pos
            
            # Command follower to match leader
            for motor_id in MOTOR_IDS:
                if motor_id in leader_positions:
                    set_motor_position(ser_follower, motor_id, leader_positions[motor_id])
            
            # --- STREAM MOTOR DATA ---
            if len(leader_positions) == len(MOTOR_IDS):
                # Stream leader positions
                connect_client.stream(
                    "leader_positions",
                    timestamp,
                    names=[f"motor_{i}" for i in MOTOR_IDS],
                    values=[leader_positions[i] for i in MOTOR_IDS]
                )
                
                # Stream follower commands
                connect_client.stream(
                    "follower_commands",
                    timestamp,
                    names=[f"motor_{i}" for i in MOTOR_IDS],
                    values=[leader_positions[i] for i in MOTOR_IDS]
                )
                
                # --- 3D VISUALIZATION ---
                # Convert follower positions to joint angles for URDF
                joint_angles = []
                for motor_id in MOTOR_IDS:
                    pos = leader_positions[motor_id]  # Follower mirrors leader
                    angle = encoder_to_radians(pos, HOME_POSITIONS[motor_id], motor_id)
                    joint_angles.append(angle)
                
                connect_client.stream(
                    "pose",
                    timestamp,
                    names=joint_names,
                    values=joint_angles
                )
            
            # --- CAMERA CAPTURE ---
            # Run at camera rate (30 FPS) instead of control rate (50 FPS)
            if time.time() - last_camera_time >= (1.0 / CAMERA_RATE):
                last_camera_time = time.time()
                camera_frame_count += 1
                
                if cap1 is not None:
                    ret1, frame1 = cap1.read()
                    if ret1:
                        frame1_rgb = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
                        rgb_data = frame1_rgb.flatten()
                        connect_client.stream_rgb("camera_1", timestamp, frame1.shape[1], rgb_data)
                
                if cap2 is not None:
                    ret2, frame2 = cap2.read()
                    if ret2:
                        frame2_rgb = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
                        rgb_data = frame2_rgb.flatten()
                        connect_client.stream_rgb("camera_2", timestamp, frame2.shape[1], rgb_data)
            
            # --- LOGGING ---
            if loop_count % (int(CONTROL_RATE) * 2) == 0:
                logger.info(f"Teleoperation active - Leader positions: {leader_positions}")
                if camera_frame_count > 0:
                    logger.info(f"Camera frames streamed: {camera_frame_count}")
            
            # Wait for next control cycle
            time.sleep(1.0 / CONTROL_RATE)
        
    except serial.SerialException as e:
        logger.error(f"Serial connection error: {e}")
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Teleoperation stopped by user.")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        
    finally:
        # Clean up serial connections
        if ser_leader and ser_leader.is_open:
            ser_leader.close()
            logger.info("Leader serial connection closed.")
        if ser_follower and ser_follower.is_open:
            ser_follower.close()
            logger.info("Follower serial connection closed.")
        
        # Clean up cameras
        if cap1 is not None:
            cap1.release()
            logger.info(f"Camera {CAMERA_1_INDEX} released.")
        if cap2 is not None:
            cap2.release()
            logger.info(f"Camera {CAMERA_2_INDEX} released.")
        
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

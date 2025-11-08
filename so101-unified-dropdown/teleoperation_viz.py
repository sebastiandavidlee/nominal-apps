"""
SO-101 Robot Teleoperation with Visualization (Dropdown Version)

Leader-follower control with configurable visualization arm via dropdown.
Configuration done via dropdown menu in app.connect.
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

# --- Configuration ---
LEADER_PORT = "/dev/ttyACM1"
FOLLOWER_PORT = "/dev/ttyACM0"
BAUD_RATE = 1_000_000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
SERIAL_TIMEOUT = 0.05

CAMERA_1_INDEX = 0
CAMERA_2_INDEX = 2
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

CONTROL_RATE = 50.0
CAMERA_RATE = 30.0

TWO_PI = 2 * math.pi

HOME_POSITIONS = {1: 2048, 2: 2048, 3: 2048, 4: 2048, 5: 2048, 6: 2048}
JOINT_ENCODER_OFFSETS = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
JOINT_MULTIPLIERS = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0}

logger = connect_python.get_logger(__name__)


def initialize_camera(camera_index, width, height):
    """Initialize a camera with specified resolution."""
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
        logger.info(f"Camera {camera_index} initialized")
        return cap
    except Exception as e:
        logger.error(f"Error initializing camera {camera_index}: {e}")
        return None


def encoder_to_radians(encoder_value, home_position, motor_id):
    """Convert encoder position to radians."""
    adjusted = (encoder_value + JOINT_ENCODER_OFFSETS[motor_id]) % ENCODER_MAX
    offset = adjusted - home_position
    if offset > ENCODER_MAX / 2:
        offset -= ENCODER_MAX
    elif offset < -ENCODER_MAX / 2:
        offset += ENCODER_MAX
    return (offset / ENCODER_MAX) * TWO_PI * JOINT_MULTIPLIERS[motor_id]


@connect_python.main
def main(connect_client: connect_python.Client):
    """Main teleoperation loop with dropdown visualization."""
    
    # Read dropdown value using get_value()
    visualize_port = connect_client.get_value("visualize_arm_port", "/dev/ttyACM0")
    
    logger.info(f"🎯 Visualization Port: {visualize_port}")
    logger.info(f"📡 Leader: {LEADER_PORT}, Follower: {FOLLOWER_PORT}")
    
    visualize_leader = (visualize_port == LEADER_PORT)
    arm_name = "Leader (Arm 1)" if visualize_leader else "Follower (Arm 2)"
    logger.info(f"📊 Displaying: {arm_name}")
    
    ser_leader = None
    ser_follower = None
    cap1 = None
    cap2 = None
    
    try:
        logger.info(f"\nConnecting to arms...")
        ser_leader = serial.Serial(LEADER_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
        ser_follower = serial.Serial(FOLLOWER_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
        logger.info("✓ Arms connected!")
        
        logger.info("Configuring follower motors...")
        for motor_id in MOTOR_IDS:
            set_motor_mode(ser_follower, motor_id, mode=0)
            set_motor_speed(ser_follower, motor_id, speed=0)
            enable_motor_torque(ser_follower, motor_id)
        logger.info("✓ Follower ready!")
        
        logger.info("Initializing cameras...")
        cap1 = initialize_camera(CAMERA_1_INDEX, FRAME_WIDTH, FRAME_HEIGHT)
        cap2 = initialize_camera(CAMERA_2_INDEX, FRAME_WIDTH, FRAME_HEIGHT)
        
        connect_client.clear_stream("motor_positions")
        connect_client.clear_stream("pose")
        
        joint_names = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
                      "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
        
        logger.info("\n🤖 TELEOPERATION ACTIVE!")
        
        loop_count = 0
        last_camera_time = time.time()
        viz_serial = ser_leader if visualize_leader else ser_follower
        
        while True:
            timestamp = time.time()
            loop_count += 1
            
            # Read leader and command follower
            leader_positions = {}
            for motor_id in MOTOR_IDS:
                pos = get_motor_position(ser_leader, motor_id)
                if pos is not None:
                    leader_positions[motor_id] = pos
                    set_motor_position(ser_follower, motor_id, pos)
            
            # Read visualization arm
            viz_positions = {}
            for motor_id in MOTOR_IDS:
                pos = get_motor_position(viz_serial, motor_id)
                if pos is not None:
                    viz_positions[motor_id] = pos
            
            # Stream motor positions (only visualized arm)
            if len(viz_positions) == len(MOTOR_IDS):
                connect_client.stream(
                    "motor_positions",
                    timestamp,
                    names=[f"motor_{i}" for i in MOTOR_IDS],
                    values=[viz_positions[i] for i in MOTOR_IDS]
                )
                
                # 3D visualization
                joint_angles = [encoder_to_radians(viz_positions[i], HOME_POSITIONS[i], i) 
                               for i in MOTOR_IDS]
                connect_client.stream("pose", timestamp, names=joint_names, values=joint_angles)
            
            # Camera capture
            if time.time() - last_camera_time >= (1.0 / CAMERA_RATE):
                last_camera_time = time.time()
                
                if cap1 is not None:
                    ret1, frame1 = cap1.read()
                    if ret1:
                        frame1_rgb = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
                        connect_client.stream_rgb("camera_1", timestamp, frame1.shape[1], frame1_rgb.flatten())
                
                if cap2 is not None:
                    ret2, frame2 = cap2.read()
                    if ret2:
                        frame2_rgb = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
                        connect_client.stream_rgb("camera_2", timestamp, frame2.shape[1], frame2_rgb.flatten())
            
            # Logging
            if loop_count % (int(CONTROL_RATE) * 2) == 0:
                logger.info(f"Leader: {leader_positions}, Displaying {arm_name}: {viz_positions}")
            
            time.sleep(1.0 / CONTROL_RATE)
        
    except serial.SerialException as e:
        logger.error(f"Serial error: {e}")
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user.")
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
    finally:
        if ser_leader and ser_leader.is_open:
            ser_leader.close()
        if ser_follower and ser_follower.is_open:
            ser_follower.close()
        if cap1:
            cap1.release()
        if cap2:
            cap2.release()
        cv2.destroyAllWindows()
        logger.info("✓ Cleanup complete")


if __name__ == "__main__":
    main()

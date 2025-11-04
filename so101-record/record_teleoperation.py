"""
SO-101 Robot Arm Teleoperation with Data Recording

This script combines teleoperation with data recording capabilities.
Press 'r' to start/stop recording episodes.

Recorded data includes:
- Leader arm motor positions (ACM1)
- Follower arm motor positions (ACM0)
- Camera frames from both cameras
- Timestamps for synchronization

Data is saved in HDF5 format compatible with robotics datasets.
"""

import serial
import time
import traceback
import connect_python
import cv2
import numpy as np
import h5py
import os
from pathlib import Path
from datetime import datetime

# --- Configuration ---
LEADER_PORT = "/dev/ttyACM1"    # Arm 1 - we READ from this
FOLLOWER_PORT = "/dev/ttyACM0"  # Arm 2 - we WRITE to this
BAUD_RATE = 1_000_000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
TIMEOUT = 0.05

CAMERA_1_ID = "/dev/video0"
CAMERA_2_ID = "/dev/video2"
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

UPDATE_RATE = 50.0  # Hz - teleoperation update rate
RECORDING_FPS = 30  # Hz - data recording rate (limited by cameras)

DATA_DIR = Path("./data/episodes")

# Feetech Protocol
SCS_WRITE = 0x03
SCS_READ = 0x02
SCS_GOAL_POSITION_L = 42
SCS_PRESENT_POSITION_L = 56
SCS_MODE = 33
SCS_GOAL_SPEED_L = 46
SCS_TORQUE_ENABLE = 40

logger = connect_python.get_logger(__name__)


# --- Motor Control Functions ---

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
    time.sleep(0.001)
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


# --- Camera Functions ---

def initialize_camera(device_path, width=640, height=480):
    """Initialize a camera with specified resolution."""
    cap = cv2.VideoCapture(device_path)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    return cap


# --- Recording Functions ---

class EpisodeRecorder:
    """Handles recording of robot demonstration episodes."""
    
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.is_recording = False
        self.current_episode_num = self._get_next_episode_num()
        self.episode_file = None
        self.frame_count = 0
        
        # HDF5 datasets
        self.timestamps = []
        self.leader_positions = []
        self.follower_positions = []
        self.camera_1_frames = []
        self.camera_2_frames = []
    
    def _get_next_episode_num(self):
        """Find the next available episode number."""
        existing = list(self.data_dir.glob("episode_*.hdf5"))
        if not existing:
            return 0
        numbers = [int(f.stem.split("_")[1]) for f in existing]
        return max(numbers) + 1
    
    def start_recording(self):
        """Start a new recording episode."""
        if self.is_recording:
            logger.warning("Already recording!")
            return
        
        self.is_recording = True
        self.frame_count = 0
        self.timestamps = []
        self.leader_positions = []
        self.follower_positions = []
        self.camera_1_frames = []
        self.camera_2_frames = []
        
        logger.info(f"🔴 RECORDING Episode {self.current_episode_num}")
    
    def add_frame(self, timestamp, leader_pos, follower_pos, cam1_frame, cam2_frame):
        """Add a frame of data to the current recording."""
        if not self.is_recording:
            return
        
        self.timestamps.append(timestamp)
        self.leader_positions.append(leader_pos)
        self.follower_positions.append(follower_pos)
        self.camera_1_frames.append(cam1_frame)
        self.camera_2_frames.append(cam2_frame)
        self.frame_count += 1
    
    def stop_recording(self):
        """Stop recording and save the episode to disk."""
        if not self.is_recording:
            logger.warning("Not currently recording!")
            return
        
        self.is_recording = False
        
        if self.frame_count == 0:
            logger.warning("No frames recorded, not saving.")
            return
        
        # Save to HDF5
        filename = self.data_dir / f"episode_{self.current_episode_num:06d}.hdf5"
        logger.info(f"💾 Saving episode to {filename}...")
        
        with h5py.File(filename, 'w') as f:
            # Metadata
            f.attrs['episode_num'] = self.current_episode_num
            f.attrs['frame_count'] = self.frame_count
            f.attrs['duration'] = self.timestamps[-1] - self.timestamps[0]
            f.attrs['date'] = datetime.now().isoformat()
            f.attrs['fps'] = RECORDING_FPS
            
            # Create datasets
            f.create_dataset('timestamps', data=np.array(self.timestamps))
            f.create_dataset('leader_positions', data=np.array(self.leader_positions))
            f.create_dataset('follower_positions', data=np.array(self.follower_positions))
            f.create_dataset('camera_1', data=np.array(self.camera_1_frames), compression='gzip')
            f.create_dataset('camera_2', data=np.array(self.camera_2_frames), compression='gzip')
        
        logger.info(f"✅ Episode {self.current_episode_num} saved! ({self.frame_count} frames)")
        
        # Prepare for next episode
        self.current_episode_num += 1


@connect_python.main
def main(connect_client: connect_python.Client):
    """
    Main teleoperation + recording loop.
    
    Press 'r' in the terminal to start/stop recording.
    Move leader arm (ACM1) to control follower arm (ACM0).
    """
    ser_leader = None
    ser_follower = None
    cam1 = None
    cam2 = None
    
    try:
        # Connect to both arms
        logger.info(f"Connecting to LEADER arm at {LEADER_PORT}...")
        ser_leader = serial.Serial(LEADER_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Leader connected!")
        
        logger.info(f"Connecting to FOLLOWER arm at {FOLLOWER_PORT}...")
        ser_follower = serial.Serial(FOLLOWER_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Follower connected!")
        
        # Configure follower motors
        logger.info("\nConfiguring follower arm motors...")
        for motor_id in MOTOR_IDS:
            set_motor_mode(ser_follower, motor_id, mode=0)
            set_motor_speed(ser_follower, motor_id, speed=0)
            enable_motor_torque(ser_follower, motor_id)
        logger.info("Follower arm ready!")
        
        # Initialize cameras
        logger.info("\nInitializing cameras...")
        cam1 = initialize_camera(CAMERA_1_ID, CAMERA_WIDTH, CAMERA_HEIGHT)
        cam2 = initialize_camera(CAMERA_2_ID, CAMERA_WIDTH, CAMERA_HEIGHT)
        logger.info("Cameras ready!")
        
        # Initialize recorder
        recorder = EpisodeRecorder(DATA_DIR)
        logger.info(f"Recorder ready. Next episode: {recorder.current_episode_num}")
        
        # Clear streams
        connect_client.clear_stream("leader_motors")
        connect_client.clear_stream("follower_motors")
        connect_client.clear_stream("camera_1")
        connect_client.clear_stream("camera_2")
        connect_client.clear_stream("recording_status")
        
        logger.info("\n" + "="*60)
        logger.info("🤖 Teleoperation + Recording ACTIVE!")
        logger.info("="*60)
        logger.info("Controls:")
        logger.info("  Type 's' + Enter: START recording episode")
        logger.info("  Type 'x' + Enter: STOP recording and save episode")
        logger.info("  Press Ctrl+C: Exit session")
        logger.info("="*60 + "\n")
        logger.info("TIP: Keep this terminal visible to see recording status!")
        logger.info("")
        
        last_recording_time = time.time()
        
        # Setup non-blocking input handling
        import sys
        import select
        
        def check_for_input():
            """Check if there's keyboard input available (non-blocking)."""
            if select.select([sys.stdin], [], [], 0)[0]:
                line = sys.stdin.readline().strip().lower()
                if line == 's':
                    recorder.start_recording()
                elif line == 'x':
                    recorder.stop_recording()
                return line
            return None
        
        # Main loop
        while True:
            timestamp = time.time()
            
            # Check for keyboard commands
            check_for_input()
            
            # Read leader arm positions
            leader_positions = []
            for motor_id in MOTOR_IDS:
                pos = get_motor_position(ser_leader, motor_id)
                if pos is not None:
                    leader_positions.append(pos)
                else:
                    leader_positions.append(0)  # Fallback
            
            # Command follower arm
            for i, motor_id in enumerate(MOTOR_IDS):
                set_motor_position(ser_follower, motor_id, leader_positions[i])
            
            # Read follower positions (for verification)
            follower_positions = []
            for motor_id in MOTOR_IDS:
                pos = get_motor_position(ser_follower, motor_id)
                if pos is not None:
                    follower_positions.append(pos)
                else:
                    follower_positions.append(0)
            
            # Capture camera frames
            ret1, frame1 = cam1.read()
            ret2, frame2 = cam2.read()
            
            if not ret1 or not ret2:
                logger.warning("Failed to capture camera frames")
                continue
            
            # Convert to RGB
            frame1_rgb = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
            frame2_rgb = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
            
            # Record data if recording is active (at RECORDING_FPS rate)
            if recorder.is_recording and (timestamp - last_recording_time) >= (1.0 / RECORDING_FPS):
                recorder.add_frame(
                    timestamp,
                    leader_positions,
                    follower_positions,
                    frame1_rgb,
                    frame2_rgb
                )
                last_recording_time = timestamp
            
            # Stream motor positions
            connect_client.stream(
                "leader_motors",
                timestamp,
                names=[f"motor_{i+1}" for i in range(6)],
                values=leader_positions
            )
            
            connect_client.stream(
                "follower_motors",
                timestamp,
                names=[f"motor_{i+1}" for i in range(6)],
                values=follower_positions
            )
            
            # Stream camera frames
            connect_client.stream_rgb(
                "camera_1",
                timestamp,
                CAMERA_WIDTH,
                frame1_rgb.flatten().tolist()
            )
            
            connect_client.stream_rgb(
                "camera_2",
                timestamp,
                CAMERA_WIDTH,
                frame2_rgb.flatten().tolist()
            )
            
            # Stream recording status
            connect_client.stream(
                "recording_status",
                timestamp,
                names=["is_recording", "episode_num", "frame_count"],
                values=[1 if recorder.is_recording else 0, recorder.current_episode_num, recorder.frame_count]
            )
            
            time.sleep(1.0 / UPDATE_RATE)
        
    except serial.SerialException as e:
        logger.error(f"Serial connection error: {e}")
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping...")
        if recorder and recorder.is_recording:
            recorder.stop_recording()
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        
    finally:
        if ser_leader and ser_leader.is_open:
            ser_leader.close()
        if ser_follower and ser_follower.is_open:
            ser_follower.close()
        if cam1:
            cam1.release()
        if cam2:
            cam2.release()
        logger.info("Cleanup complete.")


if __name__ == "__main__":
    main()

"""
SO-101 Camera Feed Check

Simple script to verify camera acquisition and streaming.
Captures from two USB cameras and streams to Nominal.
"""

import cv2
import time
import connect_python

# --- Configuration ---
CAMERA_1_INDEX = 0  # /dev/video0
CAMERA_2_INDEX = 2  # /dev/video2
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

logger = connect_python.get_logger(__name__)


def initialize_camera(camera_index, width, height):
    """Initialize a camera with specified resolution."""
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logger.error(f"Failed to open camera {camera_index}")
            return None
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
        
        # Verify actual resolution
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f"Camera {camera_index} initialized: {actual_width}x{actual_height}")
        
        return cap
        
    except Exception as e:
        logger.error(f"Error initializing camera {camera_index}: {e}")
        return None


@connect_python.main
def main(connect_client: connect_python.Client):
    """Main camera streaming loop."""
    cap1 = None
    cap2 = None
    
    try:
        # Initialize both cameras
        logger.info("Initializing cameras...")
        cap1 = initialize_camera(CAMERA_1_INDEX, FRAME_WIDTH, FRAME_HEIGHT)
        cap2 = initialize_camera(CAMERA_2_INDEX, FRAME_WIDTH, FRAME_HEIGHT)
        
        if cap1 is None and cap2 is None:
            logger.error("Failed to initialize any cameras. Exiting.")
            return
        
        if cap1 is None:
            logger.warning(f"Camera {CAMERA_1_INDEX} unavailable")
        if cap2 is None:
            logger.warning(f"Camera {CAMERA_2_INDEX} unavailable")
        
        logger.info("\nStarting camera streaming...")
        logger.info("Press Ctrl+C to stop.\n")
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            timestamp = time.time()
            
            # Capture from camera 1
            if cap1 is not None:
                ret1, frame1 = cap1.read()
                if ret1:
                    frame1_rgb = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
                    rgb_data = frame1_rgb.flatten()
                    connect_client.stream_rgb("camera_1", timestamp, frame1.shape[1], rgb_data)
                else:
                    logger.warning(f"Failed to read from camera {CAMERA_1_INDEX}")
            
            # Capture from camera 2
            if cap2 is not None:
                ret2, frame2 = cap2.read()
                if ret2:
                    frame2_rgb = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
                    rgb_data = frame2_rgb.flatten()
                    connect_client.stream_rgb("camera_2", timestamp, frame2.shape[1], rgb_data)
                else:
                    logger.warning(f"Failed to read from camera {CAMERA_2_INDEX}")
            
            # Log FPS every 100 frames
            frame_count += 1
            if frame_count % 100 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                logger.info(f"Frame {frame_count}: Streaming at {fps:.1f} FPS")
            
            time.sleep(1.0 / TARGET_FPS)
    
    except KeyboardInterrupt:
        logger.info("\nCamera stream stopped by user.")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        if cap1 is not None:
            cap1.release()
            logger.info(f"Camera {CAMERA_1_INDEX} released.")
        if cap2 is not None:
            cap2.release()
            logger.info(f"Camera {CAMERA_2_INDEX} released.")
        
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

# how to read from cameras
# and read/write to feetech motors

import serial
import time
import connect_python
import cv2
import numpy as np
import traceback    # for detailed error logging, what file and line number

# --- Configuration ---
# these are global parameters that depend on your hardware setup
# and preferred settings
CAMERA_1_INDEX = 0  # /dev/video0
CAMERA_2_INDEX = 2  # /dev/video2
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# initialize logger from connect API
logger = connect_python.get_logger(__name__)

# functions
def initialize_camera(camera_index, width, height):
    # set as video capture, and set camera properties
    try:
        cap = cv2.VideoCapture(camera_index)    # directly gets from /dev/video0
        # check if cam is available. if not..
        if not cap.isOpened():
            # log error and return None
            logger.error(f"Failed to open camera {camera_index}")
            return None
        
        # set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)

        # would be good to verify actual resolution and log it
        return cap
    
    except Exception as e:
        logger.error(f"Error initializing camera {camera_index}: {e}")
        return None


@connect_python.main
def template_main(connect_client: connect_python.Client):
    try:
        logger.info(f"Initialize cameras...")
        cap1 = initialize_camera(CAMERA_1_INDEX, FRAME_WIDTH, FRAME_HEIGHT)
        cap2 = initialize_camera(CAMERA_2_INDEX, FRAME_WIDTH, FRAME_HEIGHT)

        if cap1 is None and cap2 is None:
            logger.error("No cameras available. Exiting.")
            return
        
        # should check invidividually and log which cam has the issue

        logger.info("Starting camera streaming loop...")
        frame_count = 0     # for logging frequency
        start_time = time.time()

        while True:
            timestamp = time.time()
            # check if cam1 is available
            # if it is, then read frame
            if cap1 is not None:    # 
                ret1, frame1 = cap1.read()
                # if read was successful, then ret1=True
                if ret1:
                    # convert to rgb, then flatten
                    frame1_rgb = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
                    rgb_data = frame1_rgb.flatten()
                    # stream the flattened image
                    # camera_1 is the channel name, which we use in the app yaml
                    # frame1.shape[1] is the image width, used with the flattened data
                    # the connect api handles height from data length / width
                    connect_client.stream_rgb("camera_1", timestamp, frame1.shape[1], rgb_data)
                else:
                    logger.warning(f"Failed to read from camera {CAMERA_1_INDEX}")
            # do the same for cap2

    # makes it possible to use control+c
    except KeyboardInterrupt:
        logger.info("Script stopped by user.")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())

    finally:
        if cap1 is not None:
            cap1.release()
            logger.info(f"Released camera {CAMERA_1_INDEX}")
        # clean up resources if needed
        cv2.destroyAllWindows()

if __name__ == "__main__":
    template_main()


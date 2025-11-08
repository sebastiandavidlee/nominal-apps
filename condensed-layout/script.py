import time
import numpy as np
from datetime import datetime
import connect_python
import nominal as nm
from colorama import Fore, Style

# Define colors using colorama
GREEN = Fore.GREEN + Style.DIM
RED = Fore.RED + Style.BRIGHT
RESET = Style.RESET_ALL

logger = connect_python.get_logger(__name__)


@connect_python.main
def stream_data(client: connect_python.Client):
    # Initialize state variables from initial app state
    frequency = client.get_value("frequency", 5.0)
    y_offset = client.get_value("y_axis_offset", 0.0)
    connection_rid = client.get_value("connection_rid", "")
    channel = client.get_value("channel", "")
    tag_key = client.get_value("tag_key", "")
    tag_value = client.get_value("tag_value", "")
    stream_to_nominal = client.get_value("stream_to_nominal", False)

    logger.info(f"Initial values - frequency: {frequency}, y_offset: {y_offset}")

    connection = nm.get_connection(connection_rid) if connection_rid else None
    write_stream = connection.get_write_stream(batch_size=1) if connection else None

    if not write_stream and stream_to_nominal:
        logger.error("Error: streaming not configured!")
        exit(1)

    try:
        # clear the streams used by this script
        client.clear_stream("sine_wave")
        client.clear_stream("cosine_wave")
        client.clear_stream("tangent_wave")

        start = time.time()
        last_log_time = time.time()

        while True:
            t = time.time()
            delta = t - start
            sine = np.sin(delta * frequency) + y_offset
            cosine = np.cos(delta * frequency) + y_offset
            tangent = np.tan(delta * frequency) + y_offset

            # Log values once per second
            current_time = time.time()
            if current_time - last_log_time >= 1.0:
                color = GREEN if tangent >= 0 else RED
                logger.info(f"Tangent value: {color}{tangent:.3f}{RESET}")
                last_log_time = current_time

            client.stream("sine_wave", t, float(sine))
            client.stream("cosine_wave", t, float(cosine))
            client.stream("tangent_wave", t, float(tangent))

            if write_stream:
                tags = None
                if tag_key and tag_value:
                    tags = {tag_key: tag_value}

                write_stream.enqueue(
                    channel_name=channel if channel else "Unnamed_channel",
                    timestamp=datetime.now(),
                    value=float(sine),
                    tags=tags,
                )
            time.sleep(0.015)  # Add a small delay
    except Exception as e:
        logger.error(f"Error in stream_data: {e}")


if __name__ == "__main__":
    logger.info("aligned")
    logger.info("started telop")
    logger.info("interrupted")
    logger.info("aligned")
    logger.info("started telop")
    logger.info("interrupted")

    stream_data()

import time
import traceback

from labjack import ljm
import connect_python
import nominal as nm

from utils import (
    format_data_for_stream,
)
from labjack_utils import setup_labjack_device, configure_labjack_device

logger = connect_python.get_logger(__name__)


@connect_python.main
def stream_data(connect_client: connect_python.Client):
    """
    Main function to stream data from LabJack T-Series AI channels to ZMQ and optionally to Nominal.

    Reads configuration from stdin JSON input including:
    - Sample Rate
    - Channel configuration
    - Nominal.io streaming settings

    The function continuously reads from configured channels and streams the data to:
    - ZMQ socket on port 5555 (for local visualization)
    - Nominal.io cloud platform (if configured)

    The function runs indefinitely until interrupted or an error occurs.

    Raises
    ------
    Exception
        If there are errors in data acquisition or streaming.
    """

    sample_rate = float(connect_client.get_value("sample_rate"))
    input_1 = connect_client.get_value("input_1")
    input_2 = connect_client.get_value("input_2")
    input_3 = connect_client.get_value("input_3")
    input_4 = connect_client.get_value("input_4")
    serial = connect_client.get_value("serial")
    model = connect_client.get_value("model")

    aScanListNames = [
        c
        for c in [
            input_1,
            input_2,
            input_3,
            input_4,
        ]
        if c
    ]
    aScanList = ljm.namesToAddresses(len(aScanListNames), aScanListNames)[0]
    samples_per_read = int(sample_rate / 10)
    dt = 1 / sample_rate

    # Open and configure the device
    handle, info = setup_labjack_device(model, serial)
    logger.info(
        "Opened a LabJack with Device type: %i, Connection type: %i,\n"
        "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i"
        % (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5])
    )
    configure_labjack_device(handle, info)

    connect_client.clear_stream("channel_data")

    # Nominal Core stuff
    connection_rid = connect_client.get_value("connection_rid")
    if connection_rid:
        try:
            core_stream = nm.get_connection(connection_rid).get_write_stream()
        except Exception:
            connect_client.set_value("Nominal Connection not found")
    else:
        connect_client.set_value("Nominal Connection not found")

    while True:
        if connect_client.get_value("run_state") == "Running":
            # Set up the Nominal Streaming
            try:
                # Start LabJack stream to ljm driver
                scanRate = ljm.eStreamStart(
                    handle,
                    samples_per_read,
                    len(aScanListNames),
                    aScanList,
                    sample_rate,
                )
                connect_client.set_value("actual_sample_rate", scanRate)

                while True:
                    if connect_client.get_value("run_state") != "Running":
                        break

                    # Fetch data from ljm driver
                    readings = ljm.eStreamRead(handle)
                    timestamp = time.time()

                    samples = readings[0]
                    connect_client.set_value("device_buffer", readings[1])
                    connect_client.set_value("driver_buffer", readings[2])

                    # Send to "channel_data" plot
                    stream_args_per_channel = format_data_for_stream(
                        samples, aScanListNames, timestamp, dt
                    )

                    connect_client.stream_batch(
                        "channel_data", **stream_args_per_channel
                    )

                    # Streaming to Nominal Core
                    if bool(connect_client.get_value("stream_to_nominal", False)):
                        nom_key = connect_client.get_value("tag_key")
                        nom_value = connect_client.get_value("tag_value")

                        for i, channel in enumerate(aScanListNames):
                            core_stream.enqueue_batch(
                                channel_name=channel,
                                timestamps=stream_args_per_channel["timestamps"],
                                values=stream_args_per_channel["values"][i],
                                tags={nom_key: nom_value},
                            )

            except Exception as e:
                print(f"Error in stream_data: {e}", flush=True)
                print("\nFull traceback:", flush=True)
                print(traceback.format_exc(), flush=True)
                connect_client.set_value("run_state", "Stopped")
            finally:
                print("Stopping Acquisition...", flush=True)
                ljm.eStreamStop(handle)

        time.sleep(0.1)


if __name__ == "__main__":
    stream_data()

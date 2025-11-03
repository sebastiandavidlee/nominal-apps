from pathlib import Path
import connect_python
import numpy as np
import time
from mcap.reader import make_reader
from mcap_ros1.decoder import DecoderFactory
from scipy.spatial.transform import Rotation as R

# Debug flag to control verbose output
DEBUG = False

HERE = Path(__file__).parent
mcap_path = HERE / "data" / "dataset-calib-imu1_128_16_downscaled.mcap"


camera_topics = ["/cam0/image_raw", "/cam1/image_raw"]
transform_topics = ["/vrpn_client/raw_transform"]
imu_topics = ["/imu0"]
all_topics = camera_topics + transform_topics + imu_topics


@connect_python.main
def stream_data(client: connect_python.Client):
    print(f"Using MCAP file: {mcap_path}")

    client.clear_stream("drone_position")
    client.clear_stream("drone_velocity")
    client.clear_stream("drone_acceleration")
    client.clear_stream("camera_left")
    client.clear_stream("camera_right")
    client.clear_frame_buffer("camera_left")
    client.clear_frame_buffer("camera_right")

    # Open and read the MCAP file with ROS1 decoder
    with open(mcap_path, "rb") as f:
        reader = make_reader(f, decoder_factories=[DecoderFactory()])

        first_timestamp = None
        previous_position = None
        prev_timestamp = None
        prev_timestamp_mocap = None

        # Process all messages using decoded ROS messages
        for schema, channel, message, ros_msg in reader.iter_decoded_messages(
            topics=all_topics
        ):
            # Get timestamp in seconds
            original_timestamp_sec = message.log_time / 1e9

            # skip all data until we have the first transform (motion capture data)
            if (
                channel.topic == "/vrpn_client/raw_transform"
                and first_timestamp is None
            ):
                first_timestamp = original_timestamp_sec
                if DEBUG:
                    print(f"Found first position at time {first_timestamp:.2f}s")

            # Skip camera processing until we have a transform
            if first_timestamp is None:
                continue

            # Calculate normalized timestamp for camera frames
            timestamp_sec = original_timestamp_sec - first_timestamp

            # delta time between messages to make the streaming look realtime
            dt: float | None = None
            if prev_timestamp is not None:
                dt = timestamp_sec - prev_timestamp
            prev_timestamp = timestamp_sec

            # delta time between mocap messages for velocity calculation
            dt_mocap: float | None = None
            if prev_timestamp_mocap is not None:
                dt_mocap = timestamp_sec - prev_timestamp_mocap

            # Handle IMU messages to get acceleration data
            if channel.topic in imu_topics:
                stream_imu_data(client, timestamp_sec, ros_msg, DEBUG)

            if channel.topic == "/vrpn_client/raw_transform":
                previous_position = stream_transform_data(
                    client,
                    timestamp_sec,
                    ros_msg,
                    previous_position,
                    dt_mocap,
                    DEBUG,
                )
                prev_timestamp_mocap = timestamp_sec
            # Process camera feeds
            if channel.topic in ["/cam0/image_raw", "/cam1/image_raw"]:
                # Process image message directly
                rgb_data = convert_image_to_rgb(ros_msg)

                if channel.topic == "/cam0/image_raw":
                    client.stream_rgb(
                        "camera_left", timestamp_sec, ros_msg.width, rgb_data
                    )
                else:
                    client.stream_rgb(
                        "camera_right", timestamp_sec, ros_msg.width, rgb_data
                    )

            # Stop after desired number of frames
            # if timestamp_sec > 10.0:
            #     break

            if dt is not None:
                time.sleep(dt)


def stream_imu_data(client, timestamp_sec, imu_msg, debug=False):
    """
    Extract and stream IMU data from a ROS IMU message

    Args:
        client: Connect client
        timestamp_sec: Timestamp in seconds
        imu_msg: ROS IMU message
        debug: Debug flag
    """
    # Get linear acceleration values directly from the message
    ax = -imu_msg.linear_acceleration.x
    ay = imu_msg.linear_acceleration.y
    az = imu_msg.linear_acceleration.z

    # subtract gravity from the acceleration
    az -= 9.81

    accel_magnitude = np.sqrt(ax * ax + ay * ay + az * az)

    if debug:
        print(f"Normalized acceleration: ax={ax:.2f}, ay={ay:.2f}, az={az:.2f}")

    client.stream(
        "drone_acceleration",
        timestamp_sec,
        names=["x", "y", "z", "magnitude"],
        values=[ax, ay, az, accel_magnitude],
    )


def stream_transform_data(
    client,
    timestamp_sec,
    transform_msg,
    previous_position,
    dt: float | None,
    debug=False,
):
    """
    Extract and stream transform data from a ROS TransformStamped message

    Args:
        client: Connect client
        timestamp_sec: Timestamp in seconds
        transform_msg: ROS TransformStamped message
        previous_position: Previous position for speed calculation
        imu_msg: ROS IMU message for orientation calculations
        debug: Debug flag
    """

    # Extract position from the transform message
    x = -transform_msg.transform.translation.x
    y = transform_msg.transform.translation.y
    z = transform_msg.transform.translation.z

    # it's a right handed coordinate system
    # all based by looking at the plots of x, y, z and the camera footage

    # Extract quaternion from the transform message
    qx = transform_msg.transform.rotation.x
    qy = transform_msg.transform.rotation.y
    qz = transform_msg.transform.rotation.z
    qw = transform_msg.transform.rotation.w

    if debug:
        print(f"Position: x={x}, y={y}, z={z}")
        print(f"Quaternion: qx={qx}, qy={qy}, qz={qz}, qw={qw}")

    # Create a rotation object directly from the quaternion
    # It's less bug prone to work directly with euler angles
    # in the bevy coordinate system.
    # Bevy x axis is drone x
    # Bevy y axis is drone z (up)
    # Bevy z axis is drone -y (forward)
    rot = R.from_quat([qx, qz, -qy, qw])
    heading_deg, pitch_deg, roll_deg = rot.as_euler("YXZ", degrees=True)

    # connect uses a clockwise heading direction. the existing angle is counter-clockwise, so we need to invert it
    heading_deg = -heading_deg
    pitch_deg = -pitch_deg

    client.stream(
        "drone_position",
        timestamp_sec,
        names=[
            "x",
            "y",
            "z",
            "roll",
            "pitch",
            "heading",
        ],
        values=[
            x,
            y,
            z,
            roll_deg,
            pitch_deg,
            heading_deg,
        ],
    )

    if previous_position and dt is not None and dt > 0.0:
        dx = x - previous_position[0]
        dy = y - previous_position[1]
        dz = z - previous_position[2]
        ds = (dx**2 + dy**2 + dz**2) ** 0.5
        speed = ds / dt
        client.stream(
            "drone_velocity",
            timestamp_sec,
            names=["x", "y", "z", "magnitude"],
            values=[dx / dt, dy / dt, dz / dt, speed],
        )

    client.stream("x", timestamp_sec, x)
    client.stream("y", timestamp_sec, y)
    client.stream("z", timestamp_sec, z)

    return [x, y, z]


def convert_image_to_rgb(ros_image):
    """
    Convert a ROS Image message to RGB format for Connect streaming.

    Args:
        ros_image: A ROS Image message

    Returns:
        List of RGB pixel values suitable for client.stream_rgb
    """
    encoding = ros_image.encoding

    # Determine if we're dealing with 16-bit or 8-bit data
    is_16bit = "mono16" in encoding.lower()

    # Create a numpy array from the image data
    if is_16bit:
        # For 16-bit images
        mono_array = np.frombuffer(ros_image.data, dtype=np.uint16)
        # Convert to 8-bit for RGB
        mono_8bit = (mono_array / 256).astype(np.uint8)
    else:
        # For 8-bit images
        mono_8bit = np.frombuffer(ros_image.data, dtype=np.uint8)

    # Convert grayscale to RGB using numpy broadcasting
    rgb_array = np.stack((mono_8bit,) * 3, axis=-1).reshape(-1)

    # Convert to list for connect_python
    return rgb_array


if __name__ == "__main__":
    stream_data()

import time
import math
import connect_python


@connect_python.main
def stream_data(client: connect_python.Client):
    print("Starting robot arm replay stream", flush=True)

    names = [
        "shoulder_pan_joint",
        "shoulder_lift_joint",
        "elbow_joint",
        "wrist_1_joint",
        "wrist_2_joint",
        "wrist_3_joint",
    ]
    angle = [0.0, 0.0, 0.8 * math.pi, 0.0, 0.0, 0.0]
    bound = [
        2 * math.pi,
        2 * math.pi,
        0.8 * math.pi,
        2 * math.pi,
        2 * math.pi,
        2 * math.pi,
    ]
    velocity = [
        1,
        1,
        1,
        2,
        2,
        3,
    ]
    direction = [1, 1, 1, 1, 1, 1]

    try:
        client.clear_stream("pose")

        timestamp = 0
        while True:  # Add continuous loop
            timestamp += 0.001

            # determine which angle to modify
            i = math.floor(timestamp * 100.0) % 6

            angle[i] = angle[i] + (0.01 * math.pi * velocity[i] * direction[i])
            if abs(angle[i]) > bound[i]:
                direction[i] *= -1

            client.stream("pose", timestamp, values=angle, names=names)

            time.sleep(0.01)  # Add a small delay

    except Exception as e:
        print(f"Error in stream_data: {e}", flush=True)


if __name__ == "__main__":
    stream_data()


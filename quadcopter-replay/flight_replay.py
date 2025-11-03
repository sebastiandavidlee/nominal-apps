import time
import polars as pl
import os
import connect_python


@connect_python.main
def stream_data(client: connect_python.Client):
    print("Starting flight replay stream", flush=True)

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the full path to the CSV file
    csv_path = os.path.join(script_dir, "dji_ocean_flight_filtered.csv")

    # Read the CSV file using the full path
    df = pl.read_csv(csv_path)

    # Calculate relative coordinates by subtracting the first position
    initial_lat = df["OSD.latitude"][0]
    initial_lon = df["OSD.longitude"][0]

    # Calculate relative positions using polars expressions
    df = df.with_columns(
        [
            (pl.col("OSD.latitude") - initial_lat).alias("latitude"),
            (pl.col("OSD.longitude") - initial_lon).alias("longitude"),
        ]
    )

    delta_ts = df["timestamps_ns"].max() - df["timestamps_ns"].min() + 1
    print(f"Delta time: {delta_ts}", flush=True)
    try:
        client.clear_stream("drone_position")

        iteration = 0
        while True:  # Add continuous loop
            # Stream each row of the dataframe
            for row in df.iter_rows(named=True):
                timestamp = float(row["timestamps_ns"] + delta_ts * iteration)

                # Stream flight position data
                client.stream(
                    "drone_position",
                    timestamp,
                    names=["x", "z", "y", "pitch", "roll", "heading"],
                    values=[
                        float(row["latitude"] * 10_000.0),
                        float(row["longitude"] * 10_000.0),
                        float(row["OSD.height [ft]"] / 10.0),
                        float(row["OSD.pitch"]),
                        float(row["OSD.roll"]),
                        90 + float(row["OSD.yaw"]),  # Reference north, not east
                    ],
                )

                time.sleep(0.05)  # Add a small delay

            iteration += 1
            # Optional: Add a small delay between replays
            time.sleep(0.5)

    except Exception as e:
        print(f"Error in stream_data: {e}", flush=True)


if __name__ == "__main__":
    stream_data()

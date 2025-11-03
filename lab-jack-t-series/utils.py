from typing import Union


def format_data_for_stream(
    fetch: list[float], channel_names: list[str], t0: float, dt: float
) -> dict[str, Union[list[float], list[list[float]], list[str]]]:
    """Takes labjack data lists and channel names and creates a list of data for each computed timestamp

    Args:
        fetch (list[float]): The data from the LabJack eStreamRead() return's first element.
            Stream data list with all channels interleaved. It will contain scansPerRead*numAddresses
            values configured from eStreamStart.
        channel_names (list[str]): The channel names to associate with the data.
        t0 (float): Time, in seconds, when eStreamRead returned.
        dt (float): Period of time between datapoints in seconds

    Returns:
        list[dict[str:float, str:list[float], str:list[str]]]: A list of dicts where every element is a single sample for all channels
            for each dt.
    """
    channel_count = len(channel_names)
    samples_per_channel = int(len(fetch) / channel_count)

    timestamps = create_timestamps_from_dt(
        t0=t0, dt=dt, length=samples_per_channel, backstamp=True
    )

    samples_by_timestamp = create_samples_by_timestamp(
        fetch, channel_count, samples_per_channel
    )

    return {
        "timestamps": timestamps,
        "values": samples_by_timestamp,
        "names": channel_names,
    }


def create_timestamps_from_dt(
    t0: float, dt: float, length: int, backstamp: bool = False
) -> list[float]:
    if backstamp:
        t0 = t0 - dt * length

    return [t0 + i * dt for i in range(length)]


def create_samples_by_timestamp(
    flat_data: list[float], channel_count: int, samples_per_channel: int
) -> list[list[float]]:
    return [
        flat_data[i * channel_count : (i + 1) * channel_count]
        for i in range(samples_per_channel)
    ]


def create_samples_by_channel(
    flat_data: list[float],
    channel_count: int,
) -> list[list[float]]:
    return [flat_data[i::channel_count] for i in range(channel_count)]

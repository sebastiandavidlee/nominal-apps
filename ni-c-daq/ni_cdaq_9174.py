import time
import random
import yaml
from pathlib import Path
import connect_python

logger = connect_python.get_logger(__name__)


def temperature_units(units):
    """
    Convert the units to the correct nidaqmx type.

    class TemperatureUnits(Enum):
        DEG_C = 10143  #: Degrees Celsius.
        DEG_F = 10144  #: Degrees Fahrenheit.
        K = 10325  #: Kelvins.
        DEG_R = 10145  #: Degrees Rankine.
        FROM_CUSTOM_SCALE = 10065
    """
    from nidaqmx.constants import TemperatureUnits

    if units == "DEG_C":
        return TemperatureUnits.DEG_C
    elif units == "DEG_F":
        return TemperatureUnits.DEG_F
    elif units == "K":
        return TemperatureUnits.K
    elif units == "DEG_R":
        return TemperatureUnits.DEG_R


def tc_conversion(thermocouple_type):
    """
    Convert the thermocouple type to the correct nidaqmx type.

    Parameters
    ----------
    thermocouple_type : str
        The type of thermocouple ('K', 'J', 'T', 'E', 'N', 'R', 'S', 'B', or 'C').

    Returns
    -------
    ThermocoupleType
        The corresponding nidaqmx ThermocoupleType enum value.
    """
    from nidaqmx.constants import ThermocoupleType

    if thermocouple_type == "K":
        thermocouple_type = ThermocoupleType.K
    elif thermocouple_type == "J":
        thermocouple_type = ThermocoupleType.J
    elif thermocouple_type == "T":
        thermocouple_type = ThermocoupleType.T
    elif thermocouple_type == "E":
        thermocouple_type = ThermocoupleType.E
    elif thermocouple_type == "N":
        thermocouple_type = ThermocoupleType.N
    elif thermocouple_type == "R":
        thermocouple_type = ThermocoupleType.R
    elif thermocouple_type == "S":
        thermocouple_type = ThermocoupleType.S
    elif thermocouple_type == "B":
        thermocouple_type = ThermocoupleType.B
    elif thermocouple_type == "C":
        thermocouple_type = ThermocoupleType.C

    return thermocouple_type


def read_analog_input(
    ch, min_voltage, max_voltage, card_type, thermocouple_type, mock_data
):
    """
    Read a single analog input channel and return the measurement result.

    Parameters
    ----------
    ch : str
        Channel identifier (e.g., 'cDAQ1Mod1/ai0').
    min_voltage : float
        Minimum voltage range for the measurement.
    max_voltage : float
        Maximum voltage range for the measurement.
    card_type : str
        Type of card ('TC' for thermocouple, 'mV' for millivolt, or 'mA' for current).
    thermocouple_type : str
        Type of thermocouple if using TC card type.
    mock_data : bool
        If True, generate random data instead of reading from hardware.

    Returns
    -------
    list or float
        Measurement data from the channel. Returns a list of samples for real hardware
        or a single float value for mock data.
    """
    # Load channel-specific configuration if available
    try:
        yaml_path = Path(__file__).parent / "channels.yml"
        if yaml_path.exists():
            with open(yaml_path, "r") as f:
                channel_config = yaml.safe_load(f)
            if ch in channel_config:
                cfg = channel_config[ch]
                try:
                    min_voltage = float(cfg.get("min_val", min_voltage))
                    max_voltage = float(cfg.get("max_val", max_voltage))
                except ValueError as e:
                    logger.error(f"Invalid voltage values in config: {e}")
                if "thermocouple_type" in cfg:
                    if cfg["thermocouple_type"] in [
                        "K",
                        "J",
                        "T",
                        "E",
                        "N",
                        "R",
                        "S",
                        "B",
                        "C",
                    ]:
                        thermocouple_type = cfg["thermocouple_type"]
                    else:
                        logger.error(
                            f"Invalid thermocouple type: {cfg['thermocouple_type']}"
                        )
                if "card_type" in cfg:
                    if (
                        cfg["card_type"] == "TC"
                        or cfg["card_type"] == "mV"
                        or cfg["card_type"] == "mA"
                    ):
                        card_type = cfg["card_type"]
                    else:
                        logger.error(f"Invalid card type: {cfg['card_type']}")
                units = cfg.get("units", "DEG_C")
    except Exception as e:
        logger.error(f"Error loading channel configuration: {e}")
        units = "DEG_C"
    else:
        units = "DEG_C"

    if not mock_data:
        import nidaqmx
        from nidaqmx.constants import AcquisitionType

        with nidaqmx.Task() as task:
            # Create an analog input voltage channel (adjust the parameters as needed)

            logger.warning(f"Channel: {ch}")
            logger.warning(f"Card type: {card_type}")
            logger.warning(f"Min voltage: {min_voltage}, Max voltage: {max_voltage}")

            if card_type == "TC":
                task.ai_channels.add_ai_thrmcpl_chan(
                    ch,
                    min_val=min_voltage,
                    max_val=max_voltage,
                    thermocouple_type=tc_conversion(thermocouple_type),
                    units=temperature_units(units),
                )
            elif card_type == "mV":
                logger.warning(f"Adding AI voltage channel: {ch}")
                task.ai_channels.add_ai_voltage_chan(
                    ch,
                    min_val=min_voltage,
                    max_val=max_voltage,
                )
            elif card_type == "mA":
                logger.warning(f"Adding AI current channel: {ch}")
                task.ai_channels.add_ai_current_chan(
                    ch,
                    min_val=min_voltage,
                    max_val=max_voltage,
                )

            # Configure the sampling rate and number of samples to acquire
            sample_rate_hz = 100000  # 10kHz
            samples_per_channel = (
                2  # Quick 1ms capture of 2 samples per channel at 10k Hz
            )

            task.timing.cfg_samp_clk_timing(
                sample_rate_hz,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=samples_per_channel,
            )

            data = task.read(number_of_samples_per_channel=samples_per_channel)
    else:
        if card_type == "mV":
            mean = (max_voltage + min_voltage) / 2
            std_dev = (max_voltage - min_voltage) / 6  # 99.7% of values within range
            data = [random.gauss(mean, std_dev)]
        elif card_type == "TC" or card_type == "mA":
            mean = 21.0  # center of 19-23 range
            std_dev = 0.67  # 99.7% of values within ±2V range
            data = [random.gauss(mean, std_dev)]

    print("Data", data, flush=True)

    return data


def get_channel_list(values):
    """
    Read input fields from the app form and return the list of channels and their types.

    Parameters
    ----------
    values : dict
        Dictionary containing form input values including:
        - cdaq_model_N : str
        - analog_input_start_N : str
        - analog_input_end_N : str
        - card_type_N : str
        Where N is the module number (1-4).

    Returns
    -------
    tuple
        A tuple containing:
        - list of str: Channel names in format "cDAQ1ModX/aiY"
        - dict: Mapping of channel names to their card types
    """

    n_modules = 4
    channel_names = []
    card_type_by_channel = {}

    for i in range(n_modules):
        cdaq_model = values.get(f"cdaq_model_{i + 1}")
        if cdaq_model != "":
            start_channel = int(values.get(f"analog_input_start_{i + 1}"))
            end_channel = int(values.get(f"analog_input_end_{i + 1}"))
            print(
                f"cDAQ model: {cdaq_model}, start channel: {start_channel}, end channel: {end_channel}",
                flush=True,
            )
            for j in range(start_channel, end_channel + 1):
                channel_names.append(f"{cdaq_model}/ai{j}")
                card_type_by_channel[f"{cdaq_model}/ai{j}"] = values.get(
                    f"card_type_{i + 1}"
                )

    print("Channel names: ", channel_names, flush=True)
    return (channel_names, card_type_by_channel)


@connect_python.main
def stream_data(client: connect_python.Client):
    """
    Main function to stream data from NI-DAQ channels to ZMQ and optionally to Nominal.

    Reads configuration from stdin JSON input including:
    - Voltage ranges
    - Sampling interval
    - Channel configuration
    - Thermocouple settings
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
    print("Starting stream_example.py", flush=True)

    # cDAQ stuff
    min_voltage = float(client.get_value("min_voltage", -0.005))
    max_voltage = float(client.get_value("max_voltage", 0.005))
    interval_seconds = float(client.get_value("interval_seconds"))
    channel_names, card_type_by_channel = get_channel_list(client.get_values())
    thermocouple_type = client.get_value("thermocouple_type", "K")
    mock_data = bool(client.get_value("mock_data", False))

    logger.info(f"Mock data: {mock_data}")

    client.clear_stream("sensors")

    while True:
        t = time.time()
        single_voltage_readings = []
        for i in range(len(channel_names)):
            ch = channel_names[i]
            card_type = card_type_by_channel[ch]
            voltage = read_analog_input(
                ch,
                min_voltage,
                max_voltage,
                card_type,
                thermocouple_type,
                mock_data,
            )
            single_voltage_readings.append(voltage[0])

        client.stream("sensors", t, values=single_voltage_readings, names=channel_names)

        time.sleep(interval_seconds)


if __name__ == "__main__":
    stream_data()

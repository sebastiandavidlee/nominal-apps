import time
import connect_python
import can
import cantools

# Get logger
logger = connect_python.get_logger(__name__)

db = cantools.database.load_file("canmod-temp.dbc")

sim_data = [
    [25, 1, 23, 0, 23, 0, 24, 3, 29],
    [25, 1, 24, 0, 23, 2, 24, 0, 28],
    [25, 1, 23, 0, 23, 2, 24, 0, 28],
    [25, 1, 24, 0, 23, 2, 24, 0, 27],
    [25, 1, 24, 0, 23, 0, 24, 0, 27],
    [25, 1, 24, 0, 22, 0, 24, 0, 26],
    [25, 1, 24, 0, 22, 0, 24, 0, 26],
    [25, 1, 24, 0, 22, 0, 24, 3, 26],
    [25, 1, 24, 0, 22, 0, 24, 3, 26],
    [25, 1, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 23, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 24],
    [25, 0, 24, 0, 22, 0, 24, 0, 24],
    [25, 0, 24, 0, 22, 0, 24, 0, 24],
    [25, 0, 24, 0, 22, 0, 24, 0, 24],
    [25, 0, 24, 0, 22, 0, 24, 0, 24],
    [25, 0, 24, 0, 22, 0, 24, 0, 24],
    [25, 0, 24, 0, 22, 1, 24, 0, 24],
    [25, 0, 24, 0, 22, 1, 23, 0, 24],
    [25, 0, 24, 0, 22, 1, 23, 0, 24],
    [25, 0, 24, 0, 22, 0, 23, 0, 24],
    [25, 0, 24, 0, 22, 0, 23, 0, 24],
    [25, 0, 24, 0, 22, 0, 23, 0, 24],
    [25, 0, 24, 0, 22, 0, 23, 0, 24],
    [25, 0, 24, 0, 22, 0, 23, 0, 24],
    [25, 0, 24, 0, 22, 0, 23, 0, 24],
    [25, 0, 24, 0, 22, 0, 23, 0, 24],
    [25, 0, 24, 0, 22, 0, 23, 0, 24],
    [25, 0, 24, 0, 27, 0, 23, 0, 23],
    [25, 0, 24, 0, 27, 0, 23, 0, 23],
    [25, 0, 24, 0, 28, 0, 23, 0, 23],
    [25, 0, 24, 0, 29, 0, 23, 0, 23],
    [25, 0, 24, 0, 27, 0, 23, 0, 23],
    [25, 0, 27, 0, 26, 0, 23, 0, 23],
    [25, 0, 29, 0, 25, 0, 23, 0, 23],
    [25, 0, 30, 0, 25, 0, 22, 0, 23],
    [25, 0, 30, 0, 24, 0, 22, 0, 22],
    [25, 0, 30, 0, 24, 0, 22, 0, 22],
    [25, 0, 30, 0, 23, 0, 22, 0, 22],
    [25, 0, 28, 0, 23, 0, 23, 0, 22],
    [25, 0, 27, 0, 23, 0, 27, 0, 22],
    [25, 0, 27, 0, 23, 0, 29, 0, 23],
    [25, 0, 26, 0, 23, 0, 29, 0, 27],
    [25, 0, 26, 0, 23, 0, 29, 0, 29],
    [25, 0, 26, 0, 23, 0, 29, 0, 29],
    [25, 0, 25, 0, 23, 0, 30, 0, 30],
    [25, 0, 25, 0, 23, 0, 30, 0, 30],
    [25, 0, 25, 0, 23, 0, 30, 0, 30],
    [25, 0, 25, 0, 23, 0, 28, 0, 30],
    [25, 0, 26, 0, 23, 0, 27, 0, 28],
    [25, 0, 29, 0, 23, 0, 26, 0, 27],
    [25, 0, 30, 0, 22, 0, 25, 0, 27],
    [25, 0, 30, 0, 22, 0, 25, 0, 26],
    [25, 0, 30, 0, 22, 0, 24, 0, 26],
    [25, 0, 30, 1, 22, 0, 24, 0, 25],
    [25, 0, 28, 1, 22, 0, 26, 0, 25],
    [25, 0, 28, 0, 22, 0, 27, 0, 25],
    [25, 0, 27, 0, 22, 0, 28, 0, 24],
    [25, 0, 27, 0, 22, 0, 29, 0, 24],
    [25, 0, 26, 0, 22, 0, 30, 0, 24],
    [25, 0, 26, 0, 22, 0, 30, 0, 24],
    [25, 0, 25, 0, 22, 0, 30, 0, 24],
    [25, 0, 25, 0, 22, 0, 30, 0, 23],
    [25, 0, 25, 0, 23, 0, 30, 0, 23],
    [25, 0, 25, 0, 23, 0, 29, 0, 23],
    [25, 0, 25, 0, 23, 0, 28, 0, 23],
    [25, 0, 25, 0, 23, 0, 27, 0, 23],
    [25, 0, 24, 0, 22, 0, 26, 0, 23],
    [25, 0, 24, 0, 23, 0, 25, 0, 24],
    [25, 0, 24, 0, 23, 0, 25, 0, 25],
    [25, 0, 24, 0, 22, 0, 24, 0, 25],
    [25, 0, 24, 0, 23, 0, 24, 0, 25],
    [25, 0, 24, 0, 23, 0, 25, 0, 24],
    [25, 0, 24, 0, 23, 0, 25, 0, 24],
    [25, 0, 24, 0, 23, 0, 29, 0, 24],
    [25, 0, 24, 0, 23, 0, 28, 0, 24],
    [25, 0, 24, 0, 23, 0, 26, 0, 24],
    [25, 0, 24, 0, 23, 0, 26, 0, 24],
    [25, 0, 24, 0, 23, 0, 25, 0, 24],
    [25, 0, 25, 0, 23, 0, 25, 0, 24],
    [25, 0, 26, 0, 24, 0, 24, 0, 23],
    [25, 0, 27, 0, 24, 0, 24, 0, 23],
    [25, 0, 26, 0, 24, 0, 24, 0, 23],
    [25, 0, 26, 0, 23, 0, 24, 0, 28],
    [25, 0, 25, 0, 23, 0, 24, 0, 28],
    [25, 0, 25, 0, 23, 0, 24, 0, 28],
    [25, 0, 28, 0, 23, 0, 24, 0, 27],
    [25, 0, 28, 0, 23, 0, 23, 0, 27],
    [25, 0, 29, 0, 23, 0, 23, 0, 26],
    [25, 0, 29, 0, 23, 0, 23, 0, 26],
    [25, 0, 29, 0, 23, 0, 23, 0, 25],
    [25, 0, 28, 0, 25, 0, 22, 0, 25],
    [25, 0, 27, 0, 27, 0, 23, 0, 24],
    [25, 0, 26, 0, 28, 0, 23, 0, 27],
    [25, 0, 26, 0, 28, 0, 23, 0, 28],
    [25, 0, 25, 0, 27, 0, 24, 0, 29],
    [25, 0, 25, 0, 28, 0, 24, 0, 29],
    [25, 0, 25, 0, 28, 0, 24, 0, 29],
    [25, 0, 25, 0, 28, 0, 25, 0, 30],
    [25, 0, 25, 0, 28, 0, 25, 1, 30],
    [25, 0, 25, 0, 28, 0, 25, 1, 29],
    [25, 0, 25, 0, 30, 0, 25, 1, 30],
    [25, 0, 27, 0, 30, 0, 25, 1, 30],
    [25, 0, 27, 0, 30, 0, 24, 0, 30],
    [25, 0, 27, 0, 29, 0, 24, 0, 30],
    [25, 0, 27, 0, 30, 0, 24, 0, 29],
    [25, 0, 26, 0, 30, 0, 24, 0, 28],
    [25, 0, 26, 0, 28, 0, 24, 0, 28],
    [25, 0, 26, 0, 27, 0, 24, 0, 28],
]

Error_dict_db = {
    "OK": 0,
    "ERR1": 1,
    "ERR2": 1,
    "ERR3": 1,
}

Error_dict_sim = {
    0: 1,
    1: 0,
    2: 0,
    3: 0,
}


# Manual Decoding

# def extract_signal(data: bytes, start_bit: int, length: int, factor: float, offset: float) -> float:
#     """
#     Convert CAN data to human-readable format. Use DBC linked here:
#     https://canlogger.csselectronics.com/canmod-temp-docs/database/index.html for
#     decryption schema
#     """
#     bit_string = ''.join(f"{byte:08b}" for byte in data[::-1])  # Little-endian
#     start = len(bit_string) - start_bit - length
#     raw_value = int(bit_string[start:start + length], 2)
#     return raw_value * factor + offset

# def decode_thermocouple_message(msg_data: bytes):
#     # TODO: Use DBC file to decode the message
#     """
#     Extract human-readable signal and format in dictionary
#     """
#     return {
#         "CJTemp": extract_signal(msg_data, 0, 8, 1, -128),
#         "TLStatus": extract_signal(msg_data, 8, 2, 1, 0),
#         "TLTemp": extract_signal(msg_data, 10, 12, 1, -2048),
#         "TRStatus": extract_signal(msg_data, 22, 2, 1, 0),
#         "TRTemp": extract_signal(msg_data, 24, 12, 1, -2048),
#         "BLStatus": extract_signal(msg_data, 36, 2, 1, 0),
#         "BLTemp": extract_signal(msg_data, 38, 12, 1, -2048),
#         "BRStatus": extract_signal(msg_data, 50, 2, 1, 0),
#         "BRTemp": extract_signal(msg_data, 52, 12, 1, -2048),
#     }


@connect_python.main
def stream_data(client: connect_python.Client):
    simulated_data = client.get_value("simulated_data", False)
    for stream_name in ["CJTemp", "TLTemp", "TRTemp", "BLTemp", "BRTemp", "alarms"]:
        client.clear_stream(stream_name)

    def send_status_alarms(stream_name, status_value, t):
        """Helper function to send alarm signals"""
        client.stream(f"{stream_name}.error1", t, 1.0 if status_value == 1 else 0.0)
        client.stream(f"{stream_name}.error2", t, 1.0 if status_value == 2 else 0.0)
        client.stream(f"{stream_name}.error3", t, 1.0 if status_value == 3 else 0.0)

    channel_ids = [
        "TLStatus",
        "TRStatus",
        "BLStatus",
        "BRStatus",
    ]

    if simulated_data:
        for data in sim_data:
            t = time.time()
            client.stream("CJTemp", t, data[0])
            client.stream("TLTemp", t, data[2])
            client.stream("TRTemp", t, data[4])
            client.stream("BLTemp", t, data[6])
            client.stream("BRTemp", t, data[8])
            client.stream(
                "alarms",
                t,
                names=channel_ids,
                values=[
                    Error_dict_sim[data[1]],
                    Error_dict_sim[data[3]],
                    Error_dict_sim[data[5]],
                    Error_dict_sim[data[7]],
                ],
            )

            if any([data[1], data[3], data[5], data[7]]):  # If any status is non-zero
                logger.warning(
                    f"Temp warn at t={t}s: TL={data[1]}, TR={data[3]}, BL={data[5]}, BR={data[7]}"
                )

            time.sleep(0.25)

    else:
        available_channels = can.detect_available_configs("pcan")
        if not available_channels:
            return

        PCAN_address = available_channels[0]
        bitrate = 250000

        connection = can.interface.Bus(
            interface="pcan", channel=PCAN_address["channel"], bitrate=bitrate
        )

        try:
            for msg in connection:
                t = time.time()

                decoded = db.decode_message(msg.arbitration_id, msg.data)

                client.stream("CJTemp", t, decoded["CJTemp"])
                client.stream("TLTemp", t, decoded["TLTemp"])
                client.stream("TRTemp", t, decoded["TRTemp"])
                client.stream("BLTemp", t, decoded["BLTemp"])
                client.stream("BRTemp", t, decoded["BRTemp"])
                client.stream(
                    "alarms",
                    t,
                    names=channel_ids,
                    values=[
                        Error_dict_db[decoded["TLStatus"]],
                        Error_dict_db[decoded["TRStatus"]],
                        Error_dict_db[decoded["BLStatus"]],
                        Error_dict_db[decoded["BRStatus"]],
                    ],
                )

                statuses = [
                    Error_dict_db[decoded["TLStatus"]],
                    Error_dict_db[decoded["TRStatus"]],
                    Error_dict_db[decoded["BLStatus"]],
                    Error_dict_db[decoded["BRStatus"]],
                ]
                if any(statuses):
                    logger.warning(
                        f"Temperature warning at t={t:.1f}s: TL={decoded['TLStatus']}, TR={decoded['TRStatus']}, BL={decoded['BLStatus']}, BR={decoded['BRStatus']}"
                    )

                time.sleep(0.015)

        except KeyboardInterrupt:
            pass
        finally:
            if "connection" in locals():
                connection.shutdown()


if __name__ == "__main__":
    stream_data()

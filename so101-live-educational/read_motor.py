# read_motor
# need imports, global variables, function for reading, and main with decorator

import serial
import time
import connect_python

# configure global variables
SERIAL_PORT = 1     # read from devACM0
BAUD_RATE = 1_000_000   # 1Mbps
TIMEOUT = 0.05  # 50 ms timeout
MOTOR_IDS = [1, 2, 3, 4, 5, 6]  # motor IDs to read from
SAMPLE_RATE = 50  # target sample rate in Hz, 2ms + overhead

# Feetech Protocol Constants
SCS_READ = 0x02                 # Read command instruction
SCS_PRESENT_POSITION_L = 56     # Register address for position (lower byte)

# use connect logger instead of print statements
logger = connect_python.get_logger(__name__)

# utility functions for reading from motor
def get_motor_position(ser, motor_id):
    # so how do we read from the motor from serial and motor_id?
    # go one motor at a time

    # CONSTRUCT READ COMMAND PACKET
    # Format: [0xFF, 0xFF, ID, Length, Instruction, Address, ReadLength, Checksum]
    length = 4  # Instruction + Address + ReadLength + Checksum
    packet_without_checksum = [
        0xFF, 0xFF,                    # Header bytes
        motor_id,                      # Target motor ID
        length,                        # Packet length
        SCS_READ,                      # Read instruction
        SCS_PRESENT_POSITION_L,        # Position register address
        2                              # Number of bytes to read (16-bit position)
    ]

#
@connect_python.main
def main(connect_client: connect_python.Client):

    # there should be try-catch blocks here to add keyboard interrupt, and error message handling
    # upon termination, we also need to close ports
    # ignoring error catching for this script
    logger.info(f"connecting to port")
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
    logger.info("established connection")

    # before streaming, clear the stream
    connect_client.clear_stream("so101_arm1_motors")
    # use a descriptive names, which will be used in app

    # main acquisition loop
    logger.info("starting main acquisition loop")
    while True:
        timestamp = time.time()

        # get motor positions and put into a dictionary
        positions = {}
        for motor_id in MOTOR_IDS:
            # get position and generate key name
            position = get_motor_position(ser, motor_id)
            motor_name = f"motor_{motor_id}"
            # store position in a dictionary
            positions[motor_name] = position

            # if position is None, log a warning each time it happens
            # though it be better to log that the readings are successful? nah...
            if position is None:
                logger.warning(f"Motor {motor_id}: No response or invalid data")


        # Log status every 50 iterations or so, keep track of loop_count

        # stream data to UI, assuming values are "valid"
        # .stream() requires stream name, timestamp
        # but also channel names and values as lists
        # for example, channel_names = ["motor_1", "motor_2", "motor_3"]
        # channel_values = [100, 200, 300]

        if positions:
            channel_names = list(positions.keys())
            channel_values = list(positions.values())
            connect_client.stream(
                "so101_motors", 
                timestamp, 
                names=channel_names,
                values=channel_values
            )
        else:
            logger.warning("No valid motor positions read in this loop")
        
        time.sleep(1.0 / SAMPLE_RATE)


if __name__ == "__main__":
    main()
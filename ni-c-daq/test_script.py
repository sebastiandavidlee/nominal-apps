import nidaqmx
from nidaqmx.constants import AcquisitionType
import numpy as np
import matplotlib.pyplot as plt


def read_analog_input(channel, sample_rate, num_samples):
    # Create a task
    with nidaqmx.Task() as task:
        # Create an analog input voltage channel (adjust the parameters as needed)
        task.ai_channels.add_ai_voltage_chan(channel, min_val=-0.005, max_val=0.005)

        # Configure the sampling rate and number of samples to acquire
        task.timing.cfg_samp_clk_timing(
            sample_rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=num_samples
        )

        # Start reading data from the device
        data = task.read(number_of_samples_per_channel=num_samples)

        # Return the acquired data
        return np.array(data)


def plot_data(data, sample_rate):
    # Create time array
    time_array = np.arange(len(data)) / sample_rate

    # Plot the acquired data
    plt.figure(figsize=(10, 6))
    plt.plot(time_array, data, label="Analog Signal")
    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    plt.title("Acquired Analog Signal")
    plt.grid(True)
    plt.legend()
    plt.show()


def main():
    # Define parameters
    channel = "cDAQ1Mod1/ai1"  # Adjust this to your device and channel
    sample_rate = 1000  # Samples per second
    num_samples = 1000  # Number of samples to acquire

    print(f"Acquiring {num_samples} samples from {channel} at {sample_rate} Hz...")

    # Read data from the analog input channel
    data = read_analog_input(channel, sample_rate, num_samples)

    # Plot the acquired data
    plot_data(data, sample_rate)


if __name__ == "__main__":
    main()

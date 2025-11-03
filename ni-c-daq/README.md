# NI USB 6002

Requirements: Windows computer

## Setup

1. Install the NI-DAQmx driver from the [NI website](https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html). You can also try the [CLI installer](https://nidaqmx-python.readthedocs.io/en/stable/) with `python -m nidaqmx installdriver`. 

2. Open NI-MAX. Verify that the NIUSB 6002 displays:
<img width="945" alt="image" src="https://github.com/user-attachments/assets/f77158b6-2b4a-4abe-8480-e46d8e31e7e9" />

3. Install [nidaqmx](https://nidaqmx-python.readthedocs.io/en/stable/) with `pip install nidaqmx`. Make sure you have Powershell installed in order to do this.

4. It doesn't hurt to make sure that you can read DAQ channels in Python before starting Connect. For example, try:
![image](https://github.com/user-attachments/assets/55cdac4f-f399-4c60-a6e0-b6dc140f2e60)

```py
import nidaqmx
with nidaqmx.Task() as task:
  task.ai_channels.add_ai_voltage_chan("Dev1/ai0")
  a0 = task.read()

a0
 -0.23679729711147957
```

5. Open the `0_USB_6002` app in Connect by opening the `app.connect` file.

6. Make sure the app form fields are filled out correctly. 

7. Click "Execute Scripts" to start the app.





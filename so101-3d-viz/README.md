# SO-101 3D Visualization

Visualize your SO-101 robot arm in real-time 3D using URDF model.

## Setup

1. Open this folder in Nominal Connect
2. Update `HOME_POSITIONS` in `so101_visualize.py` with your arm's home positions
3. Set correct serial port (`/dev/ttyACM0` or `/dev/ttyACM1`)

## Files

- **`app.connect`** - UI configuration with 3D scene
- **`so101_visualize.py`** - Reads motor positions and streams joint angles
- **`urdf/so101.urdf`** - Robot arm URDF model

## Usage

1. Click "🎥 SO-101 3D Visualization" to start
2. Move the robot arm manually
3. See it update in 3D in real-time!

## Customization

### Adjust Link Lengths
Edit `urdf/so101.urdf` to match your actual arm dimensions:
- Base height
- Link lengths (cylinder lengths)
- Joint offsets

### Update Home Positions
Get your actual home positions from `so101_find_home.py` in the `so101-live-motorcam` folder.

### Change Serial Port
Edit `SERIAL_PORT` in `so101_visualize.py`:
- `/dev/ttyACM0` for Arm 2
- `/dev/ttyACM1` for Arm 1

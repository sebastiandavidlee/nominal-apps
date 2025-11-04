# SO-101 Data Recording Project

This folder contains scripts for recording robot demonstration episodes with teleoperation.

## Features

- **Teleoperation**: Control follower arm (ACM0) by moving leader arm (ACM1)
- **Data Recording**: Capture synchronized motor positions and camera frames
- **Episode Management**: Auto-numbered episodes saved as HDF5 files
- **HuggingFace Ready**: Dataset format compatible with robotics datasets

## Quick Start

1. Open this folder in Nominal Connect
2. Click "🎥 Start Teleoperation Session"
3. Use UI buttons to control recording:
   - **🔴 Start Recording** - Begin capturing episode
   - **⏹️ Stop Recording** - Save episode to disk
   - **🛑 Stop Session** - End teleoperation
4. Episodes auto-saved to `./data/episodes/`

## HuggingFace Upload

1. Install: `pip install huggingface_hub datasets`
2. Login: `huggingface-cli login`
3. Edit `upload_to_huggingface.py` - set your username
4. Click "📤 Upload to HuggingFace" button

## Data Format

Each episode is saved as `episode_XXXXXX.hdf5` with:

- `timestamps`: Frame timestamps (N,)
- `leader_positions`: Leader arm motor positions (N, 6)
- `follower_positions`: Follower arm motor positions (N, 6)
- `camera_1`: Camera 1 RGB frames (N, 480, 640, 3)
- `camera_2`: Camera 2 RGB frames (N, 480, 640, 3)
- Metadata: episode_num, frame_count, duration, date, fps

## Next Steps

- Use `upload_to_huggingface.py` to upload your dataset (coming next)
- Visualize episodes with playback script (coming next)

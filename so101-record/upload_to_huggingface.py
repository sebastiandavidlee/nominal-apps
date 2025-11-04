"""
Upload SO-101 Robot Dataset to HuggingFace

This script converts recorded episodes to HuggingFace dataset format
and uploads them to HuggingFace Hub.

Prerequisites:
1. Install: pip install huggingface_hub datasets
2. Login: huggingface-cli login
3. Create dataset repo on HuggingFace Hub

Usage:
- Configure HF_USERNAME and DATASET_NAME below
- Run this script after collecting episodes
- It will upload all episodes from ./data/episodes/
"""

import h5py
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import connect_python

try:
    from huggingface_hub import HfApi, create_repo
    from datasets import Dataset, DatasetDict, Features, Value, Image, Sequence
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

logger = connect_python.get_logger(__name__)

# --- Configuration ---
HF_USERNAME = "your-username"  # ⚠️ CHANGE THIS to your HuggingFace username
DATASET_NAME = "so101-robot-demos"  # Name for your dataset
DATA_DIR = Path("./data/episodes")

# Dataset metadata
DATASET_DESCRIPTION = """
# SO-101 Robot Arm Teleoperation Dataset

This dataset contains robot demonstration episodes collected via teleoperation.
Each episode includes synchronized motor positions and camera observations.

## Hardware
- Robot: SO-101 6-DOF Robot Arms (2x)
- Cameras: 2x USB cameras (640x480 @ 30 FPS)
- Control: Leader-follower teleoperation

## Data Format
- Motor positions: 6 joints per arm, 12-bit encoder values (0-4095)
- Images: RGB, 640x480 resolution
- Frequency: 30 Hz

## Tasks
(Describe the tasks demonstrated in this dataset)
"""


def load_episode(episode_path):
    """Load a single episode from HDF5 file."""
    with h5py.File(episode_path, 'r') as f:
        episode_data = {
            'episode_num': f.attrs['episode_num'],
            'frame_count': f.attrs['frame_count'],
            'duration': f.attrs['duration'],
            'date': f.attrs['date'],
            'fps': f.attrs['fps'],
            'timestamps': f['timestamps'][:],
            'leader_positions': f['leader_positions'][:],
            'follower_positions': f['follower_positions'][:],
            'camera_1': f['camera_1'][:],
            'camera_2': f['camera_2'][:],
        }
    return episode_data


def convert_to_hf_format(data_dir):
    """Convert all episodes to HuggingFace dataset format."""
    logger.info("Loading episodes from disk...")
    
    episode_files = sorted(data_dir.glob("episode_*.hdf5"))
    if not episode_files:
        logger.error(f"No episodes found in {data_dir}")
        return None
    
    logger.info(f"Found {len(episode_files)} episodes")
    
    # Prepare data for HuggingFace dataset
    dataset_entries = []
    
    for ep_file in episode_files:
        logger.info(f"Processing {ep_file.name}...")
        ep_data = load_episode(ep_file)
        
        # For each frame in the episode, create a dataset entry
        for i in range(ep_data['frame_count']):
            entry = {
                'episode_num': ep_data['episode_num'],
                'frame_index': i,
                'timestamp': ep_data['timestamps'][i],
                'leader_motor_1': ep_data['leader_positions'][i][0],
                'leader_motor_2': ep_data['leader_positions'][i][1],
                'leader_motor_3': ep_data['leader_positions'][i][2],
                'leader_motor_4': ep_data['leader_positions'][i][3],
                'leader_motor_5': ep_data['leader_positions'][i][4],
                'leader_motor_6': ep_data['leader_positions'][i][5],
                'follower_motor_1': ep_data['follower_positions'][i][0],
                'follower_motor_2': ep_data['follower_positions'][i][1],
                'follower_motor_3': ep_data['follower_positions'][i][2],
                'follower_motor_4': ep_data['follower_positions'][i][3],
                'follower_motor_5': ep_data['follower_positions'][i][4],
                'follower_motor_6': ep_data['follower_positions'][i][5],
                'camera_1': ep_data['camera_1'][i],
                'camera_2': ep_data['camera_2'][i],
            }
            dataset_entries.append(entry)
    
    logger.info(f"Total frames across all episodes: {len(dataset_entries)}")
    
    # Create HuggingFace dataset
    dataset = Dataset.from_list(dataset_entries)
    
    return dataset


def create_dataset_card(repo_id, num_episodes, total_frames):
    """Create a dataset card (README.md) for the HuggingFace repo."""
    card_content = f"""---
license: mit
task_categories:
- robotics
tags:
- robotics
- imitation-learning
- teleoperation
- SO-101
pretty_name: SO-101 Robot Teleoperation Dataset
size_categories:
- n<1K
---

{DATASET_DESCRIPTION}

## Dataset Statistics

- **Episodes**: {num_episodes}
- **Total Frames**: {total_frames}
- **Recording Date**: {datetime.now().strftime('%Y-%m-%d')}

## Citation

If you use this dataset in your research, please cite:

```
@dataset{{so101_robot_demos,
  author = {{{HF_USERNAME}}},
  title = {{SO-101 Robot Teleoperation Dataset}},
  year = {{{datetime.now().year}}},
  publisher = {{HuggingFace}},
  url = {{https://huggingface.co/datasets/{repo_id}}}
}}
```

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("{repo_id}")
print(dataset)

# Access a frame
frame = dataset[0]
print(f"Episode: {{frame['episode_num']}}, Frame: {{frame['frame_index']}}")
print(f"Leader positions: {{[frame[f'leader_motor_{{i}}'] for i in range(1, 7)]}}")
```
"""
    return card_content


@connect_python.main
def main(connect_client: connect_python.Client):
    """Upload dataset to HuggingFace Hub."""
    
    if not HF_AVAILABLE:
        logger.error("HuggingFace libraries not installed!")
        logger.error("Run: pip install huggingface_hub datasets")
        return
    
    if HF_USERNAME == "your-username":
        logger.error("⚠️  Please set your HuggingFace username in the script!")
        logger.error("Edit HF_USERNAME at the top of upload_to_huggingface.py")
        return
    
    logger.info("=" * 60)
    logger.info("📤 HuggingFace Dataset Upload")
    logger.info("=" * 60)
    
    # Check if data directory exists
    if not DATA_DIR.exists():
        logger.error(f"Data directory not found: {DATA_DIR}")
        return
    
    # Convert episodes to HuggingFace format
    dataset = convert_to_hf_format(DATA_DIR)
    if dataset is None:
        return
    
    # Count episodes
    num_episodes = len(set(dataset['episode_num']))
    total_frames = len(dataset)
    
    logger.info(f"\n📊 Dataset Summary:")
    logger.info(f"  Episodes: {num_episodes}")
    logger.info(f"  Total Frames: {total_frames}")
    logger.info(f"  Features: {list(dataset.features.keys())}")
    
    # Create repository ID
    repo_id = f"{HF_USERNAME}/{DATASET_NAME}"
    logger.info(f"\n🚀 Uploading to: {repo_id}")
    
    try:
        # Create repo if it doesn't exist
        api = HfApi()
        logger.info("Creating/checking repository...")
        create_repo(repo_id, repo_type="dataset", exist_ok=True)
        
        # Create dataset card
        logger.info("Creating dataset card...")
        card_content = create_dataset_card(repo_id, num_episodes, total_frames)
        
        # Upload dataset
        logger.info("Uploading dataset (this may take a while)...")
        dataset.push_to_hub(repo_id)
        
        # Upload dataset card
        api.upload_file(
            path_or_fileobj=card_content.encode(),
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type="dataset",
        )
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Upload Complete!")
        logger.info("=" * 60)
        logger.info(f"View your dataset at:")
        logger.info(f"https://huggingface.co/datasets/{repo_id}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n❌ Upload failed: {e}")
        logger.error("\nMake sure you're logged in:")
        logger.error("  huggingface-cli login")


if __name__ == "__main__":
    main()

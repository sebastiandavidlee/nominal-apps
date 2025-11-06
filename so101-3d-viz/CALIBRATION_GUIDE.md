# SO-101 3D Visualization Calibration Guide

## Quick Tuning Instructions

The visualization script now has **configurable offsets and multipliers** that you can tune to match your real robot to the simulation.

### Configuration Variables (in `so101_visualize.py`)

1. **`JOINT_ENCODER_OFFSETS`** - Add a constant encoder offset (0-4095) to each joint
   - Add these values directly to the encoder reading
   - Positive values shift the position forward
   - Negative values shift the position backward
   - Much easier to work with than radians!

2. **`JOINT_MULTIPLIERS`** - Multiply the joint angle (use -1 to flip direction)
   - Set to `1.0` for normal direction
   - Set to `-1.0` to invert the joint rotation
   - Use this if a joint moves in the opposite direction

3. **`HOME_POSITIONS`** - The encoder value (0-4095) that represents zero angle
   - These define what position is considered "neutral"
   - Usually around 2048 (middle of range)
   - Set these to your actual calibrated home positions

### Calibration Process

1. **Start the visualization**
   ```bash
   # In Nominal Connect, run the script
   ```

2. **Check initial alignment**
   - Look at the 3D model
   - Compare to your real robot
   - The script logs current angles every second

3. **Identify misalignments**
   - Which joints are oriented incorrectly?
   - Are they inverted (moving opposite direction)?
   - Are they offset by a constant amount?

4. **Tune iteratively**
   - **If joint moves backwards**: Set multiplier to `-1.0`
   - **If joint is offset**: Adjust encoder offset (e.g., +500, -200)
   - Stop the script (Ctrl+C in terminal)
   - Edit the values in `so101_visualize.py`
   - Restart the script

5. **Reading encoder offsets from logs**
   - The script logs current encoder values every second
   - Move your real robot to match the simulation's zero position
   - Read the encoder value from the log
   - Calculate offset = (desired_value - current_value)
   - Update `JOINT_ENCODER_OFFSETS` with this value

### Example Configuration

```python
# If shoulder lift needs to move 500 encoder ticks and is inverted
JOINT_ENCODER_OFFSETS = {
    1: 0,      # shoulder_pan - looks good
    2: 500,    # shoulder_lift - add 500 encoder ticks
    3: -200,   # elbow - subtract 200 encoder ticks
    4: 0,      # wrist_1 - looks good
    5: 0,      # wrist_2 - looks good
    6: 0,      # wrist_3 - looks good
}

JOINT_MULTIPLIERS = {
    1: 1.0,   # shoulder_pan - correct direction
    2: -1.0,  # shoulder_lift - inverted
    3: 1.0,   # elbow - correct direction
    4: 1.0,   # wrist_1 - correct direction
    5: 1.0,   # wrist_2 - correct direction
    6: 1.0,   # wrist_3 - correct direction
}

HOME_POSITIONS = {
    1: 2048,  # Can use your actual home positions from so101_find_home.py
    2: 1850,
    3: 2007,
    4: 2495,
    5: 2060,
    6: 2300,
}
```

### Joint Names Reference

| Motor ID | Joint Name          | Description           |
|----------|--------------------|-----------------------|
| 1        | shoulder_pan_joint  | Base rotation         |
| 2        | shoulder_lift_joint | Shoulder up/down      |
| 3        | elbow_joint         | Elbow bend            |
| 4        | wrist_1_joint       | Wrist flex            |
| 5        | wrist_2_joint       | Wrist roll            |
| 6        | wrist_3_joint       | Gripper rotation      |

### Debug Output

The script now logs:
- Configuration on startup (home positions, offsets, multipliers)
- Current joint angles every second (in radians + encoder values)

Use this info to verify your changes are working!

### Tips

- Make small changes and test frequently
- Start with joint 1 and work your way up
- Use the plots in the UI to see angle changes in real-time
- The encoder values (0-4095) are logged for reference
- Move one joint at a time to identify which needs adjustment


# SO-101 URDF Configuration

## Current Setup

We're using the **official SO-101 URDF** from TheRobotStudio's SO-ARM100 repository.

### URDF File: `urdf/so101_renamed.urdf`

This is based on `so101_new_calib.urdf` from the official repo with modifications:

1. **Source**: Generated from OnShape CAD using [onshape-to-robot](https://github.com/Rhoban/onshape-to-robot)
2. **Mesh paths**: Changed from `assets/` to `meshes/visual/` and `meshes/collision/`
3. **Joint names**: Renamed to match your visualization script:
   - `shoulder_pan` → `shoulder_pan_joint` (motor 1)
   - `shoulder_lift` → `shoulder_lift_joint` (motor 2)  
   - `elbow_flex` → `elbow_joint` (motor 3)
   - `wrist_flex` → `wrist_1_joint` (motor 4)
   - `wrist_roll` → `wrist_2_joint` (motor 5)
   - `gripper` → `wrist_3_joint` (motor 6)

## Mesh Files

All STL files copied from official repo:
- **Location**: `urdf/meshes/visual/` and `urdf/meshes/collision/`
- **Count**: 13 STL files per directory
- **Format**: Binary STL from OnShape CAD

### Mesh List:
- `base_motor_holder_so101_v1.stl`
- `base_so101_v2.stl`
- `motor_holder_so101_base_v1.stl`
- `motor_holder_so101_wrist_v1.stl`
- `moving_jaw_so101_v1.stl`
- `rotation_pitch_so101_v1.stl`
- `sts3215_03a_no_horn_v1.stl`
- `sts3215_03a_v1.stl` (motor body)
- `under_arm_so101_v1.stl`
- `upper_arm_so101_v1.stl`
- `waveshare_mounting_plate_so101_v2.stl`
- `wrist_roll_follower_so101_v1.stl`
- `wrist_roll_pitch_so101_v2.stl`

## Calibration

The URDF uses "**New Calibration**" method where:
- Each joint's zero position = **middle of joint range**
- This matches typical robot convention

From the official README:
> Each joint's virtual zero is set to the **middle** of its joint range.

## Key URDF Features

### Correct Structure:
✅ All mesh origins (xyz, rpy) are from OnShape CAD export  
✅ Joint hierarchy matches physical robot  
✅ Link transforms are correct  
✅ Multiple visual/collision meshes per link (motors + structural parts)  
✅ Relative mesh paths (no ROS package:// needed)

### Joint Limits (from official URDF):
- `shoulder_pan_joint`: -1.92 to +1.92 rad
- `shoulder_lift_joint`: -1.75 to +1.75 rad  
- `elbow_joint`: -1.69 to +1.69 rad
- `wrist_1_joint`: -1.66 to +1.66 rad
- `wrist_2_joint`: -2.74 to +2.84 rad
- `wrist_3_joint`: -0.17 to +1.75 rad

## If Meshes Look Wrong

If the 3D visualization still shows misaligned meshes, possible causes:

1. **Joint Offset Issue**: Motor encoder zero ≠ URDF joint zero
   - Solution: Adjust `JOINT_ENCODER_OFFSETS` in `so101_visualize.py`

2. **Joint Direction Issue**: Motor moves opposite to URDF expectation
   - Solution: Set `JOINT_MULTIPLIERS` to `-1.0` for inverted joints

3. **Nominal Connect Mesh Loading**: The platform may handle mesh loading differently
   - The mesh paths are correct relative paths
   - All meshes exist in the correct locations

## Files Created

- ✅ `urdf/so101_renamed.urdf` - Main URDF file (official + renamed joints)
- ✅ `urdf/meshes/visual/*.stl` - Visual meshes (13 files)
- ✅ `urdf/meshes/collision/*.stl` - Collision meshes (13 files)
- ✅ `app.connect` - Updated to use `so101_renamed.urdf`
- ✅ `so101_visualize.py` - Motor position → joint angle conversion
- ✅ `CALIBRATION_GUIDE.md` - How to tune encoder offsets

## Official Repository

Source: https://github.com/TheRobotStudio/SO-ARM100
- Path: `Simulation/SO101/`
- URDF: `so101_new_calib.urdf`
- Meshes: `assets/*.stl`

The URDF is production-quality and used in their LeRobot integration.

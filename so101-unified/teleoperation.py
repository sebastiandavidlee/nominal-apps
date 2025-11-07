"""
SO-101 Robot Arm Teleoperation

Reads motor positions from Arm 1 (leader) and commands them to Arm 2 (follower).
This creates a leader-follower setup where moving Arm 1 causes Arm 2 to mirror.

Streams motor position data for visualization (plots only, no 3D, no cameras).
"""

import serial
import time
import traceback
import connect_python
from feetech_interface import (
    get_motor_position,
    set_motor_position,
    set_motor_mode,
    set_motor_speed,
    enable_motor_torque
)

# --- Configuration ---
LEADER_PORT = "/dev/ttyACM1"    # Arm 1 - we READ from this
FOLLOWER_PORT = "/dev/ttyACM0"  # Arm 2 - we WRITE to this
BAUD_RATE = 1_000_000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
TIMEOUT = 0.05

UPDATE_RATE = 50.0  # Hz - control loop frequency

logger = connect_python.get_logger(__name__)


@connect_python.main
def main(connect_client: connect_python.Client):
    """Main teleoperation loop - reads leader, commands follower."""
    ser_leader = None
    ser_follower = None
    
    try:
        # Connect to both arms
        logger.info(f"Connecting to LEADER arm at {LEADER_PORT}...")
        ser_leader = serial.Serial(LEADER_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Leader connected!")
        
        logger.info(f"Connecting to FOLLOWER arm at {FOLLOWER_PORT}...")
        ser_follower = serial.Serial(FOLLOWER_PORT, BAUD_RATE, timeout=TIMEOUT)
        logger.info("Follower connected!")
        
        # Configure follower motors for position control
        logger.info("\nConfiguring follower arm motors...")
        for motor_id in MOTOR_IDS:
            set_motor_mode(ser_follower, motor_id, mode=0)  # Position control
            set_motor_speed(ser_follower, motor_id, speed=0)  # Maximum speed
            enable_motor_torque(ser_follower, motor_id)
        logger.info("Follower arm ready!")
        
        # Clear streams
        connect_client.clear_stream("leader_positions")
        connect_client.clear_stream("follower_commands")
        
        logger.info("\n🤖 Teleoperation ACTIVE! Move the leader arm (ACM1)...")
        logger.info("Press Ctrl+C to stop.\n")
        
        loop_count = 0
        
        # Main teleoperation loop
        while True:
            timestamp = time.time()
            loop_count += 1
            
            # Read all positions from leader arm
            leader_positions = {}
            for motor_id in MOTOR_IDS:
                pos = get_motor_position(ser_leader, motor_id)
                if pos is not None:
                    leader_positions[motor_id] = pos
            
            # Command follower arm to match leader positions
            for motor_id in MOTOR_IDS:
                if motor_id in leader_positions:
                    target_position = leader_positions[motor_id]
                    set_motor_position(ser_follower, motor_id, target_position)
            
            # Log status every 2 seconds
            if loop_count % (int(UPDATE_RATE) * 2) == 0:
                logger.info(f"Leader positions: {leader_positions}")
            
            # Stream leader positions
            if len(leader_positions) == len(MOTOR_IDS):
                connect_client.stream(
                    "leader_positions",
                    timestamp,
                    names=[f"motor_{i}" for i in MOTOR_IDS],
                    values=[leader_positions[i] for i in MOTOR_IDS]
                )
                
                # Stream follower commands (same as leader in 1:1 mapping)
                connect_client.stream(
                    "follower_commands",
                    timestamp,
                    names=[f"motor_{i}" for i in MOTOR_IDS],
                    values=[leader_positions[i] for i in MOTOR_IDS]
                )
            
            # Wait for next update
            time.sleep(1.0 / UPDATE_RATE)
        
    except serial.SerialException as e:
        logger.error(f"Serial connection error: {e}")
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Teleoperation stopped by user.")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        
    finally:
        if ser_leader and ser_leader.is_open:
            ser_leader.close()
            logger.info("Leader serial connection closed.")
        if ser_follower and ser_follower.is_open:
            ser_follower.close()
            logger.info("Follower serial connection closed.")


if __name__ == "__main__":
    main()

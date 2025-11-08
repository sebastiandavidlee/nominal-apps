"""
Feetech Servo Motor Interface

Shared functions for communicating with Feetech SCS servo motors.
Contains low-level protocol implementation for reading/writing motor registers.

Protocol: Feetech SCS (Serial Controlled Servo)
"""

import serial
import time

# Feetech Protocol Constants
SCS_WRITE = 0x03
SCS_READ = 0x02
SCS_GOAL_POSITION_L = 42
SCS_PRESENT_POSITION_L = 56
SCS_MODE = 33
SCS_GOAL_SPEED_L = 46
SCS_TORQUE_ENABLE = 40

# Encoder range
ENCODER_MAX = 4095


def calculate_checksum(packet):
    """
    Calculate Feetech protocol checksum.
    
    Args:
        packet: List of bytes (without checksum)
        
    Returns:
        Checksum byte (0-255)
    """
    total = sum(packet[2:])
    return ~total & 0xFF


def read_motor_register(ser, motor_id, register_address, num_bytes=2):
    """
    Read a register from a Feetech servo motor.
    
    Args:
        ser: Serial port object
        motor_id: Motor ID (1-6 typically)
        register_address: Register to read from
        num_bytes: Number of bytes to read (1 or 2)
        
    Returns:
        Register value as integer, or None if read fails
    """
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 4, SCS_READ, register_address, num_bytes
    ]
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    
    ser.write(packet)
    time.sleep(0.001)
    response = ser.read(5 + num_bytes + 1)
    
    if len(response) >= (5 + num_bytes) and response[0] == 0xFF and response[1] == 0xFF:
        if num_bytes == 2:
            return response[5] | (response[6] << 8)  # Combine low + high bytes
        else:
            return response[5]
    return None


def get_motor_position(ser, motor_id):
    """
    Read current position from a motor.
    
    Args:
        ser: Serial port object
        motor_id: Motor ID (1-6 typically)
        
    Returns:
        Position value (0-4095), or None if read fails
    """
    return read_motor_register(ser, motor_id, SCS_PRESENT_POSITION_L, 2)


def set_motor_position(ser, motor_id, position):
    """
    Send position command to a motor.
    
    Args:
        ser: Serial port object
        motor_id: Motor ID (1-6 typically)
        position: Target position (0-4095)
        
    Returns:
        True if command sent successfully
    """
    position = max(0, min(ENCODER_MAX, int(position)))
    pos_low = position & 0xFF
    pos_high = (position >> 8) & 0xFF
    
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 5, SCS_WRITE, 
        SCS_GOAL_POSITION_L, pos_low, pos_high
    ]
    
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.001)
    if ser.in_waiting > 0:
        ser.read(ser.in_waiting)  # Clear response buffer
    return True


def set_motor_mode(ser, motor_id, mode=0):
    """
    Set motor control mode.
    
    Args:
        ser: Serial port object
        motor_id: Motor ID (1-6 typically)
        mode: Control mode (0=position control, 1=speed control)
        
    Returns:
        True if command sent successfully
    """
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 4, SCS_WRITE, SCS_MODE, mode
    ]
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.01)
    return True


def set_motor_speed(ser, motor_id, speed=500):
    """
    Set motor movement speed.
    
    Args:
        ser: Serial port object
        motor_id: Motor ID (1-6 typically)
        speed: Speed value (0=maximum, 1-4095=limited speed)
        
    Returns:
        True if command sent successfully
    """
    speed_low = speed & 0xFF
    speed_high = (speed >> 8) & 0xFF
    
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 5, SCS_WRITE, 
        SCS_GOAL_SPEED_L, speed_low, speed_high
    ]
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.005)
    return True


def enable_motor_torque(ser, motor_id):
    """
    Enable motor torque (allows motor to hold position and move).
    
    Args:
        ser: Serial port object
        motor_id: Motor ID (1-6 typically)
        
    Returns:
        True if command sent successfully
    """
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 4, SCS_WRITE, SCS_TORQUE_ENABLE, 1
    ]
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.005)
    return True


def disable_motor_torque(ser, motor_id):
    """
    Disable motor torque (motor becomes freely movable).
    
    Args:
        ser: Serial port object
        motor_id: Motor ID (1-6 typically)
        
    Returns:
        True if command sent successfully
    """
    packet_without_checksum = [
        0xFF, 0xFF, motor_id, 4, SCS_WRITE, SCS_TORQUE_ENABLE, 0
    ]
    packet = bytes(packet_without_checksum + [calculate_checksum(packet_without_checksum)])
    ser.write(packet)
    time.sleep(0.005)
    return True

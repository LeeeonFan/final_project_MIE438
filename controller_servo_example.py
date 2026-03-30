#!/usr/bin/env python3
"""
Example: Using merged ControllerManager to read PS5 controller and get servo commands.

This demonstrates how to use the ControllerManager class to:
1. Read PS5 controller input
2. Convert to servo PWM commands
3. Use the commands to control servo hardware
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controller.controller import ControllerManager
import time

def main():
    print("Initializing ControllerManager...")
    controller = ControllerManager()
    
    print("Waiting for controller connection...")
    while not controller.is_connected():
        time.sleep(0.1)
    
    print(f"✓ Controller connected: {controller.joystick.get_name()}")
    print("\nMove right stick left/right to control servo steering")
    print("Press Ctrl+C to exit\n")
    
    try:
        while True:
            # Get servo commands based on controller input
            servo_cmd = controller.get_servo_commands()
            
            if servo_cmd:
                steering_angle = servo_cmd["steering_angle_input"]
                pwm_value = servo_cmd["steering_pwm_value_us"]
                
                print(f"Steering: {steering_angle:+.1f}° → PWM: {pwm_value} µs", end='\r')
                
                # TODO: Send pwm_value to actual servo hardware
                # Example:
                # pwm_controller.set_pulse_width(pwm_value)
                
            time.sleep(0.05)  # 20 Hz update rate
            
    except KeyboardInterrupt:
        print("\n\nShutdown requested")

if __name__ == "__main__":
    main()

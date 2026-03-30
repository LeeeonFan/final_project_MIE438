#!/usr/bin/env python3
"""
Example: Using merged ControllerManager to read PS5 controller and get commands.

This mirrors the teleop_client.py pattern but uses PS5 controller input.
Control mapping:
  - Left Stick Y: throttle (forward/backward)
  - Right Stick X: steering (left/right)
  
Alternatively, set use_triggers_for_throttle=True in ControllerManager:
  - R2: forward
  - L2: backward
  - Right Stick X: steering
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controller.controller import ControllerManager
import time

def main():
    print("Initializing ControllerManager...")
    controller = ControllerManager(use_triggers_for_throttle=False)
    
    print("Waiting for controller connection...")
    while not controller.is_connected():
        time.sleep(0.1)
    
    print(f"✓ Controller connected: {controller.joystick.get_name()}")
    print("\nControl mapping:")
    print("  Left Stick Y: throttle (up=forward, down=backward)")
    print("  Right Stick X: steering (left=-1, right=+1)")
    print("  Steering angle range: ±{:.0f}°".format(controller.servo_controller.max_steering_angle))
    print("\nPress Ctrl+C to exit\n")
    
    try:
        while True:
            # Get command payload (similar to teleop_client)
            payload = controller.get_command_payload()
            
            if payload:
                throttle = payload["throttle"]
                steering = payload["steering"]
                pwm = payload["steering_pwm_us"]
                angle = payload["steering_angle"]
                
                print(
                    f"throttle={throttle:+.2f}  steering={steering:+.2f}  "
                    f"angle={angle:+.1f}°  pwm={pwm}µs",
                    end='\r'
                )
                
                # TODO: Send to robot
                # Example:
                # socket.sendto(json.dumps(payload), (robot_ip, robot_port))
                
            time.sleep(0.05)  # 20 Hz update rate
            
    except KeyboardInterrupt:
        print("\n\nShutdown requested")

if __name__ == "__main__":
    main()

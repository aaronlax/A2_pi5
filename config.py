"""
Configuration file for the A2 Pi Client
"""

import os
import logging

# Version
VERSION = "1.0.0"

# System settings
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() == 'true'

# Server settings
SERVER_ADDRESS = os.environ.get('SERVER_ADDRESS', '192.168.50.86')  # WebSocket server address
SERVER_PORT = int(os.environ.get('SERVER_PORT', '5000'))

# Camera settings
FRAME_WIDTH = int(os.environ.get('FRAME_WIDTH', '640'))
FRAME_HEIGHT = int(os.environ.get('FRAME_HEIGHT', '480'))
FRAME_RATE = int(os.environ.get('FRAME_RATE', '30'))
JPEG_QUALITY = int(os.environ.get('JPEG_QUALITY', '75'))
SEND_EVERY_N_FRAMES = int(os.environ.get('SEND_EVERY_N_FRAMES', '2'))  # Send every 2nd frame

# Telemetry settings
TELEMETRY_INTERVAL = float(os.environ.get('TELEMETRY_INTERVAL', '1.0'))  # Send telemetry every 1 second

# Servo settings
PAN_CHANNEL = 0
TILT_CHANNEL = 1
ROLL_CHANNEL = 2
PAN_LIMITS = (-80, 80)
TILT_LIMITS = (-45, 45)
ROLL_LIMITS = (-30, 30)
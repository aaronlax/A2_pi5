# A2

# A2 Project README

## Overview

The A2 project is a sophisticated client-server system designed to operate on a Raspberry Pi with various hardware components. This system is primarily focused on capturing and processing video and audio data, controlling servo motors based on server commands, and facilitating robust communication via WebSockets. The project is ideal for applications requiring real-time video and audio monitoring and mechanical manipulation via servos, such as automated monitoring systems or interactive robots.

## Main Components

### 1. **WebSocketClient**
   - Manages WebSocket connections.
   - Handles communication with the server, sending telemetry and camera frames, and receiving commands.

### 2. **RealSenseCamera**
   - Interfaces with an Intel RealSense camera.
   - Manages capture and processing of color and depth frames.
   - Provides functionalities for frame compression and optimization for network transmission.

### 3. **ServoController**
   - Controls servo motors to adjust physical movements based on server commands.
   - Manages servo hardware for accurate positioning.

### 4. **AudioDetector**
   - Analyzes audio signals to determine levels and directions.
   - Essential for environments where audio feedback is crucial.

### 5. **MessageHandler**
   - Facilitates robust message communication to/from the server.
   - Processes incoming messages and sends appropriate responses.

## Setup and Installation

1. **Hardware Setup:**
   - Ensure that a Raspberry Pi is set up with an Intel RealSense camera and servo motors correctly connected.
   - Connect audio detection hardware if audio functionality is required.

2. **Software Requirements:**
   - Python 3.x
   - Libraries: `websockets`, `pyrealsense2`, `cv2`, `asyncio`

3. **Installation:**
   ```bash
   git clone https://github.com/your-repository/a2-project.git
   cd a2-project
   pip install -r requirements.txt
   ```

## Usage Examples

1. **Starting the System:**
   ```python
   from client import main
   main()
   ```

2. **Sending a Command to Move a Servo:**
   ```python
   from controller import ServoController
   servo = ServoController(config={"servo_pins": {"pan": 17, "tilt": 18}})
   servo.move_to("pan", 90)  # Move pan servo to 90 degrees
   ```

3. **Capturing a Frame from the Camera:**
   ```python
   from realsense_camera import RealSenseCamera
   camera = RealSenseCamera(width=1280, height=720, fps=30)
   camera.start_streaming()
   color_frame = camera.get_color_frame()
   depth_frame = camera.get_depth_frame()
   camera.stop_streaming()
   ```

## API Documentation

- **WebSocketClient:** `connect()`, `send_data(data)`, `receive()`
- **RealSenseCamera:** `start_streaming()`, `get_color_frame()`, `get_depth_frame()`
- **ServoController:** `move_to(position)`
- **AudioDetector:** `start()`, `stop()`, `set_detection_callback(callback)`
- **MessageHandler:** `send(message)`, `receive()`, `process(message)`

## Configuration Options

- **Server Settings:** `SERVER_ADDRESS`, `SERVER_PORT`
- **Camera Settings:** `FRAME_WIDTH`, `FRAME_HEIGHT`, `FRAME_RATE`
- **Telemetry Settings:** `TELEMETRY_INTERVAL`
- **Servo Settings:** `PAN_CHANNEL`, `TILT_CHANNEL`, `ROLL_CHANNEL`, `PAN_LIMITS`, `TILT_LIMITS`, `ROLL_LIMITS`
- **Servo Controller Initialization:** `servo_pins`, `min_pulse_width`, `max_pulse_width`, `frequency`

These settings can be modified in the `config.py` file or set as environment variables.

## Conclusion

The A2 project offers a powerful platform for real-time interaction and monitoring using a Raspberry Pi. It integrates advanced video and audio processing capabilities with mechanical control, making it suitable for a wide range of applications in automation and robotics.

---
*This README was automatically generated on 2025-03-21 09:35:39*

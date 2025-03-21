#!/usr/bin/env python3
import asyncio
import websockets
import logging
import json
import time
import base64
import cv2
import numpy as np
import socket
import sys
import argparse
import os
import traceback
from queue import Queue, Empty
import statistics
from typing import Dict, List, Optional, Any
import random

# Import hardware modules
from hardware.camera.realsense_camera import RealSenseCamera
from hardware.servo.controller import ServoController
from hardware.audio.audio_detector import AudioDetector

# Import config and utilities
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("client_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='A2 Pi Client')
parser.add_argument('--server', default=config.SERVER_ADDRESS, help='WebSocket server hostname or IP')
parser.add_argument('--port', type=int, default=config.SERVER_PORT, help='WebSocket server port')
parser.add_argument('--debug', action='store_true', help='Enable debug logging')
parser.add_argument('--simulation', action='store_true', help='Run in simulation mode without hardware')
args = parser.parse_args()

# Set log level
if args.debug:
    logger.setLevel(logging.DEBUG)

# Configuration
SERVER_ADDRESS = args.server
SERVER_PORT = args.port
SIMULATION_MODE = args.simulation or config.SIMULATION_MODE
WS_URL = f"ws://{SERVER_ADDRESS}:{SERVER_PORT}/pi"
RECONNECT_DELAY = 5
MAX_RECONNECT_ATTEMPTS = 10

class WebSocketClient:
    def __init__(self, camera_manager, servo_controller, audio_detector=None):
        """Initialize the WebSocket client"""
        self.camera = camera_manager
        self.servo = servo_controller
        self.audio = audio_detector
        
        self.websocket = None
        self.connected = False
        self.stopping = False
        self.reconnect_attempt = 1
        
        self.frame_count = 0
        self.last_frame_time = 0
        self.last_telemetry_time = 0
        
        # Set up a queue for frames
        self.frame_queue = asyncio.Queue(maxsize=5)
    
    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            # Check server connectivity first
            if not await self.check_server_connectivity():
                logger.warning("Server connectivity check failed, but still trying to connect...")
            
            # Connect with timeout
            logger.info(f"Connecting to {WS_URL}...")
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    WS_URL,
                    ping_interval=None,  # We'll handle pings manually
                    close_timeout=2,     # Quicker close on errors
                    max_size=20*1024*1024,  # 20MB max message size
                ),
                timeout=10  # 10 second timeout
            )
            
            self.connected = True
            logger.info("Connected to WebSocket server successfully")
            
            # Send hello message
            hello_message = json.dumps({
                "type": "hello",
                "client": "pi",
                "timestamp": time.time(),
                "hostname": socket.gethostname(),
                "simulation_mode": SIMULATION_MODE
            })
            
            logger.info("Sending hello message to server")
            await self.websocket.send(hello_message)
            
            return True
        
        except asyncio.TimeoutError:
            logger.error("Connection timeout")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            logger.error(traceback.format_exc())
            self.connected = False
            return False
    
    async def check_server_connectivity(self):
        """Check if the server is reachable"""
        try:
            # Try to resolve hostname
            ip = socket.gethostbyname(SERVER_ADDRESS)
            logger.info(f"Resolved {SERVER_ADDRESS} to {ip}")
            
            # Try to connect to the port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((ip, SERVER_PORT))
            s.close()
            logger.info(f"Successfully connected to {ip}:{SERVER_PORT}")
            return True
        except Exception as e:
            logger.error(f"Connectivity check failed: {e}")
            return False
    
    async def process_frames(self):
        """Process and send frames from the camera"""
        while self.connected and not self.stopping:
            try:
                # Get a frame from the camera
                frame = self.camera.get_color_frame()
                
                if frame is None:
                    logger.warning("Failed to get frame from camera")
                    await asyncio.sleep(0.1)
                    continue
                
                # Increment frame count
                self.frame_count += 1
                
                # Only process every N frames to reduce load
                if self.frame_count % config.SEND_EVERY_N_FRAMES == 0:
                    # Calculate FPS
                    now = time.time()
                    if self.last_frame_time > 0:
                        fps = 1.0 / (now - self.last_frame_time)
                    else:
                        fps = 30.0
                    self.last_frame_time = now
                    
                    # Encode frame to JPEG
                    encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALITY]
                    ret, jpeg = cv2.imencode('.jpg', frame, encode_params)
                    
                    if not ret:
                        logger.error("Failed to encode frame")
                        continue
                    
                    # Convert to base64 for sending via WebSocket
                    frame_data = base64.b64encode(jpeg.tobytes()).decode('utf-8')
                    
                    # Get additional camera data if available
                    camera_info = {}
                    depth_data = None
                    
                    if hasattr(self.camera, 'get_camera_info'):
                        camera_info = self.camera.get_camera_info()
                    
                    if hasattr(self.camera, 'get_depth_frame'):
                        depth_frame = self.camera.get_depth_frame()
                        if depth_frame is not None:
                            # Encode depth frame as base64
                            depth_png = cv2.imencode('.png', depth_frame)[1].tobytes()
                            depth_data = base64.b64encode(depth_png).decode('utf-8')
                    
                    # Create frame message
                    frame_message = {
                        "type": "frame",
                        "frame_id": self.frame_count,
                        "timestamp": time.time(),
                        "image": frame_data,
                        "depth_data": depth_data,
                        "camera_info": {
                            "model": camera_info.get("name", "D455"),
                            "serial": camera_info.get("serial", "unknown"),
                            "resolution": [self.camera.width, self.camera.height]
                        },
                        "depth_scale": 0.001,  # Meters per unit
                        "fps": fps
                    }
                    
                    # Send the frame
                    await self.websocket.send(json.dumps(frame_message))
                    logger.debug(f"Sent frame {self.frame_count}")
                
                # Sleep briefly to avoid overwhelming the system
                await asyncio.sleep(0.01)
            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed while sending frame")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"Error in frame processing: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(0.5)
    
    async def send_telemetry(self):
        """Send periodic telemetry data"""
        while self.connected and not self.stopping:
            try:
                # Only send telemetry every few seconds
                now = time.time()
                if now - self.last_telemetry_time < config.TELEMETRY_INTERVAL:
                    await asyncio.sleep(0.1)
                    continue
                
                self.last_telemetry_time = now
                
                # Collect telemetry data
                telemetry = {
                    "type": "telemetry",
                    "timestamp": now,
                    "system": {
                        "hostname": socket.gethostname(),
                        "uptime": self.get_uptime(),
                        "temperature": self.get_cpu_temperature(),
                        "memory": self.get_memory_usage()
                    },
                    "servo": self.servo.get_status(),
                }
                
                # Add audio data if available
                if self.audio:
                    audio_levels = self.audio.read_all_microphones()
                    telemetry["audio"] = {
                        "levels": audio_levels,
                        "direction": self.audio.detect_direction()
                    }
                
                # Send telemetry
                await self.websocket.send(json.dumps(telemetry))
                logger.debug("Sent telemetry data")
            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed while sending telemetry")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"Error sending telemetry: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(0.5)
    
    async def receive_data(self):
        """Receive and handle incoming messages from the server"""
        while self.connected and not self.stopping:
            try:
                # Receive message
                message = await self.websocket.recv()
                
                # Parse JSON
                try:
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    logger.debug(f"Received message of type: {message_type}")
                    
                    if message_type == "control":
                        # Handle control message
                        action = data.get("action")
                        
                        if action == "move_servos":
                            # Update servo positions
                            params = data.get("params", {})
                            
                            if "pan" in params or "tilt" in params or "roll" in params:
                                # Update servo positions
                                pan = params.get("pan")
                                tilt = params.get("tilt")
                                roll = params.get("roll")
                                
                                # Move servos
                                result = self.servo.set_position(pan=pan, tilt=tilt, roll=roll)
                                
                                # Send confirmation
                                response = {
                                    "type": "control_response",
                                    "action": "move_servos",
                                    "success": True,
                                    "position": {
                                        "pan": result[0],
                                        "tilt": result[1],
                                        "roll": result[2]
                                    },
                                    "timestamp": time.time()
                                }
                                
                                await self.websocket.send(json.dumps(response))
                        
                        elif action == "center_servos":
                            # Center all servos
                            result = self.servo.center()
                            
                            # Send confirmation
                            response = {
                                "type": "control_response",
                                "action": "center_servos",
                                "success": True,
                                "position": {
                                    "pan": result[0],
                                    "tilt": result[1],
                                    "roll": result[2]
                                },
                                "timestamp": time.time()
                            }
                            
                            await self.websocket.send(json.dumps(response))
                    
                    elif message_type == "ping":
                        # Respond with pong
                        await self.websocket.send(json.dumps({
                            "type": "pong",
                            "timestamp": time.time()
                        }))
                    
                    elif message_type == "detection_result":
                        # Handle detection results
                        frame_id = data.get("frame_id")
                        detections = data.get("detections", [])
                        
                        if detections:
                            # Use detections for tracking or other purposes
                            logger.debug(f"Received {len(detections)} detections for frame {frame_id}")
                    
                    elif message_type == "welcome":
                        # Server acknowledged our connection
                        logger.info("Server acknowledged connection with welcome message")
                
                except json.JSONDecodeError:
                    logger.error("Received invalid JSON")
            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed during receive")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"Error receiving data: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(0.5)
    
    async def maintain_connection(self):
        """Send periodic heartbeats to keep the connection alive"""
        while self.connected and not self.stopping:
            try:
                # Send a ping every 30 seconds
                await asyncio.sleep(30)
                
                if self.connected:
                    await self.websocket.send(json.dumps({
                        "type": "ping",
                        "timestamp": time.time()
                    }))
                    logger.debug("Sent ping")
            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed during heartbeat")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                await asyncio.sleep(0.5)
    
    async def run_client(self):
        """Main method to run the WebSocket client"""
        logger.info("Starting WebSocket client...")
        
        while not self.stopping:
            try:
                # Connect to server
                connected = await self.connect()
                
                if connected:
                    # Start tasks
                    tasks = [
                        asyncio.create_task(self.process_frames()),
                        asyncio.create_task(self.send_telemetry()),
                        asyncio.create_task(self.receive_data()),
                        asyncio.create_task(self.maintain_connection())
                    ]
                    
                    # Wait for any task to complete (which typically means an error occurred)
                    _, pending = await asyncio.wait(
                        tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel pending tasks
                    for task in pending:
                        task.cancel()
                    
                    # If we get here, the connection was lost
                    self.connected = False
                
                # Try to reconnect if not stopping
                if not self.stopping:
                    self.reconnect_attempt += 1
                    
                    if self.reconnect_attempt > MAX_RECONNECT_ATTEMPTS:
                        logger.error(f"Exceeded maximum reconnect attempts ({MAX_RECONNECT_ATTEMPTS}), giving up")
                        return
                    
                    # Wait with exponential backoff
                    delay = min(RECONNECT_DELAY * (1.5 ** (self.reconnect_attempt - 1)), 60)
                    jitter = random.uniform(0, 2)
                    total_delay = delay + jitter
                    
                    logger.info(f"Reconnecting in {total_delay:.1f} seconds (attempt {self.reconnect_attempt}/{MAX_RECONNECT_ATTEMPTS})...")
                    await asyncio.sleep(total_delay)
            
            except Exception as e:
                logger.error(f"Error in client main loop: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop the client gracefully"""
        logger.info("Stopping client...")
        self.stopping = True
        
        # Close WebSocket connection
        if self.websocket:
            await self.websocket.close()
    
    def get_uptime(self):
        """Get system uptime in seconds"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            return uptime_seconds
        except:
            return 0
    
    def get_cpu_temperature(self):
        """Get CPU temperature in Celsius"""
        try:
            temp = 0
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp') as f:
                    temp = float(f.read()) / 1000.0
            return temp
        except:
            return 0
    
    def get_memory_usage(self):
        """Get memory usage statistics"""
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            
            mem_info = {}
            for line in lines:
                if ":" in line:
                    key, value = line.split(':')
                    value = value.strip()
                    if value.endswith('kB'):
                        value = int(value[:-2]) * 1024
                    mem_info[key.strip()] = value
            
            total = int(mem_info.get('MemTotal', 0))
            free = int(mem_info.get('MemFree', 0))
            available = int(mem_info.get('MemAvailable', 0))
            
            if total > 0:
                used_percent = 100 * (total - available) / total
            else:
                used_percent = 0
            
            return {
                "total": total,
                "free": free,
                "available": available,
                "used_percent": used_percent
            }
        except:
            return {
                "total": 0,
                "free": 0,
                "available": 0,
                "used_percent": 0
            }

def init_system():
    """Initialize all system components"""
    global SIMULATION_MODE
    logger.info("Initializing system components...")
    
    # Initialize camera
    logger.info("Initializing camera...")
    camera_manager = RealSenseCamera(
        width=config.FRAME_WIDTH,
        height=config.FRAME_HEIGHT,
        fps=config.FRAME_RATE,
        simulation_mode=SIMULATION_MODE
    )
    success = camera_manager.initialize()
    
    if success:
        logger.info("Camera initialized successfully")
        camera_manager.start_streaming()
    else:
        logger.error("Failed to initialize camera")
        if not SIMULATION_MODE:
            logger.warning("Falling back to simulation mode")
            SIMULATION_MODE = True
            camera_manager = RealSenseCamera(
                width=config.FRAME_WIDTH,
                height=config.FRAME_HEIGHT,
                fps=config.FRAME_RATE,
                simulation_mode=True
            )
            camera_manager.initialize()
            camera_manager.start_streaming()
    
    # Initialize servo controller
    logger.info("Initializing servo controller...")
    try:
        servo_config = {
            'servo_pins': {
                'pan': config.PAN_CHANNEL,
                'tilt': config.TILT_CHANNEL
            },
            'min_pulse_width': 0.5,
            'max_pulse_width': 2.5,
            'frequency': 50
        }
        servo_controller = ServoController(config=servo_config)
        servo_controller.initialize()
        logger.info("Servo controller initialized")
    except Exception as e:
        logger.error(f"Failed to initialize servo controller: {e}")
        logger.error(traceback.format_exc())
        logger.warning("Using simulated servo controller")
        servo_controller = ServoController()
    
    # Initialize audio detector
    logger.info("Initializing audio detector...")
    try:
        audio_detector = AudioDetector(simulation_mode=SIMULATION_MODE)
        audio_detector.initialize()
        logger.info("Audio detector initialized")
    except Exception as e:
        logger.error(f"Failed to initialize audio detector: {e}")
        logger.warning("Audio detection will not be available")
        audio_detector = None
    
    # Initialize WebSocket client
    logger.info("Initializing WebSocket client...")
    websocket_client = WebSocketClient(
        camera_manager=camera_manager,
        servo_controller=servo_controller,
        audio_detector=audio_detector
    )
    
    return camera_manager, servo_controller, audio_detector, websocket_client

def main():
    """Main entry point"""
    # Display startup information
    logger.info(f"A2 Pi Client v{config.VERSION}")
    logger.info(f"Server: {SERVER_ADDRESS}:{SERVER_PORT}")
    logger.info(f"Simulation mode: {SIMULATION_MODE}")
    
    # Initialize system components
    camera_manager, servo_controller, audio_detector, websocket_client = init_system()
    
    try:
        # Create and get event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the client
        loop.run_until_complete(websocket_client.run_client())
    except KeyboardInterrupt:
        logger.info("Client terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Shutdown resources
        logger.info("Shutting down...")
        
        # Stop WebSocket client
        try:
            loop.run_until_complete(websocket_client.stop())
        except:
            pass
        
        # Stop camera
        try:
            camera_manager.stop_streaming()
        except:
            pass
        
        # Reset servos to center position
        try:
            servo_controller.center()
            servo_controller.shutdown()
        except:
            pass
        
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()
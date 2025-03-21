#!/usr/bin/env python3
"""
RealSense camera interface for the Pi client.
"""

import logging
import numpy as np
import time

# Import RealSense SDK
try:
    import pyrealsense2 as rs
    REALSENSE_AVAILABLE = True
except ImportError:
    REALSENSE_AVAILABLE = False
    logging.warning("pyrealsense2 not available, using simulation mode")

class RealSenseCamera:
    """Interface for Intel RealSense camera."""
    
    def __init__(self, width=640, height=480, fps=30, simulation_mode=False, depth_enabled=True):
        """
        Initialize the RealSense camera with configuration.
        
        Args:
            width (int): Frame width
            height (int): Frame height
            fps (int): Frames per second
            simulation_mode (bool): Whether to use simulation mode
            depth_enabled (bool): Whether to enable depth stream
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.depth_enabled = depth_enabled
        self.simulation_mode = simulation_mode or not REALSENSE_AVAILABLE
        
        self.logger = logging.getLogger(__name__)
        self.pipeline = None
        self.config = None
        self.running = False
        
    def initialize(self):
        """Initialize the camera resources."""
        if self.simulation_mode:
            self.logger.info("Initializing RealSense camera in simulation mode")
            return True
            
        try:
            self.logger.info(f"Initializing RealSense camera: {self.width}x{self.height}@{self.fps}fps")
            self.pipeline = rs.pipeline()
            self.config = rs.config()
            
            # Try to find a connected device
            ctx = rs.context()
            devices = ctx.query_devices()
            if len(devices) == 0:
                self.logger.error("No RealSense devices found")
                return False
                
            self.logger.info(f"Found {len(devices)} RealSense device(s)")
            device = devices[0]
            self.logger.info(f"Using device: {device.get_info(rs.camera_info.name)}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize RealSense camera: {e}")
            return False
    
    def start_streaming(self):
        """Start the camera streaming."""
        if self.running:
            self.logger.warning("Camera already running")
            return True
            
        if self.simulation_mode:
            self.logger.info("Starting RealSense camera simulation")
            self.running = True
            return True
            
        try:
            self.logger.info("Starting RealSense camera streaming...")
            
            # Configure streams
            self.config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
            if self.depth_enabled:
                self.config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)
            
            # Start streaming
            self.pipeline.start(self.config)
            
            self.running = True
            self.logger.info("RealSense camera streaming started")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start RealSense camera streaming: {e}")
            return False
            
    def stop_streaming(self):
        """Stop the camera streaming."""
        if not self.running:
            return
            
        try:
            self.logger.info("Stopping RealSense camera streaming...")
            
            if not self.simulation_mode:
                self.pipeline.stop()
            
            self.running = False
            self.logger.info("RealSense camera streaming stopped")
        except Exception as e:
            self.logger.error(f"Error stopping RealSense camera: {e}")
            
    def get_color_frame(self):
        """
        Get the latest color frame from the camera.
        
        Returns:
            numpy.ndarray: Color image as a NumPy array, or None on failure
        """
        if not self.running:
            self.logger.error("Camera not running")
            return None
            
        try:
            if self.simulation_mode:
                # Mock implementation returns a black image
                return np.zeros((self.height, self.width, 3), dtype=np.uint8)
            
            # Get actual frame from camera
            frames = self.pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            
            if not color_frame:
                self.logger.warning("Empty color frame received")
                return None
                
            return np.asanyarray(color_frame.get_data())
        except Exception as e:
            self.logger.error(f"Error getting color frame: {e}")
            return None
            
    def get_depth_frame(self):
        """
        Get the latest depth frame from the camera.
        
        Returns:
            numpy.ndarray: Depth image as a NumPy array, or None on failure
        """
        if not self.running or not self.depth_enabled:
            self.logger.error("Depth stream not available")
            return None
            
        try:
            if self.simulation_mode:
                # Mock implementation returns a zero depth image
                return np.zeros((self.height, self.width), dtype=np.uint16)
            
            # Get actual depth frame
            frames = self.pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            
            if not depth_frame:
                self.logger.warning("Empty depth frame received")
                return None
                
            return np.asanyarray(depth_frame.get_data())
        except Exception as e:
            self.logger.error(f"Error getting depth frame: {e}")
            return None
            
    def get_camera_info(self):
        """
        Get camera information.
        
        Returns:
            dict: Camera information
        """
        info = {
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "depth_enabled": self.depth_enabled,
            "simulation_mode": self.simulation_mode
        }
        
        if not self.simulation_mode and self.running:
            try:
                # Get device information
                ctx = rs.context()
                devices = ctx.query_devices()
                if devices:
                    device = devices[0]
                    info["name"] = device.get_info(rs.camera_info.name)
                    info["serial"] = device.get_info(rs.camera_info.serial_number)
                    info["firmware"] = device.get_info(rs.camera_info.firmware_version)
            except Exception as e:
                self.logger.error(f"Error getting camera info: {e}")
        
        return info 
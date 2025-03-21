#!/usr/bin/env python3
"""
RealSense camera interface for the Pi client.
"""

import logging
import numpy as np
import time
import cv2

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
        self.profile = None
        
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
            self.profile = self.pipeline.start(self.config)
            
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

    def get_depth_scale(self):
        """Get the depth scale from the RealSense camera (meters per unit)"""
        if self.simulation_mode:
            return 0.001  # Default for simulation
        
        try:
            if not self.profile:
                return 0.001  # Default value
            
            # Get depth sensor and scale
            depth_sensor = self.profile.get_device().first_depth_sensor()
            depth_scale = depth_sensor.get_depth_scale()
            
            return depth_scale
        except Exception as e:
            self.logger.error(f"Error getting depth scale: {e}")
            return 0.001  # Default value

    def optimize_depth_for_transfer(self, depth_frame):
        """
        Optimize a depth frame for network transfer.
        
        This function can be used to reduce the size of depth data before
        sending it over the network, while preserving depth values.
        
        Args:
            depth_frame: Raw depth frame from RealSense
            
        Returns:
            Optimized depth frame for transfer
        """
        if depth_frame is None:
            return None
        
        try:
            # Check for invalid/zero values
            invalid_mask = depth_frame == 0
            
            # Scale to uint16 range for PNG compression
            # This preserves depth precision while allowing for efficient PNG compression
            depth_frame = depth_frame.astype(np.uint16)
            
            # Apply invalid mask back (important to keep zero as invalid)
            depth_frame[invalid_mask] = 0
            
            return depth_frame
        except Exception as e:
            self.logger.error(f"Error optimizing depth frame: {e}")
            return depth_frame

    def apply_depth_filter(self, depth_frame):
        """
        Apply filters to depth frame to reduce noise and fill holes.
        
        Args:
            depth_frame: Raw depth frame from RealSense
            
        Returns:
            Filtered depth frame
        """
        if self.simulation_mode or depth_frame is None:
            return depth_frame
        
        try:
            import pyrealsense2 as rs
            
            # Create filters
            dec_filter = rs.decimation_filter()  # Reduces resolution
            spat_filter = rs.spatial_filter()    # Smooths and fills small holes
            temp_filter = rs.temporal_filter()   # Reduces temporal noise
            
            # Convert numpy array to rs frame
            depth_frame_rs = rs.depth_frame()
            
            # Apply filters
            filtered_frame = dec_filter.process(depth_frame_rs)
            filtered_frame = spat_filter.process(filtered_frame)
            filtered_frame = temp_filter.process(filtered_frame)
            
            # Convert back to numpy array
            filtered_depth = np.asanyarray(filtered_frame.get_data())
            
            return filtered_depth
        except Exception as e:
            self.logger.error(f"Error filtering depth frame: {e}")
            return depth_frame

    def compress_depth(self, depth_frame, quality=9):
        """
        Compress a depth frame for efficient network transmission.
        
        Args:
            depth_frame: Depth frame as numpy array (uint16)
            quality: PNG compression level (0-9)
            
        Returns:
            Compressed depth frame as bytes
        """
        if depth_frame is None:
            return None
        
        try:
            # Ensure frame is uint16
            if depth_frame.dtype != np.uint16:
                depth_frame = depth_frame.astype(np.uint16)
            
            # Compress with PNG (best for depth data)
            encode_param = [cv2.IMWRITE_PNG_COMPRESSION, quality]
            _, compressed = cv2.imencode('.png', depth_frame, encode_param)
            
            return compressed.tobytes()
        except Exception as e:
            self.logger.error(f"Error compressing depth frame: {e}")
            return None

    def decompress_depth(self, compressed_bytes):
        """
        Decompress a depth frame from bytes.
        
        Args:
            compressed_bytes: Compressed depth frame as bytes
            
        Returns:
            Decompressed depth frame as numpy array
        """
        if compressed_bytes is None:
            return None
        
        try:
            # Decode PNG
            data = np.frombuffer(compressed_bytes, dtype=np.uint8)
            depth_frame = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
            
            return depth_frame
        except Exception as e:
            self.logger.error(f"Error decompressing depth frame: {e}")
            return None 
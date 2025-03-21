#!/usr/bin/env python3
"""
Test script for Intel RealSense D455 camera on Raspberry Pi 5
This script verifies that the D455 camera is properly connected and functioning
"""

import sys
import time
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Intel RealSense D455 Camera Test")
parser.add_argument('--record', action='store_true', help='Record images to disk')
parser.add_argument('--duration', type=int, default=30, help='Duration of the test in seconds')
args = parser.parse_args()

# Import required libraries
try:
    import numpy as np
    import cv2
    print("OpenCV and NumPy libraries loaded successfully")
except ImportError as e:
    print(f"Error: {e}")
    print("Please install OpenCV and NumPy: pip install opencv-python numpy")
    sys.exit(1)

# Try to import pyrealsense2
try:
    import pyrealsense2 as rs
    print("Intel RealSense library loaded successfully")
    # Check version if available, otherwise just note that it's loaded
    try:
        version = rs.__version__
        print(f"Library version: {version}")
    except AttributeError:
        print("Library version: Unknown (version attribute not available)")
except ImportError:
    print("Error: Intel RealSense library (pyrealsense2) not found")
    print("Please install it using: pip install pyrealsense2")
    print("For Raspberry Pi, you may need to build from source or use a pre-built wheel.")
    print("See: https://github.com/IntelRealSense/librealsense/tree/master/wrappers/python")
    sys.exit(1)

# Function to colorize depth frame
def colorize_depth(depth_image, min_depth=0.1, max_depth=10.0):
    """Convert depth image to color for better visualization"""
    depth_colormap = cv2.applyColorMap(
        cv2.convertScaleAbs(depth_image, alpha=255/max_depth), 
        cv2.COLORMAP_JET
    )
    return depth_colormap

# Setup the RealSense pipeline
try:
    print("Initializing RealSense pipeline...")
    
    # Create pipeline
    pipeline = rs.pipeline()
    
    # Create a config object
    config = rs.config()
    
    # Check if any devices are connected
    ctx = rs.context()
    devices = ctx.query_devices()
    if len(list(devices)) == 0:
        print("No RealSense devices detected. Please connect a device and try again.")
        sys.exit(1)
    
    # Print information about connected devices
    print(f"Found {len(list(devices))} RealSense device(s):")
    for i, dev in enumerate(devices):
        print(f"  Device {i+1}:")
        print(f"    Name: {dev.get_info(rs.camera_info.name)}")
        print(f"    Serial Number: {dev.get_info(rs.camera_info.serial_number)}")
        print(f"    Product Line: {dev.get_info(rs.camera_info.product_line)}")
        
    # Configure streams
    print("Configuring streams...")
    # Lower resolution for better performance on Raspberry Pi
    color_width, color_height = 640, 480  
    depth_width, depth_height = 640, 480
    fps = 30
    
    # Enable streams
    config.enable_stream(rs.stream.color, color_width, color_height, rs.format.bgr8, fps)
    config.enable_stream(rs.stream.depth, depth_width, depth_height, rs.format.z16, fps)
    
    # Start streaming
    print("Starting pipeline...")
    profile = pipeline.start(config)
    
    # Get the device
    device = profile.get_device()
    print(f"Using device: {device.get_info(rs.camera_info.name)}")
    
    # Get depth sensor
    depth_sensor = device.first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()
    print(f"Depth Scale: {depth_scale}")
    
    # Create align object
    align_to = rs.stream.color
    align = rs.align(align_to)
    
    print("Camera initialized successfully!")
    print(f"Running test for {args.duration} seconds...")
    
    # Create a window for displaying the images
    cv2.namedWindow('RealSense D455 Test', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('RealSense D455 Test', color_width + depth_width, color_height)
    
    # Variables for statistics
    frame_count = 0
    start_time = time.time()
    depth_values = []
    
    # Create directory for saving images if needed
    if args.record:
        import os
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = f"d455_capture_{timestamp}"
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        print(f"Recording images to: {save_dir}/")
    
    # Main loop
    try:
        while time.time() - start_time < args.duration:
            # Wait for a coherent pair of frames: depth and color
            frames = pipeline.wait_for_frames()
            
            # Align the depth frame to color frame
            aligned_frames = align.process(frames)
            
            # Get aligned frames
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                print("Warning: Invalid frame received")
                continue
            
            # Convert to numpy arrays
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
            
            # Get some depth data for statistics
            if frame_count % 30 == 0:  # Sample once per second
                center_x, center_y = depth_width // 2, depth_height // 2
                center_distance = depth_frame.get_distance(center_x, center_y)
                if center_distance > 0:
                    depth_values.append(center_distance)
                    
            # Colorize depth for display
            depth_colormap = colorize_depth(depth_image)
            
            # Combine images side by side
            combined_image = np.hstack((color_image, depth_colormap))
            
            # Add frame counter and fps
            elapsed_time = time.time() - start_time
            fps = frame_count / elapsed_time if elapsed_time > 0 else 0
            cv2.putText(combined_image, f"Frame: {frame_count} | FPS: {fps:.1f}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Add center distance
            if depth_values:
                cv2.putText(combined_image, f"Center distance: {depth_values[-1]:.2f}m", 
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Show images
            cv2.imshow('RealSense D455 Test', combined_image)
            
            # Save images if recording is enabled
            if args.record and frame_count % 5 == 0:  # Save every 5th frame
                cv2.imwrite(f"{save_dir}/color_{frame_count:04d}.jpg", color_image)
                cv2.imwrite(f"{save_dir}/depth_{frame_count:04d}.png", depth_image)
            
            # Increment frame counter
            frame_count += 1
            
            # Exit on ESC key
            key = cv2.waitKey(1)
            if key == 27:  # ESC
                break
                
    finally:
        # Calculate and display statistics
        end_time = time.time()
        elapsed_time = end_time - start_time
        avg_fps = frame_count / elapsed_time if elapsed_time > 0 else 0
        
        print("\nTest Results:")
        print(f"  Ran for {elapsed_time:.1f} seconds")
        print(f"  Processed {frame_count} frames")
        print(f"  Average FPS: {avg_fps:.1f}")
        
        if depth_values:
            avg_depth = sum(depth_values) / len(depth_values)
            print(f"  Average center distance: {avg_depth:.2f}m")
            
        print("Stopping pipeline...")
        pipeline.stop()
        cv2.destroyAllWindows()
        
        print("Test completed successfully!")
        
except Exception as e:
    import traceback
    print(f"Error during RealSense camera test: {e}")
    print(traceback.format_exc())
    sys.exit(1) 
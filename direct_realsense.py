import usb.core
import usb.util
import cv2
import time

# Intel's vendor ID
INTEL_VID = 0x8086

def find_realsense_device():
    # Find all Intel devices
    devices = list(usb.core.find(find_all=True, idVendor=INTEL_VID))
    
    if not devices:
        print("No RealSense devices found")
        return None
    
    print(f"Found {len(devices)} Intel device(s):")
    for i, device in enumerate(devices):
        print(f"Device {i}:")
        print(f"  - Product ID: 0x{device.idProduct:04x}")
        try:
            print(f"  - Serial Number: {usb.util.get_string(device, device.iSerialNumber)}")
        except:
            print(f"  - Serial Number: Unknown")
    
    return devices[0]  # Return the first found device

def try_opencv_access():
    # Try to access the camera through OpenCV first
    for i in range(10):  # Check first 10 camera indices
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Successfully opened camera at index {i}")
            
            # Try to read a frame
            ret, frame = cap.read()
            if ret:
                print(f"Successfully read a frame of size {frame.shape}")
                cv2.imwrite(f"camera_{i}_test.jpg", frame)
                print(f"Saved image as camera_{i}_test.jpg")
            else:
                print(f"Failed to read frame from camera {i}")
            
            cap.release()
            return True
        
    print("Could not access any camera through OpenCV")
    return False

def main():
    print("Searching for RealSense devices...")
    device = find_realsense_device()
    
    if device:
        print("\nTrying to access the camera via OpenCV...")
        success = try_opencv_access()
        
        if not success:
            print("\nCould not access the camera directly through OpenCV.")
            print("This suggests that either:")
            print("1. The camera is not properly detected as a video device")
            print("2. You need the RealSense SDK to access this camera")
            print("3. The camera may need a firmware update or different drivers")
    
if __name__ == "__main__":
    main() 
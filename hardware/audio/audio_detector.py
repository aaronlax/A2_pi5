#!/usr/bin/env python3
"""
Audio detection module for the Pi client.
"""

import logging
import time
import threading
import numpy as np

# Placeholder for audio libraries
# In a real implementation, you would use:
# import pyaudio
# import librosa

class AudioDetector:
    """Interface for audio detection and processing."""
    
    def __init__(self, config=None):
        """
        Initialize the audio detector with configuration.
        
        Args:
            config (dict, optional): Audio detector configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.thread = None
        
        # Default audio settings
        self.sample_rate = self.config.get('sample_rate', 16000)
        self.chunk_size = self.config.get('chunk_size', 1024)
        self.channels = self.config.get('channels', 1)
        self.format = self.config.get('format', 'int16')
        
        # Detection settings
        self.threshold = self.config.get('threshold', 0.5)
        self.min_duration = self.config.get('min_duration', 0.5)  # Minimum sound duration in seconds
        
        # Callback for when audio is detected
        self.on_audio_detected = None
        
    def start(self):
        """Start audio detection in a background thread."""
        if self.running:
            self.logger.warning("Audio detector already running")
            return True
            
        try:
            self.logger.info("Starting audio detector...")
            
            # In a real implementation:
            # self.stream = pyaudio.PyAudio().open(
            #     format=pyaudio.paInt16,
            #     channels=self.channels,
            #     rate=self.sample_rate,
            #     input=True,
            #     frames_per_buffer=self.chunk_size
            # )
            
            self.running = True
            self.thread = threading.Thread(target=self._detection_loop)
            self.thread.daemon = True
            self.thread.start()
            
            self.logger.info("Audio detector started")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start audio detector: {e}")
            return False
            
    def stop(self):
        """Stop audio detection."""
        if not self.running:
            return
            
        try:
            self.logger.info("Stopping audio detector...")
            self.running = False
            
            if self.thread:
                self.thread.join(timeout=2.0)
                
            # In a real implementation:
            # if hasattr(self, 'stream') and self.stream:
            #     self.stream.stop_stream()
            #     self.stream.close()
            
            self.logger.info("Audio detector stopped")
        except Exception as e:
            self.logger.error(f"Error stopping audio detector: {e}")
            
    def _detection_loop(self):
        """Background thread for continuous audio detection."""
        detection_active = False
        detection_start_time = 0
        
        self.logger.info("Audio detection loop started")
        
        while self.running:
            try:
                # In a real implementation:
                # audio_data = np.frombuffer(self.stream.read(self.chunk_size), dtype=np.int16)
                # volume = np.abs(audio_data).mean() / 32768.0  # Normalize to 0.0-1.0
                
                # Mock audio detection
                time.sleep(0.1)
                volume = np.random.random() * 0.2  # Random volume between 0 and 0.2
                
                # Simulate periodic sound for testing
                if time.time() % 10 < 2:  # 2 seconds of sound every 10 seconds
                    volume = 0.8  # Higher than threshold
                
                if volume > self.threshold:
                    if not detection_active:
                        detection_active = True
                        detection_start_time = time.time()
                        self.logger.debug(f"Sound detected (volume: {volume:.2f})")
                else:
                    if detection_active:
                        duration = time.time() - detection_start_time
                        if duration >= self.min_duration:
                            self.logger.info(f"Sound detected for {duration:.2f}s")
                            if self.on_audio_detected:
                                self.on_audio_detected(duration)
                        detection_active = False
                        
            except Exception as e:
                self.logger.error(f"Error in audio detection loop: {e}")
                time.sleep(1.0)  # Avoid tight loop on error
                
        self.logger.info("Audio detection loop ended")
        
    def set_detection_callback(self, callback):
        """
        Set callback function for audio detection events.
        
        Args:
            callback (callable): Function to call when audio is detected
                The function should accept a single parameter (duration in seconds)
        """
        self.on_audio_detected = callback
        
    def set_threshold(self, threshold):
        """
        Set the volume threshold for audio detection.
        
        Args:
            threshold (float): Volume threshold between 0.0 and 1.0
        """
        self.threshold = max(0.0, min(1.0, threshold))
        self.logger.info(f"Audio detection threshold set to {self.threshold:.2f}") 
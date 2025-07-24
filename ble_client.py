#!/usr/bin/env python3
# Raspberry Pi 5 BLE Client with Camera, Mic, Speaker, Display Control
import asyncio
import struct
import subprocess
import os
import signal
import sys
from datetime import datetime
from bleak import BleakClient, BleakScanner
import pygame
import cv2
import pyaudio
import wave
import threading

# BLE Configuration
PICO_NAME = "PicoW-Sensor"
# If you know the exact MAC address, you can specify it here
PICO_ADDRESS = "88:A2:9E:02:3B:94"
SERVICE_UUID = "00001234-0000-1000-8000-00805f9b34fb"  # 16-bit UUID 0x1234
CHAR_UUID = "00005678-0000-1000-8000-00805f9b34fb"     # 16-bit UUID 0x5678

# Audio Configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class MultimediaController:
    def __init__(self):
        self.camera = None
        self.audio = None
        self.display_on = False
        self.recording = False
        self.audio_thread = None
        
        # Initialize pygame for display control
        pygame.init()
        
    def turn_on_display(self):
        """Turn on the display"""
        try:
            subprocess.run(['vcgencmd', 'display_power', '1'], check=True)
            self.display_on = True
            print("Display turned ON")
            
            # Show a window to indicate system is active
            self.screen = pygame.display.set_mode((800, 600))
            pygame.display.set_caption("Security System Active")
            self.screen.fill((0, 128, 0))  # Green background
            font = pygame.font.Font(None, 36)
            text = font.render("Security System Active", True, (255, 255, 255))
            text_rect = text.get_rect(center=(400, 300))
            self.screen.blit(text, text_rect)
            pygame.display.flip()
        except Exception as e:
            print(f"Error turning on display: {e}")
            
    def turn_off_display(self):
        """Turn off the display"""
        try:
            pygame.quit()
            subprocess.run(['vcgencmd', 'display_power', '0'], check=True)
            self.display_on = False
            print("Display turned OFF")
        except Exception as e:
            print(f"Error turning off display: {e}")
            
    def start_camera(self):
        """Start camera recording"""
        try:
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                # Set up video writer
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.video_out = cv2.VideoWriter(f'recording_{timestamp}.avi', 
                                                fourcc, 20.0, (640, 480))
                print("Camera started recording")
                
                # Start recording in a separate thread
                self.camera_thread = threading.Thread(target=self._record_video)
                self.camera_thread.daemon = True
                self.camera_thread.start()
        except Exception as e:
            print(f"Error starting camera: {e}")
            
    def _record_video(self):
        """Record video in background"""
        while self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                self.video_out.write(frame)
            else:
                break
                
    def stop_camera(self):
        """Stop camera recording"""
        try:
            if self.camera:
                self.camera.release()
                self.video_out.release()
                cv2.destroyAllWindows()
                self.camera = None
                print("Camera stopped")
        except Exception as e:
            print(f"Error stopping camera: {e}")
            
    def start_audio(self):
        """Start audio recording and speaker"""
        try:
            self.audio = pyaudio.PyAudio()
            self.recording = True
            
            # Play alert sound through speaker
            self.play_alert()
            
            # Start recording
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.audio_filename = f'audio_{timestamp}.wav'
            
            self.audio_thread = threading.Thread(target=self._record_audio)
            self.audio_thread.daemon = True
            self.audio_thread.start()
            print("Audio recording started")
        except Exception as e:
            print(f"Error starting audio: {e}")
            
    def _record_audio(self):
        """Record audio in background"""
        stream = self.audio.open(format=FORMAT,
                               channels=CHANNELS,
                               rate=RATE,
                               input=True,
                               frames_per_buffer=CHUNK)
        
        frames = []
        while self.recording:
            data = stream.read(CHUNK)
            frames.append(data)
            
        stream.stop_stream()
        stream.close()
        
        # Save audio file
        wf = wave.open(self.audio_filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
    def stop_audio(self):
        """Stop audio recording"""
        try:
            self.recording = False
            if self.audio_thread:
                self.audio_thread.join(timeout=2)
            if self.audio:
                self.audio.terminate()
                self.audio = None
            print("Audio stopped")
        except Exception as e:
            print(f"Error stopping audio: {e}")
            
    def play_alert(self):
        """Play alert sound through speaker"""
        try:
            # Generate a simple beep
            subprocess.run(['speaker-test', '-t', 'sine', '-f', '1000', '-l', '1'], 
                         timeout=1, capture_output=True)
        except:
            # Alternative method using pygame
            try:
                pygame.mixer.init()
                # Create a simple beep sound
                sample_rate = 22050
                duration = 0.5
                frequency = 1000
                
                import numpy as np
                frames = int(duration * sample_rate)
                arr = np.zeros(frames)
                for x in range(frames):
                    arr[x] = np.sin(2 * np.pi * frequency * x / sample_rate)
                sound = np.asarray(arr * 32767, dtype=np.int16)
                
                pygame.sndarray.make_sound(sound).play()
            except Exception as e:
                print(f"Could not play alert sound: {e}")
                
    def activate_all(self):
        """Activate all multimedia components"""
        print("Activating all multimedia components...")
        self.turn_on_display()
        self.start_camera()
        self.start_audio()
        
    def deactivate_all(self):
        """Deactivate all multimedia components"""
        print("Deactivating all multimedia components...")
        self.stop_camera()
        self.stop_audio()
        self.turn_off_display()

class BLEClient:
    def __init__(self):
        self.client = None
        self.multimedia = MultimediaController()
        
    async def find_pico(self):
        """Scan for Pico W device"""
        print(f"Scanning for {PICO_NAME}...")
        devices = await BleakScanner.discover()
        
        for device in devices:
            if device.name == PICO_NAME:
                print(f"Found {PICO_NAME} at {device.address}")
                return device.address
                
        # If you have a specific address, you can return it here
        # return PICO_ADDRESS
        return None
        
    def notification_handler(self, sender, data):
        """Handle notifications from Pico W"""
        try:
            command, pir_value, sound_value = struct.unpack("<BBH", data)  # Little-endian
            
            if command == 1:  # Activation signal
                print(f"Activation signal received! PIR: {pir_value}, Sound: {sound_value}")
                self.multimedia.activate_all()
                
            elif command == 2:  # Shutdown signal
                print("Shutdown signal received - 20 seconds of silence detected")
                self.multimedia.deactivate_all()
                # Optionally shutdown the Pi
                # subprocess.run(['sudo', 'shutdown', '-h', 'now'])
                
        except Exception as e:
            print(f"Error handling notification: {e}")
            
    async def connect_and_monitor(self):
        """Connect to Pico W and monitor sensors"""
        address = await self.find_pico()
        
        if not address:
            print("Pico W not found!")
            return
            
        async with BleakClient(address) as client:
            self.client = client
            print(f"Connected to {address}")
            
            # Subscribe to notifications
            await client.start_notify(CHAR_UUID, self.notification_handler)
            print("Listening for sensor data...")
            
            try:
                # Keep the connection alive
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping...")
                
            await client.stop_notify(CHAR_UUID)
            self.multimedia.deactivate_all()
            
def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down...")
    sys.exit(0)
    
async def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    client = BLEClient()
    
    while True:
        try:
            await client.connect_and_monitor()
        except Exception as e:
            print(f"Connection error: {e}")
            print("Retrying in 5 seconds...")
            await asyncio.sleep(5)
            
if __name__ == "__main__":
    # Check if running with appropriate permissions
    if os.geteuid() != 0:
        print("Warning: Some features may require sudo privileges")
        
    print("Raspberry Pi 5 BLE Client Started")
    print("Make sure Pico W is running and advertising")
    
    asyncio.run(main())

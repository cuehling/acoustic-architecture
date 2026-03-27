import sys
import time
from PyQt6.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
import socket, time
import numpy as np
import sounddevice as sd

# 1. Define a Worker class that inherits from QObject
class AudioStream(QThread):

    # AudioStream Attributes
    run = False
    # Define signals the AudioStream can emit

    # Eventually May want a progress or something in here

    # Define important attributes for initialization
    sound_input = "microphone input"
    gh_file = None

    def __init__(self, audio=sound_input, gh=gh_file):
        print("initializing Worker Class...")
        print([audio, gh])
        self.audo = audio
        self.gh = gh
        self.processor = gh

   
    def run_task(self):
        self.run = True

        while self.run:

            raw_data = self.get_audio_chunk() # Get mic or file data

            processed_data = self.processor.transform()

            # Send to Grasshopper (gHOWL)
            message = ",".join(map(str, processed_data))
            self.sock.sendto(message.encode(), ("127.0.0.1", 5005))
        

    def collect_microphone_data(self):
        if not self.device_id:

            # Show audio devices
            print("\nAvailable audio input devices:\n")
            devices = sd.query_devices()

            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0:   # 입력 가능한 장치만 표시
                    print(f"{i}: {d['name']}")

            self.device_id = int(input("\nSelect device number: "))

        # Microphone Data Settings
        SR = 48000
        FRAME_MS = 60
        FRAME = int(SR * FRAME_MS / 1000)

        # ===== Audio Stream =====
        with sd.InputStream(device= self.device_id,
                            channels=1,
                            samplerate=SR,
                            blocksize=FRAME) as stream:

            # 1) Audio read
            x, _ = stream.read(FRAME)
            return x[:, 0].astype(np.float32)
            

               

    

if __name__ == "__main__":
    worker = AudioStream()
        
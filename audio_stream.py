import sys
import time
from PyQt6.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
import socket, time
import numpy as np
import sounddevice as sd

# 1. Define a Worker class that inherits from QObject
class AudioStream(QThread):
    # Define signals the worker can emit

    # Eventually May want a progress or something in here

    # Define important attributes for initialization
    sound_input = "microphone input"
    gh_file = None

    def __init__(self, audio=sound_input, gh=gh_file):
        print("initializing Worker Class...")
        print([audio, gh])
   
    def run_task(self):
        pass

    def collect_microphone_data():

        # Show audio devices
        print("\nAvailable audio input devices:\n")
        devices = sd.query_devices()

        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:   # 입력 가능한 장치만 표시
                print(f"{i}: {d['name']}")

        device_id = int(input("\nSelect device number: "))

        # ===== UDP =====
        UDP_IP = "127.0.0.1"
        UDP_PORT = 9001
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # ===== Audio =====
        SR = 48000
        FRAME_MS = 60
        FRAME = int(SR * FRAME_MS / 1000)


        # ===== Audio Stream =====
        with sd.InputStream(device=device_id,
                            channels=1,
                            samplerate=SR,
                            blocksize=FRAME) as stream:

            while True:

                # 1) Audio read
                x, _ = stream.read(FRAME)
                x = x[:, 0].astype(np.float32)

                # 2) Amplitude
                rms = float(np.sqrt(np.mean(x*x) + 1e-12))
                amp = rms * GAIN

                # 8) UDP
                msg = ",".join([f"{v:.4f}" for v in height.flatten()])
                sock.sendto(msg.encode("utf-8"), (UDP_IP, UDP_PORT))

    

if __name__ == "__main__":
    worker = Worker()
        
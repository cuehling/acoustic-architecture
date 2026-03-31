import sys
import socket
import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QThread
from grasshopper.wave_processor import WaveProcessor # Import your new class

class AudioStream():
    def __init__(self, device_id, processor_mode=2):
        super().__init__()
        self.device_id = device_id
        self.running = False
        self.processor = WaveProcessor(mode=processor_mode)
        
        # Network Setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_address = ("127.0.0.1", 9001)

    def run(self):
        self.running = True
        SR = 48000
        FRAME = int(SR * 50 / 1000) # 50ms frames

        with sd.InputStream(device=self.device_id, channels=1, samplerate=SR, blocksize=FRAME) as stream:
            while self.running:
                # 1. Capture
                audio_chunk, _ = stream.read(FRAME)
                raw_data = audio_chunk[:, 0].astype(np.float32)

                # 2. Transform (Using the external processor)
                processed_data = self.processor.transform(raw_data)

                # 3. Transport to Grasshopper
                msg = ",".join(map(str, processed_data))
                self.sock.sendto(msg.encode("utf-8"), self.udp_address)

    def stop(self):
        self.running = False
        self.wait()

if __name__ == "__main__":
    # Quick CLI test before using with PyQt GUI
    print(sd.query_devices())
    dev_id = int(input("Select device ID: "))
    worker = AudioStream(device_id=dev_id)
    worker.run()
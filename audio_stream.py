import sys, os, re
from PyQt6.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
import socket, time
import numpy as np
import sounddevice as sd
import soundfile as sf

# Class handles the streaming of data from the sound source input
# to the transformation then finally to grasshopper

class AudioStream(QThread):
    
    # Attributes
    blocksize = 1024

    def __init__(self, **kwargs):
        super().__init__()
        print("initializing Audio Stream...")
        
        self.audio     = kwargs.get('audio', 'microphone input')
        self.processor = kwargs.get('processor', None)
        self.device_id = kwargs.get('device id', None)
        self.run       = False
        self.contents  = None
        self.file = None

    
    def run(self):
        '''
        Function that runs within its own thread.
        1. Collects microphone or wav file data
        2. Processes it
        3. Sends data to Grasshopper
        4. Repeats until stop button is pressed
        '''
        self.run = True

        while self.run: # While audio stream is running (Stop is not pressed)
            
            # Collect audio data
            if self.audio == "microphone input":
                raw_data = self.collect_mic_data()
            else:
                print('Within else')
                raw_data = self.collect_file_data()

            # Process Data
            if self.processor:
                processed_data = self.processor.transform(raw_data)
            else:
                processed_data = raw_data

            print(processed_data)
            time.sleep(1)


            # # Send to Grasshopper (gHOWL)
            # message = ",".join(map(str, processed_data))
            # self.sock.sendto(message.encode(), ("127.0.0.1", 5005))
        
    # =================== Collecting Data Functions ==================

    def collect_file_data(self):
        
        # Load file if necessary
        if not self.file:
            file = self.query_audio_file()  
                
        with sf.SoundFile(file) as infile:
            # Mirror input format exactly
            samplerate = infile.samplerate
            channels = infile.channels
            subtype = infile.subtype
                
            # Process in blocks to be memory efficient
            for block in infile.blocks(blocksize=self.blocksize):
                return block
                
        print('audio reading did not work')

    def collect_mic_data(self):
        
        # Microphone Data Settings
        SR = 48000
        FRAME_MS = 60
        FRAME = int(SR * FRAME_MS / 1000)

        # ===== Audio Stream =====
        with sd.InputStream(device= self.device_id,
                            channels=1,
                            samplerate=SR,
                            blocksize=FRAME) as stream:

            # Audio read
            x, _ = stream.read(self.blocksize)
            print(x[:, 0].astype(np.float32))
            return x[:, 0].astype(np.float32)
            

    def query_audio_file(self):
        
        # Find original location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Add audio_files folder to path location
        target_folder = os.path.join(script_dir, 'audio_files')

        if not os.path.isdir(target_folder):
            print(f"Error: The folder 'audio_files' does not exist in the script's directory.")
        
        # Find audio file
        file = os.path.join(target_folder, f"{self.audio}.wav")
        print(f'Reading audio_file {self.audio}')
        return file    

    def query_mic_input(self):

        # Show audio devices
        devices = sd.query_devices()

        # Remove virtual/stupid sound devices
        device_list = []
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0: # 입력 가능한 장치만 표시
                print(f"{i}: {d['name']}")
                device_list.append(d)
        
        return device_list
        # return devices

    # ============== Getter + Setter Functions ======================
    def set_mic_input(self, number):
        self.device_id = number
    
    # ==============Funcitonal Functions===============
    def find_folder(self, folder):
        # Find original location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Add path to location
        target_folder = os.path.join(script_dir, folder)
        return target_folder
        

               

if __name__ == "__main__":
    worker = AudioStream()
    content = worker.collect_audio_data()
    print(content)
        
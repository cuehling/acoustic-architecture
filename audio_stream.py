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

    # Microphone Data Settings
    samplerate = 48000
    frame_ms = 60
    frame = int(samplerate * frame_ms / 1000)

    # Socket
    udp_ip = "127.0.0.1"
    udp_port = 9001


    def __init__(self, **kwargs):
        super().__init__()
        print("initializing Audio Stream...")
        
        self.file_data = {'name': kwargs.get('audio', 'microphone input'),
                          'samplerate': self.samplerate,
                          'frame': self.frame,
                          'device_id': kwargs.get('device id', None),
                          '': kwargs.get('blocksize', self.blocksize)}
        self.processor = kwargs.get('processor', None)
        self.run       = False

    def run(self):
        '''
        Function that runs within its own thread.
        1. Collects microphone or wav file data
        2. Processes it
        3. Sends data to Grasshopper
        4. Repeats until stop button is pressed
        '''
        # Start Running
        self.run = True

        # Set up audio source
        if self.file_data['name'] != "microphone input":
            file, file_data = self.collect_file_data()
            self.file_data.update(file_data)

        # Create GH Connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while self.run: # While audio stream is running (Stop is not pressed)
            
            # Collect audio data
            if self.file_data['name'] == "microphone input":
                raw_data = self.collect_mic_data()
            else:
                raw_data = self.collect_file_data(file, file_data)

            # Process Data
            if self.processor:
                processed_data = self.processor.transform(raw_data)
            else:
                processed_data = raw_data

            print(processed_data)
            processed_data = 200*processed_data

            # # Send to Grasshopper (gHOWL)
            msg = ",".join(f"{v:.5f}" for v in processed_data.T.flatten())
            sock.sendto(msg.encode("utf-8"), (self.udp_ip, self.udp_port))
            time.sleep(.5)
        


    # =================== Collecting Data Functions ==================

    def collect_file_data(self, file):
        
        if self.block_num == self.blocksize:
            self.block_num = 0

        with sf.SoundFile(file) as infile:

            print(infile.blocks(blocksize=self.blocksize))
            # Process in blocks to be memory efficient
            for i, block in enumerate(infile.blocks(blocksize=self.blocksize)): 
                if i == self.block_num:
                    return block
                
        print('audio reading did not work')

    def collect_mic_data(self):
        
        # audio_stream the data
        with sd.InputStream(device     = self.file_data['device_id'],
                            channels   = 1,
                            samplerate = self.file_data['samplerate'],
                            blocksize  = self.file_data['frame']) as stream:

            # Audio read
            x, _ = stream.read(self.blocksize)
            print(x[:, 0].astype(np.float32)) # Returns
            stream.close()
            return x[:, 0].astype(np.float32)
            
    # ================ Querying Data functions ======================
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

        with sf.SoundFile(file) as infile:
            file_data = {}
            # Mirror input format exactly
            file_data['samplerate'] = infile.samplerate
            file_data['blocksize']  = self.blocksize
            file_data['blocknum']   = 0
            
            blocks = infile.blocks(blocksize=self.blocksize)
            return file, file_data
        
        print('Soundfile opening did not work. Is file corrupted??') 


    def query_mic_input(self):

        # Show audio devices
        devices = sd.query_devices()
        
        device_list = []
        for i, d in enumerate(devices):
            # Remove virtual/stupid sound devices
            print(d['name'])
            if d['max_input_channels'] > 0 and not re.match('Speaker', d['name'], re.IGNORECASE): # 입력 가능한 장치만 표시
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
        



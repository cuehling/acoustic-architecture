import os, re
from PyQt6.QtCore import QThread
import socket, time
import numpy as np
import sounddevice as sd
import soundfile as sf
import importlib.util

# Class handles the streaming of data from the sound source input
# to the transformation then finally to grasshopper

class AudioStream(QThread):

    # Default Data Settings
    metadata = {'samplerate': 48000,
                'frame'     : 128}

    # Audio Parameters
    audio_gain   = 18.0    # Gain of signal
    gate         = 0.008   # Gate for something
    base_lvl     = 0.000   # idk what this is yet
    audio_scale  = 1.4     # idk what this is yet
    audio_smooth = 0.08    # idk what this is yet

    # Transmission optimization
    send_every_n_frames = 3
    clip_value          = 9.9
    scale_factor        = 10

    # Grid 
    nx = 120
    ny = 90
    spacing = 10

    # Transmission
    udp_ip   = "127.0.0.1"
    udp_port = 9001

    def __init__(self):
        super().__init__()
        print("initializing Audio Stream...")

        # Precompute Distances
        self.x = np.arange(self.nx) * self.spacing
        self.y = np.arange(self.ny) * self.spacing
        self.X, self.Y = np.meshgrid(self.x, self.y)
        self.run       = False


    def set_up_stream(self, audio, processor, device=None):
        # Set up audio source
        self.audio = audio

        # Prepare audio
        if audio != "microphone input":
            self.file, file_data = self.query_audio_file()
            self.metadata.update(file_data)
        else:
            self.metadata['device_id'] = device

        # Send over data to processor
        if processor == 'None':
            self.processor = None
        else:
            self.processor = self.choose_processor(processor)(self.x, self.y, self.metadata)
        
        # Create GH Connection
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        


    def run(self):
        '''
        Function that runs within its own thread.
        1. Collects microphone or wav file data
        2. Processes it
        3. Sends data to Grasshopper
        4. Repeats until stop button is pressed
        '''

        block_num = 0
        frame = self.metadata['frame']
        sr    = self.metadata['samplerate']

        if self.audio == "microphone input":
            with sd.InputStream(device=self.metadata['device_id'],
                                channels=1,
                                samplerate=sr,
                                blocksize=frame) as stream:
                while self.run:

                    t = (np.arange(0, frame, dtype=np.float32) + block_num*frame)/sr

                    raw_data, _ = stream.read(frame)
                    raw_data = raw_data[:, 0].astype(np.float32)

                    if self.processor:
                        processed_data = self.processor.transform(t, raw_data)
                    else:
                        processed_data = 20*raw_data
                        flat = processed_data.T.flatten()
                        scaled = np.round(np.clip(flat, -9.9, 9.9) * 10).astype(np.int16)
                        processed_data = ",".join(scaled.astype(str))

                    # print(processed_data)
                    
                    # Send to Grasshopper (gHOWL)
                    if block_num % 2 == 0:
                        self.sock.sendto(processed_data.encode("utf-8"), (self.udp_ip, self.udp_port))
                    block_num += 1

        else:
            # blocks
            block_num = 0

            blocks = []

            for block in sf.blocks(self.file, blocksize=frame, dtype='float32'):
                blocks.append(block)
            
            tot = []
            for block in blocks:
                for sample in block:
                    tot.append(abs(sample))
            max = np.max(tot)

            print(f'Maximum: {max}')
            blocks = 1/max * np.array(blocks, dtype=object)

            while self.run:

                print("="*80)
                t = (np.arange(0, frame, dtype=np.float32) + block_num*frame)/sr
                
                if block_num == len(blocks):
                    block_num = 0
                
                # Process in blocks to be memory efficient 
                if self.processor:
                    processed_data = self.processor.transform(t, blocks[block_num][:])
                else:
                    processed_data = 20*blocks[block_num][:]
                    flat = processed_data.T.flatten()
                    scaled = np.round(np.clip(flat, -9.9, 9.9) * 10).astype(np.int16)
                    processed_data = ",".join(scaled.astype(str))
                
                # Send to Grasshopper (gHOWL)
                if block_num % 2 == 0:
                    self.sock.sendto(processed_data.encode("utf-8"), (self.udp_ip, self.udp_port))
                block_num += 1


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
            # Record audio metadata
            self.metadata['samplerate'] = infile.samplerate
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
        # return devices
        return device_list
        


    # =========================================================
    def choose_processor(self, module_name):
        # If none was chosen, return None
        if module_name == 'None':
            print('No Processor Chosen')
            return None
        
        print(f'Module_name = {module_name + ".py"}')

        # Find Grasshopper folder
        current_dir = os.path.dirname(os.path.abspath(__file__))
        gh_dir = os.path.join(current_dir, 'grasshopper')
        module_path = os.path.join(gh_dir, f"{module_name}.py")
        
        # Use importlib to load module from specific path
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        
        # If loading didn't work:
        if spec is None:
            raise ImportError(f"Could not load spec for {module_name} at {gh_dir}")
        
        # collect module folder
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"Module: {module}")

        # convert from snake_case to PascalCase
        class_name = "".join(word.capitalize() for word in module_name.split('_'))
        print(f"Class Name: {class_name}")

        # Return Class from the module
        if hasattr(module, class_name):
            SelectedClass = getattr(module, class_name)
            return SelectedClass
        else:
            raise AttributeError(f"Module '{module_name}' has no class named '{class_name}'")



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
        



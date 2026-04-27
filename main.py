import sys, os, re
import importlib.util
from PyQt6 import QtWidgets, uic
from audio_stream import AudioStream

# Creates the Graphic User Interface (GUI) of the Grasshopper-Python
# Code which simulates physical sound concepts
    
# Has two dropdown menus:
# - audio source: choose between microphone input or .wav files
# - Processor: choose what is simulated in Grasshopper

# Has two buttons:
# - Run: starts the program. Sends user input to the AudioStream Class.
# - stop: ends the program


class AudioApp(QtWidgets.QMainWindow):


    def __init__(self):
     
        super().__init__()
        
        # Load the UI file
        uic.loadUi("gui.ui", self)
        self.audio_stream = None

        # Set Up Dropdown menus
        self.set_up_sound_input_choice()
        self.set_up_processor_input_choice()

        # Initialize Buttons
        self.run.clicked.connect(self.pressed_run)
        self.stop.clicked.connect(self.pressed_stop)

        
    # ================== Button Functions ========================

    def pressed_run(self):
        '''
        - Starts AudioStream, 
        - Sends user choices/data to stream, 
        - Starts AudioStream.run()
        '''
        print("Run was pressed")

        # Collect user's choices
        audio = self.sound_input_choice.currentText()
        processor = self.gh_input_choice.currentText()

        # Create AudioStream if needed
        if self.audio_stream is None:
            self.audio_stream = AudioStream()

        # Check if AudioStream is already running
        elif self.audio_stream.run is True:
            print('Program is already running')
            return

        # Start running
        self.audio_stream.run = True

        # Choose Sound Source
        if audio == 'microphone input':
            device = self.choose_mic_input()
            self.audio_stream.set_up_stream(audio, processor, device)
        else:
            self.audio_stream.set_up_stream(audio, processor)

        # If processor has inputs needed, create popups and answer them:
        response = {}
        if hasattr(self.audio_stream.processor, 'inputs'):
            for question, options in self.audio_stream.processor.inputs.items():
                choice = self.popup_query(title=question, list=options)
                response.update({question: choice})

            self.audio_stream.processor.set_up_processor(response)
        
        # Update audio_stream and start
        self.audio_stream.start()

    def pressed_stop(self):
        print("Stopping GH")
        self.audio_stream.run = False

        
    # =============== Initialization Functions ====================

    def set_up_sound_input_choice(self):

        # Add Microphone Input
        self.sound_input_choice.addItem('microphone input')

        # Find Audio Files Folder
        contents = self.find_folder('audio_files')
        
        for content in contents:
            audio_file = re.match(r'([\w-]+)\.(wav)', content) 
            if audio_file:
                self.sound_input_choice.addItem(audio_file.group(1))
    
    def set_up_processor_input_choice(self):
        
        # Add Microphone Input
        self.gh_input_choice.addItem('None')

        # Find Audio Files Folder
        contents = self.find_folder('grasshopper')
        
        # Write Grasshopper Files in gh input dropdown menu
        for content in contents:
            gh_file = re.match(r'([\w-]+)\.(py)', content) 
            if gh_file:
                self.gh_input_choice.addItem(gh_file.group(1))
        
    # =================== Choose Inputs =====================

    def choose_mic_input(self):
        # Query Which input device to use
        devices = self.audio_stream.query_mic_input()
            
        # Sort through viable devices (work on this some more!)
        device_list = []
        for d in devices:
            print(f"{d['index']}: {d['name']}")
            device_list.append(f"{d['index']}: {d['name']}")
        
        # Choose device via dropdown menu
        device_chosen = self.popup_query(title='Device Selection', list=device_list)

        # Find device associated
        if device_chosen:
            id = re.match(r'([\d]+): ', device_chosen)
            for device in devices:
                if id.group(1) == device['index']:
                    return device
        else:
            print('No device chosen.')


    # ===================================================
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
            return SelectedClass()
        else:
            raise AttributeError(f"Module '{module_name}' has no class named '{class_name}'")


    # ============= Functional Functions ==================
    def popup_query(self, **kwargs):
        
        # Get data from kwargs
        QtWidgets.QDialog()
        title    = kwargs.get('title', '')
        label    = kwargs.get('label', None)
        list     = kwargs.get('list', None)
        editable = kwargs.get('editable', False)
        
        # Create Popups with choices
        choice, ok = QtWidgets.QInputDialog.getItem(
        None,             # Parent (QWidget or None)
        title,            # Title
        label,            # Label
        list,             # List
        0,                # Current Index
        False             # Editable (False = Dropdown, True = Textbox)
        )

        # Return choice
        if ok and choice:
            print(f"User chose: {choice}")
            return choice
        else:
            print("Closing Program...")
            self.stop_gh()
            return None

    def find_folder(self, folder):
        # Find original location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Add path to location
        target_folder = os.path.join(script_dir, folder)
        
        if not os.path.isdir(target_folder):
            print(f"Error: The folder {folder} does not exist in the script's directory.")
        else:
            contents = os.listdir(target_folder)
            return contents

        
def main():
    print("Hello from acoustic-architecture!")
    app = QtWidgets.QApplication(sys.argv)
    window = AudioApp()
    window.show()
    sys.exit(app.exec())
    

if __name__ == "__main__":
    main()

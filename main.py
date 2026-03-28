import sys, os, re
from PyQt6 import QtWidgets, uic
from audio_stream import AudioStream


class MyApp(QtWidgets.QMainWindow):


    def __init__(self):
        super().__init__()
        
        # Load the UI file
        # Ensure 'design.ui' is in the same folder as this script
        uic.loadUi("gui.ui", self)

        # Set Up Combo Boxes
        self.set_up_sound_input_choice()
        self.set_up_grasshopper_input_choice()

        # Initialize Buttons
        self.run.clicked.connect(self.run_gh)
        self.stop.clicked.connect(self.stop_gh)

        self.audio_stream = AudioStream()

    # ==================Button Functions========================
    def run_gh(self):
        print("Running GH")

        audio = self.sound_input_choice.currentText()
        gh = self.gh_input_choice.currentText()

        
        if audio == 'microphone input':
            devices = self.audio_stream.query_mic_input()
            print(devices)
            
            QtWidgets.QDialog()

            choice, ok = QtWidgets.QInputDialog.getItem(
            None,             # Parent (QWidget or None)
            "Selection Menu", # Title
            "Choose Source:", # Label
            devices,            # The List
            0,                # Current Index
            False             # Editable (False = Dropdown, True = Textbox)
            )
            if ok and choice:
                print(f"User chose: {choice}")
                id = re.match(r'([\d]+): ', choice)
                print(id.group(1))
                self.audio_stream.device_id = id.group(1)
                
        
           

    def stop_gh(self):
        print("Stopping GH")
        
        pass
        
    # ============= Initialization Functions ================

    def set_up_sound_input_choice(self):
        
        # Add Microphone Input
        self.sound_input_choice.addItem('microphone input')

        # Find Audio Files Folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        target_folder = os.path.join(script_dir, 'audio_files')

        if not os.path.isdir(target_folder):
            print(f"Error: The folder 'audio_files' does not exist in the script's directory.")
        else:
            contents = os.listdir(target_folder)
        
        # Write Audio Files in sound input dropdown menu
        for content in contents:
            audio_file = re.match(r'([\w-]+)\.(mp3|wav)', content) 
            if audio_file:
                self.sound_input_choice.addItem(audio_file.group(1))
    

    def set_up_grasshopper_input_choice(self):

        # Find Grasshopper Files Folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        target_folder = os.path.join(script_dir, 'grasshopper')

        if not os.path.isdir(target_folder):
            print(f"Error: The folder 'grasshopper' does not exist in the script's directory.")
        else:
            contents = os.listdir(target_folder)
        
        # Write Grasshopper Files in gh input dropdown menu
        for content in contents:
            gh_file = re.match(r'([\w-]+)\.(py)', content) 
            if gh_file:
                self.gh_input_choice.addItem(gh_file.group(1))
        
        
def main():
    print("Hello from acoustic-architecture!")
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

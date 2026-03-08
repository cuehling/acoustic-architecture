import sys, os, re
from PyQt6 import QtWidgets, uic


class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Load the UI file
        # Ensure 'design.ui' is in the same folder as this script
        uic.loadUi("gui.ui", self)

        # Read audio files and fill it in
        self.sound_input_choice.addItem('microphone input')

        script_dir = os.path.dirname(os.path.abspath(__file__))
        target_folder = os.path.join(script_dir, 'audio_files')

        if not os.path.isdir(target_folder):
            print(f"Error: The folder 'audio_files' does not exist in the script's directory.")
        else:
            contents = os.listdir(target_folder)
        
        for content in contents:
            hello = re.match(r'([\w-]+)\.(mp3|wav)', content) 
            if hello:
                self.sound_input_choice.addItem(hello.group(1))
        
        
    
def main():
    print("Hello from acoustic-architecture!")
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

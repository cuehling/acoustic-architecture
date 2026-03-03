import sys
from PyQt6 import QtWidgets, uic


class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Load the UI file
        # Ensure 'design.ui' is in the same folder as this script
        uic.loadUi("gui.ui", self)
        
        # Example: Accessing a widget by its 'objectName' from Designer
        # self.myButton.clicked.connect(self.handle_click)
        
    def handle_click(self):
        print("Button clicked!")

    
def main():
    print("Hello from acoustic-architecture!")
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

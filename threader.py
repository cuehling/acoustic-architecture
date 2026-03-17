import sys
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QProgressBar
from PyQt6.QtCore import QThread, QObject, pyqtSignal, pyqtSlot

# 1. Define a Worker class that inherits from QObject
class Worker(QObject):
    # Define signals the worker can emit
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    @pyqtSlot()
    def run_task(self):
        """Long-running task in a separate thread."""
        for i in range(1, 101):
            time.sleep(0.05)  # Simulate work
            self.progress.emit(i)  # Emit progress signal
        self.finished.emit() # Emit finished signal when done
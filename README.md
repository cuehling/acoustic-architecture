Audio-Reactive Mesh Visualization Pipeline

## System Overview
This project uses a high-performance bridge to stream audio-driven displacement data from Python to a 3D mesh in Rhino/Grasshopper. The system is optimized for a 120x90 grid at approximately 25-30 FPS.

### Core Components
- **AudioApp:** The main GUI and threading manager that controls the application lifecycle.
- **AudioStream:** Captures audio frames via sounddevice from either a microphone or a .wav file.WaveProcessor: The mathematical engine that converts audio signals into a height field using sine-wave synthesis.
- **Grasshopper Listener:** A GHPython component that receives UDP packets and deforms a cached mesh in real-time.

## Processor API Rules
To ensure compatibility with the AudioApp pipeline, any new processor (e.g., fluid sim, particle field) must follow these strict structural rules:

### 1. Initialization Protocol
The constructor must accept these specific arguments to integrate with the grid system:Pythondef __init__(self, nx, ny, spacing, metadata):
- **nx, ny:** Grid dimensions (e.g., 120, 90)
- **spacing:** The physical distance between grid points
- **metadata:** Dictionary containing 'samplerate' and 'frame' size

### 2. The transform Method
This method is called every frame and must be optimized for speed:
- **Input:** Must accept (t_scalar, raw_audio) where raw_audio is a NumPy array.Output: Must return a flattened NumPy array of type int8.
- **Normalization:** Data must be clipped and scaled (e.g., clip_value=20, scale_factor=10) before conversion to int8 to fit within UDP packet size limits.
- **File Name:** File name must be in pascal_case with CamelCase for the actual file name

## Adding Audio FilesFormat: 
- **Format:** Files must be Mono .wav format. using all lowercase and uppercase letters (a-z, A-Z).
all digits (0-9), and the underscore character (_).
- **Sample Rate:** The processor uses the metadata from the file (e.g., 16000Hz or 44100Hz) to calculate the time_step.
- **Persistence:** To ensure microphone input doesn't "snap" to zero, processors should use an Attack/Release envelope follower rather than raw amplitude.

## Anti-Aliasing & Stability
The system prevents spatial and temporal aliasing through the following constraints:
- **Nyquist Limit:** The visual wavelength ($\lambda$) is clamped to a minimum of 4.0 grid units.
- **Oscillation Decoupling:** High audio frequencies are scaled down (using osc_speed) to prevent flickering on screens with lower refresh rates.
- **Vectorization:** All calculations must use NumPy slicing; standard Python loops will cause significant frame-rate drops.

## UDP Configuration
- **Port:** 9001.
- **IP:** 127.0.0.1 (Localhost).
- **Mode:** Non-blocking UDP to prevent the Python thread from hanging if Grasshopper is busy.

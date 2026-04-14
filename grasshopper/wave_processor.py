import socket
import time
import numpy as np
import sounddevice as sd


class WaveProcessor:
    # Grid
    WAVELENGTH   = 200.0      # visual wavelength
    VISUAL_SPEED = 1200.0     # propagation speed for delayed envelope (unit/sec)
    OSC_SPEED1   = 0.45       # oscillation speed for source 1
    OSC_SPEED2   = 0.45       # oscillation speed for source 2
    ATT1         = 0.00075
    ATT2         = 0.00075
    AMP1         = 4.0
    AMP2         = 4.0
    PHASE1       = 0.0
    PHASE2       = 0.0

    TIME_STEP = 0.03          # simulation time step
    ALPHA = 0.18              # field smoothing

    # =========================
    # Audio parameters
    # =========================

    AUDIO_GAIN   = 18.0       # microphone sensitivity
    GATE         = 0.008      # noise gate
    BASE_LEVEL   = 0.00       # minimum excitation even in silence
    AUDIO_SCALE  = 1.4        # microphone influence
    AUDIO_SMOOTH = 0.08       # envelope smoothing (smaller = smoother)

    # =========================
    # Transmission optimization
    # =========================
    SEND_EVERY_N_FRAMES = 3   # send every N frames
    CLIP_VALUE          = 9.9 # for integer scaling
    SCALE_FACTOR        = 10  # int decoding in GH => divide by 10



    def __init__(self):
        mode_input = input("Enter mode (1/2/3): ")

        if mode_input == "1":
            MODE = 0
        elif mode_input == "2":
            MODE = 1
        else:
            MODE = 2

    def transform(self, raw_audio):
        pass


# -*- coding: utf-8 -*-






# =========================
# Grid
# =========================
NX = 100
NY = 72
SPACING = 30.0

x = np.arange(NX) * SPACING
y = np.arange(NY) * SPACING
X, Y = np.meshgrid(x, y)

# =========================
# Source positions
# =========================
SRC1 = (0, 1080, 0)
SRC2 = (3000, 1080, 0)

# =========================
# Wave / propagation parameters
# =========================
WAVELENGTH = 200.0           # visual wavelength
VISUAL_SPEED = 1200.0        # propagation speed for delayed envelope (unit/sec)
OSC_SPEED1 = 0.45            # oscillation speed for source 1
OSC_SPEED2 = 0.45            # oscillation speed for source 2
ATT1 = 0.00075
ATT2 = 0.00075
AMP1 = 4.0
AMP2 = 4.0
PHASE1 = 0.0
PHASE2 = 0.0

TIME_STEP = 0.03             # simulation time step
ALPHA = 0.18                 # field smoothing

# =========================
# Audio parameters
# =========================
SR = 48000
FRAME_MS = 50
FRAME = int(SR * FRAME_MS / 1000)

AUDIO_GAIN = 18.0            # microphone sensitivity
GATE = 0.008                 # noise gate
BASE_LEVEL = 0.00            # minimum excitation even in silence
AUDIO_SCALE = 1.4            # microphone influence
AUDIO_SMOOTH = 0.08          # envelope smoothing (smaller = smoother)

# =========================
# Transmission optimization
# =========================
SEND_EVERY_N_FRAMES = 3      # send every N frames
CLIP_VALUE = 9.9             # for integer scaling
SCALE_FACTOR = 10            # int decoding in GH => divide by 10

# =========================
# Device selection
# =========================
print("\nAvailable audio input devices:\n")
devices = sd.query_devices()
for i, d in enumerate(devices):
    if d["max_input_channels"] > 0:
        print(f"{i}: {d['name']}")

device_id = int(input("\nSelect device number: "))

print("\nSelect mode:")
print("1 = wave1 only")
print("2 = wave2 only")
print("3 = wave1 + wave2")

mode_input = input("Enter mode (1/2/3): ")

if mode_input == "1":
    MODE = 0
elif mode_input == "2":
    MODE = 1
else:
    MODE = 2

# =========================
# Precompute distances
# =========================
EPS = 1e-6
r1 = np.sqrt((X - SRC1[0])**2 + (Y - SRC1[1])**2 + EPS)
r2 = np.sqrt((X - SRC2[0])**2 + (Y - SRC2[1])**2 + EPS)

k = 2.0 * np.pi / WAVELENGTH
env1 = np.exp(-ATT1 * r1)
env2 = np.exp(-ATT2 * r2)

# =========================
# Delay buffer setup
# =========================
max_r = max(np.max(r1), np.max(r2))
max_delay_sec = max_r / VISUAL_SPEED

# a bit of extra safety margin
BUFFER_SEC = max_delay_sec + 1.0
BUFFER_LEN = int(BUFFER_SEC / TIME_STEP) + 10

audio_buffer = np.full(BUFFER_LEN, BASE_LEVEL, dtype=np.float32)
buffer_index = 0

# delay steps per grid point
delay_steps1 = np.round((r1 / VISUAL_SPEED) / TIME_STEP).astype(np.int32)
delay_steps2 = np.round((r2 / VISUAL_SPEED) / TIME_STEP).astype(np.int32)

# =========================
# States
# =========================
field_state = np.zeros((NY, NX), dtype=np.float32)
audio_state = 0.0
t = 0.0
frame_count = 0

# =========================
# Main loop
# =========================
with sd.InputStream(
    device=device_id,
    channels=1,
    samplerate=SR,
    blocksize=FRAME
) as stream:

    while True:
        # ===== Read microphone =====
        audio, _ = stream.read(FRAME)
        audio = audio[:, 0].astype(np.float32)

        # RMS
        rms = float(np.sqrt(np.mean(audio * audio) + 1e-12))
        amp = rms * AUDIO_GAIN

        if amp < GATE:
            amp = 0.0

        amp = min(amp, 1.0)

        # Smooth envelope
        audio_state = (1.0 - AUDIO_SMOOTH) * audio_state + AUDIO_SMOOTH * amp

        # Store source excitation history
        current_excitation = BASE_LEVEL + AUDIO_SCALE * audio_state
        audio_buffer[buffer_index] = current_excitation

        # ===== Get delayed excitation for each point =====
        idx1 = (buffer_index - delay_steps1) % BUFFER_LEN
        idx2 = (buffer_index - delay_steps2) % BUFFER_LEN

        gain1 = audio_buffer[idx1]
        gain2 = audio_buffer[idx2]

        # ===== Traveling-looking waves =====
        w1 = 2.0 * np.pi * OSC_SPEED1
        w2 = 2.0 * np.pi * OSC_SPEED2

        wave1 = gain1 * AMP1 * np.sin(k * r1 - w1 * t + PHASE1) * env1
        wave2 = gain2 * AMP2 * np.sin(k * r2 - w2 * t + PHASE2) * env2

        if MODE == 0:
            field = wave1
        elif MODE == 1:
            field = wave2
        else:
            field = wave1 + wave2

        # Smooth visual output
        field_state = (1.0 - ALPHA) * field_state + ALPHA * field
        field_state = np.nan_to_num(field_state, nan=0.0, posinf=0.0, neginf=0.0)

        # ===== Send to Grasshopper less frequently =====
        frame_count += 1
        if frame_count % SEND_EVERY_N_FRAMES == 0:
            flat = field_state.T.flatten()

            # integer scaling for shorter message
            scaled = np.round(np.clip(flat, -CLIP_VALUE, CLIP_VALUE) * SCALE_FACTOR).astype(np.int16)
            msg = ",".join(str(v) for v in scaled)

            sock.sendto(msg.encode("utf-8"), (UDP_IP, UDP_PORT))

        # ===== Advance =====
        buffer_index = (buffer_index + 1) % BUFFER_LEN
        t += TIME_STEP
        time.sleep(TIME_STEP)
# =======
NX = 120
NY = 60
SPACING = 30.0

# actual coordinates
x = np.arange(NX) * SPACING
y = np.arange(NY) * SPACING
X, Y = np.meshgrid(x, y)

WAVELENGTH = 200.0
SPEED1 = 0.5
SPEED2 = 0.5
ATT1 = 0.0008
ATT2 = 0.0008
AMP1 = 5.0
AMP2 = 5.0
PHASE1 = 0.0
PHASE2 = 0.0
TIME_STEP = 0.02
ALPHA = 0.3

SRC1 = (0, 900, 0)
SRC2 = (3600, 900, 0)

print("\nSelect mode:")
print("1 = wave1 only")
print("2 = wave2 only")
print("3 = wave1 + wave2")

mode_input = input("Enter mode (1/2/3): ")

if mode_input == "1":
    MODE = 0
elif mode_input == "2":
    MODE = 1
else:
    MODE = 2

field_state = np.zeros((NY, NX), dtype=np.float32)
t = 0.0
EPS = 1e-6

while True:
    r1 = np.sqrt((X - SRC1[0])**2 + (Y - SRC1[1])**2 + EPS)
    r2 = np.sqrt((X - SRC2[0])**2 + (Y - SRC2[1])**2 + EPS)

    k = 2.0 * np.pi / WAVELENGTH
    w1 = 2.0 * np.pi * SPEED1
    w2 = 2.0 * np.pi * SPEED2

    env1 = np.exp(-ATT1 * r1)
    env2 = np.exp(-ATT2 * r2)

    wave1 = AMP1 * np.sin(k * r1 - w1 * t + PHASE1) * env1
    wave2 = AMP2 * np.sin(k * r2 - w2 * t + PHASE2) * env2

    if MODE == 0:
        field = wave1
    elif MODE == 1:
        field = wave2
    else:
        field = wave1 + wave2

    field_state = (1.0 - ALPHA) * field_state + ALPHA * field




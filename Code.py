# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
#C:\Users\zmsxh\acoustic-architecture

import socket
import time
import numpy as np
import sounddevice as sd

# =========================
# UDP
# =========================
UDP_IP = "127.0.0.1"
UDP_PORT = 9001
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# =========================
# Grid
# =========================
NX = 120
NY = 90
SPACING = 20
x = np.arange(NX) * SPACING
y = np.arange(NY) * SPACING
X, Y = np.meshgrid(x, y)

# =========================
# Source positions
# =========================
SRC1 = (0, 900, 0)
SRC2 = (2400, 900, 0)

# =========================
# Wave / propagation parameters
# =========================
VISUAL_SPEED = 1200.0        # propagation speed for delayed envelope (unit/sec)
OSC_SPEED1 = 0.45            # oscillation speed for source 1
OSC_SPEED2 = 0.45            # oscillation speed for source 2
ATT1 = 0.00075
ATT2 = 0.00075
AMP1 = 4.0
AMP2 = 4.0
PHASE1 = 0.0
PHASE2 = 0.0

TIME_STEP = 0.03
ALPHA = 0.18                 # field smoothing

# =========================
# Audio parameters
# =========================
SR = 48000
FRAME_MS = 50
FRAME = int(SR * FRAME_MS / 1000)

AUDIO_GAIN = 18.0
GATE = 0.008
BASE_LEVEL = 0.00
AUDIO_SCALE = 1.4
AUDIO_SMOOTH = 0.08

# =========================
# Frequency analysis parameters
# =========================
MIN_FREQ = 30.0              # ignore rumble / very low noise
MAX_FREQ = 900.0            # upper analysis bound
FREQ_SMOOTH = 0.08           # smaller = smoother
DEFAULT_FREQ = 250.0         # fallback frequency

# visual wavelength mapping
MIN_WAVELENGTH = 30.0       # shortest visible spacing
MAX_WAVELENGTH = 300.0      # longest visible spacing

# optional stability threshold for FFT peak
FFT_MAG_THRESHOLD = 0.01

# =========================
# Transmission optimization
# =========================
SEND_EVERY_N_FRAMES = 3
CLIP_VALUE = 30.0
SCALE_FACTOR = 50

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

env1 = np.exp(-ATT1 * r1)
env2 = np.exp(-ATT2 * r2)

# =========================
# Delay buffer setup
# =========================
max_r = max(np.max(r1), np.max(r2))
max_delay_sec = max_r / VISUAL_SPEED

BUFFER_SEC = max_delay_sec + 1.0
BUFFER_LEN = int(BUFFER_SEC / TIME_STEP) + 10

audio_buffer = np.full(BUFFER_LEN, BASE_LEVEL, dtype=np.float32)
buffer_index = 0

delay_steps1 = np.round((r1 / VISUAL_SPEED) / TIME_STEP).astype(np.int32)
delay_steps2 = np.round((r2 / VISUAL_SPEED) / TIME_STEP).astype(np.int32)

# =========================
# States
# =========================
field_state = np.zeros((NY, NX), dtype=np.float32)
audio_state = 0.0
freq_state = DEFAULT_FREQ
t = 0.0
frame_count = 0

# =========================
# Helper: frequency -> wavelength
# =========================
def map_frequency_to_wavelength(freq_hz):
    """
    Low frequency  -> long visual wavelength
    High frequency -> short visual wavelength
    """
    freq_clamped = np.clip(freq_hz, MIN_FREQ, MAX_FREQ)
    ratio = (freq_clamped - MIN_FREQ) / (MAX_FREQ - MIN_FREQ)
    wavelength = MAX_WAVELENGTH - ratio * (MAX_WAVELENGTH - MIN_WAVELENGTH)
    return wavelength

# =========================
# Helper: dominant frequency from FFT
# =========================
def estimate_dominant_frequency(audio_frame, sr):
    """
    Estimate dominant frequency using FFT.
    Returns None when no reliable peak is found.
    """
    if len(audio_frame) == 0:
        return None

    # remove DC
    sig = audio_frame - np.mean(audio_frame)

    # windowing
    window = np.hanning(len(sig))
    spec = np.fft.rfft(sig * window)
    freqs = np.fft.rfftfreq(len(sig), d=1.0 / sr)
    mag = np.abs(spec)

    # valid band only
    valid = (freqs >= MIN_FREQ) & (freqs <= MAX_FREQ)
    if not np.any(valid):
        return None

    freqs_valid = freqs[valid]
    mag_valid = mag[valid]

    if len(mag_valid) == 0:
        return None

    peak_idx = np.argmax(mag_valid)
    peak_mag = mag_valid[peak_idx]

    if peak_mag < FFT_MAG_THRESHOLD:
        return None

    return float(freqs_valid[peak_idx])

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

        # ===== Amplitude (RMS) =====
        rms = float(np.sqrt(np.mean(audio * audio) + 1e-12))
        amp = rms * AUDIO_GAIN

        if amp < GATE:
            amp = 0.0

        amp = min(amp, 1.0)

        # Smooth envelope
        audio_state = (1.0 - AUDIO_SMOOTH) * audio_state + AUDIO_SMOOTH * amp

        # ===== Frequency estimation =====
        dominant_freq = estimate_dominant_frequency(audio, SR)

        if dominant_freq is not None and amp > 0.0:
            freq_state = (1.0 - FREQ_SMOOTH) * freq_state + FREQ_SMOOTH * dominant_freq

        # Convert frequency to visual wavelength
        wavelength_dynamic = map_frequency_to_wavelength(freq_state)
        k = 2.0 * np.pi / wavelength_dynamic

        # ===== Store source excitation history =====
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

            scaled = np.round(
                np.clip(flat, -CLIP_VALUE, CLIP_VALUE) * SCALE_FACTOR
            ).astype(np.int16)

            msg = ",".join(str(v) for v in scaled)
            sock.sendto(msg.encode("utf-8"), (UDP_IP, UDP_PORT))

            # optional debug
            print(
                f"amp={audio_state:.3f} | freq={freq_state:7.1f} Hz | "
                f"lambda={wavelength_dynamic:7.1f}"
            )

        # ===== Advance =====
        buffer_index = (buffer_index + 1) % BUFFER_LEN
        t += TIME_STEP
        time.sleep(TIME_STEP)
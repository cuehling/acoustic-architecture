# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import socket, time
import numpy as np
import sounddevice as sd

# ===== UDP =====
UDP_IP = "127.0.0.1"
UDP_PORT = 9001
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ===== Grid =====
NY = 15   # waterfall history (Y axis in GH)
NX = 18   # columns per row (X axis in GH)
height = np.zeros((NY, NX), dtype=float)

# ===== Audio =====
SR = 16000          # Sampling rate (samples per second)
FRAME_MS = 60       # Frame length (lower = faster response)
FRAME = int(SR * FRAME_MS / 1000)   # number of samples per frame

# ===== Tuning knobs =====
GAIN = 90            # amplitude scaling (response strength: 20~120)
GATE = 0.04          # Remove background nois: < Value -> 0 (0.01~0.05)
DECAY = 0.85         # fade speed (0.85~0.97)
ALPHA = 0.2          # smoothing factor (response speed: 0.15~0.4)
PHASE_SPEED = 0.3    # (0.15~0.8)
NOISE = 0.05         # randomness(0~0.05)

phase = 0.0
row_state = np.zeros(NX, dtype=float) 

def smooth_row(row):
    return (np.roll(row, 1) + 2*row + np.roll(row, -1)) / 4.0

with sd.InputStream(channels=1, samplerate=SR, blocksize=FRAME) as stream:
    while True:
        # 1) Audio read
        x, _ = stream.read(FRAME)
        x = x[:, 0].astype(np.float32)

        # 2) Amplitude
        rms = float(np.sqrt(np.mean(x*x) + 1e-12))
        amp = rms * GAIN
        #amp = np.clip(rms * GAIN, 0.0, 1.0)

        # 3) Gate: Background noise filter
        if amp < GATE:
            amp = 0.0

        # 4) Watr fall
        xs = np.linspace(0, 2*np.pi, NX, endpoint=False)
        wave = 0.5 + 0.5*np.sin(xs + phase)          # 0~1
        wave = smooth_row(wave)                      # 더 부드럽게
        wave = amp * wave                            # 볼륨이 클수록 높아짐

        # Noise ctrl
        if NOISE > 0:
            wave = np.clip(wave + NOISE*np.random.randn(NX), 0.0, 1.0)

        # 5) Alpha: Smoothing
        row_state = (1-ALPHA)*row_state + ALPHA*wave
        new_row = row_state

        # 6) Decay
        height *= DECAY

        # 7) Waterfall data mapping
        height[1:, :] = height[:-1, :]
        height[0, :] = new_row

        # 8) UDP 
        msg = ",".join([f"{v:.4f}" for v in height.flatten()])
        sock.sendto(msg.encode("utf-8"), (UDP_IP, UDP_PORT))

        # phase update
        phase += PHASE_SPEED

        time.sleep(0.02)
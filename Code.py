# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import socket, time
import numpy as np
import sounddevice as sd

# ===== Show audio devices =====
print("\nAvailable audio input devices:\n")
devices = sd.query_devices()

for i, d in enumerate(devices):
    if d['max_input_channels'] > 0:   # 입력 가능한 장치만 표시
        print(f"{i}: {d['name']}")

device_id = int(input("\nSelect device number: "))

# ===== UDP =====
UDP_IP = "127.0.0.1"
UDP_PORT = 9001
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ===== Grid =====
NY = 20
NX = 30
height = np.zeros((NY, NX), dtype=float)

# ===== Audio =====
SR = 48000
FRAME_MS = 60
FRAME = int(SR * FRAME_MS / 1000)

# ===== Tuning knobs =====
GAIN = 90
GATE = 0.04
DECAY = 0.85
ALPHA = 0.4
PHASE_SPEED = 0.2
NOISE = 0.01

phase = 0.0
row_state = np.zeros(NX, dtype=float)

def smooth_row(row):
    return (np.roll(row, 1) + 2*row + np.roll(row, -1)) / 4.0

# ===== Audio Stream =====
with sd.InputStream(device=device_id,
                    channels=1,
                    samplerate=SR,
                    blocksize=FRAME) as stream:

    while True:

        # 1) Audio read
        x, _ = stream.read(FRAME)
        x = x[:, 0].astype(np.float32)

        # 2) Amplitude
        rms = float(np.sqrt(np.mean(x*x) + 1e-12))
        amp = rms * GAIN

        # 3) Gate
        if amp < GATE:
            amp = 0.0

        # 4) Wave generation
        xs = np.linspace(0, 2*np.pi, NX, endpoint=False)
        wave = 0.5 + 0.5*np.sin(xs + phase)
        wave = smooth_row(wave)
        wave = amp * wave

        if NOISE > 0:
            wave = np.clip(wave + NOISE*np.random.randn(NX), 0.0, 1.0)

        # 5) smoothing
        row_state = (1-ALPHA)*row_state + ALPHA*wave
        new_row = row_state

        # 6) decay
        height *= DECAY

        # 7) waterfall
        height[1:, :] = height[:-1, :]
        height[0, :] = new_row

        # 8) UDP
        msg = ",".join([f"{v:.4f}" for v in height.flatten()])
        sock.sendto(msg.encode("utf-8"), (UDP_IP, UDP_PORT))

        phase += PHASE_SPEED

        time.sleep(0.02)
    
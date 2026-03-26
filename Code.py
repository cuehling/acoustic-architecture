# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import socket
import time
import numpy as np

UDP_IP = "127.0.0.1"
UDP_PORT = 9001
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

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

    msg = ",".join(f"{v:.5f}" for v in field_state.T.flatten())
    sock.sendto(msg.encode("utf-8"), (UDP_IP, UDP_PORT))

    t += TIME_STEP
    time.sleep(0.03)
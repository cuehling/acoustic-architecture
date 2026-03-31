import numpy as np

class WaveProcessor:
    def __init__(self, mode=2):
        # Grid Setup
        self.NX, self.NY = 100, 72
        self.SPACING = 30.0
        x = np.arange(self.NX) * self.SPACING
        y = np.arange(self.NY) * self.SPACING
        self.X, self.Y = np.meshgrid(x, y)

        # Constants
        self.WAVELENGTH = 200.0
        self.VISUAL_SPEED = 1200.0
        self.OSC_SPEED1 = 0.45
        self.OSC_SPEED2 = 0.45
        self.ATT1 = self.ATT2 = 0.00075
        self.AMP1 = self.AMP2 = 4.0
        self.TIME_STEP = 0.03
        self.ALPHA = 0.18
        self.MODE = mode # 0, 1, or 2

        # Precompute Distances
        self.SRC1, self.SRC2 = (0, 1080, 0), (3000, 1080, 0)
        self.r1 = np.sqrt((self.X - self.SRC1[0])**2 + (self.Y - self.SRC1[1])**2 + 1e-6)
        self.r2 = np.sqrt((self.X - self.SRC2[0])**2 + (self.Y - self.SRC2[1])**2 + 1e-6)
        
        # State & Buffers
        self.field_state = np.zeros((self.NY, self.NX), dtype=np.float32)
        self.audio_state = 0.0
        self.t = 0.0
        
        # Delay Buffer Logic
        max_r = max(np.max(self.r1), np.max(self.r2))
        self.BUFFER_LEN = int((max_r / self.VISUAL_SPEED + 1.0) / self.TIME_STEP) + 10
        self.audio_buffer = np.full(self.BUFFER_LEN, 0.0, dtype=np.float32)
        self.buffer_index = 0
        self.delay_steps1 = np.round((self.r1 / self.VISUAL_SPEED) / self.TIME_STEP).astype(np.int32)
        self.delay_steps2 = np.round((self.r2 / self.VISUAL_SPEED) / self.TIME_STEP).astype(np.int32)

    def transform(self, raw_audio):
        # Calculate RMS and Envelope
        rms = float(np.sqrt(np.mean(raw_audio**2) + 1e-12))
        amp = min(rms * 18.0, 1.0) # Using AUDIO_GAIN=18.0
        self.audio_state = (1.0 - 0.08) * self.audio_state + 0.08 * amp
        
        # Update Buffer
        current_excitation = 0.0 + 1.4 * self.audio_state # BASE_LEVEL + AUDIO_SCALE
        self.audio_buffer[self.buffer_index] = current_excitation

        # Calculate Waves
        idx1 = (self.buffer_index - self.delay_steps1) % self.BUFFER_LEN
        idx2 = (self.buffer_index - self.delay_steps2) % self.BUFFER_LEN
        
        k = 2.0 * np.pi / self.WAVELENGTH
        wave1 = self.audio_buffer[idx1] * self.AMP1 * np.sin(k * self.r1 - (2.0 * np.pi * self.OSC_SPEED1) * self.t) * np.exp(-self.ATT1 * self.r1)
        wave2 = self.audio_buffer[idx2] * self.AMP2 * np.sin(k * self.r2 - (2.0 * np.pi * self.OSC_SPEED2) * self.t) * np.exp(-self.ATT2 * self.r2)

        field = wave1 + wave2 if self.MODE == 2 else (wave1 if self.MODE == 0 else wave2)
        self.field_state = (1.0 - self.ALPHA) * self.field_state + self.ALPHA * field
        
        # Advance State
        self.buffer_index = (self.buffer_index + 1) % self.BUFFER_LEN
        self.t += self.TIME_STEP
        
        # Prepare for GH: Scale and Flatten
        scaled = np.round(np.clip(self.field_state.T.flatten(), -9.9, 9.9) * 10).astype(np.int16)
        return scaled
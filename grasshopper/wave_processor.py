import socket
import time
import numpy as np
import sounddevice as sd


class WaveProcessor():

    # Grid 
    nx = 100
    ny = 72
    spacing = 10

    # Source Position
    src1 = (  0, 180, 0)
    src2 = (500, 360, 0)
    src3 = (400,   0, 0)

    # Wave Propagation Parameters
    vis_speed = 1200.0  # Propagation Speed
    osc_speed = 0.45    # oscillation speed for source 1
    att       = 0.00075 # Attenuation for source
    amp       = 4.0     # Amplitude for source
    phase     = 0.0     # Phase for source
    time_step = 0.03    # time step
    alpha     = 0.18    # field smoothing

    # Audio parameters
    SR = 48000
    FRAME_MS = 50
    FRAME = int(SR * FRAME_MS / 1000)

    audio_gain   = 18.0
    gate         = 0.008
    base_lvl     = 0.00
    audio_scale  = 1.4
    audio_smooth = 0.08

    # Frequency Parameters
    min_freq = 80.0        # ignore rumble
    max_freq = 1200.0      # upper analysis bound
    freq_smooth = 0.08     # smaller = smoother
    default_freq = 250.0   # fallback freq

    # visual wavelength mapping
    min_wavelength = 60.0  # shortest visible spacing
    max_wavelength = 500.0 # longest visible spacing
    eps = 1e-6

    # Optional stability threshold for FFT peak
    fft_mag_threshold = 0.01

    # Transmission Optimization
    send_every_n_frames = 3
    clip_value          = 9.9
    scale_factor        = 10

    def __init__(self):
        self.audio_metadata = None

        print('Initializing Wave Processor...')

        # Precompute Distances
        x = np.arange(self.nx) * self.spacing
        y = np.arange(self.ny) * self.spacing
        self.X, self.Y = np.meshgrid(x, y)

        print("\nSelect mode:")
        print("1 = wave1 only")
        print("2 = wave2 only")
        print("3 = wave1 + wave2")

        mode_input = input("Enter mode (1/2/3): ")

        if mode_input == "1":
            self.mode = 0
        elif mode_input == "2":
            self.mode = 1
        else:
            self.mode = 2

        # Precompute Distances
        self.r1 = np.sqrt((self.X - self.src1[0])**2 + (self.Y - self.src1[1])**2 + self.eps)
        self.r2 = np.sqrt((self.X - self.src2[0])**2 + (self.Y - self.src2[1])**2 + self.eps)
        self.r3 = np.sqrt((self.X - self.src3[0])**2 + (self.Y - self.src3[1])**2 + self.eps)
        
        self.env1 = np.exp(-self.att * self.r1)
        self.env2 = np.exp(-self.att * self.r2)
        self.env3 = np.exp(-self.att * self.r3)

        # Delay buffer setup
        max_r = max(np.max(self.r1), np.max(self.r2))
        max_delay_sec = max_r / self.vis_speed

        buffer_sec = max_delay_sec + 1.0
        self.buffer_len = int(buffer_sec / self.time_step) + 10

        self.audio_buffer = np.full(self.buffer_len, self.base_lvl, dtype=np.float32)
        self.buffer_index = 0

        self.delay_steps1 = np.round((self.r1 / self.vis_speed) / self.time_step).astype(np.int32)
        self.delay_steps2 = np.round((self.r2 / self.vis_speed) / self.time_step).astype(np.int32)

        # States
        self.field_state = np.zeros((self.ny, self.nx), dtype=np.float32)
        self.audio_state = 0.0
        self.freq_state = self.default_freq
        self.t = 0.0
        self.frame_count = 0

    def set_up_processor(self, audio_metadata):
        pass

    # ======================================================================
    def transform(self, raw_audio):

        # read data
        audio = raw_audio.astype(np.float32)

        # get audio metadata
        self.samplerate = self.audio_metadata['samplerate']

        # ===== Amplitude (RMS) =====
        rms = float(np.sqrt(np.mean(audio * audio) + 1e-12))
        amp = rms * self.audio_gain

        if amp < self.gate:
            amp = 0.0

        amp = min(amp, 1.0)

        # Smooth envelope
        self.audio_state = (1.0 - self.audio_smooth) * self.audio_state + self.audio_smooth * amp

        # ===== Frequency estimation =====
        dominant_freq = self.estimate_dominant_frequency(audio, self.samplerate)

        if dominant_freq is not None and amp > 0.0:
            self.freq_state = (1.0 - self.freq_smooth) * self.freq_state + self.freq_smooth * dominant_freq

        # Convert frequency to visual wavelength
        wavelength_dynamic = self.map_frequency_to_wavelength(self.freq_state)
        k = 2.0 * np.pi / wavelength_dynamic

        # ===== Store source excitation history =====
        current_excitation = self.base_lvl + self.audio_scale * self.audio_state
        self.audio_buffer[self.buffer_index] = current_excitation

        # ===== Get delayed excitation for each point =====
        idx1 = (self.buffer_index - self.delay_steps1) % self.buffer_len 
        idx2 = (self.buffer_index - self.delay_steps2) % self.buffer_len

        gain1 = self.audio_buffer[idx1]
        gain2 = self.audio_buffer[idx2]

        # ===== Traveling-looking waves =====
        w1 = 2.0 * np.pi * self.osc_speed
        w2 = 2.0 * np.pi * self.osc_speed
        wave1 = gain1 * self.amp * np.sin(k * self.r1 - w1 * self.t + self.phase) * self.env1
        wave2 = gain2 * self.amp * np.sin(k * self.r2 - w2 * self.t + self.phase) * self.env2

        if self.mode == 0:
            field = wave1
        elif self.mode == 1:
            field = wave2
        else:
            field = wave1 + wave2

        # Smooth visual output
        self.field_state = (1.0 - self.alpha) * self.field_state + self.alpha * field
        self.field_state = np.nan_to_num(self.field_state, nan=0.0, posinf=0.0, neginf=0.0)

        # ===== Send to Grasshopper less frequently =====
        # self.frame_count = 0
        # if self.frame_count % self.send_every_n_frames == 0:

        flat = self.field_state.T.flatten()

        scaled = np.round(
            np.clip(flat, -self.clip_value, self.clip_value) * self.scale_factor
        ).astype(np.int16)

        msg = ",".join(str(v) for v in scaled)

        # optional debug
        print(
            f"amp={self.audio_state:.3f} | freq={self.freq_state:7.1f} Hz | "
            f"lambda={wavelength_dynamic:7.1f}"
        )

        # ===== Advance =====
        self.buffer_index = (self.buffer_index + 1) % self.buffer_len
        self.t += self.time_step 
        time.sleep(self.time_step)
        return msg

        

        


    # ==============  Helper Functions  =====================
    def map_frequency_to_wavelength(self, freq_hz):
        """
        Low frequency  -> long visual wavelength
        High frequency -> short visual wavelength
        """
        freq_clamped = np.clip(freq_hz, self.min_freq, self.max_freq)
        ratio = (freq_clamped - self.min_freq) / (self.max_freq - self.min_freq)
        wavelength = self.max_wavelength - ratio * (self.max_wavelength - self.min_wavelength)
        return wavelength

    
    def estimate_dominant_frequency(self, audio_frame, sr):
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
        valid = (freqs >= self.min_freq) & (freqs <= self.max_freq)
        if not np.any(valid):
            return None

        freqs_valid = freqs[valid]
        mag_valid = mag[valid]

        if len(mag_valid) == 0:
            return None

        peak_idx = np.argmax(mag_valid)
        peak_mag = mag_valid[peak_idx]

        if peak_mag < self.fft_mag_threshold:
            return None

        return float(freqs_valid[peak_idx])


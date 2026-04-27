
import time
import numpy as np
import sounddevice as sd


class WaveProcessor():

    inputs = { 'Choose Mode: ':[ 'Source 1',
                                'Source 2',
                                'Both Sources' ]}

    # Source Position
    src1 = (  0, 0.5,  0) 
    src2 = (  1, 0.5,  0)

    # Wave Propagation Parameters
    osc_speed = 0.005   # oscillation speed
    att       = 0.003  # Attenuation for source
    alpha     = 0.25    # field smoothing

    audio_gain   = 5
    gate         = 0.002
    base_lvl     = 0.00
    audio_scale  = 1.4
    audio_smooth = 0.01

    # Frequency Parameters
    min_freq = 80.0        # ignore rumble
    max_freq = 1200.0      # upper analysis bound
    freq_smooth = 0.08     # smaller = smoother
    default_freq = 250.0   # fallback freq

    # visual wavelength mapping
    min_wavelength = 50.0  # shortest visible spacing
    max_wavelength = 500.0 # longest visible spacing
    eps = 1e-6

    # Optional stability threshold for FFT peak
    fft_mag_threshold = 0.01

    # Transmission Optimization
    clip_value          = 20
    scale_factor        = 10

    def __init__(self, nx, ny, spacing, metadata):
        print('Initializing Wave Processor...')
        print(metadata)

        x = np.arange(0, nx) * spacing
        y = np.arange(0, ny) * spacing

        self.X, self.Y = np.meshgrid(x, y)
        self.audio_metadata = metadata
        self.sr = metadata['samplerate']
        self.time_step = metadata['frame'] / metadata['samplerate']

        self.src1 = (x[-1]*self.src1[0], y[-1]*self.src1[1], 0)
        self.src2 = (x[-1]*self.src2[0], y[-1]*self.src2[1], 0)
        print(f"src1: {self.src1}, src2: {self.src2}")

        # Precompute Distances
        self.r1 = np.sqrt((self.X - self.src1[0])**2 + (self.Y - self.src1[1])**2 + self.eps)
        self.r2 = np.sqrt((self.X - self.src2[0])**2 + (self.Y - self.src2[1])**2 + self.eps)
        
        self.env1 = np.exp(-self.att * self.r1)
        self.env2 = np.exp(-self.att * self.r2)

        # States
        self.field_state = np.zeros((ny, nx), dtype=np.float32)
        self.audio_state = 0.0
        self.freq_state  = 0.0

    def set_up_processor(self, response_dict=None):

        # Collect Source Data
        if response_dict:
            for key1, value1 in response_dict.items():
                if key1 == 'Choose Mode: ':
                    if value1 == 'Source 1':
                        self.mode = 0
                    elif value1 == 'Source 2':
                        self.mode = 1
                    else:
                        self.mode = 2
        
        
    # ======================================================================
    def transform(self, t_scalar, raw_audio):

        # read data
        audio = raw_audio.astype(np.float32)
        t = t_scalar[-1]

        #  1.) Amplitude Tracking (RMS)
        rms = float(np.sqrt(np.mean(audio * audio) + 1e-12))
        amp_env = (rms * self.audio_gain)
        print(amp_env)

        # Use a fast attack to catch the sound, but a slow release to let it linger
        target_amp = amp_env # This is your incoming mic level

        # ATTACK: Fast response to new sound   
        if target_amp > self.audio_state: alpha = 0.2 
        # RELEASE: Very slow fade out
        else: alpha = 0.005 

        self.audio_state = (1.0 - alpha) * self.audio_state + alpha * target_amp

        # if amp_env < self.gate: amp_env = 0.0
        # self.audio_state = (1.0 - self.audio_smooth) * self.audio_state + self.audio_smooth * amp_env

        #  2.) Frequency with Clamping
        dom_freq = self.estimate_dominant_frequency(audio, self.sr)

        if dom_freq is not None and amp_env > 0.0:
            self.freq_state = (1.0 - self.freq_smooth) * self.freq_state + self.freq_smooth * dom_freq

        #  3.) Antialiasing mapping 
        wavelength_dynamic = self.map_frequency_to_wavelength(self.freq_state)
        k = 2.0 * np.pi / wavelength_dynamic

        #   4.) Oscillation Freq Decoupling 
        w = 2.0 * np.pi * self.osc_speed * dom_freq *0.1
        
        # 5. Field Calculation (store source excitation history)
        current_excitation = self.base_lvl + self.audio_scale * self.audio_state
        
       
        wave1 = amp_env * current_excitation* np.sin( - k * self.r1 + w * t) * self.env1
        wave2 = amp_env * current_excitation* np.sin( - k * self.r2 + w * t) * self.env2

        #  6.) Mode Selection
        if self.mode == 0:   field = wave1
        elif self.mode == 1: field = wave2
        else:                field = wave1 + wave2

        #   7.) Spatial Smoothing 
        self.field_state = (1.0 - self.alpha) * self.field_state + self.alpha * field
        self.field_state = np.nan_to_num(self.field_state, nan=0.0, posinf=0.0, neginf=0.0)

        # optional debug
        print(
            f"amp={self.audio_state:.3f} | freq={self.freq_state:7.1f} Hz | "
            f"lambda={wavelength_dynamic:7.1f}"
        )

        return self.field_state


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
            return self.default_freq

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
            return self.default_freq

        freqs_valid = freqs[valid]
        mag_valid = mag[valid]

        if len(mag_valid) == 0:
            return self.default_freq

        peak_idx = np.argmax(mag_valid)
        peak_mag = mag_valid[peak_idx]

        if peak_mag < self.fft_mag_threshold:
            return self.default_freq

        return float(freqs_valid[peak_idx])


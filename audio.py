"""Audio capture and playback for the AIY Voice HAT via ALSA (arecord/aplay).

Works on stock Raspberry Pi OS once the Voice HAT sound-card overlay is enabled
(see setup notes). No `aiy` library required — just alsa-utils, which ships with
Raspberry Pi OS.
"""

import signal
import subprocess


class Recorder:
    """Records to a WAV file for as long as the button is held.

    Usage:
        rec = Recorder(device="plughw:CARD=sndrpigooglevoi,DEV=0")
        rec.start("/tmp/in.wav")
        button.wait_for_release()
        rec.stop()
    """

    def __init__(self, device="default", rate=16000, channels=1):
        self.device = device
        self.rate = rate
        self.channels = channels
        self._proc = None

    def start(self, wav_path):
        self._proc = subprocess.Popen([
            "arecord",
            "-D", self.device,
            "-f", "S16_LE",          # 16-bit signed little-endian
            "-r", str(self.rate),    # 16 kHz is ideal for speech models
            "-c", str(self.channels),
            "-t", "wav",
            "-q",
            wav_path,
        ])

    def stop(self):
        if self._proc:
            # SIGINT lets arecord finalise the WAV header cleanly.
            self._proc.send_signal(signal.SIGINT)
            self._proc.wait()
            self._proc = None


def play_wav(wav_path, device="default"):
    subprocess.run(["aplay", "-q", "-D", device, wav_path], check=False)

"""Audio capture and playback for the AIY Voice HAT via ALSA (arecord/aplay).

Works on stock Raspberry Pi OS once the Voice HAT sound-card overlay is enabled
(see setup notes). No `aiy` library required — just alsa-utils, which ships with
Raspberry Pi OS.
"""

import array
import signal
import subprocess
import wave


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


def _scale_wav(src_path, dst_path, volume):
    """Write a copy of a 16-bit PCM WAV with every sample multiplied by `volume`.

    The Voice HAT v1 sound card has no ALSA mixer, so this is how we set volume:
    scale the samples in software before handing the file to aplay.
    """
    with wave.open(src_path, "rb") as w:
        params = w.getparams()
        frames = w.readframes(w.getnframes())

    if params.sampwidth == 2:  # 16-bit signed — what OpenAI TTS gives us
        samples = array.array("h")
        samples.frombytes(frames)
        for i in range(len(samples)):
            v = int(samples[i] * volume)
            samples[i] = 32767 if v > 32767 else -32768 if v < -32768 else v
        frames = samples.tobytes()

    with wave.open(dst_path, "wb") as w:
        w.setparams(params)
        w.writeframes(frames)


def play_wav(wav_path, device="default", volume=1.0):
    if volume < 1.0:
        scaled = wav_path + ".vol.wav"
        _scale_wav(wav_path, scaled, volume)
        wav_path = scaled
    subprocess.run(["aplay", "-q", "-D", device, wav_path], check=False)

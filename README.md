# openaiy

A simple, private **push-to-talk voice assistant** for the **Google AIY Voice
Kit v1** hardware — powered by OpenAI instead of Google Assistant.

Reuse the exact kit you already built (Raspberry Pi 3 + Voice HAT + arcade
button). Hold the button, speak, release, and get a spoken answer. No Google
account, no always-on listening — it only records while you hold the button, and
the button LED flashes so you can see exactly when it's listening.

Everything runs through OpenAI, so the only thing you need to supply is **one
OpenAI API key**.

---

## What it does

- **Push-to-talk.** Hold the button = recording. Release = it answers. It never
  listens on its own.
- **Visible state via the LED** (see the table below) — you always know what
  it's doing without a screen.
- **OpenAI end to end:** Whisper for speech-to-text, a chat model for the reply,
  and OpenAI text-to-speech for the voice.
- **Boots ready.** A systemd service starts it automatically on power-on. Plug
  it in, wait for it to boot, press the button.

## How it works

```
button press ─▶ record (arecord) ─▶ Whisper (speech-to-text) ─▶ chat model ─▶ OpenAI TTS ─▶ play (aplay)
```

## What you need

- An assembled **AIY Voice Kit v1** (Raspberry Pi 3, Voice HAT, mic, speaker,
  arcade button).
- A fresh **Raspberry Pi OS (64-bit)** SD card from the Raspberry Pi Imager,
  with Wi-Fi/network and SSH set up.
- An **OpenAI API key** — <https://platform.openai.com/api-keys>.

## Files

| File             | What it is                                                      |
|------------------|-----------------------------------------------------------------|
| `assistant.py`   | The main loop: button → record → transcribe → reply → speak.    |
| `audio.py`       | Recording and playback via ALSA (`arecord` / `aplay`).          |
| `providers.py`   | The three OpenAI stages (STT, chat, TTS).                       |
| `config.yaml`    | Your settings: voice, model, system prompt, audio device.       |
| `install.sh`     | One-shot setup: deps, sound card, key, and the boot service.    |
| `requirements.txt` | Python dependencies (install.sh handles these).               |

## Install

On the Pi:

```bash
git clone https://github.com/<you>/openaiy.git
cd openaiy
chmod +x install.sh
sudo ./install.sh
```

The script will:

1. Install the system and Python packages.
2. Enable the Voice HAT sound card (adds `dtoverlay=googlevoicehat-soundcard`).
3. Add your user to the `gpio` and `audio` groups.
4. Prompt once for your **OpenAI API key** (hidden input; saved to
   `openaiy.env`, permissions `600`, git-ignored).
5. Register and enable the `openaiy` systemd service.

Because the sound card is enabled for the first time, the script asks you to
reboot once:

```bash
sudo reboot
```

After that, the assistant comes up automatically on every boot. **Hold the
button, talk, release.**

## Using it — the LED tells you what's happening

| LED                 | Meaning                                              |
|---------------------|------------------------------------------------------|
| Two quick blinks    | Just booted and ready                                |
| Flashing            | Listening (button held)                              |
| Solid on            | Thinking (transcribing + asking the model + speaking)|
| Three quick blinks  | That turn hit an error (it keeps running)            |
| Off                 | Idle, waiting for a press                            |

## Configuration

Edit `config.yaml`, then `sudo systemctl restart openaiy`. The interesting bits:

```yaml
audio:
  volume: 0.3             # playback loudness, 0.0–1.0 (default 0.3)

llm:
  model: gpt-4o-mini      # any OpenAI chat model
  system_prompt: >
    You are a helpful voice assistant. Reply in one or two short sentences.

tts:
  voice: alloy            # alloy | echo | fable | onyx | nova | shimmer
```

Want a different personality? Change `system_prompt`. Want a different voice?
Change `voice`. Want smarter (pricier) answers? Point `llm.model` at a larger
OpenAI model.

### Volume

The Voice HAT v1 sound card has **no hardware volume control** (`alsamixer`
shows nothing for it), so loudness is set in software via `audio.volume` in
`config.yaml` — a fraction from `0.0` (silent) to `1.0` (full scale), defaulting
to `0.3`. The samples are scaled before playback, so it works on the stock card
with no extra setup. Edit the value and `sudo systemctl restart openaiy` to
apply.

## Managing the service

```bash
systemctl status openaiy          # is it running?
journalctl -u openaiy -f          # live logs + transcripts
sudo systemctl restart openaiy    # after editing config.yaml
sudo systemctl disable openaiy    # stop it auto-starting on boot
```

## Troubleshooting

- **No sound / mic not found.** Run `arecord -l` and `aplay -l`. If the card
  isn't named `sndrpigooglevoi`, update `record_device` / `play_device` in
  `config.yaml` to match, then restart the service. Test the raw hardware with:
  ```bash
  arecord -D plughw:CARD=sndrpigooglevoi,DEV=0 -f S16_LE -r 16000 -c 1 -d 3 t.wav
  aplay   -D plughw:CARD=sndrpigooglevoi,DEV=0 t.wav
  ```
- **Too quiet or too loud.** The Voice HAT v1 has no hardware mixer, so
  `alsamixer` won't help — adjust `audio.volume` in `config.yaml` (0.0–1.0) and
  restart the service.
- **It says the key is missing.** Check `openaiy.env` contains a real
  `OPENAI_API_KEY=...`, then restart the service.
- **Nothing happens on button press.** Confirm your user is in the `gpio` group
  (`groups`); log out/in or reboot if you were just added.

## A note on cost and privacy

Every interaction sends your recorded audio and the reply text to OpenAI, which
bills per use. With the default small model and short spoken replies this is
very cheap, but it is not free and it is not fully local — audio leaves the
device. (A Raspberry Pi 3 isn't powerful enough to run capable models locally;
that's why this kit uses an API.)

## License

MIT — see `LICENSE`. Permissive: use it, fork it, build on it, even sell it —
just keep the copyright notice. Contributions and forks welcome.

## Disclaimer

A community project for reusing AIY Voice Kit v1 hardware. Not affiliated with,
sponsored by, or endorsed by Google or OpenAI.

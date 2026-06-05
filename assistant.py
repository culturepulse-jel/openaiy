#!/usr/bin/env python3
"""Provider-agnostic push-to-talk voice assistant for the AIY Voice Kit v1,
running on stock 64-bit Raspberry Pi OS. No Google, no aiy library.

Hardware (v1): Raspberry Pi 3 + Voice HAT + arcade button.
    Button -> GPIO 23, button LED -> GPIO 25 (Voice HAT defaults).

LED states:
    two quick blinks at startup   -> ready
    flashing while button held    -> listening
    solid on                      -> thinking (transcribe + LLM + speech)
    three quick blinks            -> an error happened this turn (it keeps running)

STT / LLM / TTS are selected in config.yaml (OpenAI by default).
"""

import os
import yaml
from gpiozero import Button, LED

from audio import Recorder, play_wav
from providers import build_stt, build_llm, build_tts

HERE = os.path.dirname(os.path.abspath(__file__))
IN_WAV = "/tmp/aiy_in.wav"
OUT_WAV = "/tmp/aiy_out.wav"

BUTTON_GPIO = 23   # Voice HAT v1 arcade button
LED_GPIO = 25      # Voice HAT v1 arcade-button LED


def load_config(path=None):
    with open(path or os.path.join(HERE, "config.yaml")) as f:
        return yaml.safe_load(f)


def main():
    cfg = load_config()
    stt = build_stt(cfg["stt"])
    llm = build_llm(cfg["llm"])
    tts = build_tts(cfg["tts"])

    audio = cfg.get("audio", {})
    recorder = Recorder(
        device=audio.get("record_device", "default"),
        rate=audio.get("sample_rate", 16000),
        channels=audio.get("channels", 1),
    )
    play_device = audio.get("play_device", "default")

    button = Button(BUTTON_GPIO)   # pull_up=True (default) matches the HAT wiring
    led = LED(LED_GPIO)

    system_prompt = cfg["llm"].get(
        "system_prompt",
        "You are a helpful voice assistant. Keep replies short and conversational.",
    )
    history = [{"role": "system", "content": system_prompt}]
    max_turns = cfg.get("max_history_turns", 8)

    # Ready signal: two quick blinks.
    led.blink(on_time=0.1, off_time=0.1, n=2, background=False)
    led.off()

    print("Ready. Hold the button and speak; release when you're done. Ctrl-C to quit.")
    try:
        while True:
            button.wait_for_press()
            led.blink(on_time=0.2, off_time=0.2)   # flashing = listening
            recorder.start(IN_WAV)

            button.wait_for_release()
            recorder.stop()

            led.on()                                # solid = thinking
            try:
                text = stt.transcribe(IN_WAV)
                if not text:
                    print("(heard nothing)")
                    led.off()
                    continue
                print("You:", text)

                history.append({"role": "user", "content": text})
                reply = llm.chat(history)
                history.append({"role": "assistant", "content": reply})
                print("Assistant:", reply)

                # Keep system prompt + most recent turns so context stays small.
                if len(history) > 1 + 2 * max_turns:
                    history = [history[0]] + history[-2 * max_turns:]

                tts.synthesize(reply, OUT_WAV)
                led.off()
                play_wav(OUT_WAV, device=play_device)

            except Exception as exc:
                print("Error this turn:", exc)
                # Drop the half-finished user turn so history stays consistent.
                if len(history) > 1 and history[-1]["role"] == "user":
                    history.pop()
                led.blink(on_time=0.1, off_time=0.1, n=3, background=False)
                led.off()
    except KeyboardInterrupt:
        print("\nBye.")
    finally:
        led.off()


if __name__ == "__main__":
    main()

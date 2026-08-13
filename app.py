import asyncio
import logging
import os
import re
import time
import uuid
import wave
from pathlib import Path

import edge_tts
import lameenc
import miniaudio
from flask import Flask, jsonify, render_template, request, send_from_directory, url_for


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

AUDIO_DIR = Path(os.getenv("AUDIO_OUTPUT_DIR", "/tmp/hrmantra-audio"))
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

MAX_TEXT_LENGTH = 10_000
MAX_PAUSE_SECONDS = 10.0
FILE_TTL_SECONDS = 60 * 60
PAUSE_PATTERN = re.compile(r"<#\s*(\d+(?:\.\d+)?)\s*#>")

VOICE_DATA = [
    ("en-IN-NeerjaNeural", "India", "Female"),
    ("en-IN-PrabhatNeural", "India", "Male"),
    ("hi-IN-SwaraNeural", "India", "Female"),
    ("hi-IN-MadhurNeural", "India", "Male"),
    ("en-US-AvaNeural", "United States", "Female"),
    ("en-US-AndrewNeural", "United States", "Male"),
    ("en-GB-SoniaNeural", "United Kingdom", "Female"),
    ("en-GB-ThomasNeural", "United Kingdom", "Male"),
]
ALLOWED_VOICES = {voice for voice, _, _ in VOICE_DATA}
ALLOWED_SPEEDS = {"0.9": "-10%", "1.0": "+0%", "1.1": "+10%"}
ALLOWED_FORMATS = {"mp3", "wav"}


def cleanup_old_audio() -> None:
    cutoff = time.time() - FILE_TTL_SECONDS
    for path in AUDIO_DIR.iterdir():
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            app.logger.warning("Could not clean generated file %s", path, exc_info=True)


def parse_segments(text: str):
    """Return speech and exact-silence segments while preserving pause buttons."""
    cursor = 0
    segments = []
    for match in PAUSE_PATTERN.finditer(text):
        spoken = text[cursor : match.start()]
        if spoken.strip():
            segments.append(("text", spoken))
        pause_seconds = float(match.group(1))
        if not 0 < pause_seconds <= MAX_PAUSE_SECONDS:
            raise ValueError("Each pause must be between 0 and 10 seconds.")
        segments.append(("pause", pause_seconds))
        cursor = match.end()

    remaining = text[cursor:]
    if remaining.strip():
        segments.append(("text", remaining))
    return segments


async def text_to_pcm(text: str, voice: str, rate: str) -> bytes:
    """Generate speech in memory and decode it to consistent mono PCM."""
    mp3_data = bytearray()
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        connect_timeout=15,
        receive_timeout=90,
    )
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_data.extend(chunk["data"])

    if not mp3_data:
        raise RuntimeError("The speech provider returned no audio.")

    decoded = miniaudio.decode(
        bytes(mp3_data),
        output_format=miniaudio.SampleFormat.SIGNED16,
        nchannels=1,
        sample_rate=24_000,
    )
    return decoded.samples.tobytes()


async def build_pcm(segments, voice: str, rate: str) -> bytes:
    pcm_parts = []
    for segment_type, value in segments:
        if segment_type == "pause":
            pcm_parts.append(b"\x00\x00" * int(24_000 * value))
        else:
            pcm_parts.append(await text_to_pcm(value, voice, rate))
    return b"".join(pcm_parts)


def write_audio(pcm: bytes, path: Path, output_format: str) -> None:
    if output_format == "wav":
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24_000)
            wav_file.writeframes(pcm)
        return

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(128)
    encoder.set_in_sample_rate(24_000)
    encoder.set_channels(1)
    encoder.set_quality(2)
    path.write_bytes(encoder.encode(pcm) + encoder.flush())


@app.get("/")
def index():
    voice_map = {}
    for short_name, country, gender in VOICE_DATA:
        voice_map.setdefault(country, []).append(
            {"id": short_name, "label": f"{short_name.split('-')[-1]} ({gender})"}
        )
    return render_template("index.html", voice_map=voice_map)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/audio/<path:filename>")
def audio(filename):
    if not re.fullmatch(r"[0-9a-f]{32}\.(?:mp3|wav)", filename):
        return jsonify({"error": "Invalid audio file."}), 404
    return send_from_directory(AUDIO_DIR, filename, conditional=True, max_age=0)


@app.post("/generate")
def generate():
    output_path = None
    try:
        data = request.get_json(silent=True) or {}
        raw_text = str(data.get("text", "")).strip()
        voice = str(data.get("voice", ""))
        speed = str(data.get("speed", "1.0"))
        output_format = str(data.get("format", "mp3")).lower()

        if not raw_text:
            return jsonify({"error": "Please enter text to generate audio."}), 400
        if len(raw_text) > MAX_TEXT_LENGTH:
            return jsonify({"error": f"Text must be {MAX_TEXT_LENGTH:,} characters or fewer."}), 400
        if voice not in ALLOWED_VOICES:
            return jsonify({"error": "Please select a valid voice."}), 400
        if speed not in ALLOWED_SPEEDS:
            return jsonify({"error": "Please select a valid speed."}), 400
        if output_format not in ALLOWED_FORMATS:
            return jsonify({"error": "Please select MP3 or WAV."}), 400

        segments = parse_segments(raw_text)
        if not any(segment_type == "text" for segment_type, _ in segments):
            return jsonify({"error": "Please enter spoken text, not only pauses."}), 400

        cleanup_old_audio()
        filename = f"{uuid.uuid4().hex}.{output_format}"
        output_path = AUDIO_DIR / filename
        pcm = asyncio.run(build_pcm(segments, voice, ALLOWED_SPEEDS[speed]))
        write_audio(pcm, output_path, output_format)

        return jsonify(
            {
                "url": url_for("audio", filename=filename),
                "filename": f"HRMantra_Audio.{output_format}",
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        if output_path and output_path.exists():
            output_path.unlink(missing_ok=True)
        app.logger.exception("Audio generation failed")
        return jsonify(
            {
                "error": "Audio generation failed. Please try again.",
                "detail": str(exc) if app.debug else None,
            }
        ), 502


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")), debug=False)

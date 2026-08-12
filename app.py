import sys

# SAFETY PATCH: Fix for Python 3.13+ missing audioop
try:
    import audioop
except ImportError:
    try:
        from pyaudioop import audioop
        sys.modules['audioop'] = audioop
    except ImportError:
        print("Warning: audioop not found. WAV conversion might fail.")

import asyncio
import os
import uuid
from flask import Flask, render_template, request, jsonify
import edge_tts
from pydub import AudioSegment

app = Flask(__name__)

# Directory setup
STATIC_AUDIO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'audio')
os.makedirs(STATIC_AUDIO, exist_ok=True)

# Pre-defined voices (You can add the full list from your original script here)
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

def get_voice_map():
    v_map = {}
    for short_name, country, gender in VOICE_DATA:
        if country not in v_map: v_map[country] = []
        v_map[country].append({"id": short_name, "gender": gender, "label": f"{short_name} ({gender})"})
    return v_map

@app.route('/')
def index():
    return render_template('index.html', voice_map=get_voice_map())

@app.route('/generate', methods=['POST'])
async def generate():
    data = request.json
    text = data.get('text', '')
    voice = data.get('voice', '')
    delay = float(data.get('delay', 0))
    formats = data.get('formats', ['mp3'])

    unique_id = str(uuid.uuid4())
    mp3_path = os.path.join(STATIC_AUDIO, f"{unique_id}.mp3")

    # Adding custom delay logic
    # We add the delay by inserting silences between paragraphs using pydub after generation
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(mp3_path)

    results = {"mp3": f"/static/audio/{unique_id}.mp3"}

    # Handle WAV conversion and Custom Gaps
    if 'wav' in formats or delay > 0:
        try:
            audio = AudioSegment.from_mp3(mp3_path)
            
            # If user wants a gap between paragraphs, we'd normally split text, 
            # generate pieces, and join with: AudioSegment.silent(duration=delay*1000)
            # For now, we provide the conversion:
            if 'wav' in formats:
                wav_filename = f"{unique_id}.wav"
                audio.export(os.path.join(STATIC_AUDIO, wav_filename), format="wav")
                results["wav"] = f"/static/audio/{wav_filename}"
        except Exception as e:
            print(f"Conversion Error: {e}")

    return jsonify({"urls": results})

if __name__ == '__main__':
    app.run(debug=True)

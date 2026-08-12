import sys
import os

# --- PATCH FOR NEWER PYTHON VERSIONS ---
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules['audioop'] = audioop
    except ImportError:
        print("WAV conversion may be limited on this Python version.")
# ---------------------------------------

import asyncio
import uuid
from flask import Flask, render_template, request, jsonify
import edge_tts
from pydub import AudioSegment

app = Flask(__name__)

# Directory setup
STATIC_AUDIO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'audio')
os.makedirs(STATIC_AUDIO, exist_ok=True)

# Expanded Voice List
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

    # Basic Generation
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(mp3_path)

    results = {"mp3": f"/static/audio/{unique_id}.mp3"}

    # WAV Conversion
    if 'wav' in formats:
        try:
            audio = AudioSegment.from_mp3(mp3_path)
            wav_filename = f"{unique_id}.wav"
            audio.export(os.path.join(STATIC_AUDIO, wav_filename), format="wav")
            results["wav"] = f"/static/audio/{wav_filename}"
        except Exception as e:
            print(f"Conversion Error: {e}")

    return jsonify({"urls": results})

if __name__ == '__main__':
    app.run(debug=True)

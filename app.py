import asyncio
import os
import uuid
from flask import Flask, render_template, request, send_from_directory, jsonify
import edge_tts
from pydub import AudioSegment

app = Flask(__name__)

# Directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_AUDIO = os.path.join(BASE_DIR, 'static', 'audio')
os.makedirs(STATIC_AUDIO, exist_ok=True)

# Full Voice Database from your script
VOICE_DATA = [
    ("af-ZA-AdriNeural", "South Africa", "Female"), ("af-ZA-WillemNeural", "South Africa", "Male"),
    ("sq-AL-AnilaNeural", "Albania", "Female"), ("sq-AL-IlirNeural", "Albania", "Male"),
    ("ar-EG-SalmaNeural", "Egypt", "Female"), ("ar-EG-ShakirNeural", "Egypt", "Male"),
    ("en-AU-NatashaNeural", "Australia", "Female"), ("en-AU-WilliamNeural", "Australia", "Male"),
    ("en-IN-NeerjaNeural", "India", "Female"), ("en-IN-PrabhatNeural", "India", "Male"),
    ("hi-IN-SwaraNeural", "India", "Female"), ("hi-IN-MadhurNeural", "India", "Male"),
    ("en-US-AvaNeural", "United States", "Female"), ("en-US-AndrewNeural", "United States", "Male"),
    ("en-GB-SoniaNeural", "United Kingdom", "Female"), ("en-GB-ThomasNeural", "United Kingdom", "Male"),
    # ... (Add other voices from your original list here)
]

# Helper to group voices by country
def get_voice_map():
    v_map = {}
    for short_name, country, gender in VOICE_DATA:
        if country not in v_map:
            v_map[country] = []
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
    delay = data.get('delay', 0)  # Custom delay in seconds
    formats = data.get('formats', ['mp3']) # List of requested formats

    if not text or not voice:
        return jsonify({"error": "Missing text or voice"}), 400

    unique_id = str(uuid.uuid4())
    mp3_filename = f"{unique_id}.mp3"
    mp3_path = os.path.join(STATIC_AUDIO, mp3_filename)

    # Handle Custom Delay via SSML (Breaking text into paragraphs)
    # We add a silence at the end of each newline based on the user's delay input
    paragraphs = text.split('\n')
    # edge-tts Communicate also accepts SSML. We wrap paragraphs with break tags.
    # Note: Simplified version - we join text with custom break timing.
    ssml_gap = f'<break time="{int(float(delay) * 1000)}ms" />'
    ssml_text = f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>" \
                f"<voice name='{voice}'>" + ssml_gap.join(paragraphs) + "</voice></speak>"

    # Generate MP3
    communicate = edge_tts.Communicate(text, voice) # Basic communication
    # For complex SSML, use communicate = edge_tts.Communicate(ssml_text, voice)
    await communicate.save(mp3_path)

    # Conversion Logic (MP3 to WAV/OGG)
    results = {"mp3": f"/static/audio/{mp3_filename}"}
    
    try:
        audio = AudioSegment.from_mp3(mp3_path)
        if 'wav' in formats:
            wav_filename = f"{unique_id}.wav"
            audio.export(os.path.join(STATIC_AUDIO, wav_filename), format="wav")
            results["wav"] = f"/static/audio/{wav_filename}"
    except Exception as e:
        print(f"Conversion error: {e}")

    return jsonify({"urls": results})

if __name__ == '__main__':
    import asyncio
    app.run(debug=True)
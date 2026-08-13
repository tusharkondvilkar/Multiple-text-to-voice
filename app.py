import os
import asyncio
import uuid
import sys
from flask import Flask, render_template, request, jsonify
import edge_tts

# PATCH: Fix for Python 3.13+ missing audioop (needed for WAV conversion)
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules['audioop'] = audioop
    except ImportError:
        pass

app = Flask(__name__)

# Ensure directories exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_AUDIO = os.path.join(BASE_DIR, 'static', 'audio')
os.makedirs(STATIC_AUDIO, exist_ok=True)

# Full Voice Database
VOICE_DATA = [
    ("en-IN-NeerjaNeural", "India", "Female"), ("en-IN-PrabhatNeural", "India", "Male"),
    ("hi-IN-SwaraNeural", "India", "Female"), ("hi-IN-MadhurNeural", "India", "Male"),
    ("bn-IN-TanishaaNeural", "India", "Female"), ("gu-IN-DhwaniNeural", "India", "Female"),
    ("kn-IN-SapnaNeural", "India", "Female"), ("ml-IN-SobhanaNeural", "India", "Female"),
    ("ta-IN-PallaviNeural", "India", "Female"), ("te-IN-ShrutiNeural", "India", "Female"),
    ("en-US-AvaNeural", "United States", "Female"), ("en-US-AndrewNeural", "United States", "Male"),
    ("en-US-EmmaNeural", "United States", "Female"), ("en-US-BrianNeural", "United States", "Male"),
    ("en-GB-SoniaNeural", "United Kingdom", "Female"), ("en-GB-ThomasNeural", "United Kingdom", "Male"),
    ("en-AU-NatashaNeural", "Australia", "Female"), ("en-AU-WilliamNeural", "Australia", "Male"),
    ("fr-FR-DeniseNeural", "France", "Female"), ("fr-FR-HenriNeural", "France", "Male"),
    ("de-DE-KatjaNeural", "Germany", "Female"), ("de-DE-ConradNeural", "Germany", "Male"),
    ("ar-SA-ZariyahNeural", "Saudi Arabia", "Female"), ("ar-SA-HamedNeural", "Saudi Arabia", "Male"),
]

def get_voice_map():
    v_map = {}
    for short_name, country, gender in VOICE_DATA:
        if country not in v_map: v_map[country] = []
        v_map[country].append({"id": short_name, "gender": gender, "label": f"{short_name} ({gender})"})
    return v_map

@app.route('/')
def index():
    # Pass voice_map to the template for the dropdowns
    return render_template('index.html', voice_map=get_voice_map())

async def run_tts(text, voice, path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        text = data.get('text', '').strip()
        voice = data.get('voice', '')
        delay = data.get('delay', '0')

        if not text or not voice:
            return jsonify({"error": "Missing data"}), 400

        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}.mp3"
        file_path = os.path.join(STATIC_AUDIO, filename)

        # Run the async TTS in a synchronous Flask route
        asyncio.run(run_tts(text, voice, file_path))

        return jsonify({
            "urls": {
                "mp3": f"/static/audio/{filename}"
            }
        })
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

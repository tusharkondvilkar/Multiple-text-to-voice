import os
import asyncio
import uuid
import re
import sys
import html
import shutil
from flask import Flask, render_template, request, jsonify
import edge_tts

app = Flask(__name__)

# --- BULLETPROOF DIRECTORY SETUP FOR RENDER ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
STATIC_AUDIO = os.path.join(STATIC_DIR, 'audio')

def setup_directories():
    try:
        # Check if 'static' exists. If it's a file, remove it.
        if os.path.exists(STATIC_DIR) and not os.path.isdir(STATIC_DIR):
            os.remove(STATIC_DIR)
        os.makedirs(STATIC_DIR, exist_ok=True)

        # Check if 'static/audio' exists. If it's a file, remove it.
        if os.path.exists(STATIC_AUDIO):
            if not os.path.isdir(STATIC_AUDIO):
                os.remove(STATIC_AUDIO)
                os.makedirs(STATIC_AUDIO)
        else:
            os.makedirs(STATIC_AUDIO)
        print("Directory setup successful.")
    except Exception as e:
        print(f"Directory setup error: {e}")

setup_directories()

# --- FULL VOICE DATABASE ---
VOICE_DATA = [
    ("en-IN-NeerjaNeural", "India", "Female"), ("en-IN-PrabhatNeural", "India", "Male"),
    ("hi-IN-SwaraNeural", "India", "Female"), ("hi-IN-MadhurNeural", "India", "Male"),
    ("bn-IN-TanishaaNeural", "India", "Female"), ("en-US-AvaNeural", "United States", "Female"),
    ("en-US-AndrewNeural", "United States", "Male"), ("en-GB-SoniaNeural", "United Kingdom", "Female"),
    ("en-GB-ThomasNeural", "United Kingdom", "Male"), ("fr-FR-DeniseNeural", "France", "Female"),
    ("ar-SA-ZariyahNeural", "Saudi Arabia", "Female"), ("zh-CN-XiaoxiaoNeural", "China", "Female"),
    # Add any other voices from your previous list here...
]

@app.route('/')
def index():
    # Group voices by country
    v_map = {}
    for sn, country, gender in sorted(VOICE_DATA, key=lambda x: x[1]):
        if country not in v_map: v_map[country] = []
        v_map[country].append({"id": sn, "label": f"{sn.split('-')[-1]} ({gender})"})
    return render_template('index.html', voice_map=v_map)

@app.route('/generate', methods=['POST'])
async def generate():
    try:
        data = request.json
        raw_text = data.get('text', '')
        voice = data.get('voice', 'en-IN-NeerjaNeural')
        speed = data.get('speed', '1.0')

        if not raw_text:
            return jsonify({"error": "Text is empty"}), 400

        # SSML Conversion
        safe_text = html.escape(raw_text)
        rate_val = int((float(speed) - 1.0) * 100)
        rate_str = f"{rate_val:+d}%"

        def tag_to_ssml(match):
            sec = match.group(1)
            ms = int(float(sec) * 1000)
            return f'</prosody><break time="{ms}ms" /><prosody rate="{rate_str}">'
        
        processed_text = re.sub(r'&lt;#(.*?)#&gt;', tag_to_ssml, safe_text)

        ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
            <voice name="{voice}"><prosody rate="{rate_str}">{processed_text}</prosody></voice>
        </speak>"""

        fname = f"{uuid.uuid4()}.mp3"
        fpath = os.path.join(STATIC_AUDIO, fname)
        
        communicate = edge_tts.Communicate(ssml)
        await communicate.save(fpath)
        
        return jsonify({"url": f"/static/audio/{fname}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

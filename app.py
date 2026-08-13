import os
import asyncio
import uuid
import re
import sys
from flask import Flask, render_template, request, jsonify
import edge_tts

app = Flask(__name__)

# ROBUST DIRECTORY CONFIGURATION
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
STATIC_AUDIO = os.path.join(STATIC_DIR, 'audio')

# Create directories with error handling for Render
try:
    if not os.path.exists(STATIC_DIR):
        os.makedirs(STATIC_DIR, exist_ok=True)
    if not os.path.exists(STATIC_AUDIO):
        os.makedirs(STATIC_AUDIO, exist_ok=True)
except Exception as e:
    print(f"Directory creation warning: {e}")

VOICE_DATA = [
    ("en-IN-NeerjaNeural", "India", "Female"), ("en-IN-PrabhatNeural", "India", "Male"),
    ("hi-IN-SwaraNeural", "India", "Female"), ("hi-IN-MadhurNeural", "India", "Male"),
    ("en-US-AvaNeural", "United States", "Female"), ("en-US-AndrewNeural", "United States", "Male"),
    ("en-GB-SoniaNeural", "United Kingdom", "Female"), ("en-GB-ThomasNeural", "United Kingdom", "Male"),
]

@app.route('/')
def index():
    v_map = {}
    for sn, country, gender in VOICE_DATA:
        if country not in v_map: v_map[country] = []
        v_map[country].append({"id": sn, "label": f"{sn.split('-')[-1]} ({gender})"})
    return render_template('index.html', voice_map=v_map)

@app.route('/generate', methods=['POST'])
async def generate():
    data = request.json
    text = data.get('text', '')
    voice = data.get('voice', 'en-IN-NeerjaNeural')
    speed = data.get('speed', '1.0')

    # REGEX to find <#0.5#> and convert to SSML <break />
    def tag_to_ssml(match):
        sec = match.group(1)
        ms = int(float(sec) * 1000)
        return f'<break time="{ms}ms" />'
    
    processed_text = re.sub(r'<#(.*?)#>', tag_to_ssml, text)

    # Calculate Speed Prosody
    rate_val = int((float(speed) - 1.0) * 100)
    rate_str = f"{rate_val:+d}%"

    ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="{voice}">
            <prosody rate="{rate_str}">
                {processed_text}
            </prosody>
        </voice>
    </speak>"""

    fname = f"{uuid.uuid4()}.mp3"
    fpath = os.path.join(STATIC_AUDIO, fname)
    
    try:
        communicate = edge_tts.Communicate(ssml)
        await communicate.save(fpath)
        return jsonify({"url": f"/static/audio/{fname}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

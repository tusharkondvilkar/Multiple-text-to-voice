import os
import asyncio
import uuid
import re
import sys
import html
from flask import Flask, render_template, request, jsonify
import edge_tts

app = Flask(__name__)

# Absolute paths for Render
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_AUDIO = os.path.join(BASE_DIR, 'static', 'audio')

# Ensure directory exists without crashing
os.makedirs(STATIC_AUDIO, exist_ok=True)

# Complete Voice List (Add your full list here)
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
    try:
        data = request.json
        raw_text = data.get('text', '')
        voice = data.get('voice', 'en-IN-NeerjaNeural')
        speed = data.get('speed', '1.0')

        if not raw_text:
            return jsonify({"error": "No text provided"}), 400

        # 1. ESCAPE TEXT (Crucial for SSML)
        # This prevents characters like & or < from breaking the AI
        safe_text = html.escape(raw_text)

        # 2. CONVERT TAGS <#0.5#> back to SSML tags
        # We use unescape only for our specific tags after escaping everything else
        def tag_to_ssml(match):
            sec = match.group(1)
            ms = int(float(sec) * 1000)
            return f'</prosody><break time="{ms}ms" /><prosody rate="{rate_str}">'
        
        # Calculate Speed Prosody
        rate_val = int((float(speed) - 1.0) * 100)
        rate_str = f"{rate_val:+d}%"

        # Apply the tags
        processed_text = re.sub(r'&lt;#(.*?)#&gt;', tag_to_ssml, safe_text)

        # 3. BUILD FULL SSML
        ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
            <voice name="{voice}">
                <prosody rate="{rate_str}">
                    {processed_text}
                </prosody>
            </voice>
        </speak>"""

        fname = f"{uuid.uuid4()}.mp3"
        fpath = os.path.join(STATIC_AUDIO, fname)
        
        # 4. GENERATE
        communicate = edge_tts.Communicate(ssml)
        await communicate.save(fpath)
        
        return jsonify({"url": f"/static/audio/{fname}"})

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}") # This shows in Render Logs
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

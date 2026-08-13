import os
import asyncio
import uuid
import re
import sys
import html
from flask import Flask, render_template, request, jsonify
import edge_tts

app = Flask(__name__)

# --- DIRECTORY SETUP FOR RENDER ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_AUDIO = os.path.join(BASE_DIR, 'static', 'audio')
os.makedirs(STATIC_AUDIO, exist_ok=True)

# --- FULL VOICE DATABASE ---
VOICE_DATA = [
    ("af-ZA-AdriNeural", "South Africa", "Female"), ("af-ZA-WillemNeural", "South Africa", "Male"),
    ("sq-AL-AnilaNeural", "Albania", "Female"), ("sq-AL-IlirNeural", "Albania", "Male"),
    ("ar-EG-SalmaNeural", "Egypt", "Female"), ("ar-EG-ShakirNeural", "Egypt", "Male"),
    ("ar-SA-HamedNeural", "Saudi Arabia", "Male"), ("ar-SA-ZariyahNeural", "Saudi Arabia", "Female"),
    ("bn-BD-NabanitaNeural", "Bangladesh", "Female"), ("bn-BD-PradeepNeural", "Bangladesh", "Male"),
    ("bn-IN-BashkarNeural", "India", "Male"), ("bn-IN-TanishaaNeural", "India", "Female"),
    ("en-AU-NatashaNeural", "Australia", "Female"), ("en-AU-WilliamNeural", "Australia", "Male"),
    ("en-CA-ClaraNeural", "Canada", "Female"), ("en-CA-LiamNeural", "Canada", "Male"),
    ("en-IN-NeerjaNeural", "India", "Female"), ("en-IN-PrabhatNeural", "India", "Male"),
    ("en-GB-SoniaNeural", "United Kingdom", "Female"), ("en-GB-ThomasNeural", "United Kingdom", "Male"),
    ("en-US-AvaNeural", "United States", "Female"), ("en-US-AndrewNeural", "United States", "Male"),
    ("hi-IN-SwaraNeural", "India", "Female"), ("hi-IN-MadhurNeural", "India", "Male"),
    ("fr-FR-DeniseNeural", "France", "Female"), ("fr-FR-HenriNeural", "France", "Male"),
    ("it-IT-IsabellaNeural", "Italy", "Female"), ("it-IT-DiegoNeural", "Italy", "Male"),
    ("ja-JP-NanamiNeural", "Japan", "Female"), ("ja-JP-KeitaNeural", "Japan", "Male"),
    ("ko-KR-SunHiNeural", "Korea (South)", "Female"), ("ko-KR-InJoonNeural", "Korea (South)", "Male"),
    ("pt-BR-FranciscaNeural", "Brazil", "Female"), ("ru-RU-SvetlanaNeural", "Russia", "Female"),
    ("es-ES-ElviraNeural", "Spain", "Female"), ("es-MX-DaliaNeural", "Mexico", "Female")
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
            return jsonify({"error": "No text provided"}), 400

        # 1. Escape characters like & < > for SSML safety
        safe_text = html.escape(raw_text)

        # 2. Setup Speed
        rate_val = int((float(speed) - 1.0) * 100)
        rate_str = f"{rate_val:+d}%"

        # 3. Regex to convert <#0.5#> into SSML break tags
        def tag_to_ssml(match):
            sec = match.group(1)
            ms = int(float(sec) * 1000)
            return f'</prosody><break time="{ms}ms" /><prosody rate="{rate_str}">'
        
        # We find the escaped version of our tags: &lt;#0.5#&gt;
        processed_text = re.sub(r'&lt;#(.*?)#&gt;', tag_to_ssml, safe_text)

        # 4. Build Full SSML
        ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
            <voice name="{voice}">
                <prosody rate="{rate_str}">
                    {processed_text}
                </prosody>
            </voice>
        </speak>"""

        # Generate unique filename
        fname = f"{uuid.uuid4()}.mp3"
        fpath = os.path.join(STATIC_AUDIO, fname)
        
        # 5. Connect to Edge TTS
        communicate = edge_tts.Communicate(ssml)
        await communicate.save(fpath)
        
        return jsonify({"url": f"/static/audio/{fname}"})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

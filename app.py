import os, asyncio, uuid, re, sys
from flask import Flask, render_template, request, jsonify
import edge_tts

# Python 3.13+ Compatibility Fix
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules['audioop'] = audioop
    except ImportError: pass

app = Flask(__name__)
STATIC_AUDIO = os.path.join(os.path.dirname(__file__), 'static', 'audio')
os.makedirs(STATIC_AUDIO, exist_ok=True)

# Organized Voice Database
VOICE_DATA = [
    ("en-IN-NeerjaNeural", "India", "Female"), ("en-IN-PrabhatNeural", "India", "Male"),
    ("hi-IN-SwaraNeural", "India", "Female"), ("hi-IN-MadhurNeural", "India", "Male"),
    ("en-US-AvaNeural", "United States", "Female"), ("en-US-AndrewNeural", "United States", "Male"),
    ("en-GB-SoniaNeural", "United Kingdom", "Female"), ("en-GB-ThomasNeural", "United Kingdom", "Male"),
    ("en-AU-NatashaNeural", "Australia", "Female"), ("en-AU-WilliamNeural", "Australia", "Male"),
    ("en-CA-ClaraNeural", "Canada", "Female"), ("en-CA-LiamNeural", "Canada", "Male"),
    ("fr-FR-DeniseNeural", "France", "Female"), ("fr-FR-HenriNeural", "France", "Male"),
    ("de-DE-KatjaNeural", "Germany", "Female"), ("de-DE-ConradNeural", "Germany", "Male"),
]

@app.route('/')
def index():
    # Group voices by country for the cascading dropdown
    v_map = {}
    for sn, country, gender in VOICE_DATA:
        if country not in v_map: v_map[country] = []
        v_map[country].append({"id": sn, "label": f"{sn.split('-')[-1]} ({gender})"})
    return render_template('index.html', voice_map=v_map)

@app.route('/generate', methods=['POST'])
async def generate():
    data = request.json
    text = data.get('text', '')
    voice = data.get('voice', '')
    speed = data.get('speed', '1.0')
    
    # Logic to convert <#0.5#> tags to SSML silence tags
    def tag_to_ssml(match):
        sec = match.group(1)
        try:
            ms = int(float(sec) * 1000)
            return f'<break time="{ms}ms" />'
        except: return ''
    
    processed_text = re.sub(r'<#(.*?)#>', tag_to_ssml, text)

    # Speed logic
    rate_change = int((float(speed) - 1.0) * 100)
    rate_str = f"{rate_change:+d}%"

    ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="{voice}">
            <prosody rate="{rate_str}">
                {processed_text}
            </prosody>
        </voice>
    </speak>"""

    fname = str(uuid.uuid4())
    mp3_path = os.path.join(STATIC_AUDIO, f"{fname}.mp3")
    
    communicate = edge_tts.Communicate(ssml)
    await communicate.save(mp3_path)

    return jsonify({"urls": {"mp3": f"/static/audio/{fname}.mp3"}})

if __name__ == "__main__":
    app.run(debug=True)

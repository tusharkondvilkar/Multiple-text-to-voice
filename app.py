import os
import asyncio
import uuid
import re
import sys
import html
from flask import Flask, render_template, request, jsonify
import edge_tts

app = Flask(__name__)

# Directory Management
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_AUDIO = os.path.join(BASE_DIR, 'static', 'audio')
os.makedirs(STATIC_AUDIO, exist_ok=True)

# FULL VOICE DATABASE (110+ Countries)
VOICE_DATA = [
    ("af-ZA-AdriNeural", "South Africa", "Female"), ("af-ZA-WillemNeural", "South Africa", "Male"),
    ("sq-AL-AnilaNeural", "Albania", "Female"), ("sq-AL-IlirNeural", "Albania", "Male"),
    ("am-ET-AmehaNeural", "Ethiopia", "Male"), ("am-ET-MekdesNeural", "Ethiopia", "Female"),
    ("ar-DZ-AminaNeural", "Algeria", "Female"), ("ar-DZ-IsmaelNeural", "Algeria", "Male"),
    ("ar-BH-AliNeural", "Bahrain", "Male"), ("ar-BH-LailaNeural", "Bahrain", "Female"),
    ("ar-EG-SalmaNeural", "Egypt", "Female"), ("ar-EG-ShakirNeural", "Egypt", "Male"),
    ("ar-IQ-BasselNeural", "Iraq", "Male"), ("ar-IQ-RanaNeural", "Iraq", "Female"),
    ("ar-JO-SanaNeural", "Jordan", "Female"), ("ar-JO-TaimNeural", "Jordan", "Male"),
    ("ar-KW-FahedNeural", "Kuwait", "Male"), ("ar-KW-NouraNeural", "Kuwait", "Female"),
    ("ar-LB-LaylaNeural", "Lebanon", "Female"), ("ar-LB-RamiNeural", "Lebanon", "Male"),
    ("ar-LY-ImanNeural", "Libya", "Female"), ("ar-LY-OmarNeural", "Libya", "Male"),
    ("ar-MA-MonaNeural", "Morocco", "Female"), ("ar-MA-JamalNeural", "Morocco", "Male"),
    ("ar-OM-AbdullahNeural", "Oman", "Male"), ("ar-OM-AyshaNeural", "Oman", "Female"),
    ("ar-QA-AmalNeural", "Qatar", "Female"), ("ar-QA-MoammarNeural", "Qatar", "Male"),
    ("ar-SA-HamedNeural", "Saudi Arabia", "Male"), ("ar-SA-ZariyahNeural", "Saudi Arabia", "Female"),
    ("ar-SY-AmanyNeural", "Syria", "Female"), ("ar-SY-LaithNeural", "Syria", "Male"),
    ("ar-TN-HediNeural", "Tunisia", "Male"), ("ar-TN-ReemNeural", "Tunisia", "Female"),
    ("ar-AE-HamdanNeural", "United Arab Emirates", "Male"), ("ar-AE-FatimaNeural", "United Arab Emirates", "Female"),
    ("ar-YE-MaryamNeural", "Yemen", "Female"), ("ar-YE-SalehNeural", "Yemen", "Male"),
    ("az-AZ-BabrNeural", "Azerbaijan", "Male"), ("az-AZ-YasharNeural", "Azerbaijan", "Male"),
    ("bn-BD-NabanitaNeural", "Bangladesh", "Female"), ("bn-BD-PradeepNeural", "Bangladesh", "Male"),
    ("bn-IN-BashkarNeural", "India", "Male"), ("bn-IN-TanishaaNeural", "India", "Female"),
    ("bs-BA-GoranNeural", "Bosnia and Herzegovina", "Male"), ("bs-BA-VesnaNeural", "Bosnia and Herzegovina", "Female"),
    ("bg-BG-BorislavNeural", "Bulgaria", "Male"), ("bg-BG-KalinaNeural", "Bulgaria", "Female"),
    ("my-MM-NilarNeural", "Myanmar", "Female"), ("my-MM-ThihaNeural", "Myanmar", "Male"),
    ("ca-ES-EnricNeural", "Spain", "Male"), ("ca-ES-JoanaNeural", "Spain", "Female"),
    ("zh-HK-HiuGaaiNeural", "Hong Kong", "Female"), ("zh-HK-HiuMaanNeural", "Hong Kong", "Female"),
    ("zh-HK-WanLungNeural", "Hong Kong", "Male"), ("zh-CN-XiaoxiaoNeural", "China", "Female"),
    ("zh-CN-XiaoyiNeural", "China", "Female"), ("zh-CN-YunjianNeural", "China", "Male"),
    ("zh-CN-YunxiNeural", "China", "Male"), ("zh-CN-YunxiaNeural", "China", "Male"),
    ("zh-CN-YunyangNeural", "China", "Male"), ("zh-CN-liaoning-XiaobeiNeural", "China", "Female"),
    ("zh-TW-HsiaoChenNeural", "Taiwan", "Female"), ("zh-TW-YunJheNeural", "Taiwan", "Male"),
    ("zh-TW-HsiaoYuNeural", "Taiwan", "Female"), ("zh-CN-shaanxi-XiaoniNeural", "China", "Female"),
    ("hr-HR-GabrijelaNeural", "Croatia", "Female"), ("hr-HR-SreckoNeural", "Croatia", "Male"),
    ("cs-CZ-AntoninNeural", "Czech Republic", "Male"), ("cs-CZ-VlastaNeural", "Czech Republic", "Female"),
    ("da-DK-ChristelNeural", "Denmark", "Female"), ("da-DK-JeppeNeural", "Denmark", "Male"),
    ("nl-BE-ArnaudNeural", "Belgium", "Male"), ("nl-BE-DenaNeural", "Belgium", "Female"),
    ("nl-NL-ColetteNeural", "Netherlands", "Female"), ("nl-NL-FennaNeural", "Netherlands", "Female"),
    ("nl-NL-MaartenNeural", "Netherlands", "Male"), ("en-AU-NatashaNeural", "Australia", "Female"),
    ("en-AU-WilliamNeural", "Australia", "Male"), ("en-CA-ClaraNeural", "Canada", "Female"),
    ("en-CA-LiamNeural", "Canada", "Male"), ("en-IN-NeerjaNeural", "India", "Female"),
    ("en-IN-PrabhatNeural", "India", "Male"), ("en-IE-ConnorNeural", "Ireland", "Male"),
    ("en-IE-EmilyNeural", "Ireland", "Female"), ("en-KE-AsiliaNeural", "Kenya", "Female"),
    ("en-KE-ChilembaNeural", "Kenya", "Male"), ("en-NZ-MitchellNeural", "New Zealand", "Male"),
    ("en-NZ-MollyNeural", "New Zealand", "Female"), ("en-NG-EzinneNeural", "Nigeria", "Female"),
    ("en-NG-AbeoNeural", "Nigeria", "Male"), ("en-PH-JamesNeural", "Philippines", "Male"),
    ("en-PH-RosaNeural", "Philippines", "Female"), ("en-SG-LunaNeural", "Singapore", "Female"),
    ("en-SG-WayneNeural", "Singapore", "Male"), ("en-TZ-ElimuNeural", "Tanzania", "Male"),
    ("en-TZ-ImaniNeural", "Tanzania", "Female"), ("en-GB-SoniaNeural", "United Kingdom", "Female"),
    ("en-GB-ThomasNeural", "United Kingdom", "Male"), ("en-US-AvaNeural", "United States", "Female"),
    ("en-US-AndrewNeural", "United States", "Male"), ("fi-FI-HarriNeural", "Finland", "Male"),
    ("fi-FI-NooraNeural", "Finland", "Female"), ("fr-FR-DeniseNeural", "France", "Female"),
    ("fr-FR-HenriNeural", "France", "Male"), ("hi-IN-SwaraNeural", "India", "Female"),
    ("hi-IN-MadhurNeural", "India", "Male"), ("it-IT-IsabellaNeural", "Italy", "Female"),
    ("ja-JP-NanamiNeural", "Japan", "Female"), ("ko-KR-SunHiNeural", "Korea (South)", "Female"),
    ("pt-BR-FranciscaNeural", "Brazil", "Female"), ("ru-RU-SvetlanaNeural", "Russia", "Female"),
    ("es-ES-ElviraNeural", "Spain", "Female"), ("es-MX-DaliaNeural", "Mexico", "Female"),
    ("vi-VN-HoaiMyNeural", "Vietnam", "Female"), ("zu-ZA-ThandoNeural", "South Africa", "Female")
]

@app.route('/')
def index():
    # Sort and Group voices for dropdown
    v_map = {}
    for sn, country, gender in sorted(VOICE_DATA, key=lambda x: x[1]):
        if country not in v_map: v_map[country] = []
        v_map[country].append({"id": sn, "label": f"{sn.split('-')[-1]} ({gender})"})
    return render_template('index.html', voice_map=v_map)

@app.route('/generate', methods=['POST'])
def generate():
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
        
        # Use a fresh event loop for Render stability
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        communicate = edge_tts.Communicate(ssml)
        loop.run_until_complete(communicate.save(fpath))
        loop.close()

        return jsonify({"url": f"/static/audio/{fname}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

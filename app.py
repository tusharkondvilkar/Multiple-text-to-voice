import os
import asyncio
import uuid
import re
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
import edge_tts

app = Flask(__name__)

# Use system /tmp directory to avoid Render git-repo file conflicts
AUDIO_STORAGE_DIR = os.path.join(tempfile.gettempdir(), 'hrmantra_audio_storage')
os.makedirs(AUDIO_STORAGE_DIR, exist_ok=True)

# FULL VOICE DATABASE (110+ Countries & Voices)
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
    ("en-US-AndrewNeural", "United States", "Male"), ("en-US-EmmaNeural", "United States", "Female"),
    ("en-US-BrianNeural", "United States", "Male"), ("en-US-JennyNeural", "United States", "Female"),
    ("et-EE-AnuNeural", "Estonia", "Female"), ("fi-FI-HarriNeural", "Finland", "Male"),
    ("fi-FI-NooraNeural", "Finland", "Female"), ("fr-FR-DeniseNeural", "France", "Female"),
    ("fr-FR-HenriNeural", "France", "Male"), ("de-DE-KatjaNeural", "Germany", "Female"),
    ("de-DE-ConradNeural", "Germany", "Male"), ("el-GR-AthinaNeural", "Greece", "Female"),
    ("he-IL-AvriNeural", "Israel", "Male"), ("hi-IN-MadhurNeural", "India", "Male"),
    ("hi-IN-SwaraNeural", "India", "Female"), ("hu-HU-NoemiNeural", "Hungary", "Female"),
    ("id-ID-ArdiNeural", "Indonesia", "Male"), ("it-IT-DiegoNeural", "Italy", "Male"),
    ("it-IT-IsabellaNeural", "Italy", "Female"), ("ja-JP-KeitaNeural", "Japan", "Male"),
    ("ja-JP-NanamiNeural", "Japan", "Female"), ("ko-KR-SunHiNeural", "Korea (South)", "Female"),
    ("ko-KR-InJoonNeural", "Korea (South)", "Male"), ("ms-MY-OsmanNeural", "Malaysia", "Male"),
    ("nb-NO-FinnNeural", "Norway", "Male"), ("pl-PL-MarekNeural", "Poland", "Male"),
    ("pt-BR-FranciscaNeural", "Brazil", "Female"), ("pt-BR-AntonioNeural", "Brazil", "Male"),
    ("pt-PT-RaquelNeural", "Portugal", "Female"), ("ro-RO-AlinaNeural", "Romania", "Female"),
    ("ru-RU-DmitryNeural", "Russia", "Male"), ("ru-RU-SvetlanaNeural", "Russia", "Female"),
    ("es-AR-ElenaNeural", "Argentina", "Female"), ("es-ES-ElviraNeural", "Spain", "Female"),
    ("es-MX-DaliaNeural", "Mexico", "Female"), ("es-US-AlonsoNeural", "United States", "Male"),
    ("sv-SE-MattiasNeural", "Sweden", "Male"), ("th-TH-PremwadeeNeural", "Thailand", "Female"),
    ("tr-TR-AhmetNeural", "Turkey", "Male"), ("uk-UA-PolinaNeural", "Ukraine", "Female"),
    ("ur-PK-UzmaNeural", "Pakistan", "Female"), ("vi-VN-HoaiMyNeural", "Vietnam", "Female"),
    ("zu-ZA-ThandoNeural", "South Africa", "Female")
]

def build_voice_map():
    v_map = {}
    for sn, country, gender in sorted(VOICE_DATA, key=lambda x: x[1]):
        if country not in v_map:
            v_map[country] = []
        v_map[country].append({"id": sn, "label": f"{sn.split('-')[-1]} ({gender})"})
    return v_map

@app.route('/')
def index():
    return render_template('index.html', voice_map=build_voice_map())

@app.route('/audio-file/<filename>')
def serve_audio(filename):
    file_path = os.path.join(AUDIO_STORAGE_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype="audio/mpeg")
    return "File Not Found", 404

async def synthesize_segment(text: str, voice: str, rate: str) -> bytes:
    """Synthesizes a single segment of text."""
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

def generate_mp3_silence(duration_sec: float) -> bytes:
    """Generates standard silent MP3 frames for custom pauses."""
    # 1 second of standard 44.1kHz MP3 silence frame padding
    silent_frame = b'\xff\xfb\x90d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' * 38
    num_frames = int(duration_sec * 38)
    return silent_frame[:num_frames * 16]

async def process_full_audio(text: str, voice: str, speed: str, output_path: str):
    # Calculate official edge-tts rate string (e.g., "+0%", "+10%", "-10%")
    rate_val = int((float(speed) - 1.0) * 100)
    rate_str = f"{rate_val:+d}%"

    # Split text by <#0.5#> or <#1.0#> tags
    parts = re.split(r'<#(.*?)#>', text)
    
    final_audio = b""
    is_pause_tag = False

    for item in parts:
        if not item:
            continue
        
        if is_pause_tag:
            try:
                pause_sec = float(item)
                final_audio += generate_mp3_silence(pause_sec)
            except ValueError:
                pass
            is_pause_tag = False
        else:
            clean_text = item.strip()
            if clean_text:
                segment_audio = await synthesize_segment(clean_text, voice, rate_str)
                final_audio += segment_audio
            is_pause_tag = True  # Next item in split is the pause duration

    with open(output_path, "wb") as f:
        f.write(final_audio)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json or {}
        text = data.get('text', '').strip()
        voice = data.get('voice', 'en-IN-NeerjaNeural')
        speed = data.get('speed', '1.0')

        if not text:
            return jsonify({"error": "Text is empty"}), 400

        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}.mp3"
        output_path = os.path.join(AUDIO_STORAGE_DIR, filename)

        # Run async synthesis safely
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_full_audio(text, voice, speed, output_path))
        loop.close()

        return jsonify({"url": f"/audio-file/{filename}"})

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

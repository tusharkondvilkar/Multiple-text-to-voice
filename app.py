import os
import asyncio
import uuid
import re
import sys
import html
from flask import Flask, render_template, request, jsonify
import edge_tts

app = Flask(__name__)

# ROBUST DIRECTORY CONFIG FOR RENDER
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# We use a simple path that works on Render's ephemeral disk
STATIC_AUDIO = os.path.join(BASE_DIR, 'static', 'audio')

# Create the directory once. exist_ok=True prevents the FileExistsError
os.makedirs(STATIC_AUDIO, exist_ok=True)

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

        # SSML Conversion Logic
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
2. Updated templates/index.html (New Action Bar)
The player and a "Download Now" link will appear on the right side of the buttons as soon as the audio is ready.
code
Html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Audio Studio | HRMantra</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root { --hrm-blue: #003366; --accent: #5c67f2; }
        body { background: #f8fafc; font-family: 'Inter', sans-serif; margin: 0; }
        .top-nav { background: white; padding: 10px 40px; border-bottom: 1px solid #e1e5eb; }
        
        /* Header Selectors */
        .controls-row { background: white; padding: 15px 40px; border-bottom: 1px solid #e1e5eb; display: flex; gap: 15px; justify-content: center; }
        .sel-box { border: 1px solid #e2e8f0; border-radius: 12px; padding: 8px 15px; background: white; min-width: 180px; }
        .sel-label { font-size: 0.65rem; font-weight: 800; color: #94a3b8; text-transform: uppercase; margin-bottom: 2px; }
        .form-select { border: none; font-weight: 700; color: var(--hrm-blue); padding: 0; font-size: 0.9rem; }

        /* Content Area */
        .glass-card { background: white; border-radius: 30px; padding: 40px; box-shadow: 0 10px 40px rgba(0,0,0,0.04); max-width: 1100px; margin: 40px auto; }
        #textInput { width: 100%; border: 2px solid #e2e8f0; border-radius: 20px; padding: 30px; min-height: 350px; font-size: 1.1rem; line-height: 1.8; resize: none; outline: none; background: #fafbff; margin-bottom: 20px; }
        #textInput:focus { border-color: var(--accent); }

        /* Buttons & Player Row */
        .action-bar { display: flex; align-items: center; gap: 15px; flex-wrap: wrap; }
        .btn-pause { border: 1px solid #cbd5e1; background: #fff; border-radius: 8px; padding: 6px 18px; font-weight: 700; font-size: 0.85rem; }
        .btn-main { font-weight: 700; border-radius: 12px; padding: 12px 25px; border: none; transition: 0.2s; }
        .btn-play { background: #f1f5f9; color: var(--hrm-blue); }
        .btn-download { background: var(--hrm-blue); color: white; }
        
        /* The Player Section */
        #outputPanel { display: none; background: #eef2ff; padding: 10px 20px; border-radius: 15px; align-items: center; gap: 15px; border: 1px solid #c7d2fe; }
        .btn-quick-dl { background: #5c67f2; color: white; border-radius: 8px; padding: 5px 12px; font-size: 0.8rem; text-decoration: none; font-weight: 700; }
    </style>
</head>
<body>

<div class="top-nav"><img src="https://hrmantra.com/assets/images/hrmantralogosvg.svg" height="35"></div>

<div class="controls-row">
    <div class="sel-box">
        <p class="sel-label">1. Country</p>
        <select id="countrySelect" class="form-select" onchange="updateVoices()">
            <option value="">Select Country</option>
            {% for country in voice_map.keys() %}
            <option value="{{ country }}">{{ country }}</option>
            {% endfor %}
        </select>
    </div>
    <div class="sel-box">
        <p class="sel-label">2. Voice</p>
        <select id="voiceSelect" class="form-select" disabled><option>Choose Country first</option></select>
    </div>
    <div class="sel-box">
        <p class="sel-label">3. Speed</p>
        <select id="speedSelect" class="form-select">
            <option value="1.0">1.0x (Normal)</option>
            <option value="1.1">1.1x (Fast)</option>
            <option value="0.9">0.9x (Slow)</option>
        </select>
    </div>
    <div class="sel-box">
        <p class="sel-label">4. Format</p>
        <select class="form-select"><option>MP3</option><option>WAV</option></select>
    </div>
</div>

<div class="glass-card">
    <h3 class="fw-bold">AI Audio Studio</h3>
    <textarea id="textInput" placeholder="Type here...">If you think of a paragraph as a sandwich, <#0.5#>the supporting sentences are the filling between the bread.</textarea>

    <div class="action-bar">
        <div>
            <span class="small fw-bold text-muted me-2">Add pause</span>
            <button class="btn-pause" onclick="addTag('0.5')">0.5s</button>
            <button class="btn-pause" onclick="addTag('1.0')">1.0s</button>
            <button class="btn-pause" onclick="addTag('2.0')">2.0s</button>
        </div>

        <div class="ms-auto d-flex align-items-center gap-2">
            <button class="btn-main btn-play" id="playBtn" onclick="generate(true)">▶ GENERATE & PLAY</button>
            <button class="btn-main btn-download" id="dlBtn" onclick="generate(false)">↓ GENERATE & DOWNLOAD</button>
            
            <!-- This panel appears on the right side after generation -->
            <div id="outputPanel">
                <audio id="audioPlayer" controls style="height: 35px;"></audio>
                <a id="quickDownload" class="btn-quick-dl" href="#" download="audio.mp3">Download Now</a>
            </div>
        </div>
    </div>
</div>

<script>
    const voiceMap = {{ voice_map | tojson }};

    function updateVoices() {
        const country = document.getElementById('countrySelect').value;
        const vSelect = document.getElementById('voiceSelect');
        vSelect.innerHTML = '';
        if (country && voiceMap[country]) {
            vSelect.disabled = false;
            voiceMap[country].forEach(v => {
                let opt = document.createElement('option');
                opt.value = v.id; opt.textContent = v.label;
                vSelect.appendChild(opt);
            });
        }
    }

    function addTag(sec) {
        const area = document.getElementById('textInput');
        const tag = `<#${sec}#>`;
        const start = area.selectionStart;
        area.value = area.value.substring(0, start) + tag + area.value.substring(area.selectionEnd);
        area.focus();
        area.setSelectionRange(start + tag.length, start + tag.length);
    }

    async function generate(isPlayAction) {
        const text = document.getElementById('textInput').value;
        const voice = document.getElementById('voiceSelect').value;
        const speed = document.getElementById('speedSelect').value;

        if(!voice || voice.includes("Choose")) return alert("Please select a voice!");

        document.getElementById('playBtn').disabled = true;
        document.getElementById('dlBtn').disabled = true;

        try {
            const res = await fetch('/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ text, voice, speed })
            });
            const data = await res.json();
            
            if(data.url) {
                // Show the output panel on the right
                document.getElementById('outputPanel').style.display = 'flex';
                const player = document.getElementById('audioPlayer');
                player.src = data.url;
                document.getElementById('quickDownload').href = data.url;

                if(isPlayAction) {
                    player.play();
                } else {
                    document.getElementById('quickDownload').click();
                }
            } else {
                alert("Error: " + data.error);
            }
        } catch (e) {
            alert("Connection error. Please wait for Render to spin up.");
        }
        
        document.getElementById('playBtn').disabled = false;
        document.getElementById('dlBtn').disabled = false;
    }
</script>
</body>
</html>

import asyncio
import logging
import os
import re
import time
import uuid
import wave
from pathlib import Path

import edge_tts
import lameenc
import miniaudio
from flask import Flask, jsonify, render_template, request, send_from_directory, url_for


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # 15MB Upload Limit

AUDIO_DIR = Path(os.getenv("AUDIO_OUTPUT_DIR", "/tmp/hrmantra-audio"))
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Extended Character Limit & Session/File TTL
MAX_TEXT_LENGTH = 50_000        # Supports up to 50,000 characters per conversion
MAX_PAUSE_SECONDS = 60.0       # Supports pauses up to 60 seconds
FILE_TTL_SECONDS = 24 * 60 * 60 # Extended file retention to 24 hours (86,400s)

PAUSE_PATTERN = re.compile(r"<#\s*(\d+(?:\.\d+)?)\s*#>")

VOICE_DATA = [
    ("af-ZA-AdriNeural", "South Africa", "Female"),
    ("af-ZA-WillemNeural", "South Africa", "Male"),
    ("sq-AL-AnilaNeural", "Albania", "Female"),
    ("sq-AL-IlirNeural", "Albania", "Male"),
    ("am-ET-AmehaNeural", "Ethiopia", "Male"),
    ("am-ET-MekdesNeural", "Ethiopia", "Female"),
    ("ar-DZ-AminaNeural", "Algeria", "Female"),
    ("ar-DZ-IsmaelNeural", "Algeria", "Male"),
    ("ar-BH-AliNeural", "Bahrain", "Male"),
    ("ar-BH-LailaNeural", "Bahrain", "Female"),
    ("ar-EG-SalmaNeural", "Egypt", "Female"),
    ("ar-EG-ShakirNeural", "Egypt", "Male"),
    ("ar-IQ-BasselNeural", "Iraq", "Male"),
    ("ar-IQ-RanaNeural", "Iraq", "Female"),
    ("ar-JO-SanaNeural", "Jordan", "Female"),
    ("ar-JO-TaimNeural", "Jordan", "Male"),
    ("ar-KW-FahedNeural", "Kuwait", "Male"),
    ("ar-KW-NouraNeural", "Kuwait", "Female"),
    ("ar-LB-LaylaNeural", "Lebanon", "Female"),
    ("ar-LB-RamiNeural", "Lebanon", "Male"),
    ("ar-LY-ImanNeural", "Libya", "Female"),
    ("ar-LY-OmarNeural", "Libya", "Male"),
    ("ar-MA-MonaNeural", "Morocco", "Female"),
    ("ar-MA-JamalNeural", "Morocco", "Male"),
    ("ar-OM-AbdullahNeural", "Oman", "Male"),
    ("ar-OM-AyshaNeural", "Oman", "Female"),
    ("ar-QA-AmalNeural", "Qatar", "Female"),
    ("ar-QA-MoammarNeural", "Qatar", "Male"),
    ("ar-SA-HamedNeural", "Saudi Arabia", "Male"),
    ("ar-SA-ZariyahNeural", "Saudi Arabia", "Female"),
    ("ar-SY-AmanyNeural", "Syria", "Female"),
    ("ar-SY-LaithNeural", "Syria", "Male"),
    ("ar-TN-HediNeural", "Tunisia", "Male"),
    ("ar-TN-ReemNeural", "Tunisia", "Female"),
    ("ar-AE-HamdanNeural", "United Arab Emirates", "Male"),
    ("ar-AE-FatimaNeural", "United Arab Emirates", "Female"),
    ("ar-YE-MaryamNeural", "Yemen", "Female"),
    ("ar-YE-SalehNeural", "Yemen", "Male"),
    ("az-AZ-BabrNeural", "Azerbaijan", "Male"),
    ("az-AZ-YasharNeural", "Azerbaijan", "Male"),
    ("bn-BD-NabanitaNeural", "Bangladesh", "Female"),
    ("bn-BD-PradeepNeural", "Bangladesh", "Male"),
    ("bn-IN-BashkarNeural", "India", "Male"),
    ("bn-IN-TanishaaNeural", "India", "Female"),
    ("bs-BA-GoranNeural", "Bosnia and Herzegovina", "Male"),
    ("bs-BA-VesnaNeural", "Bosnia and Herzegovina", "Female"),
    ("bg-BG-BorislavNeural", "Bulgaria", "Male"),
    ("bg-BG-KalinaNeural", "Bulgaria", "Female"),
    ("my-MM-NilarNeural", "Myanmar", "Female"),
    ("my-MM-ThihaNeural", "Myanmar", "Male"),
    ("ca-ES-EnricNeural", "Spain", "Male"),
    ("ca-ES-JoanaNeural", "Spain", "Female"),
    ("zh-HK-HiuGaaiNeural", "Hong Kong", "Female"),
    ("zh-HK-HiuMaanNeural", "Hong Kong", "Female"),
    ("zh-HK-WanLungNeural", "Hong Kong", "Male"),
    ("zh-CN-XiaoxiaoNeural", "China", "Female"),
    ("zh-CN-XiaoyiNeural", "China", "Female"),
    ("zh-CN-YunjianNeural", "China", "Male"),
    ("zh-CN-YunxiNeural", "China", "Male"),
    ("zh-CN-YunxiaNeural", "China", "Male"),
    ("zh-CN-YunyangNeural", "China", "Male"),
    ("zh-CN-liaoning-XiaobeiNeural", "China", "Female"),
    ("zh-TW-HsiaoChenNeural", "Taiwan", "Female"),
    ("zh-TW-YunJheNeural", "Taiwan", "Male"),
    ("zh-TW-HsiaoYuNeural", "Taiwan", "Female"),
    ("zh-CN-shaanxi-XiaoniNeural", "China", "Female"),
    ("hr-HR-GabrijelaNeural", "Croatia", "Female"),
    ("hr-HR-SreckoNeural", "Croatia", "Male"),
    ("cs-CZ-AntoninNeural", "Czech Republic", "Male"),
    ("cs-CZ-VlastaNeural", "Czech Republic", "Female"),
    ("da-DK-ChristelNeural", "Denmark", "Female"),
    ("da-DK-JeppeNeural", "Denmark", "Male"),
    ("nl-BE-ArnaudNeural", "Belgium", "Male"),
    ("nl-BE-DenaNeural", "Belgium", "Female"),
    ("nl-NL-ColetteNeural", "Netherlands", "Female"),
    ("nl-NL-FennaNeural", "Netherlands", "Female"),
    ("nl-NL-MaartenNeural", "Netherlands", "Male"),
    ("en-AU-NatashaNeural", "Australia", "Female"),
    ("en-AU-WilliamNeural", "Australia", "Male"),
    ("en-CA-ClaraNeural", "Canada", "Female"),
    ("en-CA-LiamNeural", "Canada", "Male"),
    ("en-IN-NeerjaExpressiveNeural", "India", "Female"),
    ("en-IN-NeerjaNeural", "India", "Female"),
    ("en-IN-PrabhatNeural", "India", "Male"),
    ("en-IE-ConnorNeural", "Ireland", "Male"),
    ("en-IE-EmilyNeural", "Ireland", "Female"),
    ("en-KE-AsiliaNeural", "Kenya", "Female"),
    ("en-KE-ChilembaNeural", "Kenya", "Male"),
    ("en-NZ-MitchellNeural", "New Zealand", "Male"),
    ("en-NZ-MollyNeural", "New Zealand", "Female"),
    ("en-NG-EzinneNeural", "Nigeria", "Female"),
    ("en-NG-AbeoNeural", "Nigeria", "Male"),
    ("en-PH-JamesNeural", "Philippines", "Male"),
    ("en-PH-RosaNeural", "Philippines", "Female"),
    ("en-SG-LunaNeural", "Singapore", "Female"),
    ("en-SG-WayneNeural", "Singapore", "Male"),
    ("en-TZ-ElimuNeural", "Tanzania", "Male"),
    ("en-TZ-ImaniNeural", "Tanzania", "Female"),
    ("en-GB-LibbyNeural", "United Kingdom", "Female"),
    ("en-GB-MaisieNeural", "United Kingdom", "Female"),
    ("en-GB-RyanNeural", "United Kingdom", "Male"),
    ("en-GB-SoniaNeural", "United Kingdom", "Female"),
    ("en-GB-ThomasNeural", "United Kingdom", "Male"),
    ("en-US-AvaMultilingualNeural", "United States", "Female"),
    ("en-US-AndrewMultilingualNeural", "United States", "Male"),
    ("en-US-EmmaMultilingualNeural", "United States", "Female"),
    ("en-US-BrianMultilingualNeural", "United States", "Male"),
    ("en-US-AvaNeural", "United States", "Female"),
    ("en-US-AndrewNeural", "United States", "Male"),
    ("en-US-EmmaNeural", "United States", "Female"),
    ("en-US-BrianNeural", "United States", "Male"),
    ("en-US-AnaNeural", "United States", "Female"),
    ("en-US-AriaNeural", "United States", "Female"),
    ("en-US-ChristopherNeural", "United States", "Male"),
    ("en-US-EricNeural", "United States", "Male"),
    ("en-US-GuyNeural", "United States", "Male"),
    ("en-US-JennyNeural", "United States", "Female"),
    ("en-US-MichelleNeural", "United States", "Female"),
    ("en-US-RogerNeural", "United States", "Male"),
    ("en-US-SteffanNeural", "United States", "Male"),
    ("et-EE-AnuNeural", "Estonia", "Female"),
    ("et-EE-KertNeural", "Estonia", "Male"),
    ("fi-FI-HarriNeural", "Finland", "Male"),
    ("fi-FI-NooraNeural", "Finland", "Female"),
    ("fr-BE-CharlineNeural", "Belgium", "Female"),
    ("fr-BE-GerardNeural", "Belgium", "Male"),
    ("fr-CA-ThierryNeural", "Canada", "Male"),
    ("fr-CA-AntoineNeural", "Canada", "Male"),
    ("fr-CA-JeanNeural", "Canada", "Male"),
    ("fr-CA-SylvieNeural", "Canada", "Female"),
    ("fr-FR-VivienneMultilingualNeural", "France", "Female"),
    ("fr-FR-RemyMultilingualNeural", "France", "Male"),
    ("fr-FR-DeniseNeural", "France", "Female"),
    ("fr-FR-EloiseNeural", "France", "Female"),
    ("fr-FR-HenriNeural", "France", "Male"),
    ("fr-CH-ArianeNeural", "Switzerland", "Female"),
    ("fr-CH-FabriceNeural", "Switzerland", "Male"),
    ("ka-GE-EkaNeural", "Georgia", "Female"),
    ("ka-GE-GiorgiNeural", "Georgia", "Male"),
    ("de-AT-IngridNeural", "Austria", "Female"),
    ("de-AT-JonasNeural", "Austria", "Male"),
    ("de-DE-SeraphinaMultilingualNeural", "Germany", "Female"),
    ("de-DE-FlorianMultilingualNeural", "Germany", "Male"),
    ("de-DE-AmalaNeural", "Germany", "Female"),
    ("de-DE-ConradNeural", "Germany", "Male"),
    ("de-DE-KatjaNeural", "Germany", "Female"),
    ("de-DE-KillianNeural", "Germany", "Male"),
    ("de-CH-JanNeural", "Switzerland", "Male"),
    ("de-CH-LeniNeural", "Switzerland", "Female"),
    ("el-GR-AthinaNeural", "Greece", "Female"),
    ("el-GR-NestorasNeural", "Greece", "Male"),
    ("he-IL-AvriNeural", "Israel", "Male"),
    ("he-IL-HilaNeural", "Israel", "Female"),
    ("hi-IN-MadhurNeural", "India", "Male"),
    ("hi-IN-SwaraNeural", "India", "Female"),
    ("hu-HU-NoemiNeural", "Hungary", "Female"),
    ("hu-HU-TamasNeural", "Hungary", "Male"),
    ("is-IS-GudrunNeural", "Iceland", "Female"),
    ("is-IS-GunnarNeural", "Iceland", "Male"),
    ("id-ID-ArdiNeural", "Indonesia", "Male"),
    ("id-ID-GadisNeural", "Indonesia", "Female"),
    ("it-IT-GiuseppeMultilingualNeural", "Italy", "Male"),
    ("it-IT-DiegoNeural", "Italy", "Male"),
    ("it-IT-ElviraNeural", "Italy", "Female"),
    ("it-IT-IsabellaNeural", "Italy", "Female"),
    ("ja-JP-KeitaNeural", "Japan", "Male"),
    ("ja-JP-NanamiNeural", "Japan", "Female"),
    ("kk-KZ-DauletNeural", "Kazakhstan", "Male"),
    ("kk-KZ-AigulNeural", "Kazakhstan", "Female"),
    ("km-KH-PisethNeural", "Cambodia", "Male"),
    ("km-KH-SreymomNeural", "Cambodia", "Female"),
    ("ko-KR-HyunsuMultilingualNeural", "Korea (South)", "Male"),
    ("ko-KR-InJoonNeural", "Korea (South)", "Male"),
    ("ko-KR-SunHiNeural", "Korea (South)", "Female"),
    ("lo-LA-ChanthavongNeural", "Laos", "Male"),
    ("lo-LA-KeomanyNeural", "Laos", "Female"),
    ("lv-LV-EveritaNeural", "Latvia", "Female"),
    ("lv-LV-NaurisNeural", "Latvia", "Male"),
    ("lt-LT-OonasNeural", "Lithuania", "Male"),
    ("lt-LT-OnaNeural", "Lithuania", "Female"),
    ("mk-MK-AleksandarNeural", "North Macedonia", "Male"),
    ("mk-MK-MarijaNeural", "North Macedonia", "Female"),
    ("ms-MY-OsmanNeural", "Malaysia", "Male"),
    ("ms-MY-YasminNeural", "Malaysia", "Female"),
    ("mt-MT-GraceNeural", "Malta", "Female"),
    ("mt-MT-JosephNeural", "Malta", "Male"),
    ("mn-MN-BataaNeural", "Mongolia", "Male"),
    ("mn-MN-YesuiNeural", "Mongolia", "Female"),
    ("ne-NP-HemkalaNeural", "Nepal", "Female"),
    ("ne-NP-SagarNeural", "Nepal", "Male"),
    ("nb-NO-FinnNeural", "Norway", "Male"),
    ("nb-NO-PernilleNeural", "Norway", "Female"),
    ("ps-AF-GulNawazNeural", "Afghanistan", "Male"),
    ("ps-AF-LatifaNeural", "Afghanistan", "Female"),
    ("fa-IR-DilaraNeural", "Iran", "Female"),
    ("fa-IR-FaridNeural", "Iran", "Male"),
    ("pl-PL-MarekNeural", "Poland", "Male"),
    ("pl-PL-ZofiaNeural", "Poland", "Female"),
    ("pt-BR-ThalitaMultilingualNeural", "Brazil", "Female"),
    ("pt-BR-AntonioNeural", "Brazil", "Male"),
    ("pt-BR-FranciscaNeural", "Brazil", "Female"),
    ("pt-PT-DuarteNeural", "Portugal", "Male"),
    ("pt-PT-RaquelNeural", "Portugal", "Female"),
    ("ro-RO-AlinaNeural", "Romania", "Female"),
    ("ro-RO-EmilNeural", "Romania", "Male"),
    ("ru-RU-DmitryNeural", "Russia", "Male"),
    ("ru-RU-SvetlanaNeural", "Russia", "Female"),
    ("sr-RS-NicholasNeural", "Serbia", "Male"),
    ("sr-RS-SophieNeural", "Serbia", "Female"),
    ("si-LK-SameeraNeural", "Sri Lanka", "Male"),
    ("si-LK-ThiliniNeural", "Sri Lanka", "Female"),
    ("sk-SK-LukasNeural", "Slovakia", "Male"),
    ("sk-SK-ViktoriaNeural", "Slovakia", "Female"),
    ("sl-SI-RokNeural", "Slovenia", "Male"),
    ("sl-SI-PetraNeural", "Slovenia", "Female"),
    ("so-SO-MuuseNeural", "Somalia", "Male"),
    ("so-SO-UbaxNeural", "Somalia", "Female"),
    ("es-AR-ElenaNeural", "Argentina", "Female"),
    ("es-AR-TomasNeural", "Argentina", "Male"),
    ("es-BO-MarceloNeural", "Bolivia", "Male"),
    ("es-BO-SofiaNeural", "Bolivia", "Female"),
    ("es-CL-CatalinaNeural", "Chile", "Female"),
    ("es-CL-LorenzoNeural", "Chile", "Male"),
    ("es-CO-GonzaloNeural", "Colombia", "Male"),
    ("es-CO-SalomeNeural", "Colombia", "Female"),
    ("es-CR-JuanNeural", "Costa Rica", "Male"),
    ("es-CR-MariaNeural", "Costa Rica", "Female"),
    ("es-CU-BelkysNeural", "Cuba", "Female"),
    ("es-CU-ManuelNeural", "Cuba", "Male"),
    ("es-DO-EmilioNeural", "Dominican Republic", "Male"),
    ("es-DO-RamonaNeural", "Dominican Republic", "Female"),
    ("es-EC-AndreaNeural", "Ecuador", "Female"),
    ("es-EC-LuisNeural", "Ecuador", "Male"),
    ("es-SV-LorenaNeural", "El Salvador", "Female"),
    ("es-SV-RodrigoNeural", "El Salvador", "Male"),
    ("es-GQ-JavierNeural", "Equatorial Guinea", "Male"),
    ("es-GQ-TeresaNeural", "Equatorial Guinea", "Female"),
    ("es-GT-AndresNeural", "Guatemala", "Male"),
    ("es-GT-MartaNeural", "Guatemala", "Female"),
    ("es-HN-CarlosNeural", "Honduras", "Male"),
    ("es-HN-KarlaNeural", "Honduras", "Female"),
    ("es-MX-DaliaNeural", "Mexico", "Female"),
    ("es-MX-JorgeNeural", "Mexico", "Male"),
    ("es-NI-FedericoNeural", "Nicaragua", "Male"),
    ("es-NI-YolandaNeural", "Nicaragua", "Female"),
    ("es-PA-MargaritaNeural", "Panama", "Female"),
    ("es-PA-RobertoNeural", "Panama", "Male"),
    ("es-PY-MarioNeural", "Paraguay", "Male"),
    ("es-PY-TaniaNeural", "Paraguay", "Female"),
    ("es-PE-CamilaNeural", "Peru", "Female"),
    ("es-PE-AlexNeural", "Peru", "Male"),
    ("es-PR-KarinaNeural", "Puerto Rico", "Female"),
    ("es-PR-VictorNeural", "Puerto Rico", "Male"),
    ("es-ES-XimenaNeural", "Spain", "Female"),
    ("es-ES-ElviraNeural", "Spain", "Female"),
    ("es-ES-AlvaroNeural", "Spain", "Male"),
    ("es-US-AlonsoNeural", "United States", "Male"),
    ("es-US-PalomaNeural", "United States", "Female"),
    ("es-UY-MateoNeural", "Uruguay", "Male"),
    ("es-UY-ValentinaNeural", "Uruguay", "Female"),
    ("es-VE-PaolaNeural", "Venezuela", "Female"),
    ("es-VE-SebastianNeural", "Venezuela", "Male"),
    ("sv-SE-MattiasNeural", "Sweden", "Male"),
    ("sv-SE-SofieNeural", "Sweden", "Female"),
    ("th-TH-NiwatNeural", "Thailand", "Male"),
    ("th-TH-PremwadeeNeural", "Thailand", "Female"),
    ("tr-TR-AhmetNeural", "Turkey", "Male"),
    ("tr-TR-EmelNeural", "Turkey", "Female"),
    ("uk-UA-OstapNeural", "Ukraine", "Male"),
    ("uk-UA-PolinaNeural", "Ukraine", "Female"),
    ("ur-PK-AsadNeural", "Pakistan", "Male"),
    ("ur-PK-UzmaNeural", "Pakistan", "Female"),
    ("uz-UZ-MadinaNeural", "Uzbekistan", "Female"),
    ("uz-UZ-SardorNeural", "Uzbekistan", "Male"),
    ("vi-VN-HoaiMyNeural", "Vietnam", "Female"),
    ("vi-VN-NamMinhNeural", "Vietnam", "Male"),
    ("cy-GB-AledNeural", "United Kingdom", "Male"),
    ("cy-GB-NiaNeural", "United Kingdom", "Female"),
    ("zu-ZA-ThandoNeural", "South Africa", "Female"),
    ("zu-ZA-ThembaNeural", "South Africa", "Male"),
]
ALLOWED_VOICES = {voice for voice, _, _ in VOICE_DATA}
ALLOWED_SPEEDS = {"0.8": "-20%", "0.9": "-10%", "1.0": "+0%", "1.1": "+10%", "1.2": "+20%"}
ALLOWED_FORMATS = {"mp3", "wav"}


def cleanup_old_audio() -> None:
    cutoff = time.time() - FILE_TTL_SECONDS
    for path in AUDIO_DIR.iterdir():
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            app.logger.warning("Could not clean generated file %s", path, exc_info=True)


def parse_segments(text: str):
    """Return speech and exact-silence segments while preserving pause buttons."""
    cursor = 0
    segments = []
    for match in PAUSE_PATTERN.finditer(text):
        spoken = text[cursor : match.start()]
        if spoken.strip():
            segments.append(("text", spoken))
        pause_seconds = float(match.group(1))
        if not 0 < pause_seconds <= MAX_PAUSE_SECONDS:
            raise ValueError(f"Each pause must be between 0 and {int(MAX_PAUSE_SECONDS)} seconds.")
        segments.append(("pause", pause_seconds))
        cursor = match.end()

    remaining = text[cursor:]
    if remaining.strip():
        segments.append(("text", remaining))
    return segments


def split_text_into_chunks(text: str, max_chunk_size: int = 1200):
    """Splits text into sub-chunks on sentence boundaries for ultra-fast processing."""
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    sentences = re.split(r'(?<=[.!?\n])\s+', text)
    current_chunk = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > max_chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_len = 0
        current_chunk.append(sentence)
        current_len += len(sentence)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


async def text_chunk_to_pcm(text: str, voice: str, rate: str) -> bytes:
    """Streams a single text chunk from edge-tts and converts to mono PCM."""
    mp3_data = bytearray()
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        connect_timeout=15,
        receive_timeout=60,
    )
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_data.extend(chunk["data"])

    if not mp3_data:
        raise RuntimeError("The speech provider returned no audio for chunk.")

    decoded = miniaudio.decode(
        bytes(mp3_data),
        output_format=miniaudio.SampleFormat.SIGNED16,
        nchannels=1,
        sample_rate=24_000,
    )
    return decoded.samples.tobytes()


async def text_to_pcm(text: str, voice: str, rate: str) -> bytes:
    """Processes large texts via concurrent parallel requests for instant speed."""
    chunks = split_text_into_chunks(text, max_chunk_size=1200)

    async def fetch_chunk(chunk):
        if not chunk.strip():
            return b""
        for attempt in range(3):
            try:
                return await text_chunk_to_pcm(chunk, voice, rate)
            except Exception as e:
                if attempt == 2:
                    raise e
                await asyncio.sleep(0.5)

    # Run chunk generation concurrently in parallel!
    tasks = [fetch_chunk(c) for c in chunks]
    pcm_chunks = await asyncio.gather(*tasks)
    return b"".join(pcm_chunks)


async def build_pcm(segments, voice: str, rate: str) -> bytes:
    pcm_parts = []
    for segment_type, value in segments:
        if segment_type == "pause":
            pcm_parts.append(b"\x00\x00" * int(24_000 * value))
        else:
            pcm_parts.append(await text_to_pcm(value, voice, rate))
    return b"".join(pcm_parts)


def write_audio(pcm: bytes, path: Path, output_format: str) -> None:
    if output_format == "wav":
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24_000)
            wav_file.writeframes(pcm)
        return

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(128)
    encoder.set_in_sample_rate(24_000)
    encoder.set_channels(1)
    encoder.set_quality(2)
    path.write_bytes(encoder.encode(pcm) + encoder.flush())


@app.get("/")
def index():
    voice_map = {}
    for short_name, country, gender in VOICE_DATA:
        voice_map.setdefault(country, []).append(
            {"id": short_name, "label": f"{short_name.split('-')[-1]} ({gender})"}
        )

    return render_template("index.html", voice_map=voice_map)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/audio/<path:filename>")
def audio(filename):
    if not re.fullmatch(r"[0-9a-f]{32}\.(?:mp3|wav)", filename):
        return jsonify({"error": "Invalid audio file."}), 404
    return send_from_directory(AUDIO_DIR, filename, conditional=True, max_age=0)


@app.post("/generate")
def generate():
    output_path = None
    try:
        data = request.get_json(silent=True) or {}
        raw_text = str(data.get("text", "")).strip()
        voice = str(data.get("voice", ""))
        speed = str(data.get("speed", "1.0"))
        output_format = str(data.get("format", "mp3")).lower()

        if not raw_text:
            return jsonify({"error": "Please enter text to generate audio."}), 400
        if len(raw_text) > MAX_TEXT_LENGTH:
            return jsonify({"error": f"Text must be {MAX_TEXT_LENGTH:,} characters or fewer."}), 400
        if voice not in ALLOWED_VOICES:
            return jsonify({"error": "Please select a valid voice."}), 400
        if speed not in ALLOWED_SPEEDS:
            return jsonify({"error": "Please select a valid speed."}), 400
        if output_format not in ALLOWED_FORMATS:
            return jsonify({"error": "Please select MP3 or WAV."}), 400

        segments = parse_segments(raw_text)
        if not any(segment_type == "text" for segment_type, _ in segments):
            return jsonify({"error": "Please enter spoken text, not only pauses."}), 400

        cleanup_old_audio()
        filename = f"{uuid.uuid4().hex}.{output_format}"
        output_path = AUDIO_DIR / filename
        
        pcm = asyncio.run(build_pcm(segments, voice, ALLOWED_SPEEDS[speed]))
        write_audio(pcm, output_path, output_format)

        return jsonify(
            {
                "url": url_for("audio", filename=filename),
                "filename": f"HRMantra_Audio.{output_format}",
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        if output_path and output_path.exists():
            output_path.unlink(missing_ok=True)
        app.logger.exception("Audio generation failed")
        return jsonify(
            {
                "error": f"Audio generation failed: {str(exc)}",
            }
        ), 500


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")), debug=False)

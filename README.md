# HRMantra AI Audio Studio

## Render settings

- Runtime: Python 3
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
- Health check path: `/health`

If the service was created before `render.yaml` was added, copy these values into
the existing service settings and deploy with **Clear build cache & deploy**.

Generated audio is stored temporarily in `/tmp/hrmantra-audio` and expires after
one hour. MP3 and WAV output, speed selection, voice selection, play/download,
and the 0.5/1/2-second pause controls are supported.

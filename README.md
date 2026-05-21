# Brainrot Fusion Webapp - Render Ready

## Local test
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
Open: http://127.0.0.1:8000

## Render deploy
Upload these files to GitHub, then create a Render Web Service from the repo.

Manual settings if needed:
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Optional Environment Variables:
- `IMAGE_PROVIDER=openai`
- `OPENAI_API_KEY=...`
- `OPENAI_IMAGE_MODEL=gpt-image-1`

Without OpenAI key, it uses Pollinations server-side.


## Fix Render exit status 1
This version adds:
- runtime.txt -> python-3.11.9
- pinned package versions
- start command using `python -m uvicorn`

Recommended Render Start Command:
`python -m uvicorn main:app --host 0.0.0.0 --port $PORT`


## Render Python version
This package includes BOTH:
- `.python-version` -> 3.11.9
- `runtime.txt` -> python-3.11.9
- `render.yaml` env var `PYTHON_VERSION=3.11.9`

If Render still uses Python 3.14, manually add Environment Variable:
`PYTHON_VERSION = 3.11.9`
Then redeploy with Clear build cache.


## V3 Render start fix
Use Start Command:
`python main.py`

This avoids `$PORT` command parsing issues. `main.py` reads Render's `PORT` env variable internally.

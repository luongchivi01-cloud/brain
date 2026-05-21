import base64, json, os, random
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
FALLBACK_INDEX = STATIC_DIR / "index.html"
if not FALLBACK_INDEX.exists():
    FALLBACK_INDEX.write_text("<!doctype html><html><body><h1>Brainrot Fusion is running</h1><p>Missing static/index.html</p></body></html>", encoding="utf-8")

IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "pollinations").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1").strip()
POLLINATIONS_MODEL = os.getenv("POLLINATIONS_MODEL", "flux").strip()
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))

class Monster(BaseModel):
    id: str
    name: str
    type: str
    desc: str
    traits: List[str]
    hp: int
    atk: int
    defense: int = Field(default=70, alias="def")
    spd: int
    model_config = {"populate_by_name": True}

class FusionRequest(BaseModel):
    monster1: Monster
    monster2: Monster

app = FastAPI(title="Brainrot Fusion Webapp")

VISUAL_PROFILES = {
    "il-cacto-hipopotamo": "hippopotamus body fused with giant green cactus, hippo head emerging from cactus, cactus ribs, spikes, big brown sandals, desert setting",
    "tung-tung-hurar-tung-tung-tung-sahur": "walking wooden log humanoid, cylinder wood body, meme eyes, baseball bat, 3AM Indonesian sahur vibe",
    "frulli-frulla": "penguin with round glasses, coffee cup, hipster poetic vibe",
    "bobrito-bandito": "beaver gangster, fedora hat, Tommy gun, mafia noir clothing",
    "bombombini-gusini": "goose fighter jet hybrid, goose head and beak, jet wings, cockpit, missile details, feathers mixed with aircraft metal",
    "bombardiro-crocodilo": "green crocodile head fused with WWII bomber airplane body, wings, propellers, bombs, metal panels and reptile scales",
    "tralalero-tralala": "three-legged blue shark body, shark head, blue Nike sneakers, sporty running pose",
    "chimpanzini-bananini": "chimpanzee and banana hybrid, yellow banana peel body, chimp face, banana grenade details",
    "lirili-larila": "elephant body fused with tall green cactus, cactus ribs and spikes, oversized sandals, mystical desert vibe",
    "cocofanto-elefanto": "elephant with coconut head, gray elephant body, coconut shell texture, tropical splash",
    "pot-hotspot": "skeleton holding smartphone, WiFi signal motif, internet addict meme vibe",
    "la-vaca-saturno-saturnita": "upright cow with Saturn ring orbiting its body, cosmic cow hide",
    "orangutini-ananasini": "orangutan fused with pineapple, orange fur, spiky pineapple texture, pineapple leaf crest",
    "burbaloni-lulilolli": "calm capybara living inside a coconut shell, zen relaxed face",
    "frigo-camelo": "camel body with refrigerator torso, fridge door details, cooling vents, icy breath",
    "cappuccino-assassino": "dark cappuccino ninja, coffee cup head, black cloak, knife, assassin pose",
    "ballerina-cappucina": "cappuccino cup ballerina, coffee foam head, pink tutu, ballet shoes, elegant pose",
}

def mdict(m: Monster) -> Dict[str, Any]:
    return {"id": m.id, "name": m.name, "type": m.type, "desc": m.desc, "traits": m.traits, "hp": m.hp, "atk": m.atk, "def": m.defense, "spd": m.spd}

def vdesc(m: Dict[str, Any]) -> str:
    return VISUAL_PROFILES.get(m["id"], f"{m['type']}, {m['desc']}, traits: {', '.join(m['traits'])}")

def prompt_for(m1: Dict[str, Any], m2: Dict[str, Any]) -> str:
    return (
        "Create ONE single full-body Italian brainrot fusion character. "
        "It must be instantly recognizable as a hybrid of BOTH parents, not a random monster. "
        f"Parent 1 {m1['name']}: {vdesc(m1)}. "
        f"Parent 2 {m2['name']}: {vdesc(m2)}. "
        "Fusion rule: use the large body/silhouette from parent 1 and the head, accessories, or signature objects from parent 2; "
        "also blend textures and colors from both parents. Make every important parent trait visible. "
        "Cute absurd 3D cartoon render, polished meme character design, vibrant neon colors, cinematic lighting, dark neon lab background, "
        "centered square composition, one creature only, no text, no watermark."
    )

def fusion_meta(m1: Dict[str, Any], m2: Dict[str, Any]) -> Dict[str, Any]:
    a = "".join(ch for ch in m1["name"].split()[0] if ch.isalpha())[:5]
    b = "".join(ch for ch in m2["name"].split()[0] if ch.isalpha())[:4]
    last = "".join(ch for ch in m2["name"].split()[-1] if ch.isalpha())[:8]
    power = min(100, round((m1["atk"] + m2["atk"] + m1["hp"] + m2["hp"]) / 4 + 12))
    return {
        "name": f"{a}{b} {last}ILLO".upper(),
        "type": f"{m1['type'].split('•')[0].strip()} • {m2['type'].split('•')[-1].strip()}",
        "description": f"Sinh vật fusion kết hợp trực quan đặc điểm của {m1['name']} và {m2['name']}. Nhìn vào phải thấy được cả hai cha mẹ chứ không phải một quái vật ngẫu nhiên.",
        "lore": f"Được dung hợp từ ADN của {m1['name'].split()[0]} và {m2['name'].split()[0]} trong một thí nghiệm brainrot.",
        "abilities": (m1["traits"][:2] + m2["traits"][:2])[:4],
        "rarity": "legendary" if power >= 96 else "epic" if power >= 86 else "rare",
        "power": power,
        "hp": min(100, round((m1["hp"] + m2["hp"]) / 2 + 5)),
        "atk": min(100, round((m1["atk"] + m2["atk"]) / 2 + 5)),
        "def": min(100, round((m1["def"] + m2["def"]) / 2 + 5)),
        "spd": min(100, round((m1["spd"] + m2["spd"]) / 2 + 5)),
    }

def data_url(content: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(content).decode('utf-8')}"

def img_pollinations(prompt: str) -> str:
    seed = random.randint(1, 999999)
    encoded = quote(prompt[:1800] + ", high quality, no text, no watermark", safe="")
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=768&seed={seed}&nologo=true&model={POLLINATIONS_MODEL}"
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return data_url(r.content, r.headers.get("content-type", "image/png").split(";")[0])

def img_openai(prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY missing")
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": OPENAI_IMAGE_MODEL, "prompt": prompt[:3800], "size": "1024x1024"},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    item = r.json()["data"][0]
    if "b64_json" in item:
        return "data:image/png;base64," + item["b64_json"]
    img = requests.get(item["url"], timeout=REQUEST_TIMEOUT)
    img.raise_for_status()
    return data_url(img.content, img.headers.get("content-type", "image/png").split(";")[0])

def make_image(prompt: str) -> str:
    if IMAGE_PROVIDER == "openai":
        try:
            return img_openai(prompt)
        except Exception as e:
            print("[WARN] OpenAI failed, fallback pollinations:", e)
    return img_pollinations(prompt)

@app.get("/health")
def health():
    return {"ok": True, "message": "Brainrot Fusion Webapp ready", "image_provider": IMAGE_PROVIDER}

@app.post("/api/fusion")
def api_fusion(req: FusionRequest):
    try:
        m1, m2 = mdict(req.monster1), mdict(req.monster2)
        fusion = fusion_meta(m1, m2)
        prompt = prompt_for(m1, m2)
        fusion["imagePrompt"] = prompt
        fusion["image_data_url"] = make_image(prompt)
        return fusion
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

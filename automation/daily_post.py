#!/usr/bin/env python3
"""Create an original @veteriner post and publish it through official APIs.

Secrets arrive only from GitHub Actions environment variables. No user token is
printed, checked into the repo, or included in an image URL.
"""

import base64
import io
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
TODAY = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
IG_ID = "17841415352502900"
IG_API = "https://graph.instagram.com/v26.0"
OPENAI_API = "https://api.openai.com/v1"
REPO = os.environ.get("GITHUB_REPOSITORY", "2xdod/veteriner-media")
TEXT_MODEL = os.environ.get("TEXT_MODEL", "gpt-5-mini")
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-1")

# Narrow, predictable fallback subjects if a current event cannot be verified.
EVERGREEN = [
    "Yaz sıcağında evcil hayvanlar için serin ve temiz su",
    "Taşıma çantasıyla güvenli veteriner yolculuğu",
    "Evde kedi ve köpek için zehirli maddeleri güvenle saklama",
    "Kaybolma riskine karşı mikroçip ve iletişim bilgilerinin güncelliği",
    "Afet çantasında evcil hayvanlar için temel hazırlık",
    "Kışın açık havada hayvanlar için güvenli barınak ve su",
    "Yürüyüş dönüşünde pati ve tüy kontrolü",
    "Evcil hayvanların erişebileceği ilaçları güvenle saklama",
]


def request_json(url, payload=None, token=None, method=None, timeout=100):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=body, headers=headers, method=method or ("POST" if body else "GET"))
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except HTTPError as exc:
        # Never echo the request URL or payload: some APIs include secret values.
        try:
            detail = json.load(exc)
            message = detail.get("error", {}).get("message", "request failed")
        except (ValueError, OSError):
            message = "request failed"
        raise RuntimeError(f"API HTTP {exc.code}: {message}") from None


def openai(path, payload):
    return request_json(f"{OPENAI_API}/{path}", payload, os.environ["OPENAI_API_KEY"], timeout=180)


def output_text(response):
    return "\n".join(
        part.get("text", "") for item in response.get("output", [])
        for part in item.get("content", []) if part.get("type") == "output_text"
    ).strip()


def recent_event():
    response = openai("responses", {
        "model": TEXT_MODEL,
        "tools": [{"type": "web_search"}],
        "tool_choice": "required",
        "input": (
            f"Bugün Türkiye saatiyle {TODAY}. İstanbul/Türkiye'de son 48 saatte "
            "evcil veya sokak hayvanlarının güvenliğiyle doğrudan ilgili doğrulanmış "
            "tek bir olay ara (ör. sel, sıcak hava). İki bağımsız güvenilir kaynak "
            "aynı olayı tarih ve yer belirterek doğrulamıyorsa yalnızca NONE yaz. "
            "Varsa tek cümlelik olay özeti ve kaynakları URL'leriyle yaz. "
            "Hava tahminini gerçekleşmiş olay gibi anlatma."
        ),
    })
    text = output_text(response)
    citations = []
    for item in response.get("output", []):
        for part in item.get("content", []):
            for note in part.get("annotations", []):
                if note.get("type") == "url_citation":
                    url = note.get("url", "")
                    if url.startswith("https://"):
                        citations.append(url)
    domains = {urlparse(url).hostname for url in citations}
    if text.upper().startswith("NONE") or len(domains) < 2:
        return None
    return {"summary": text[:1200], "sources": list(dict.fromkeys(citations))[:3]}


def draft(event):
    fallback = EVERGREEN[datetime.fromisoformat(TODAY).date().toordinal() % len(EVERGREEN)]
    topic = json.dumps(event, ensure_ascii=False) if event else fallback
    response = openai("responses", {
        "model": TEXT_MODEL,
        "input": (
            "Sen @veteriner hesabının Türkçe editörüsün. Özgün, sakin, faydalı "
            "tek bir Instagram gönderisi oluştur. Konu: " + topic + "\n"
            "Olaysa yalnızca verilen doğrulanmış olay özeti ve kaynaklarındaki "
            "olguları kullan; kaynak dışı yaralı sayısı, konum veya klinik iddia ekleme. "
            "Genel bilgiyse belirli güncel olaydan söz etme. Reçete, ilaç dozu, "
            "kesin teşhis veya acil müdahale tekniği verme. Risk belirtisinde "
            "veteriner hekime başvurmayı öner. Başlık kısa olsun; 3 kısa madde "
            "ve en fazla 900 karakter açıklama yaz. Görsel temsili illüstrasyondur. "
            "Başka hesaptan metin alıntılama. Yanıt yalnızca JSON olsun: "
            '{"title":"...","bullets":["...","...","..."],'
            '"caption":"...","visual":"English illustration brief, no text"}'
        ),
        "text": {"format": {"type": "json_schema", "name": "instagram_post", "strict": True,
                 "schema": {"type": "object", "additionalProperties": False,
                            "properties": {"title": {"type": "string"}, "bullets": {
                                "type": "array", "items": {"type": "string"}},
                                "caption": {"type": "string"}, "visual": {"type": "string"}},
                            "required": ["title", "bullets", "caption", "visual"]}}},
    })
    item = json.loads(output_text(response))
    if (not isinstance(item["bullets"], list) or len(item["bullets"]) != 3
            or len(item["title"]) > 55 or any(len(x) > 110 for x in item["bullets"])
            or len(item["caption"]) > 900 or not item["visual"]):
        raise RuntimeError("Draft failed editorial length checks; nothing published")
    if event:
        item["caption"] += "\n\nKaynaklar: " + " | ".join(event["sources"][:2])
    item["caption"] += "\n\nGörsel özgün, temsili bir illüstrasyondur. #veteriner #hayvansağlığı"
    return item


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)


def wrap(draw, text, face, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and draw.textlength(trial, font=face) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])


def post_path():
    event = os.environ.get("GITHUB_EVENT_NAME")
    if event == "schedule":
        filename = f"{TODAY}-veteriner.jpg"
    elif event == "workflow_dispatch":
        run_id = os.environ.get("GITHUB_RUN_ID", "")
        if not run_id.isdecimal():
            raise RuntimeError("Missing GitHub run ID; nothing published")
        filename = f"{TODAY}-manual-{run_id}-veteriner.jpg"
    else:
        raise RuntimeError("Unexpected workflow event; nothing published")
    return ROOT / "posts" / filename


def make_image(post, path):
    result = openai("images/generations", {
        "model": IMAGE_MODEL,
        "prompt": (
            "Original premium editorial illustration for a Turkish veterinary education "
            "Instagram post. Warm teal, ivory and terracotta palette. Empathetic, "
            "accurate anatomy, calm and non-graphic. No lettering, text, symbols, "
            "watermarks, logos or misleading photojournalism. " + post["visual"]
        ),
        "size": "1024x1024",
        "quality": "medium",
    })
    art = Image.open(io.BytesIO(base64.b64decode(result["data"][0]["b64_json"]))).convert("RGB")
    art = art.resize((1080, 1080), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1080, 1350), "#f5f1e8")
    canvas.paste(art.crop((0, 0, 1080, 900)), (0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 900, 1080, 1350), fill="#f5f1e8")
    draw.text((70, 928), "@veteriner  /  BİLGİ NOTU", font=font(27, True), fill="#0d5554")
    title_font = font(52, True)
    title_lines = wrap(draw, post["title"], title_font, 940)
    if len(title_lines) > 2:
        raise RuntimeError("Title does not fit poster; nothing published")
    y = 985
    for line in title_lines:
        draw.text((70, y), line, font=title_font, fill="#143b3c")
        y += 64
    body_font = font(25)
    for bullet in post["bullets"]:
        for line in wrap(draw, "• " + bullet, body_font, 940):
            draw.text((70, y), line, font=body_font, fill="#143b3c")
            y += 36
        y += 5
    if y > 1305:
        raise RuntimeError("Bullet text does not fit poster; nothing published")
    path.parent.mkdir(exist_ok=True)
    canvas.save(path, "JPEG", quality=90, optimize=True)
    return path


def github(method, path, payload=None):
    return request_json(f"https://api.github.com/repos/{REPO}/{path}", payload,
                        os.environ["GITHUB_TOKEN"], method=method)


def upload(path):
    relative = path.relative_to(ROOT).as_posix()
    data = base64.b64encode(path.read_bytes()).decode()
    github("PUT", f"contents/{relative}", {"message": f"Original @veteriner art {TODAY}",
                                       "content": data, "branch": "main"})
    url = f"https://raw.githubusercontent.com/{REPO}/main/{relative}"
    # The CDN can lag immediately after a commit. Confirm public availability.
    for _ in range(12):
        try:
            with urlopen(Request(url, method="GET"), timeout=20) as resp:
                if resp.status == 200 and resp.headers.get("Content-Type", "").startswith("image/"):
                    return url
        except (HTTPError, OSError):
            pass
        time.sleep(5)
    raise RuntimeError("Image is not publicly available yet; nothing published")


def meta(method, path, fields=None):
    body = urlencode(fields).encode() if fields else None
    req = Request(f"{IG_API}/{path}", data=body, method=method,
                  headers={"Authorization": f"Bearer {os.environ['IG_ACCESS_TOKEN']}",
                           "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except HTTPError as exc:
        try:
            error = json.load(exc).get("error", {})
        except (ValueError, OSError):
            error = {}
        raise RuntimeError(f"Meta HTTP {exc.code}: {error.get('message', 'request failed')}") from None


def publish(url, caption):
    profile = meta("GET", f"{IG_ID}?fields=username")
    if profile.get("username", "").lower() != "veteriner":
        raise RuntimeError("Token does not belong to @veteriner; nothing published")
    container = meta("POST", f"{IG_ID}/media", {"image_url": url, "caption": caption})["id"]
    for _ in range(18):
        status = meta("GET", f"{container}?fields=status_code").get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram container {status}; nothing published")
        time.sleep(5)
    else:
        raise RuntimeError("Instagram container still processing; nothing published")
    # Never retry this call automatically; a network failure could hide success.
    media = meta("POST", f"{IG_ID}/media_publish", {"creation_id": container})
    print(f"Published Instagram media ID: {media['id']}")
    try:
        print("Post:", meta("GET", f"{media['id']}?fields=permalink").get("permalink"))
    except RuntimeError:
        print("Published; permalink lookup failed")


def main():
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("IG_ACCESS_TOKEN"):
        raise RuntimeError("Set OPENAI_API_KEY and IG_ACCESS_TOKEN as repository Actions secrets")
    if REPO != "2xdod/veteriner-media":
        raise RuntimeError("Unexpected GitHub repository; nothing published")
    path = post_path()
    try:
        github("GET", f"contents/{path.relative_to(ROOT).as_posix()}")
    except RuntimeError as exc:
        if not str(exc).startswith("API HTTP 404:"):
            raise
    else:
        print("This workflow run already has an image; skipping a duplicate post")
        return
    try:
        event = recent_event()
    except (RuntimeError, ValueError) as exc:
        print(f"Recent-event research unavailable ({type(exc).__name__}); using evergreen topic")
        event = None
    post = draft(event)
    image_url = upload(make_image(post, path))
    publish(image_url, post["caption"])


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, KeyError, ValueError) as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        sys.exit(1)

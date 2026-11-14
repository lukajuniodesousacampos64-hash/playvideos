import wave, subprocess, math, os, sys, re, json, argparse, numpy as np
from PIL import Image, ImageDraw, ImageFont
W, H, FPS = 720, 1280, 24
TITULO, OUT = "Play Vídeos", "docs/videos"
PURPLE, LIGHT = (139, 92, 246), (221, 205, 255)

def font(s):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p, s)
    return ImageFont.load_default(s)

yy = np.linspace(0, 1, H)[:, None, None]
BG = Image.fromarray((np.array([30, 12, 52]) * (1 - yy) + np.array([4, 2, 9]) * yy).repeat(W, 1).astype(np.uint8))

def wrap(d, text, f, maxw):
    out, cur = [], ""
    for w in text.split():
        n = (cur + " " + w).strip()
        if d.textlength(n, font=f) <= maxw: cur = n
        else: out.append(cur); cur = w
    return out + [cur]

def narr(lines, name):
    parts, segs, t = [], [], 0.0
    for i, l in enumerate(lines):
        f = f"/tmp/{name}{i}.wav"
        subprocess.run(["espeak-ng", "-v", "pt-br", "-s", "150", "-p", "45", "-w", f, l], check=True)
        w = wave.open(f); sr = w.getframerate()
        d = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768; w.close()
        d = np.concatenate([d, np.zeros(int(sr * .4))]); parts.append(d)
        segs.append((t, t + len(d) / sr)); t += len(d) / sr
    return np.concatenate(parts), sr, segs, t

def render(name, lines, frame):
    v, sr, segs, T = narr(lines, name); T += 1.0
    n = int(sr * T); m = np.zeros(n)
    ch = [[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]]
    for i in range(int(T // 4) + 1):
        s, e = int(i * 4 * sr), min(n, int((i * 4 + 4) * sr))
        if s >= n: break
        x = np.arange(e - s) / sr
        m[s:e] = sum(np.sin(2 * np.pi * f * x) for f in ch[i % 4]) * np.sin(np.pi * x / 4) ** .5 * .04
    a = m.copy(); a[:len(v)] += v * .9
    a = np.clip(a, -1, 1)
    wp = f"/tmp/{name}_mix.wav"
    w = wave.open(wp, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((a * 32767).astype(np.int16).tobytes()); w.close()
    out = f"{OUT}/{name}.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", wp, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", out], stdin=subprocess.PIPE)
    for i in range(int(T * FPS)):
        t = i / FPS
        k = next((j for j, (s, e) in enumerate(segs) if s <= t < e), len(segs) - 1)
        p.stdin.write(frame(t, k, segs, lines).tobytes())
    p.stdin.close(); p.wait(); print("ok", out)

def caption(d, text, prog, y, size=46):
    f = font(size); words = text.split(); shown = max(1, int(len(words) * min(1, prog * 1.15) + .5))
    lines = wrap(d, " ".join(words[:shown]), f, W - 100); lh = size + 14
    for j, l in enumerate(lines):
        d.text((W / 2, y + j * lh), l, font=f, fill=(255, 255, 255), anchor="mm")

# ---------- Modelo 1: vídeo dinâmico ----------
def dyn(t, k, segs, lines):
    img = BG.copy(); d = ImageDraw.Draw(img)
    for i in range(7):
        x = W / 2 + math.sin(t * .6 + i * 1.7) * 280; y = H / 2 + math.cos(t * .5 + i * 2.3) * 480; r = 60 + 40 * math.sin(t + i)
        d.ellipse([x - r, y - r, x + r, y + r], outline=PURPLE, width=3)
    s, e = segs[k]; prog = (t - s) / (e - s)
    f = font(78); words = lines[k].split(); shown = max(1, int(len(words) * min(1, prog * 1.2) + .5))
    ls = wrap(d, " ".join(words[:shown]), f, W - 90); y0 = H / 2 - len(ls) * 50
    for j, l in enumerate(ls):
        last = j == len(ls) - 1
        d.text((W / 2, y0 + j * 100), l, font=f, fill=LIGHT if not last else PURPLE, anchor="mm")
    d.rectangle([0, 0, W * (t / segs[-1][1]), 12], fill=PURPLE)
    d.text((W / 2, 70), "Play Vídeos", font=font(30), fill=(150, 130, 200), anchor="mm")
    return img

# ---------- Modelo 2: vídeo 3D (renderizador de polígonos em software) ----------
FACES = [(0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)]
SH = [1, .5, .8, .6, .9, .7]
def box(c, s, col):
    x, y, z = c; a, b, dd = [q / 2 for q in s]
    V = [(x + i * a, y + j * b, z + k * dd) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]
    return [([V[i] for i in f], col, SH[n]) for n, f in enumerate(FACES)]

def P(p, ang):
    x, y, z = p; ca, sa = math.cos(ang), math.sin(ang)
    x, z = x * ca - z * sa, x * sa + z * ca
    y2 = y * .94 - z * .34; z2 = y * .34 + z * .94
    dep = z2 + 11; f = 950 / dep
    return W / 2 + x * f, H * .45 - y2 * f, dep

def mix(c, b, a): return tuple(int(c[i] * a + b[i] * (1 - a)) for i in range(3))

def d3(t, k, segs, lines):
    img = BG.copy(); d = ImageDraw.Draw(img); ang = .5 + t * .22
    for g in range(-8, 9, 2):
        for a, b in (((g, -.4, -8), (g, -.4, 8)), ((-8, -.4, g), (8, -.4, g))):
            (x1, y1, _), (x2, y2, _) = P(a, ang), P(b, ang); d.line([x1, y1, x2, y2], fill=(50, 30, 90), width=1)
    rings = []
    if k >= 1:
        for i in range(3):
            r = ((t * 1.5 + i / 3) % 1) * 7.5; rings.append(r)
            pts = [P((r * math.cos(q / 64 * 6.2832), .9, r * math.sin(q / 64 * 6.2832)), ang) for q in range(65)]
            d.line([(a, b) for a, b, _ in pts], fill=mix(PURPLE, (30, 12, 52), max(0, 1 - r / 7.5)), width=5)
    on = any(abs(r - 4.46) < .5 for r in rings) and k >= 3
    faces = []
    faces += box((0, 0, 0), (3, .5, 1.8), (110, 60, 220)); faces += box((.8, .3, .9), (.2, .12, .1), (120, 255, 190))
    for ax in (-1.1, 1.1): faces += box((ax, .9, 0), (.16, 1.4, .16), (70, 40, 150))
    faces += box((4.2, -.15, 1.5), (.8, .1, 1.4), (230, 255, 240) if on else (60, 60, 90))
    quads = []
    for vs, col, sh in faces:
        pp = [P(v, ang) for v in vs]; quads.append((sum(q[2] for q in pp) / 4, [(q[0], q[1]) for q in pp], tuple(int(c * sh) for c in col)))
    for _, pts, col in sorted(quads, key=lambda q: -q[0]):
        d.polygon(pts, fill=col, outline=(20, 8, 40))
    d.text((W / 2, 130), TITULO, font=font(46), fill=LIGHT, anchor="mm")
    s, e = segs[k]; caption(d, lines[k], (t - s) / (e - s), 1010)
    d.rectangle([0, 0, W * (t / segs[-1][1]), 12], fill=PURPLE)
    return img

def roteiro(tema, modelo):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            import urllib.request
            estilo = "explicativo" if modelo == "3d" else "dinâmico, de ritmo rápido"
            body = json.dumps({"model": "claude-sonnet-4-6", "max_tokens": 800, "messages": [{"role": "user", "content":
                f"Escreva a narração em português do Brasil de um vídeo curto {estilo} sobre: {tema}. Responda só com um array JSON de 5 a 6 frases curtas (até 20 palavras cada), sem markdown."}]}).encode()
            r = urllib.request.Request("https://api.anthropic.com/v1/messages", body, {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
            t = json.load(urllib.request.urlopen(r, timeout=60))["content"][0]["text"]
            l = json.loads(t[t.index("["):t.rindex("]") + 1])
            if l: return [str(x) for x in l]
        except Exception as e: print("sem IA, usando o texto do pedido:", e)
    fr = [x.strip() + "." for x in re.split(r"[.!?]\s*", tema) if x.strip()]
    return fr or [tema]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--id", required=True); ap.add_argument("--modelo", default="dinamico"); ap.add_argument("--tema", required=True)
    a = ap.parse_args(); a.id = re.sub(r"[^a-zA-Z0-9-]", "", a.id)[:40]
    os.makedirs(OUT, exist_ok=True); TITULO = a.tema[:36]
    render(a.id, roteiro(a.tema, a.modelo), d3 if a.modelo == "3d" else dyn)
    ip = OUT + "/index.json"; idx = json.load(open(ip, encoding="utf8")) if os.path.exists(ip) else []
    idx.insert(0, {"id": a.id, "titulo": a.tema[:80], "modelo": "3D" if a.modelo == "3d" else "Dinâmico", "arquivo": f"videos/{a.id}.mp4"})
    json.dump(idx, open(ip, "w", encoding="utf8"), ensure_ascii=False, indent=1)

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "opencv-python-headless", "pillow"]
# ///
"""Easter egg Shorts montajı: gerçek oyun klipleri (16:9) -> 1080x1920 30 fps dikey video.

Kaynak: uretim/s03b-boya-oyun/montaj/kur.py (altyazı parçalama, miks, LUFS, sınırlayıcı oradan kopya).
Bu sürümde görüntü AI kare/klip değil, kaynak kliplerden kesitlerdir:
  - her çekim: kaynak (kaynaklar sözlüğünden), kt (kaynaktaki başlangıç sn), hiz, kadraj anahtarları
    (x, y = kırpma merkezi kaynakta 0-1; z = yakınlık, z=1 -> kaynak yüksekliğinin tamamı 9:16 kırpılır)
  - kesimde kısa "vuruş" yakınlaşması, isteğe bağlı parlaklık/gama, kırmızı daire işareti (kaynak koordinatlı)
  - beyaz flaş geçişleri (ayar.flas), kelime zamanlı altyazı, çekimin kaynağına göre "clip: @kanal" künyesi
  - ses: anlatım + Epidemic müzik (konuşmada kısılır, baştan sona) + SFX + kaynak klip sesi (çok kısık ya da sessiz)

Kullanım:  kur.py cekimler.json                     # tam render -> ayar.cikti
           kur.py cekimler.json --bas 0 --son 3.6   # parça render (kanca önizlemesi)
           kur.py cekimler.json --kare 0.2,5,12     # yalnız PNG -> <tablo dizini>/kontrol/
Yollar tablo dosyasının dizinine göredir.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BETIK = Path(__file__).resolve().parent
SR = 48000
NOKTA_SONU = (".", "!", "?", ",", ";", ":")
KOK = Path(".")


def yol(p) -> Path:
    p = Path(p)
    if p.is_absolute():
        return p
    if (KOK / p).exists():
        return KOK / p
    return BETIK / p


def smooth(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def egri(ad, u):
    u = min(max(u, 0.0), 1.0)
    if ad == "io":
        return smooth(u)
    if ad == "o":
        return 1 - (1 - u) ** 3
    if ad == "i":
        return u ** 3
    return u


# ---------------------------------------------------------------- kaynak okuyucu
class KesitOkur:
    """Bir çekimin kaynak kesitini ffmpeg ile sırayla çözer (setpts ile hız, fps ile çıkış kare hızı)."""

    def __init__(self, dosya: Path, kt: float, sure: float, hiz: float, fps: int):
        self.w, self.h = self._boyut(dosya)
        vf = f"setpts=PTS/{hiz:.5f},fps={fps}" if abs(hiz - 1) > 1e-3 else f"fps={fps}"
        cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{kt:.3f}", "-i", str(dosya),
               "-t", f"{sure * hiz + 0.5:.3f}", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.son = None

    @staticmethod
    def _boyut(dosya):
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", str(dosya)], capture_output=True, text=True)
        w, h = r.stdout.strip().split(",")[:2]
        return int(w), int(h)

    def kare(self):
        n = self.w * self.h * 3
        b = self.p.stdout.read(n)
        if len(b) == n:
            self.son = np.frombuffer(b, np.uint8).reshape(self.h, self.w, 3)
        return self.son

    def kapat(self):
        try:
            self.p.stdout.close()
            self.p.kill()
        except Exception:
            pass


# ---------------------------------------------------------------- çekim
class Cekim:
    def __init__(self, d, A, kaynaklar):
        self.d = d
        self.A = A
        self.bas, self.son = float(d["bas"]), float(d["son"])
        self.kaynak = kaynaklar[d["kaynak"]]
        self.dosya = yol(self.kaynak["dosya"])
        self.kt = float(d["kt"])
        self.hiz = float(d.get("hiz", 1.0))
        self.anahtar = d.get("kadraj") or [{"u": 0, "x": 0.5, "y": 0.5, "z": 1.0}]
        self.okur = None

    def ac(self, fps, t0=None):
        bas = self.bas if t0 is None else t0
        kt = self.kt + (bas - self.bas) * self.hiz
        self.okur = KesitOkur(self.dosya, kt, self.son - bas, self.hiz, fps)

    def kapat(self):
        if self.okur:
            self.okur.kapat()
            self.okur = None

    def kamera(self, t):
        """t: çekim içi sn -> (x, y, z)"""
        sure = self.son - self.bas
        noktalar = []
        for k in self.anahtar:
            tk = k["t"] if "t" in k else k.get("u", 0) * sure
            noktalar.append((tk, k))
        noktalar.sort(key=lambda p: p[0])
        if t <= noktalar[0][0]:
            k = noktalar[0][1]
            return k["x"], k["y"], k["z"]
        for (ta, a), (tb, b) in zip(noktalar, noktalar[1:]):
            if t <= tb:
                u = egri(b.get("egri", "io"), (t - ta) / max(tb - ta, 1e-6))
                return tuple(a[q] + (b[q] - a[q]) * u for q in ("x", "y", "z"))
        k = noktalar[-1][1]
        return k["x"], k["y"], k["z"]

    def matris(self, t, Wo, Ho, sw, sh):
        x, y, z = self.kamera(t)
        # kesimde vuruş: ilk 'vurus_sure' sn'de 'vurus' oranında fazladan yakınlık, hızla söner
        v = float(self.d.get("vurus", self.A.get("vurus", 0.05)))
        vs = float(self.A.get("vurus_sure", 0.22))
        if v and t < vs:
            z *= 1 + v * (1 - egri("o", t / vs))
        ch = sh / max(z, 1.0)
        cw = ch * Wo / Ho
        if cw > sw:  # kaynak dar ise
            cw = sw
            ch = cw * Ho / Wo
        cx = min(max(x * sw, cw / 2), sw - cw / 2)
        cy = min(max(y * sh, ch / 2), sh - ch / 2)
        s = Wo / cw
        return np.float32([[s, 0, -(cx - cw / 2) * s], [0, s, -(cy - ch / 2) * s]])

    def ciz(self, t, Wo, Ho):
        src = self.okur.kare()
        if src is None:
            return np.zeros((Ho, Wo, 3), np.uint8)
        sh, sw = src.shape[:2]
        M = self.matris(t, Wo, Ho, sw, sh)
        img = cv2.warpAffine(src, M, (Wo, Ho), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        # renk: kazanç (parlaklik) ve gama
        g = float(self.d.get("parlaklik", 1.0))
        gm = float(self.d.get("gama", 1.0))
        if abs(g - 1) > 1e-3 or abs(gm - 1) > 1e-3:
            lut = np.clip(((np.arange(256) / 255.0) ** (1 / gm)) * 255 * g, 0, 255).astype(np.uint8)
            img = cv2.LUT(img, lut)
        b = float(self.d.get("bulanik", 0))
        if b > 0:  # analiz kartı zemini: kaynak tanınmayacak kadar bulanık + karartılmış
            img = cv2.GaussianBlur(img, (0, 0), b)
        else:
            k = float(self.A.get("keskinlik", 0.4))
            if k > 0:
                bl = cv2.GaussianBlur(img, (0, 0), 2.0)
                img = cv2.addWeighted(img, 1 + k, bl, -k, 0)
        kr = float(self.d.get("karart", 0))
        if kr > 0:
            img = (img.astype(np.float32) * (1 - kr)).astype(np.uint8)
        for isr in self.d.get("isaret", []):
            img = isaret_ciz(img, isr, M, t)
        if self.d.get("kart"):
            img = kart_ciz(img, src, self.d["kart"], t)
        for k in self.d.get("katman", []):
            img = katman_ciz(img, k, M, t)
        return img


def isaret_ciz(img, isr, M, t):
    """Kırmızı daire: kaynak koordinatında (sx, sy, r piksel) -> kamera ile birlikte hareket eder."""
    bas = float(isr.get("bas", 0.0))
    son = float(isr.get("son", 99))
    if not (bas <= t < son):
        return img
    p = M @ np.array([isr["sx"], isr["sy"], 1.0])
    r = isr["r"] * M[0, 0]
    u = (t - bas) / 0.18
    k = 1.25 - 0.25 * egri("o", u) if u < 1 else 1.0
    a = min(1.0, u * 2) if u < 0.5 else 1.0
    kat = img.copy()
    kal = int(isr.get("kalinlik", 12))
    cv2.ellipse(kat, (int(p[0]), int(p[1])), (int(r * k), int(r * k * isr.get("oran", 1.0))), 0, 0, 360,
                (0, 0, 0), kal + 8, cv2.LINE_AA)
    cv2.ellipse(kat, (int(p[0]), int(p[1])), (int(r * k), int(r * k * isr.get("oran", 1.0))), 0, 0, 360,
                (40, 40, 235), kal, cv2.LINE_AA)
    return cv2.addWeighted(kat, a, img, 1 - a, 0)


def kart_ciz(img, src, k, t):
    """Kanıt kartı: kaynak karenin bir bölgesi (ör. kupa bildirimi) büyütülüp ortaya bindirilir; arka plan kararır."""
    bas = float(k.get("bas", 0.0))
    if t < bas:
        return img
    u = (t - bas) / float(k.get("pop", 0.22))
    a = min(1.0, u)
    kar = float(k.get("karart", 0.45)) * a
    img = (img.astype(np.float32) * (1 - kar)).astype(np.uint8)
    x0, y0, x1, y1 = (int(k[q]) for q in ("x0", "y0", "x1", "y1"))
    parca = src[y0:y1, x0:x1]
    gen = float(k.get("genislik", 980))
    olc = gen / max(parca.shape[1], 1)
    if u < 1:
        olc *= 0.8 + 0.2 * egri("o", u)
    parca = cv2.resize(parca, None, fx=olc, fy=olc, interpolation=cv2.INTER_CUBIC)
    h, w = parca.shape[:2]
    H, W = img.shape[:2]
    cx, cy = W // 2, int(k.get("orta_y", 800))
    if H < 1500:  # sunucu kipi üst bölmesi: altyazı sınırına çarpmasın
        cy = int(min(cy, H - 90 - h // 2))
    xa, ya = cx - w // 2, cy - h // 2
    # gölge
    gol = np.zeros((H, W), np.float32)
    cv2.rectangle(gol, (xa + 10, ya + 16), (xa + w + 10, ya + h + 16), 1.0, -1)
    gol = cv2.GaussianBlur(gol, (0, 0), 18) * 0.7 * a
    img = (img.astype(np.float32) * (1 - gol[:, :, None])).astype(np.uint8)
    xa2, ya2 = max(xa, 0), max(ya, 0)
    xb2, yb2 = min(xa + w, W), min(ya + h, H)
    roi = img[ya2:yb2, xa2:xb2].astype(np.float32)
    p = parca[ya2 - ya:yb2 - ya, xa2 - xa:xb2 - xa].astype(np.float32)
    img[ya2:yb2, xa2:xb2] = np.clip(roi * (1 - a) + p * a, 0, 255).astype(np.uint8)
    return img


# ---------------------------------------------------------------- stil (tek yer: motor/ayar.json "stil")
STIL = {}
_PANEL = {}
FONT_YOLU = None


def renk(ad, vars=(255, 255, 255)):
    """'vurgu' / 'beyaz' / 'gri' / 'kirmizi' / 'siyah' ya da [r,g,b] -> (r,g,b)."""
    if isinstance(ad, (list, tuple)):
        return tuple(int(x) for x in ad[:3])
    r = STIL.get("renkler", {}).get(ad)
    if r is None and ad == "sari":
        r = STIL.get("renkler", {}).get("vurgu")
    return tuple(r) if r else vars


def stil_yukle(A):
    """motor/ayar.json 'stil' + (varsa) tablo ayar.stil üst yazımı -> STIL, FONT_YOLU."""
    global FONT_YOLU
    STIL.clear()
    ap = BETIK.parent / "ayar.json"
    if ap.exists():
        STIL.update(json.loads(ap.read_text()).get("stil", {}))
    for k, v in (A.get("stil") or {}).items():
        STIL[k] = {**STIL.get(k, {}), **v} if isinstance(v, dict) else v
    FONT_YOLU = str(yol(STIL.get("font", "font/Montserrat.ttf")))


def stil_font(agirlik_ad, boy):
    return font_al(FONT_YOLU, int(boy), STIL.get("agirliklar", {}).get(agirlik_ad, agirlik_ad))


def _ikon_ciz(dr, ikon, x, y, r, renk_):
    zemin = renk("panel_zemin", (14, 14, 20))
    if ikon == "pin":
        dr.ellipse((x - r, y - r * 1.9, x + r, y + r * 0.1), fill=renk_ + (255,))
        dr.polygon([(x - r * 0.72, y - r * 0.35), (x + r * 0.72, y - r * 0.35), (x, y + r * 1.05)], fill=renk_ + (255,))
        dr.ellipse((x - r * 0.38, y - r * 1.28, x + r * 0.38, y - r * 0.52), fill=zemin + (255,))
    elif ikon == "film":
        dr.rounded_rectangle((x - r, y - r * 0.7, x + r, y + r * 0.8), radius=8, fill=renk_ + (255,))
        for i in range(4):
            xx = x - r + 8 + i * (2 * r - 16) / 3
            dr.rectangle((xx - 5, y - r * 0.55, xx + 5, y - r * 0.35), fill=zemin + (255,))
            dr.rectangle((xx - 5, y + r * 0.45, xx + 5, y + r * 0.65), fill=zemin + (255,))
    elif ikon == "kupa":
        dr.pieslice((x - r * 0.8, y - r * 1.2, x + r * 0.8, y + r * 0.4), 0, 180, fill=renk_ + (255,))
        dr.rectangle((x - r * 0.8, y - r * 1.2, x + r * 0.8, y - r * 0.4), fill=renk_ + (255,))
        dr.rectangle((x - r * 0.15, y + r * 0.35, x + r * 0.15, y + r * 0.75), fill=renk_ + (255,))
        dr.rectangle((x - r * 0.55, y + r * 0.75, x + r * 0.55, y + r * 0.95), fill=renk_ + (255,))


def panel_goruntu(p):
    """Bilgi kartı (stil.panel): satirlar [[metin, boyut, renk], ...]; renk 'gri' satırlar ince/küçük alt satır sayılır."""
    anahtar = json.dumps(p, sort_keys=True)
    if anahtar in _PANEL:
        return _PANEL[anahtar]
    S = STIL.get("panel", {})
    olc = float(S.get("olcek", 1.0))
    satirlar = []
    for metin, boy, rn in p["satirlar"]:
        alt = rn == "gri"
        f = stil_font(S.get("alt_agirlik", "Bold") if alt else S.get("agirlik", "ExtraBold"), float(boy) * olc)
        if S.get("buyuk_harf", True) and not alt and not metin.startswith('"'):
            metin = metin.upper()
        bb = f.getbbox(metin)
        satirlar.append((metin, f, bb, renk(rn)))
    ik = int(S.get("ikon_alani", 104)) if p.get("ikon") else 0
    ic_w = max(bb[2] - bb[0] for _, _, bb, _ in satirlar)
    bosluk = int(S.get("satir_arasi", 14))
    ic_h = sum(bb[3] for _, _, bb, _ in satirlar) + bosluk * (len(satirlar) - 1)
    pad_x, pad_y = int(S.get("ic_bosluk_x", 46)), int(S.get("ic_bosluk_y", 34))
    serit = int(S.get("vurgu_serit", 10))
    W = int(min(max(ic_w + ik + 2 * pad_x + serit, int(p.get("min_genislik", S.get("min_genislik", 520)))), 1000))
    H = int(ic_h + 2 * pad_y)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    vurgu = renk(p.get("vurgu", "vurgu"))
    z = S.get("zemin", [12, 12, 16, 0.86])
    R = int(S.get("yaricap", 26))
    dr.rounded_rectangle((0, 0, W - 1, H - 1), radius=R, fill=tuple(z[:3]) + (int(255 * z[3]),),
                         outline=(255, 255, 255, int(255 * float(S.get("kenar_opak", 0.12)))), width=2)
    if serit:
        dr.rounded_rectangle((0, 0, serit + R, H - 1), radius=R, fill=vurgu + (255,))
        dr.rectangle((serit, 0, serit + R, H - 1), fill=tuple(z[:3]) + (int(255 * z[3]),))
    if ik:
        _ikon_ciz(dr, p["ikon"], serit + 16 + ik // 2, H // 2 + 12, 32, vurgu)
    y = pad_y
    for metin, f, bb, rn in satirlar:
        x = serit + ik + (W - serit - ik - (bb[2] - bb[0])) // 2 - bb[0]
        dr.text((x, y), metin, font=f, fill=rn + (255,))
        y += bb[3] + bosluk
    arr = np.asarray(im).astype(np.float32) / 255.0
    _PANEL[anahtar] = arr
    return arr


def katman_ciz(img, k, M, t):
    bas, son = float(k.get("bas", 0.0)), float(k.get("son", 99))
    if not (bas <= t < son):
        return img
    u = (t - bas) / 0.2
    H, W = img.shape[:2]
    if k["tur"] == "panel":
        arr = panel_goruntu(k)
        a = min(1.0, u)
        if u < 1:
            arr = cv2.resize(arr, None, fx=0.88 + 0.12 * egri("o", u), fy=0.88 + 0.12 * egri("o", u),
                             interpolation=cv2.INTER_AREA)
        h, w = arr.shape[:2]
        oy = int(k.get("orta_y", 760))
        if H < 1500:  # sunucu kipi üst bölmesi: bant + künye altı ile altyazı sınırı arası
            ust_sinir = int(STIL.get("sunucu", {}).get("panel_ust", 470))
            oy = int(min(max(oy * H / 1920, ust_sinir + h / 2), H - 90 - h / 2))
        return bindir(img, arr, int(k.get("orta_x", W // 2)) - w // 2, oy - h // 2, a)
    p = M @ np.array([k["sx"], k["sy"], 1.0])
    x, y = int(p[0]), int(p[1])
    if k["tur"] == "pin":
        r = int(k.get("r", 46))
        dus = int(-60 * (1 - egri("o", min(u, 1.0))))
        kat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(kat)
        faz = ((t - bas) % 1.0)
        rr = int(r * (0.6 + 1.6 * faz))
        kr = renk(k.get("renk", "kirmizi"))
        dr.ellipse((x - rr, y - rr * 0.45, x + rr, y + rr * 0.45), outline=kr + (int(255 * (1 - faz)),), width=6)
        _ikon_ciz(dr, "pin", x + 3, y + dus + 3, r, (0, 0, 0))
        _ikon_ciz(dr, "pin", x, y + dus, r, kr)
        return bindir(img, np.asarray(kat).astype(np.float32) / 255.0, 0, 0)
    if k["tur"] == "ok":
        dx, dy = k.get("dx", 0), k.get("dy", -260)
        bos = int(k.get("bosluk", 40))
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        uz = min(1.0, u)
        x1, y1 = x + ux * bos, y + uy * bos
        x0, y0 = x1 + dx * uz, y1 + dy * uz
        kat = img.copy()
        cv2.arrowedLine(kat, (int(x0), int(y0)), (int(x1), int(y1)), (0, 0, 0), 30, cv2.LINE_AA, tipLength=0.32)
        rn = renk(k.get("renk", "vurgu"))
        cv2.arrowedLine(kat, (int(x0), int(y0)), (int(x1), int(y1)), rn[::-1], 18, cv2.LINE_AA, tipLength=0.3)
        return kat
    return img


def metin_rgba(parcalar, f, kontur, golge=None, pad=None, atla=None):
    """parcalar: [(metin, (r,g,b)), ...] tek satır. Siyah kontur + yumuşak gölge. Dönen: RGBA float, kelime kutuları."""
    bosluk = f.getlength(" ")
    genis = [f.getlength(m) for m, _ in parcalar]
    asc, desc = f.getmetrics()
    pad = pad if pad is not None else kontur + 18
    W = int(sum(genis) + bosluk * (len(parcalar) - 1) + 2 * pad)
    H = int(asc + desc + 2 * pad)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    kutular = []
    x = pad
    for (m, _), g in zip(parcalar, genis):
        kutular.append((x, x + g))
        x += g + bosluk
    if golge:
        gx, gy, gb, ga = golge
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(sh)
        for j, ((m, _), (x0, _)) in enumerate(zip(parcalar, kutular)):
            if j == atla:
                continue
            dr.text((x0 + gx, pad + gy), m, font=f, fill=(0, 0, 0, int(255 * ga)), stroke_width=kontur,
                    stroke_fill=(0, 0, 0, int(255 * ga)))
        from PIL import ImageFilter
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(gb)))
    dr = ImageDraw.Draw(im)
    for j, ((m, rn), (x0, _)) in enumerate(zip(parcalar, kutular)):
        if j == atla:
            continue
        dr.text((x0, pad), m, font=f, fill=rn + (255,), stroke_width=kontur, stroke_fill=(0, 0, 0, 255))
    return np.asarray(im).astype(np.float32) / 255.0, kutular, pad


class UstBaslik:
    """Üst başlık bandı (stil.ust_baslik): '<KONU> IN GTA 6?', 'GTA 6' vurgu renginde; yarı saydam koyu şerit;
    ilk 'giris_sn' içinde aşağı kayarak + belirerek girer."""

    def __init__(self, cfg, Wo):
        self.arr = None
        if not cfg or not cfg.get("metin"):
            return
        S = STIL.get("ust_baslik", {})
        metin = cfg["metin"].upper()
        vk = S.get("vurgu_kelime", "GTA 6")
        parca = []
        if vk in metin:
            on, son = metin.split(vk, 1)
            parca = [(x, renk("beyaz")) for x in on.split()] + [(vk, renk("vurgu"))] + [(x, renk("beyaz")) for x in son.split()]
            # tek başına kalan noktalama ('?') önceki parçaya boşluksuz yapışır
            while len(parca) >= 2 and parca[-1][0] in ("?", "!", "."):
                parca[-2] = (parca[-2][0] + parca[-1][0], parca[-2][1])
                parca.pop()
        else:
            parca = [(x, renk("beyaz")) for x in metin.split()]
        boy = int(S.get("boyut", 86))
        while True:
            f = stil_font(S.get("agirlik", "Black"), boy)
            arr, _, _ = metin_rgba(parca, f, int(S.get("kontur", 8)), S.get("golge"))
            if arr.shape[1] <= int(S.get("azami_genislik", 1000)) or boy < 40:
                break
            boy -= 4
        h, w = arr.shape[:2]
        serit_h = h + int(S.get("serit_ek", 0))
        bant = np.zeros((serit_h, Wo, 4), np.float32)
        so = float(S.get("serit_opak", 0.4))
        if so > 0:
            # yumuşak kenarlı koyu şerit
            prof = np.ones(serit_h, np.float32)
            k = max(int(serit_h * 0.18), 1)
            prof[:k] = np.linspace(0, 1, k)
            prof[-k:] = np.linspace(1, 0, k)
            bant[:, :, 3] = so * prof[:, None]
        x0 = (Wo - w) // 2
        y0 = (serit_h - h) // 2
        a = arr[:, :, 3:4]
        bant[y0:y0 + h, x0:x0 + w, :3] = bant[y0:y0 + h, x0:x0 + w, :3] * (1 - a) + arr[:, :, :3] * a
        bant[y0:y0 + h, x0:x0 + w, 3:4] = np.maximum(bant[y0:y0 + h, x0:x0 + w, 3:4], a)
        self.arr = bant
        self.y = int(S.get("ust_y", 210))
        self.giris = float(S.get("giris_sn", 0.4))

    def alt_kenar(self):
        return self.y + (self.arr.shape[0] if self.arr is not None else 0)

    def uygula(self, img, t=99.0):
        if self.arr is None:
            return img
        if t < self.giris:
            u = egri("o", t / self.giris)
            return bindir(img, self.arr, 0, self.y - int(40 * (1 - u)), u)
        return bindir(img, self.arr, 0, self.y)


class Sayac:
    """Adım sayacı rozeti (stil.sayac): [{t, metin}] ; metin null -> gizle."""

    def __init__(self, liste, Wo, y=None):
        self.liste = sorted(liste or [], key=lambda e: e["t"])
        S = STIL.get("sayac", {})
        self.y = int(y if y is not None else S.get("y", 420))
        self.Wo = Wo
        self.onbellek = {}

    def uygula(self, img, t):
        etkin = None
        for e in self.liste:
            if e["t"] <= t:
                etkin = e
        if not etkin or not etkin.get("metin"):
            return img
        S = STIL.get("sayac", {})
        m = (S.get("onek", "") + etkin["metin"]).upper()
        if m not in self.onbellek:
            f = stil_font(S.get("agirlik", "Black"), int(S.get("boyut", 40)))
            bb = f.getbbox(m)
            hh = int(S.get("yukseklik", 76))
            w = max(bb[2] - bb[0] + 52, hh)
            im = Image.new("RGBA", (w, hh), (0, 0, 0, 0))
            dr = ImageDraw.Draw(im)
            dr.rounded_rectangle((0, 0, w - 1, hh - 1), radius=hh // 2, fill=renk("vurgu") + (255,),
                                 outline=(0, 0, 0, 255), width=4)
            dr.text(((w - (bb[2] - bb[0])) // 2 - bb[0], (hh - (bb[3] - bb[1])) // 2 - bb[1]), m, font=f,
                    fill=renk("siyah", (10, 10, 10)) + (255,))
            self.onbellek[m] = np.asarray(im).astype(np.float32) / 255.0
        arr = self.onbellek[m]
        u = (t - etkin["t"]) / 0.18
        if u < 1:
            arr = cv2.resize(arr, None, fx=0.7 + 0.3 * egri("o", u), fy=0.7 + 0.3 * egri("o", u))
        h, w = arr.shape[:2]
        return bindir(img, arr, self.Wo - int(S.get("sag_bosluk", 48)) - w, self.y - h // 2)


# ---------------------------------------------------------------- altyazı (S03b'den)
def kelimeleri_duzelt(kelimeler, kurallar):
    """birlestir: [["a", ".m.", "AM"]] -> ardışık kelimeleri tek kelimeye indir."""
    out = list(kelimeler)
    for kural in kurallar:
        *desen, yeni = kural
        i = 0
        while i <= len(out) - len(desen):
            if [w["word"].strip().lower().strip(".,!?;:") for w in out[i:i + len(desen)]] == \
                    [d.lower().strip(".,!?;:") for d in desen]:
                son = out[i + len(desen) - 1]
                sonek = re.search(r"[.,!?;:]*$", son["word"].strip()).group(0)  # cümle sonu korunur
                out[i:i + len(desen)] = [{"word": yeni + sonek, "start": out[i]["start"], "end": son["end"]}]
            i += 1
    return out


def altyazi_parcala(kelimeler, cfg, sure):
    en_cok = int(cfg.get("en_cok_kelime", 3))
    harf = int(cfg.get("en_cok_harf", 17))
    bosluk = float(cfg.get("bosluk_kir", 0.28))
    parcalar, cur = [], []
    for w in kelimeler:
        metin = w["word"].strip()
        if not metin:
            continue
        if cur:
            yazi = " ".join(c["word"].strip() for c in cur + [w])
            if (len(yazi.split()) > en_cok or len(yazi) > harf or w["start"] - cur[-1]["end"] > bosluk
                    or cur[-1]["word"].strip().endswith(NOKTA_SONU)):
                parcalar.append(cur)
                cur = []
        cur.append(w)
    if cur:
        parcalar.append(cur)
    bag = set(cfg.get("bag_kelimeler", "a an the of to in at on and or but with from that is are his her my".split()))
    for i in range(len(parcalar) - 1):
        p, q = parcalar[i], parcalar[i + 1]
        son = p[-1]["word"].strip().lower()
        if (len(p) > 1 and sum(len(w["word"].split()) for w in q) < en_cok and son in bag
                and q[0]["start"] - p[-1]["end"] <= bosluk
                and len(" ".join(w["word"].strip() for w in [p[-1]] + q)) <= harf):
            q.insert(0, p.pop())
    kuyruk = float(cfg.get("kuyruk", 0.35))
    sonuc = []
    for i, p in enumerate(parcalar):
        bas = p[0]["start"]
        son = p[-1]["end"] + kuyruk
        if i + 1 < len(parcalar):
            son = min(son, parcalar[i + 1][0]["start"])
        son = min(son, sure)
        kel = []
        for w in p:
            m = w["word"].strip()
            if not cfg.get("noktalama", False):
                m = " ".join(x.rstrip(".,;:") for x in m.split())
            if cfg.get("buyuk_harf"):
                m = m.upper()
            kel.append((m, w["start"]))
        yazi = " ".join(m for m, _ in kel)
        sonuc.append((bas, son, yazi, kel))
    return sonuc


def font_al(yolu, boy, agirlik=None):
    f = ImageFont.truetype(str(yolu), boy)
    if agirlik:
        try:
            f.set_variation_by_name(agirlik)
        except Exception:
            pass
    return f


def yazi_goruntu(yazi, font_yolu, boy, kontur, azami, agirlik, renk=(255, 255, 255, 255)):
    while True:
        f = font_al(font_yolu, boy, agirlik)
        bb = f.getbbox(yazi, stroke_width=kontur)
        if bb[2] - bb[0] <= azami or boy < 28:
            break
        boy -= 4
    asc, desc = f.getmetrics()
    w = bb[2] - bb[0] + 2 * kontur + 8
    h = asc + desc + 2 * kontur + 8
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((kontur + 4 - bb[0], kontur + 4), yazi, font=f, fill=renk,
                            stroke_width=kontur, stroke_fill=(0, 0, 0, 255))
    return np.asarray(im).astype(np.float32) / 255.0


def bindir(img, arr, x0, y0, opak=1.0):
    h, w = arr.shape[:2]
    H, W = img.shape[:2]
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb:
        return img
    a = arr[ya - y0:yb - y0, xa - x0:xb - x0]
    al = a[:, :, 3:4] * opak
    roi = img[ya:yb, xa:xb].astype(np.float32)
    img[ya:yb, xa:xb] = np.clip(roi * (1 - al) + a[:, :, 2::-1] * 255.0 * al, 0, 255).astype(np.uint8)
    return img


class Altyazi:
    """Shorts altyazısı (stil.altyazi): BÜYÜK HARF, kalın display font, siyah kontur + gölge, 1-3 kelime;
    konuşulan kelime vurgu renginde ve girişte kısa 'pop' (pop_bas -> 1,0)."""

    def __init__(self, cfg, kelime_yolu, sure, Wo, t_kayma=0.0):
        d = json.loads(Path(kelime_yolu).read_text())
        kel = kelimeleri_duzelt(d["words"], cfg.get("birlestir", []))
        kel = [dict(w, start=w["start"] + t_kayma, end=w["end"] + t_kayma) for w in kel]
        self.cfg = cfg
        self.parcalar = altyazi_parcala(kel, cfg, sure)
        self.Wo = Wo
        self.onbellek = {}

    def _goruntu(self, i, etkin, olc):
        anahtar = (i, etkin, olc)
        if anahtar in self.onbellek:
            return self.onbellek[anahtar]
        c = self.cfg
        kel = self.parcalar[i][3]
        boy = int(c.get("boyut", 92))
        while True:
            f = stil_font(c.get("agirlik", "Black"), boy)
            genis = sum(f.getlength(m) for m, _ in kel) + f.getlength(" ") * (len(kel) - 1)
            if genis <= int(c.get("azami_genislik", 900)) or boy < 40:
                break
            boy -= 4
        parca = [(m, renk(c.get("etkin_renk", "vurgu")) if j == etkin else renk(c.get("renk", "beyaz")))
                 for j, (m, _) in enumerate(kel)]
        kontur = int(c.get("kontur", 12))
        golge = c.get("golge")
        kucuk = olc < 0.999 and etkin is not None
        arr, kutular, pad = metin_rgba(parca, f, kontur, golge, atla=etkin if kucuk else None)
        if kucuk:
            # etkin kelime kendi merkezinde küçük basılır (pop girişi); diğer kelimeler yerinde kalır
            arr = arr.copy()
            fk = stil_font(c.get("agirlik", "Black"), max(int(boy * olc), 10))
            kw, _, _ = metin_rgba([parca[etkin]], fk, max(int(round(kontur * olc)), 2), golge)
            x0, x1 = kutular[etkin]
            kh, kwid = kw.shape[:2]
            ya, xa = arr.shape[0] // 2 - kh // 2, int((x0 + x1) / 2) - kwid // 2
            ys0, xs0 = max(ya, 0), max(xa, 0)
            ys1, xs1 = min(ya + kh, arr.shape[0]), min(xa + kwid, arr.shape[1])
            parc = kw[ys0 - ya:ys1 - ya, xs0 - xa:xs1 - xa]
            al = parc[:, :, 3:4]
            bolge = arr[ys0:ys1, xs0:xs1]
            bolge[:, :, :3] = bolge[:, :, :3] * (1 - al) + parc[:, :, :3] * al
            bolge[:, :, 3:4] = np.maximum(bolge[:, :, 3:4], al)
        self.onbellek[anahtar] = arr
        return arr

    def uygula(self, img, t, y=None):
        for i, (bas, son, yazi, kel) in enumerate(self.parcalar):
            if bas <= t < son:
                break
        else:
            return img
        etkin = None
        for j, (_, ks) in enumerate(kel):
            if ks <= t:
                etkin = j
        pop = float(self.cfg.get("pop", 0.1))
        pb = float(self.cfg.get("pop_bas", 0.85))
        olc = 1.0
        if etkin is not None and pop > 0 and t - kel[etkin][1] < pop:
            olc = pb + (1 - pb) * egri("o", (t - kel[etkin][1]) / pop)
            olc = round(olc * 20) / 20  # önbellek için 0,05 adım
        arr = self._goruntu(i, etkin, olc)
        h, w = arr.shape[:2]
        return bindir(img, arr, self.Wo // 2 - w // 2, int(y or self.cfg.get("orta_y", 1320)) - h // 2)


class Kunye:
    """'clip: @kanal' künyesi (stil.kunye): küçük, yarı saydam koyu kapsül içinde."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.onbellek = {}

    def uygula(self, img, etiket):
        if not etiket or not self.cfg:
            return img
        c = self.cfg
        if etiket not in self.onbellek:
            f = stil_font(c.get("agirlik", "Bold"), int(c.get("boyut", 30)))
            fo = stil_font(c.get("onek_agirlik", "SemiBold"), int(c.get("boyut", 30)))
            onek = c.get("onek", "clip:")
            w1 = fo.getlength(onek + " ")
            w2 = f.getlength(etiket)
            asc, desc = f.getmetrics()
            px, py = int(c.get("ic_x", 18)), int(c.get("ic_y", 9))
            W, H = int(w1 + w2 + 2 * px), int(asc + desc + 2 * py)
            im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dr = ImageDraw.Draw(im)
            z = c.get("zemin", [0, 0, 0, 0.5])
            dr.rounded_rectangle((0, 0, W - 1, H - 1), radius=H // 2, fill=tuple(z[:3]) + (int(255 * z[3]),))
            dr.text((px, py), onek, font=fo, fill=renk(c.get("onek_renk", "gri")) + (255,))
            dr.text((px + w1, py), etiket, font=f, fill=renk("beyaz") + (255,))
            self.onbellek[etiket] = np.asarray(im).astype(np.float32) / 255.0
        return bindir(img, self.onbellek[etiket], int(c.get("x", 48)), int(c.get("y", 392)), float(c.get("opak", 1.0)))


# ---------------------------------------------------------------- ses (S03b'den sadeleştirilmiş)
def ses_oku(p, bas=0.0, sure=None, af=None):
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{bas:.4f}"]
    if sure is not None:
        cmd += ["-t", f"{sure:.4f}"]
    cmd += ["-i", str(p)] + (["-af", af] if af else []) + ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def _yerlestir(hedef, x, t):
    i = int(round(t * SR))
    if i < 0:
        x, i = x[-i:], 0
    n = min(len(x), len(hedef) - i)
    if n > 0:
        hedef[i:i + n] += x[:n]


def _rampa(n, bas, son):
    return np.linspace(bas, son, max(n, 1), dtype=np.float32)[:, None]


def lufs_olc(x):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                        "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                       input=x.astype(np.float32).tobytes(), capture_output=True)
    for satir in r.stderr.decode(errors="ignore").splitlines()[::-1]:
        if satir.strip().startswith("I:"):
            v = float(satir.split()[1])
            return v if v > -70 else None
    return None


def sinirla(x, tavan, w_ms=20.0):
    g = np.minimum(1.0, tavan / np.maximum(np.abs(x).max(axis=1), 1e-9)).astype(np.float32)
    w = max(int(w_ms / 1000 * SR), 3)
    g = cv2.erode(g.reshape(1, -1), np.ones((1, 2 * w + 1), np.uint8), borderType=cv2.BORDER_REPLICATE)
    g = cv2.blur(g, (w | 1, 1), borderType=cv2.BORDER_REPLICATE).reshape(-1)
    return x * g[:, None]


def konusma_kisma(nar, kis):
    e = np.abs(nar.mean(axis=1))
    w = int(0.05 * SR)
    e = np.sqrt(np.convolve(e * e, np.ones(w, np.float32) / w, mode="same"))
    aktif = (e > 10 ** (-40 / 20)).astype(np.float32)
    g = int(0.25 * SR)
    aktif = np.minimum(np.convolve(aktif, np.ones(g, np.float32), mode="same"), 1)
    s = int(0.08 * SR)
    aktif = np.convolve(aktif, np.ones(s, np.float32) / s, mode="same")
    return (1 - aktif * (1 - 10 ** (kis / 20))).astype(np.float32)


def miks(T, cekimler, bas, son, cikti: Path):
    """Anlatım (0 dB referans) + müzik + SFX + kaynak sesi -> [bas, son] aralığı, -14 LUFS."""
    A = T["ayar"]
    N = int(round((son - bas) * SR))
    nar = np.zeros((N, 2), np.float32)
    an = ses_oku(yol(A["anlatim"]), af=A.get("anlatim_zinciri"))
    l_nar = lufs_olc(an)
    if l_nar is not None:
        an *= 10 ** ((float(A.get("anlatim_lufs", -16)) - l_nar) / 20)
    _yerlestir(nar, an, float(A.get("anlatim_t", 0.0)) - bas)
    muz = np.zeros_like(nar)
    M = A.get("muzik")
    ozet = ["anlatım"]
    if M:
        m = ses_oku(yol(M["dosya"]), float(M.get("ofset", 0.0)) + bas, son - bas)
        lv = np.full(len(m), float(M.get("db", -18)), np.float32)
        tt = bas + np.arange(len(m), dtype=np.float32) / SR
        if M.get("seviye_noktalari"):
            ts = [float(p[0]) for p in M["seviye_noktalari"]]
            ds = [float(p[1]) for p in M["seviye_noktalari"]]
            lv = np.interp(tt, ts, ds).astype(np.float32)
        m *= (10 ** (lv / 20))[:, None]
        fi = int(float(M.get("giris_sn", 0.3)) * SR)
        if bas < 0.01 and fi:
            m[:fi] *= _rampa(min(fi, len(m)), 0, 1)
        fo = int(float(M.get("cikis_sn", 0.6)) * SR)
        if fo and len(m) > fo:
            m[-fo:] *= _rampa(fo, 1, 0.25)  # son kareye kadar susmaz
        _yerlestir(muz, m, 0.0)
        kis = float(M.get("konusmada_kis_db", -5))
        if kis < 0:
            muz *= konusma_kisma(nar, kis)[:, None]
        ozet.append("müzik")
    sfx = np.zeros_like(nar)
    for e in T.get("sfx", []):
        t = float(e["t"])
        x = ses_oku(yol(e["dosya"]), float(e.get("kirp_bas_sn", 0.0)), e.get("kirp_sure_sn"))
        x *= 10 ** (float(e.get("db", -8)) / 20)
        fi = min(max(int(0.005 * SR), int(float(e.get("fade_giris_sn", 0.0)) * SR)), len(x))
        x[:fi] *= _rampa(fi, 0, 1)
        fo = min(int(float(e.get("fade_cikis_sn", 0.05)) * SR), len(x))
        if fo:
            x[-fo:] *= _rampa(fo, 1, 0)
        _yerlestir(sfx, x, t - bas)
    if T.get("sfx"):
        ozet.append(f"{len(T['sfx'])} SFX")
    kay = np.zeros_like(nar)
    varsayilan = A.get("kaynak_ses_db")
    for c in cekimler:
        db = c.d.get("kaynak_ses_db", varsayilan)
        if db is None or c.son <= bas or c.bas >= son:
            continue
        a, b = max(c.bas, bas), min(c.son, son)
        af = f"atempo={c.hiz:.4f}" if abs(c.hiz - 1) > 1e-3 and 0.5 <= c.hiz <= 2 else None
        try:
            x = ses_oku(c.dosya, c.kt + (a - c.bas) * c.hiz, (b - a) * c.hiz, af)
        except subprocess.CalledProcessError:
            continue
        x *= 10 ** (float(db) / 20)
        f = min(int(0.015 * SR), len(x) // 2)
        if f:
            x[:f] *= _rampa(f, 0, 1)
            x[-f:] *= _rampa(f, 1, 0)
        _yerlestir(kay, x[:int((b - a) * SR)], a - bas)
    if varsayilan is not None:
        ozet.append(f"kaynak sesi {varsayilan} dB")
    toplam = nar + muz + sfx + kay
    hedef = float(A.get("ses_lufs", -14))
    lufs = lufs_olc(toplam)
    if lufs is not None:
        toplam *= 10 ** ((hedef - lufs) / 20)
        ozet.append(f"miks {lufs:.1f} -> {hedef:.0f} LUFS")
    toplam = sinirla(toplam, 10 ** (-1.5 / 20))
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_s24le", str(cikti)], input=toplam.astype(np.float32).tobytes(), check=True)
    return ", ".join(ozet)


# ---------------------------------------------------------------- sunucu kipi
class Sunucu:
    """Sunucu kipi: harici sunucu/avatar aracı çıktısı gibi kendi sesi olan 9:16 sunucu videosu alt bölmeye kırpılır
    (yeşil ekran yok). ayar.sunucu: {dosya, bas, x, y, z}; bölme oranı stil.sunucu.ust_oran."""

    def __init__(self, cfg, Wo, Ho, fps):
        S = STIL.get("sunucu", {})
        self.cfg = cfg
        self.dosya = yol(cfg["dosya"])
        self.Wo, self.Ho, self.fps = Wo, Ho, fps
        self.ust = int(round(Ho * float(cfg.get("ust_oran", S.get("ust_oran", 0.58)))))
        self.h = Ho - self.ust
        self.okur = None
        self.ayrac = int(S.get("ayrac", 6))

    def ac(self, t0, sure):
        self.kapat()
        self.okur = KesitOkur(self.dosya, float(self.cfg.get("bas", 0.0)) + t0, sure, 1.0, self.fps)

    def kapat(self):
        if self.okur:
            self.okur.kapat()
            self.okur = None

    def kare(self):
        src = self.okur.kare() if self.okur else None
        if src is None:
            return np.zeros((self.h, self.Wo, 3), np.uint8)
        sh, sw = src.shape[:2]
        z = max(float(self.cfg.get("z", 1.2)), 1.0)
        a = self.Wo / self.h
        cw = sw / z
        ch = cw / a
        if ch > sh:
            ch = sh
            cw = ch * a
        cx = min(max(float(self.cfg.get("x", 0.5)) * sw, cw / 2), sw - cw / 2)
        cy = min(max(float(self.cfg.get("y", 0.37)) * sh, ch / 2), sh - ch / 2)
        s_ = self.Wo / cw
        M = np.float32([[s_, 0, -(cx - cw / 2) * s_], [0, s_, -(cy - ch / 2) * s_]])
        return cv2.warpAffine(src, M, (self.Wo, self.h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    def birlestir(self, ust_img):
        img = np.empty((self.Ho, self.Wo, 3), np.uint8)
        img[:self.ust] = ust_img
        img[self.ust:] = self.kare()
        if self.ayrac:
            y0 = self.ust - self.ayrac // 2
            img[y0:y0 + self.ayrac] = np.array(renk("vurgu")[::-1], np.uint8)
        return img


# ---------------------------------------------------------------- flaş
def flas_kazanc(flaslar, t):
    """Beyaz flaş: tepe t'de 1, öncesi sure_once, sonrası sure_sonra boyunca söner."""
    g = 0.0
    for f in flaslar:
        tf = float(f["t"])
        o, s = float(f.get("sure_once", 0.12)), float(f.get("sure_sonra", 0.35))
        if tf - o <= t <= tf:
            g = max(g, egri("i", (t - (tf - o)) / max(o, 1e-3)))
        elif tf < t <= tf + s:
            g = max(g, 1 - egri("o", (t - tf) / max(s, 1e-3)))
    return g * max((float(f.get("guc", 1.0)) for f in flaslar), default=1.0)


# ---------------------------------------------------------------- ana
def main():
    global KOK
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tablo")
    ap.add_argument("--bas", type=float, default=0.0)
    ap.add_argument("--son", type=float, default=None)
    ap.add_argument("--cikti", default=None)
    ap.add_argument("--kare", default=None)
    ap.add_argument("--crf", type=int, default=17)
    a = ap.parse_args()

    tablo = Path(a.tablo).resolve()
    KOK = tablo.parent
    T = json.loads(tablo.read_text())
    A = T["ayar"]
    Wo, Ho, fps = int(A.get("genislik", 1080)), int(A.get("yukseklik", 1920)), int(A.get("fps", 30))
    sure = float(A["sure"])
    kaynaklar = T["kaynaklar"]
    cekimler = [Cekim(d, A, kaynaklar) for d in T["cekimler"]]
    for x, y in zip(cekimler, cekimler[1:]):
        if abs(x.son - y.bas) > 1e-6:
            sys.exit(f"çekimler bitişik değil: {x.son} -> {y.bas}")
    if abs(cekimler[-1].son - sure) > 1e-6:
        sys.exit(f"son çekim {cekimler[-1].son} != sure {sure}")
    stil_yukle(A)
    alt = Altyazi({**A.get("altyazi", {}), **STIL.get("altyazi", {})}, yol(A["kelimeler"]), sure, Wo,
                  float(A.get("anlatim_t", 0.0))) \
        if A.get("altyazi") and A.get("kelimeler") else None
    kunye = Kunye({**(A.get("kunye") or {}), **STIL.get("kunye", {})} if A.get("kunye") else None)
    ub = dict(A.get("ust_baslik") or {})
    if ub is not None and not ub.get("metin") and A.get("konu"):
        ub["metin"] = f"{A['konu'].upper()} IN GTA 6?"
    ust = UstBaslik(ub if (A.get("ust_baslik") is not None or A.get("konu")) else None, Wo)
    sayac = Sayac(A.get("sayac"), Wo, A.get("sayac_y"))
    flaslar = A.get("flas", [])

    def cekim_index(t):
        for i, c in enumerate(cekimler):
            if c.bas <= t < c.son:
                return i
        return len(cekimler) - 1

    sunucu = Sunucu(A["sunucu"], Wo, Ho, fps) if A.get("kip") == "sunucu" else None
    if sunucu and alt:
        alt.cfg = {**alt.cfg, "orta_y": alt.cfg.get("sunucu_orta_y", sunucu.ust)}  # altyazı iki bölmenin sınırında

    def kare_uret(c, t):
        if sunucu:
            img = sunucu.birlestir(c.ciz(t - c.bas, Wo, sunucu.ust))
        else:
            img = c.ciz(t - c.bas, Wo, Ho)
        g = flas_kazanc(flaslar, t)
        if g > 0.002:
            img = cv2.addWeighted(img, 1 - g, np.full_like(img, 255), g, 0)
        img = ust.uygula(img, t)
        img = sayac.uygula(img, t)
        img = kunye.uygula(img, c.kaynak.get("etiket"))
        if alt and c.d.get("altyazi", True):
            img = alt.uygula(img, t, None if sunucu else c.d.get("altyazi_y"))  # çekime özel yükseklik (tam kipte)
        return img

    if a.kare:
        out = KOK / "kontrol"
        out.mkdir(exist_ok=True)
        for s in a.kare.split(","):
            t = float(s)
            c = cekimler[cekim_index(t)]
            c.ac(fps, t)
            if sunucu:
                sunucu.ac(t, 0.5)
            img = kare_uret(c, t)
            c.kapat()
            p = out / f"kare_{t:06.2f}.png"
            cv2.imwrite(str(p), img)
            print(p)
        return

    bas = a.bas
    son = min(a.son if a.son is not None else sure, sure)
    cikti = Path(a.cikti) if a.cikti else KOK / A.get("cikti", "cikti.mp4")
    if not cikti.is_absolute():
        cikti = KOK / cikti
    ara = KOK / "ara"
    ara.mkdir(exist_ok=True)
    wav = ara / f"miks_{bas:g}-{son:g}.wav"
    print("ses:", miks(T, cekimler, bas, son, wav), file=sys.stderr)

    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{Wo}x{Ho}", "-r", str(fps), "-i", "-", "-i", str(wav),
                            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest",
                            "-movflags", "+faststart", str(cikti)], stdin=subprocess.PIPE)
    n0, n1 = int(round(bas * fps)), int(round(son * fps))
    acik = None
    if sunucu:
        sunucu.ac(bas, son - bas)
    for n in range(n0, n1):
        t = n / fps
        i = cekim_index(t)
        if acik != i:
            if acik is not None:
                cekimler[acik].kapat()
            cekimler[i].ac(fps, max(t, cekimler[i].bas))
            acik = i
        enc.stdin.write(kare_uret(cekimler[i], t).tobytes())
        if n % 150 == 0:
            print(f"  {t:5.1f}/{son:.1f} sn", file=sys.stderr)
    if acik is not None:
        cekimler[acik].kapat()
    if sunucu:
        sunucu.kapat()
    enc.stdin.close()
    enc.wait()
    print(cikti)


if __name__ == "__main__":
    main()

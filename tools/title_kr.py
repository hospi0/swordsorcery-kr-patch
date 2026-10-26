# -*- coding: utf-8 -*-
r"""타이틀(SSSS/00OPEN/TITLE.DG2 = «DC» u16 폭 u16 높이 + RGB555 BE, 320×240) 위쪽 «ソード&ソーサリー» → 한글(2026-10-26)
  글자 화소(주변 흐림 바탕과 많이 다른 것)만 찾아 OpenCV inpaint 로 메우고, 같은 모양(밝은 글씨 + 오른쪽 아래 어두운 그림자 + 기울임)으로 다시 씀.
  python tools/title_kr.py [글]          → work/gfx/title_preview.png (원본|새것 전체 2배 + 글자 부분 6배)
  python tools/title_kr.py --write       → work/build/SSSS/00OPEN/TITLE.DG2"""
import os, struct, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'work', 'disc0', 'SSSS', '00OPEN', 'TITLE.DG2')
FONT = r'C:\claude\utils\font\nanum-myeongjo\NanumMyeongjoExtraBold.ttf'
BOX = (132, 20, 276, 42)            # 원본 글자 범위(여유 포함) x0 y0 x1 y1
TEXT = '소드 & 소서리'


def load():
    d = open(SRC, 'rb').read(); w, h = struct.unpack_from('>HH', d, 2)
    u = np.array(struct.unpack_from('>%dH' % (w * h), d, 6), dtype=np.uint16).reshape(h, w)
    rgb = np.stack([(u & 31) << 3, ((u >> 5) & 31) << 3, ((u >> 10) & 31) << 3], -1).astype(np.uint8)
    return d, w, h, rgb


def save(d, rgb):
    r, g, b = [(rgb[..., i].astype(np.uint16) >> 3) for i in range(3)]
    u = 0x8000 | r | (g << 5) | (b << 10)
    return d[:6] + struct.pack('>%dH' % u.size, *u.flatten().tolist())


def text_mask(rgb):
    x0, y0, x1, y1 = BOX
    reg = rgb[y0:y1, x0:x1].astype(np.int16)
    bg = cv2.medianBlur(rgb, 9)[y0:y1, x0:x1].astype(np.int16)
    diff = np.abs(reg - bg).sum(-1)
    m = np.zeros(rgb.shape[:2], np.uint8); m[y0:y1, x0:x1] = (diff > 60).astype(np.uint8) * 255
    return cv2.dilate(m, np.ones((3, 3), np.uint8))


def render(rgb, text):
    x0, y0, x1, y1 = BOX
    S = 4                                                   # 크게 그려 줄여서 부드러운 가장자리
    f = ImageFont.truetype(FONT, 13 * S)
    tw, th = f.getbbox(text)[2], f.getbbox(text)[3]
    lay = Image.new('L', (tw + 8 * S, th + 8 * S), 0); ImageDraw.Draw(lay).text((2 * S, 2 * S), text, font=f, fill=255)
    lay = lay.transform(lay.size, Image.AFFINE, (1, 0.22, -0.22 * lay.size[1] / 2, 0, 1, 0), Image.BICUBIC)   # 오른쪽으로 기울임
    lay = lay.resize((lay.width // S, lay.height // S), Image.LANCZOS)
    a = np.asarray(lay).astype(np.float32) / 255
    ys, xs = np.nonzero(a > 0.05); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    hh, ww = a.shape
    cx, cy = (137 + 268) // 2, 31                            # 원본 글자 가운데
    ox, oy = cx - ww // 2, cy - hh // 2
    out = rgb.astype(np.float32)
    shadow = np.array([8, 8, 16], np.float32); fill_top = np.array([248, 248, 248], np.float32); fill_bot = np.array([176, 184, 208], np.float32)
    for dx, dy in ((2, 2), (1, 2), (2, 1), (1, 1)):          # 진한 검은 그림자(원본처럼 글자 반쯤 덮게 — 하스피 2026-10-26)
        sub = out[oy + dy:oy + dy + hh, ox + dx:ox + dx + ww]; k = np.clip(a * 1.2, 0, 1)[..., None]
        sub[:] = sub * (1 - k) + shadow * k
    grad = np.linspace(0, 1, hh)[:, None, None]; col = fill_top * (1 - grad) + fill_bot * grad
    sub = out[oy:oy + hh, ox:ox + ww]; k = a[..., None]; sub[:] = sub * (1 - k) + col * k
    return np.clip(out, 0, 255).astype(np.uint8)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    text = args[0] if args else TEXT
    d, w, h, rgb = load()
    m = text_mask(rgb)
    clean = cv2.inpaint(rgb, m, 3, cv2.INPAINT_TELEA)
    new = render(clean, text)
    q = save(d, new); assert len(q) == len(d)
    # 미리보기: 실제 화면에 찍힐 RGB555 로 되읽어서
    _, _, _, back = (None, None, None, None)
    u = np.array(struct.unpack_from('>%dH' % (w * h), q, 6), dtype=np.uint16).reshape(h, w)
    back = np.stack([(u & 31) << 3, ((u >> 5) & 31) << 3, ((u >> 10) & 31) << 3], -1).astype(np.uint8)
    A, B = Image.fromarray(rgb), Image.fromarray(back)
    P = Image.new('RGB', (w * 4 + 8, h * 2 + 8 + 35 * 6), (0, 0, 0))
    P.paste(A.resize((w * 2, h * 2), 0), (0, 0)); P.paste(B.resize((w * 2, h * 2), 0), (w * 2 + 8, 0))
    crop = (120, 12, 290, 47)
    P.paste(A.crop(crop).resize((170 * 6 // 2 * 1, 35 * 6 // 2 * 1), 0).resize((w * 2, 35 * 6), 0), (0, h * 2 + 8))
    P.paste(B.crop(crop).resize((w * 2, 35 * 6), 0), (w * 2 + 8, h * 2 + 8))
    n = 1
    while os.path.exists(os.path.join(ROOT, 'work', 'gfx', 'title_preview_v%d.png' % n)): n += 1
    p = os.path.join(ROOT, 'work', 'gfx', 'title_preview_v%d.png' % n); P.save(p); print(p)
    if '--write' in sys.argv:
        o = os.path.join(ROOT, 'work', 'build', 'SSSS', '00OPEN'); os.makedirs(o, exist_ok=True)
        open(os.path.join(o, 'TITLE.DG2'), 'wb').write(q); print('→', os.path.join(o, 'TITLE.DG2'))


if __name__ == '__main__':
    main()

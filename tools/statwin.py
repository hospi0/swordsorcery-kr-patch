# -*- coding: utf-8 -*-
r"""STATWIN.TEX(상태 창 글자판) 읽기·쓰기(2026-10-26)
  mato 블록 = [u32 pp 절대 오프셋][u32 pp 크기] + «pp»(70 70) u16 폭 u16 높이 + 16색 BE RGB555 + 4bpp 그림(왼쪽 화소 = 높은 니블)
  블록 0·1 = 글자판 160×180 · 2~8 = 얼굴 «PP»(50 50) 80×119
  python tools/statwin.py png  → work/gfx/statwin/pp<k>.png (원본 색, 투명 = 회색)"""
import os, struct, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'work', 'disc0', 'SSSS', '1WINDOW', 'STATWIN.TEX')


def blocks(d):
    n = struct.unpack_from('>I', d, 8)[0]
    return [struct.unpack_from('>I', d, 0x10 + 4 * i)[0] for i in range(n + 1)]


def read_pp(d, k):
    po, sz = struct.unpack_from('>II', d, blocks(d)[k])
    assert d[po:po + 2] == b'pp', k
    w, h = struct.unpack_from('>HH', d, po + 2); pal = struct.unpack_from('>16H', d, po + 6)
    raw = d[po + 38:po + 38 + w * h // 2]
    idx = [(raw[i // 2] >> 4) if i % 2 == 0 else raw[i // 2] & 15 for i in range(w * h)]
    return po, w, h, pal, idx


def rgb(u): return ((u & 31) * 8, ((u >> 5) & 31) * 8, ((u >> 10) & 31) * 8)


def to_png(w, h, pal, idx, bg=(70, 70, 70)):
    im = Image.new('RGB', (w, h), bg)
    im.putdata([rgb(pal[p]) if p else bg for p in idx]); return im


def write_pp(d, k, idx):
    po, w, h, pal, _ = read_pp(d, k)
    b = bytearray(d); b[po + 38:po + 38 + w * h // 2] = bytes((idx[i] << 4) | idx[i + 1] for i in range(0, w * h, 2))
    return bytes(b)


if __name__ == '__main__':
    d = open(SRC, 'rb').read(); out = os.path.join(ROOT, 'work', 'gfx', 'statwin'); os.makedirs(out, exist_ok=True)
    for k in (0, 1):
        po, w, h, pal, idx = read_pp(d, k)
        to_png(w, h, pal, idx).resize((w * 3, h * 3), 0).save(os.path.join(out, 'pp%d.png' % k))
        print(k, w, h, ['%04x' % u for u in pal])

# -*- coding: utf-8 -*-
r"""PRESS.FNT 한글판 만들기(2026-10-26) — FNTC(LE 머리): 'FNTC' · u32 크기 · 0 ·0 · +0x10 코드표 위치 · 글리프 위치 · 글자 수 · (폭 16, 높이 12, 1, 0)
  코드표 = SJIS u16 LE 오름차순(게임 0x0603EEFC 가 이분 탐색), 글리프 = 16×12 1비트(24 B, 행마다 u16 BE, 원본 잉크 열 0~10·행 0~11).
  build(codes_glyphs) → 바이트 · hangul_glyph(ch) = 갈무리11 비트맵(잉크 윗줄 → 행 1, 왼쪽 맞춤, 폭 11 넘으면 실패)
  기존 글자는 PRESS.FNT → 없으면 PRESSALL.FNT 에서 그대로."""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
FONTDIR = os.path.join(ROOT, 'work', 'disc0', 'SSSS', '0FONT')
GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'


def read_fnt(name):
    d = open(os.path.join(FONTDIR, name), 'rb').read()
    co, go, n, wh = struct.unpack_from('<IIII', d, 0x10)
    codes = struct.unpack_from('<%dH' % n, d, co)
    return {c: d[go + 24 * i:go + 24 * i + 24] for i, c in enumerate(codes)}


ORIG = None


def orig_glyph(code):
    global ORIG
    if ORIG is None:
        ORIG = (read_fnt('PRESS.FNT'), read_fnt('PRESSALL.FNT'))
    return ORIG[0].get(code) or ORIG[1].get(code)


_G = None


def hangul_glyph(ch):
    global _G
    if _G is None:
        import bdf
        _G = bdf.Font(GALMURI)
        ys = [y for c in '가각힣맑앙' for x, y in _G.draw(c)[0]]
        _G.top = min(ys)
    pts, w = _G.draw(ch)
    rows = [0] * 12
    for x, y in pts:
        yy = y - _G.top + 1
        assert 0 <= yy < 12 and 0 <= x < 12, ('글자 칸 밖', ch, x, yy)
        rows[yy] |= 0x8000 >> x
    return b''.join(struct.pack('>H', r) for r in rows)


def build(glyphs):
    """glyphs = {SJIS 코드: 24 B} → FNTC 바이트"""
    codes = sorted(glyphs)
    n = len(codes); co = 0x20; go = (co + 2 * n + 3) & ~3
    out = bytearray(go + 24 * n)
    out[0:4] = b'FNTC'
    struct.pack_into('<I', out, 4, len(out))
    struct.pack_into('<IIII', out, 0x10, co, go, n, 0x00010C10)
    for i, c in enumerate(codes):
        struct.pack_into('<H', out, co + 2 * i, c)
        g = glyphs[c]; assert len(g) == 24
        out[go + 24 * i:go + 24 * i + 24] = g
    return bytes(out)


def check_roundtrip():
    """원본 PRESS.FNT 를 build 로 다시 만들면 똑같은지"""
    d = open(os.path.join(FONTDIR, 'PRESS.FNT'), 'rb').read()
    return build(read_fnt('PRESS.FNT')) == d


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('원본 왕복 같음', check_roundtrip())

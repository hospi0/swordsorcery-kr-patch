# -*- coding: utf-8 -*-
r"""상태 창 글자판(STATWIN.TEX 블록 0·1, 160×180 4bpp) 한글화(2026-10-26)
  일본어 글자 자리(사각형)만 지우고(바탕 = 투명 0) Galmuri11 Bold 로 다시 그림 — 테두리 2번 색, 채움은 원본처럼 위→아래 단계색.
  HP·MP·% 는 원본 그대로. 숫자는 게임이 따로 찍음.
  python tools/statwin_kr.py          → work/gfx/statwin/preview_v4.png (원본|한글, 양피지 바탕, 3배)
  python tools/statwin_kr.py --write  → work/build/SSSS/1WINDOW/STATWIN.TEX"""
import os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import bdf, statwin

BOLD = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Bold.bdf'
WHITE = (15, 15, 15, 15, 15, 15, 14, 14, 14, 14, 9, 9, 9)  # 글자 위→아래 줄마다 채움 색(원본 흰 글자: F → E → 9)
GOLD = (15, 15, 13, 13, 13, 13, 10, 10, 10, 6, 6, 6, 6)   # 제목(노란 글자: F → D → A → 6)
# (블록, 지울 사각형 x0 y0 x1 y1, 쓸 x, 글자 윗줄 y, 글, 색)
LAYOUT = [
    (0, (2, 7, 56, 22), 4, 9, '종합 능력', GOLD),
    (0, (2, 22, 44, 35), 5, 23, '레벨', WHITE),
    (0, (2, 61, 44, 74), 5, 62, '공격력', WHITE),
    (0, (2, 74, 44, 88), 5, 76, '파괴력', WHITE),
    (0, (2, 88, 44, 102), 5, 90, '방어력', WHITE),
    (0, (2, 102, 56, 116), 5, 104, '마법력', WHITE),
    (0, (2, 116, 56, 129), 5, 117, '치명타율', WHITE),
    (0, (2, 129, 44, 143), 5, 131, '회피율', WHITE),
    (0, (2, 143, 46, 157), 5, 145, '경험치', WHITE),
    (0, (2, 157, 46, 171), 5, 159, '소지금', WHITE),
    (0, (95, 157, 150, 171), 97, 159, '골드', WHITE),
    (1, (3, 7, 58, 23), 5, 10, '기본 능력', GOLD),
    (1, (3, 23, 34, 37), 6, 25, '완력', WHITE),
    (1, (79, 25, 122, 38), 82, 26, '지혜', WHITE),
    (1, (3, 37, 34, 50), 6, 38, '체력', WHITE),
    (1, (79, 38, 122, 52), 82, 40, '정신력', WHITE),
    (1, (3, 50, 46, 64), 6, 52, '민첩', WHITE),
    (1, (3, 65, 58, 81), 5, 67, '내성 능력', GOLD),
    (1, (3, 80, 34, 92), 6, 81, '독', WHITE),
    (1, (3, 92, 34, 104), 6, 93, '수면', WHITE),
    (1, (3, 104, 34, 120), 6, 105, '마비', WHITE),
    (1, (84, 80, 126, 92), 84, 81, '불꽃', WHITE),
    (1, (84, 92, 126, 104), 84, 93, '얼음', WHITE),
    (1, (84, 104, 126, 116), 84, 105, '땅', WHITE),
    (1, (84, 116, 126, 129), 84, 117, '바람', WHITE),
    (1, (84, 129, 126, 143), 84, 130, '번개', WHITE),
    (1, (2, 143, 46, 157), 5, 145, '경험치', WHITE),
    (1, (2, 157, 46, 171), 5, 159, '소지금', WHITE),
    (1, (95, 157, 150, 171), 97, 159, '골드', WHITE),
]
_F = None


def font():
    global _F
    if _F is None:
        _F = bdf.Font(BOLD)
        ys = [y for c in '가각힣맑앙' for x, y in _F.draw(c)[0]]; _F.top = min(ys)
    return _F


def mask(text):
    """글자 화소 집합 {(x, y)} (y = 0 이 글자 윗줄)"""
    f = font(); pts = set(); x0 = 0
    for ch in text:
        if ch == ' ': x0 += 4; continue
        p, w = f.draw(ch)
        pts |= {(x0 + x, y - f.top) for x, y in p}; x0 += w
    return pts


def apply(k, idx, w, h):
    idx = list(idx)
    for blk, (a, b, c, e), x, y, text, col in LAYOUT:     # 지우기를 먼저 전부(한 줄씩 지우고 그리면 아랫줄 지우기가 윗글자 아래를 자름)
        if blk != k: continue
        for yy in range(b, e):
            for xx in range(a, c): idx[yy * w + xx] = 0
    fills = []
    for blk, (a, b, c, e), x, y, text, col in LAYOUT:
        if blk != k: continue
        m = mask(text)
        assert max(px for px, _ in m) + x + 1 < c or text in ('골드',), ('폭 넘침', text, max(px for px, _ in m) + x)
        for px, py in m:                                    # 테두리(8방향)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + px + dx, y + py + dy)
                    if 0 <= q[0] < w and 0 <= q[1] < h: idx[q[1] * w + q[0]] = 2
        fills.append((m, x, y, col))
    for m, x, y, col in fills:                               # 채움은 테두리를 전부 그린 뒤에(아랫줄 테두리가 윗글자 아랫줄을 덮지 않게)
        for px, py in m:
            idx[(y + py) * w + x + px] = col[min(py, len(col) - 1)]
    return idx


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = open(statwin.SRC, 'rb').read(); out = d
    sheets = []
    for k in (0, 1):
        po, w, h, pal, idx = statwin.read_pp(d, k)
        new = apply(k, idx, w, h)
        out = statwin.write_pp(out, k, new)
        bg = (206, 178, 120)                                   # 양피지 바탕(실기 창 색)
        a = statwin.to_png(w, h, pal, idx, bg); b = statwin.to_png(w, h, pal, new, bg)
        s = Image.new('RGB', (w * 2 + 8, h), (0, 0, 0)); s.paste(a, (0, 0)); s.paste(b, (w + 8, 0)); sheets.append(s)
    W = sheets[0].width; P = Image.new('RGB', (W, sheets[0].height * 2 + 8), (0, 0, 0))
    P.paste(sheets[0], (0, 0)); P.paste(sheets[1], (0, sheets[0].height + 8))
    p = os.path.join(ROOT, 'work', 'gfx', 'statwin', 'preview_v4.png'); P.resize((P.width * 3, P.height * 3), 0).save(p); print(p)
    if '--write' in sys.argv:
        q = os.path.join(ROOT, 'work', 'build', 'SSSS', '1WINDOW'); os.makedirs(q, exist_ok=True)
        open(os.path.join(q, 'STATWIN.TEX'), 'wb').write(out); print('→', os.path.join(q, 'STATWIN.TEX'), len(out), len(d))


if __name__ == '__main__':
    main()

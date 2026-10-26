# -*- coding: utf-8 -*-
r"""번역 넣기(2026-10-26) — data/번역/텍스트_*.tsv(번호·종류·최대바이트·원문·번역·메모·곳) → work/build/<디스크 경로>
  ★규칙은 «쓰는 순간» 막는다: 제어 코드(@V…_ @w1 @n @p … /C0 %d %s \n) 개수·순서가 원문과 다르면 실패 · «기록» 최대바이트 넘으면 실패
    · 문장부호 뒤 공백은 여기서 지움(전프로젝트 규칙).
  글자: 한글 = 번역에 쓰인 것만 SJIS 한자 영역(0x889F~)의 «아무 문자열에도 안 쓰인» 코드에 차례로 배정 → PRESS.FNT 새로(tools/fontkr.py).
        나머지 글자는 cp932 그대로. 새 PRESS.FNT = 최종 문자열에 쓰인 2바이트 글자 전부 + 원본 PRESS 의 가나·기호(0x8140~0x839F, 한자 아님).
  MAP scn: 제자리(새 길이 ≤ 원래 길이, 나머지 NUL) · 넘치면 풀 끝에 붙이고 그 문자열을 가리키는 0x41/0xC7 u16 만 새 위치로. «기록»은 제자리만.
           scn 이 커지면 블록 머리(크기)·scn 머리(LE 크기)·mato 총 크기·끝 오프셋 갱신.
  SSSS.BIN·OPENING.BIN: 제자리 · 넘치면 같은 파일 안 «줄어든 문자열들의 남는 칸»에 넣고 그 BE 포인터(4바이트 정렬)만 · 꼬리 포인터는 부모 따라.
  python tools/insert.py [--test]   (--test = work/build_test 로, 번역 대신 원문의 가나를 한글로 바꾼 시험 번역 + 일부러 길게)"""
import collections, glob, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import extract, fontkr

D = extract.D
OUT = os.path.join(ROOT, 'work', 'build')
TOK = re.compile(r'@[Vv][0-9a-z_]{8}|@[a-zA-Z][0-9a-z]?|/[A-Za-z][0-9]?|%[-0-9]*[dsx]|\\n')   # 음성 = @V + 8자(a004b13_·y02903__·_c000a01) · @ha 처럼 얼굴 번호가 글자인 것도
PUNCT = ',.!?:;)]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜'
HANGUL = re.compile('[가-힣]')


def squeeze(s):
    return re.sub('([' + re.escape(PUNCT) + ']) +', r'\1', s)


def fit(src, dst):
    """문장부호 뒤 공백 지우기 — 단 원문부터 «부호 뒤 공백»이면 그건 채울 칸(장비 «頭:　…» 에 게임이 이름을 써 넣음, 디버그 [GROBAL.   ])
       이라 그대로 둠(지우면 줄이 짧아져 게임이 NUL 을 덮어 다음 줄까지 이어 찍힘). verify.py 도 같은 것을 씀"""
    return dst if re.search('[' + re.escape(PUNCT) + '][ 　]', src) else squeeze(dst)


def load_tr(test=False):
    """{원문: 번역}"""
    tr = {}
    if test:
        rows = []
        for p in sorted(glob.glob(os.path.join(ROOT, 'data', '번역할것', '텍스트_*.tsv'))):
            rows += [l.split('\t') for l in open(p, encoding='utf-8-sig').read().split('\n')[1:] if l.strip()]
        kana = 'ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをん'
        ko = '가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허고노도로모보소오조초코토포호구누두루무부수우주추쿠투푸후그느드르므브스으즈츠크트프흐기니디리미비시이지치키티피히'
        for r in rows:
            src = r[3]; t = ''.join(ko[kana.index(c) % len(ko)] if c in kana else ('카' if '゠' <= c <= 'ヿ' else c) for c in src)
            if r[1] != '기록' and int(r[0]) % 7 == 0 and '@' in t:
                t = t + '시험길게늘인문장'                      # 넘침 경로 시험
            tr[src.replace('\\n', '\n')] = t.replace('\\n', '\n')
        return tr
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', '번역', '텍스트_*.tsv'))):
        for l in open(p, encoding='utf-8-sig').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) > 4 and c[4].strip():
                # ★앞뒤 공백 = 메뉴 정렬 — 지우지 말 것 · 가운뎃점 U+00B7 은 cp932 에 없어 ・ 로
                tr[c[3].replace('\\n', '\n')] = c[4].rstrip('\r').replace('·', '・').replace('\\n', '\n')
    return tr


def toks(t):
    """제어 코드 열 — 글자마다 붙는 효과 코드(@c2 @z6 …)가 이어진 것은 한 번으로(글자 수가 달라 개수는 다름)"""
    out = []
    for k in TOK.findall(t.replace('\n', '\\n')):
        if not (out and out[-1] == k and re.fullmatch(r'@[cz][0-9]', k)):
            out.append(k)
    return out


def check(src, dst, cap=None):
    a = toks(src); b = toks(dst)
    assert a == b, ('제어 코드 다름', src, dst, a, b)


class Enc:
    """한글 → SJIS 코드 배정(최종 문자열에 안 쓰인 한자 코드)"""
    def __init__(self, texts):
        used = set()
        for t in texts:
            for ch in t:
                if not HANGUL.match(ch):
                    try:
                        b = ch.encode('cp932')
                    except UnicodeEncodeError:
                        raise SystemExit('⛔ cp932 로 못 쓰는 글자 %r in %r' % (ch, t))
                    if len(b) == 2: used.add(b[0] << 8 | b[1])
        hs = sorted({ch for t in texts for ch in t if HANGUL.match(ch)})
        free = (c for lead in list(range(0x88, 0xA0)) + list(range(0xE0, 0xEB)) for tr in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD))
                for c in [lead << 8 | tr] if c >= 0x889F and c not in used)
        self.map = {ch: next(free) for ch in hs}
        self.used = used

    def enc(self, t):
        out = bytearray()
        for ch in t:
            if ch in self.map:
                c = self.map[ch]; out += bytes([c >> 8, c & 255])
            else:
                out += ch.encode('cp932')
        return bytes(out)


def do_map(path, tr, enc, stat):
    d = bytearray(open(path, 'rb').read())
    n = struct.unpack_from('>I', d, 8)[0]; off = list(struct.unpack_from('>%dI' % (n + 1), d, 0x10))
    bi = n - 1; b0 = off[bi]; s = bytearray(d[b0 + 8:off[n]])
    assert s[:4] == b'scn\0'
    c0, p0, st = extract.pool(bytes(s)); rf = extract.refs(bytes(s), c0, p0, st)
    size0 = struct.unpack_from('<I', s, 4)[0]; s = s[:size0]
    for o, t in st.items():
        u = extract.dec(t)
        if u is None or u not in tr: continue
        new = enc.enc(tr[u])
        if len(new) <= len(t):
            s[o:o + len(t)] = new + bytes(len(t) - len(new)); stat['제자리'] += 1
        else:
            assert rf[o], ('⛔ 기록 넘침', path, hex(o), u, tr[u], len(new), len(t))
            no = len(s); s += new + b'\0'
            assert no < 0x10000
            for k, op in rf[o]:
                struct.pack_into('<H', s, k + 1, no)
            stat['옮김'] += 1
    struct.pack_into('<I', s, 4, len(s))
    blk = struct.pack('>II', b0 + 8, len(s)) + bytes(s)
    blk += bytes((-len(blk)) % 4)
    d = d[:b0] + blk
    off[n] = len(d)
    struct.pack_into('>%dI' % (n + 1), d, 0x10, *off)
    struct.pack_into('>I', d, 4, len(d))
    return bytes(d)


def do_bin(name, tr, enc, stat, data_from):
    b = bytearray(open(os.path.join(D, name), 'rb').read())
    rows = [r for r in extract.bin_rows(name, data_from)]
    ptrs = collections.defaultdict(list)
    for k in range(0, len(b) - 3, 4):
        v = struct.unpack_from('>I', b, k)[0]
        if extract.BIN_BASE <= v < extract.BIN_BASE + len(b): ptrs[v - extract.BIN_BASE].append(k)
    parents = sorted((int(r['at'], 16), r) for r in rows if r['kind'] == '메뉴')
    tails = [(int(r['at'], 16), r) for r in rows if r['kind'] == '꼬리']
    # ① 덩어리: 사이가 NUL·0xFF 뿐인 연속 문자열 + 뒤 0xFF 채움(★0 은 안 씀 — 살아 있는 변수일 수 있음)
    clusters = []; end = None
    for o, r in parents:
        if clusters and all(x in (0, 0xFF) for x in b[end:o]):
            clusters[-1][1].append((o, r))
        else:
            clusters.append([o, [(o, r)]])
        end = o + r['size'] + 1
    spans = []
    for a, items in clusters:
        z = items[-1][0] + items[-1][1]['size'] + 1
        while z < len(b) and b[z] == 0xFF: z += 1
        spans.append([a, z, items])
    # ② 덩어리마다 원래 차례로 4바이트 정렬해 다시 이어 씀 — 안 들어가는 건 넘침 목록
    moved = {}; over = []; holes = []
    for a, z, items in spans:
        orig = bytes(b[a:z]); b[a:z] = b'\xff' * (z - a); p = a
        for o, r in items:
            new = enc.enc(tr[r['text']]) if r['text'] in tr else orig[o - a:o - a + r['size']]
            if p + len(new) + 1 <= z:
                b[p:p + len(new)] = new; b[p + len(new)] = 0; moved[o] = p
                p = (p + len(new) + 1 + 3) & ~3
            else:
                over.append((o, new))
        if z - p >= 8: holes.append([p, z])
    # ③ 넘친 것은 다른 덩어리 끝 남는 칸에(큰 것부터 best-fit)
    for o, new in sorted(over, key=lambda x: -len(x[1])):
        h = min((h for h in holes if h[1] - h[0] >= len(new) + 1), key=lambda h: h[1] - h[0], default=None)
        assert h, ('⛔ 메뉴 문자열 넘침 — 남는 칸 없음', name, hex(o), len(new))
        p = h[0]; b[p:p + len(new)] = new; b[p + len(new)] = 0; moved[o] = p
        h[0] = (p + len(new) + 1 + 3) & ~3
    for o, p in moved.items():
        for k in ptrs[o]:
            struct.pack_into('>I', b, k, extract.BIN_BASE + p)
    stat['메뉴(다시 이음)'] += len(moved); stat['메뉴 다른 덩어리로'] += len(over)
    for a, z in extract.LISTS.get(name, []):                 # 포인터 없는 목록: 차례 그대로 구역 안에 다시 이어 씀(넘치면 실패)
        items = [r['text'] for r in rows if r['kind'] == '목록' and a <= int(r['at'], 16) < z]
        blob = b''.join(enc.enc(tr.get(t, t)) + b'\0' for t in items)
        assert len(blob) <= z - a, ('⛔ 목록 넘침', name, hex(a), len(blob), z - a)
        b[a:z] = blob + bytes(z - a - len(blob)); stat['목록'] += len(items)
    BT = re.compile(TOK.pattern.encode())
    for o, r in tails:                                       # 꼬리 = 부모 안 «같은 차례의 제어 코드» 자리(/C0休息 → 0休息 · …/n(最大 %6dG… → %6dG…)
        par, pr = max(((p, x) for p, x in parents if p < o), key=lambda t: t[0])
        if par not in moved: continue
        d = o - par; P = enc.enc(pr['text']); Q = enc.enc(tr.get(pr['text'], pr['text']))
        tp = list(BT.finditer(P)); tq = list(BT.finditer(Q))
        i = next(i for i, m in enumerate(tp) if m.start() <= d < max(m.end(), m.start() + 1))
        assert tp[i].group() == tq[i].group(), ('⛔ 꼬리 코드 어긋남', name, hex(o))
        nd = tq[i].start() + (d - tp[i].start())
        for k in ptrs[o]:
            struct.pack_into('>I', b, k, extract.BIN_BASE + moved[par] + nd)
    return bytes(b)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    test = '--test' in sys.argv
    global OUT
    if test: OUT = os.path.join(ROOT, 'work', 'build_test')      # 시험 번역은 빌드 폴더에 안 섞이게
    tr = load_tr(test)
    rows = [r for r in extract.map_rows() + extract.bin_rows() + extract.bin_rows('OPENING.BIN', 0x50000)]
    caps = {}; list_bad = 0
    for r in rows:
        if r['kind'] == '기록': caps[r['text']] = min(caps.get(r['text'], 1 << 30), r['size'])
    for a, z in extract.LISTS.get('SSSS.BIN', []):           # 목록은 «전체 바이트»만 미리 검사
        its = [r['text'] for r in rows if r['kind'] == '목록' and a <= int(r['at'], 16) < z]
        blen = lambda t: sum(2 if HANGUL.match(ch) else len(ch.encode('cp932')) for ch in t)
        tot = sum(blen(squeeze(tr.get(t, t))) + 1 for t in its)
        if tot > z - a: print('⛔ 장비 분류 목록 넘침 %d > %d B — 짧게' % (tot, z - a)); list_bad += 1
    bad = list_bad
    for src, dst in list(tr.items()):
        dst = fit(src, dst)   # 원문부터 «부호 뒤 공백»이면 그건 채울 칸(장비 «頭:　…» 에 게임이 이름을 써 넣음) — 지우면 NUL 이 덮여 다음 줄까지 이어 찍힘
        tr[src] = dst
        try:
            check(src, dst)
        except AssertionError as e:
            print('⛔', e.args[0]); bad += 1
    final = [tr.get(r['text'], r['text']) for r in rows if r['kind'] != '꼬리']
    enc = Enc(final)
    for src, cap in caps.items():
        if src in tr and len(enc.enc(tr[src])) > cap:
            print('⛔ 기록 최대바이트 넘음 %d > %d: %s → %s' % (len(enc.enc(tr[src])), cap, src, tr[src])); bad += 1
    for r in rows:                                           # 아이템·장비 이름표는 «짝수 바이트»(게임이 2바이트 단위로 읽어 홀수면 뒤에 쓰레기 글자 «@» — 2026-10-26 실기)
        if r['file'] == 'SSSS.BIN' and r['kind'] == '메뉴' and 0xC2300 <= int(r['at'], 16) < 0xC29A0 and len(enc.enc(tr.get(r['text'], r['text']))) % 2:
            print('⛔ 아이템 이름 홀수 바이트(공백 하나를 전각으로): %s → %s' % (r['text'], tr.get(r['text']))); bad += 1
    if bad: raise SystemExit('⛔ %d줄 규칙 위반 — 안 넣음' % bad)
    stat = collections.Counter()
    os.makedirs(os.path.join(OUT, 'SSSS', '3MAP'), exist_ok=True); os.makedirs(os.path.join(OUT, 'SSSS', '0FONT'), exist_ok=True)
    grow = 0
    for f in sorted(os.listdir(os.path.join(D, 'SSSS', '3MAP'))):
        if not f.endswith('.MAP'): continue
        p = os.path.join(D, 'SSSS', '3MAP', f); nd = do_map(p, tr, enc, stat)
        grow = max(grow, len(nd) - os.path.getsize(p))
        open(os.path.join(OUT, 'SSSS', '3MAP', f), 'wb').write(nd)
    open(os.path.join(OUT, 'SSSS.BIN'), 'wb').write(do_bin('SSSS.BIN', tr, enc, stat, extract.BIN_DATA))
    open(os.path.join(OUT, 'OPENING.BIN'), 'wb').write(do_bin('OPENING.BIN', tr, enc, stat, 0x50000))
    # 글꼴
    glyphs = {}
    for c in enc.used:
        g = fontkr.orig_glyph(c)
        if g is not None: glyphs[c] = g
    for c, g in fontkr.read_fnt('PRESS.FNT').items():
        if c < 0x889F: glyphs[c] = g                          # 가나·기호·전각 영숫자는 늘 둠
    for ch, c in enc.map.items():
        glyphs[c] = fontkr.hangul_glyph(ch)
    fnt = fontkr.build(glyphs)
    open(os.path.join(OUT, 'SSSS', '0FONT', 'PRESS.FNT'), 'wb').write(fnt)
    # OPENING.BIN 은 PRESSALL.FNT 를 씀 → 같은 배정 코드 자리 글리프만 한글로(크기 그대로)
    pa = fontkr.read_fnt('PRESSALL.FNT')
    for ch, c in enc.map.items():
        assert c in pa, ('PRESSALL 에 없는 코드', hex(c)); pa[c] = fontkr.hangul_glyph(ch)
    pall = fontkr.build(pa); assert len(pall) == os.path.getsize(os.path.join(fontkr.FONTDIR, 'PRESSALL.FNT'))
    open(os.path.join(OUT, 'SSSS', '0FONT', 'PRESSALL.FNT'), 'wb').write(pall)
    if not test:                                             # 상태 창 글자판 그림(2026-10-26 하스피 승인 — tools/statwin_kr.py)
        import statwin, statwin_kr
        d = open(statwin.SRC, 'rb').read(); nd = d
        for k in (0, 1):
            _, w, h, _, idx = statwin.read_pp(d, k); nd = statwin.write_pp(nd, k, statwin_kr.apply(k, idx, w, h))
        os.makedirs(os.path.join(OUT, 'SSSS', '1WINDOW'), exist_ok=True)
        open(os.path.join(OUT, 'SSSS', '1WINDOW', 'STATWIN.TEX'), 'wb').write(nd); assert len(nd) == len(d)
        import title_kr, cv2                                 # 타이틀 «ソード&ソーサリー» → «소드 & 소서리»(2026-10-26 하스피 «완벽해»)
        td, _, _, rgb = title_kr.load()
        q = title_kr.save(td, title_kr.render(cv2.inpaint(rgb, title_kr.text_mask(rgb), 3, cv2.INPAINT_TELEA), title_kr.TEXT)); assert len(q) == len(td)
        os.makedirs(os.path.join(OUT, 'SSSS', '00OPEN'), exist_ok=True)
        open(os.path.join(OUT, 'SSSS', '00OPEN', 'TITLE.DG2'), 'wb').write(q)
    print('넣음 %s · 한글 %d자 · 글꼴 %d칸 %d B(원본 1,248칸 32,480 B) · 맵 최대 증가 %d B' % (dict(stat), len(enc.map), len(glyphs), len(fnt), grow))


if __name__ == '__main__':
    main()

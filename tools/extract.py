# -*- coding: utf-8 -*-
r"""Sword & Sorcery 문자열 추출(2026-10-26) → work/strings.tsv(곳마다 한 줄) + data/번역할것/텍스트_NN.tsv(고유 문자열, 20KB 단위)
  ① 3MAP/NNN.MAP(mato) 의 `scn` 블록: 머리 'scn\0' · u32 LE 크기 · u16 LE 코드 시작 · u16 LE 문자열 풀 시작 — 풀 = NUL 로 끝나는 문자열들.
     코드에서 0x41(푸시)·0xC7(대사 표시?) 다음 u16 LE = 풀 안 문자열 오프셋(scn 머리 기준). 참조 없는 일본어 문자열 = 고정 길이 기록(몬스터 이름 등)
     → 종류 «기록»(넣을 땐 원래 바이트 안에서만).
  ② SSSS.BIN·OPENING.BIN(둘 다 램 0x06018000, /0 이 번갈아 실음): BE u32 절대 포인터가 가리키는 SJIS 문자열(데이터 구역 0xB0000 뒤, 가나·한자 1자 이상, 제어 문자 없음).
  제어 코드: 대사 @w1 @w2 @n @p @c @h1 @f1 @V<번호>_ / SSSS.BIN /C0 /M3 등 — 원문 그대로 두고 번역에도 같은 수로(적재기가 막을 것).
  python tools/extract.py"""
import collections, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
D = os.path.join(ROOT, 'work', 'disc0')
CTRL = re.compile('[' + chr(0) + '-' + chr(9) + chr(11) + '-' + chr(31) + chr(127) + ']')
JP = re.compile(r'[ぁ-んァ-ヶ一-龯ー々]')
BIN_BASE = 0x06018000; BIN_DATA = 0xB0000
LISTS = {'SSSS.BIN': [(0xC1744, 0xC17AD)]}          # (시작, 마지막 NUL 다음 = 0xFF 자리)          # 포인터 없는 «NUL 로 이은 목록»(장비 분류 頭防具…長斧 19개) — 차례로 세어 쓰는 듯, 넣을 땐 구역 안에서 다시 이어 씀


def scn_blocks(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'mato'
    n = struct.unpack_from('>I', d, 8)[0]; off = struct.unpack_from('>%dI' % (n + 1), d, 0x10)
    for i in range(n):
        if d[off[i] + 8:off[i] + 12] == b'scn\0':
            yield i, off[i] + 8, d[off[i] + 8:off[i + 1]]


def pool(s):
    c0, p0 = struct.unpack_from('<HH', s, 8)
    out = {}; o = p0
    while o < len(s):
        e = s.find(b'\0', o); e = len(s) if e < 0 else e
        if e > o: out[o] = s[o:e]
        o = e + 1
    return c0, p0, out


def refs(s, c0, p0, starts):
    r = collections.defaultdict(list)
    for k in range(c0, p0 - 2):
        if s[k] in (0x41, 0xC7):
            v = s[k + 1] | s[k + 2] << 8
            if v in starts: r[v].append((k, s[k]))
    return r


def dec(t):
    try:
        return t.decode('cp932')
    except UnicodeDecodeError:
        return None


def map_rows():
    rows = []
    for f in sorted(os.listdir(os.path.join(D, 'SSSS', '3MAP'))):
        if not f.endswith('.MAP'): continue
        for bi, base, s in scn_blocks(os.path.join(D, 'SSSS', '3MAP', f)):
            c0, p0, st = pool(s); rf = refs(s, c0, p0, st)
            for o, t in st.items():
                u = dec(t)
                if u is None or not JP.search(u): continue
                kind = ('대사' if any(op == 0xC7 for _, op in rf[o]) else '문자') if rf[o] else '기록'
                rows.append(dict(file='SSSS/3MAP/' + f, at='%d:%X' % (bi, o), kind=kind, nref=len(rf[o]), size=len(t), text=u))
    return rows


def bin_rows(name='SSSS.BIN', data_from=BIN_DATA):
    b = open(os.path.join(D, name), 'rb').read()
    ptr = collections.Counter()
    for k in range(0, len(b) - 3, 2):
        v = struct.unpack_from('>I', b, k)[0]
        if BIN_BASE + data_from <= v < BIN_BASE + len(b): ptr[v - BIN_BASE] += 1
    cand = []
    for o in sorted(ptr):
        e = b.find(b'\0', o)
        if e <= o or e - o > 512: continue
        u = dec(b[o:e])
        if u is None or not JP.search(u) or CTRL.search(u): continue
        cand.append((o, e, u))
    rows = []; ends = {}
    for o, e, u in cand:                                    # 꼬리 = 앞 후보 문자열과 같은 NUL 로 끝남(/C0休息 의 0休息) — 번역표엔 안 넣고 넣을 때 부모 따라 옮김
        kind = '꼬리' if e in ends else '메뉴'
        ends.setdefault(e, o)
        rows.append(dict(file=name, at='%X' % o, kind=kind, nref=ptr[o], size=e - o, text=u))
    for a, z in LISTS.get(name, []):
        o = a
        while o < z:
            e = b.find(b'\0', o)
            rows.append(dict(file=name, at='%X' % o, kind='목록', nref=0, size=e - o, text=dec(b[o:e]))); o = e + 1
    return rows


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = map_rows() + bin_rows() + bin_rows('OPENING.BIN', 0x50000)        # OPENING.BIN 도 램 0x06018000(오프닝 때 같은 자리)
    with open(os.path.join(ROOT, 'work', 'strings.tsv'), 'w', encoding='utf-8') as fo:
        fo.write('파일\t위치\t종류\t참조\t바이트\t원문\n')
        for r in rows:
            fo.write('%s\t%s\t%s\t%d\t%d\t%s\n' % (r['file'], r['at'], r['kind'], r['nref'], r['size'], r['text'].replace('\n', '\\n')))
    uniq = collections.OrderedDict()
    for r in rows:
        if r['kind'] == '꼬리': continue
        u = uniq.setdefault(r['text'], dict(kinds=collections.Counter(), locs=[], size=r['size']))
        u['kinds'][r['kind']] += 1; u['locs'].append('%s@%s' % (r['file'].split('/')[-1], r['at']))
    k = collections.Counter(r['kind'] for r in rows)
    print('곳 %d (%s) · 고유 %d 문자열 · %d 자' % (len(rows), dict(k), len(uniq), sum(len(re.sub(r'@V[0-9a-z]+_|@[a-zA-Z][0-9]?|/[A-Z][0-9]', '', t)) for t in uniq)))
    out = os.path.join(ROOT, 'data', '번역할것'); os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.startswith('텍스트_'): os.remove(os.path.join(out, f))
    head = '번호\t종류\t최대바이트\t원문\t번역\t메모\t곳\n'
    part, buf, no = 1, head, 0
    for t, u in uniq.items():
        no += 1
        kind = '/'.join(u['kinds'])
        cap = str(u['size']) if '기록' in u['kinds'] else ('목록' if '목록' in u['kinds'] else '')
        line = '%05d\t%s\t%s\t%s\t\t\t%s\n' % (no, kind, cap, t.replace('\n', '\\n'), ' '.join(u['locs']))
        if len((buf + line).encode('utf-8')) > 20000 and buf != head:
            open(os.path.join(out, '텍스트_%02d.tsv' % part), 'w', encoding='utf-8-sig').write(buf); part += 1; buf = head
        buf += line
    open(os.path.join(out, '텍스트_%02d.tsv' % part), 'w', encoding='utf-8-sig').write(buf)
    print('번역 TSV %d개 → %s' % (part, out))


if __name__ == '__main__':
    main()

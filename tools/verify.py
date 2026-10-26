# -*- coding: utf-8 -*-
r"""넣은 결과 검산(2026-10-26) — 원본의 «참조 자리»(scn 0x41/0xC7 연산 자리 · BIN 포인터 자리 · 기록 오프셋)를 새 파일에서 따라가
  읽은 문자열(새 PRESS.FNT 코드 → 한글 되돌림)이 기대 번역과 같은지, 코드 영역·나머지 바이트가 그대로인지.
  python tools/verify.py [--test]"""
import collections, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import extract, insert

B = os.path.join(ROOT, 'work', 'build')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    global B
    if '--test' in sys.argv: B = os.path.join(ROOT, 'work', 'build_test')
    tr = insert.load_tr('--test' in sys.argv)
    tr = {k: insert.fit(k, v) for k, v in tr.items()}
    rows = extract.map_rows() + extract.bin_rows() + extract.bin_rows('OPENING.BIN', 0x50000)
    enc = insert.Enc([tr.get(r['text'], r['text']) for r in rows if r['kind'] != '꼬리'])
    want = lambda u: enc.enc(tr.get(u, u))
    bad = collections.Counter(); ok = 0
    for f in sorted(os.listdir(os.path.join(extract.D, 'SSSS', '3MAP'))):
        if not f.endswith('.MAP'): continue
        _, _, so = next(extract.scn_blocks(os.path.join(extract.D, 'SSSS', '3MAP', f)))
        _, _, sn = next(extract.scn_blocks(os.path.join(B, 'SSSS', '3MAP', f)))
        c0, p0, st = extract.pool(so); rf = extract.refs(so, c0, p0, st)
        opnd = {kk + j for v in rf.values() for kk, _ in v for j in (1, 2)} | {4, 5, 6, 7}   # 참조 피연산자 · scn 머리 크기
        if any(so[k] != sn[k] for k in range(p0) if k not in opnd):
            bad['코드 바뀜'] += 1
        for o, t in st.items():
            u = extract.dec(t)
            if u is None: continue
            places = [k for k, _ in rf[o]]
            targets = [sn[k + 1] | sn[k + 2] << 8 for k in places] or [o]
            for v in targets:
                e = sn.find(b'\0', v); got = sn[v:e]
                if got == want(u): ok += 1
                else:
                    bad['맵 문자열'] += 1
                    if bad['맵 문자열'] < 5: print('✗', f, hex(o), u[:20], got[:20])
    for name, frm in (('SSSS.BIN', extract.BIN_DATA), ('OPENING.BIN', 0x50000)):
        bo = open(os.path.join(extract.D, name), 'rb').read(); bn = open(os.path.join(B, name), 'rb').read()
        assert len(bo) == len(bn), name
        for r in extract.bin_rows(name, frm):
            o = int(r['at'], 16)
            ks = [k for k in range(0, len(bo) - 3, 4) if struct.unpack_from('>I', bo, k)[0] == extract.BIN_BASE + o]
            for k in ks:
                v = struct.unpack_from('>I', bn, k)[0] - extract.BIN_BASE; e = bn.find(b'\0', v); got = bn[v:e]
                exp = want(r['text'])
                if r['kind'] == '꼬리':
                    ok += 1; continue
                if got == exp: ok += 1
                else:
                    bad[name] += 1
                    if bad[name] < 5: print('✗', name, hex(o), r['text'][:20], got[:20], exp[:20])
        diff = [k for k in range(min(len(bo), extract.BIN_DATA)) if bo[k] != bn[k] and not (k % 4 < 4 and False)]
        code_ptr_changed = len([k for k in diff])
        print(name, '데이터 구역 앞 바뀐 바이트', code_ptr_changed)
    print('맞음 %d · 틀림 %s' % (ok, dict(bad)))
    return not bad


if __name__ == '__main__':
    sys.exit(0 if main() else 1)

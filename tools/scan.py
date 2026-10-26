# -*- coding: utf-8 -*-
r"""SJIS 평문 훑기(2026-10-26) — 파일마다 «가나·한자 2바이트가 4자 이상 이어진» 문자열 수·글자 수.
  python tools/scan.py [파일…]  (없으면 work/disc0 전부, WAV 뺌) → work/scan.tsv"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAT = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e]){4,}')


def strings(d):
    out = []
    for m in PAT.finditer(d):
        s = m.group()
        try:
            t = s.decode('cp932')
        except UnicodeDecodeError:
            continue
        jp = len(re.findall(r'[ぁ-んァ-ヶ一-龯ー、。！？「」]', t))
        if jp >= 4: out.append((m.start(), t))
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    fs = sys.argv[1:] or [os.path.join(dp, f) for dp, _, fn in os.walk(os.path.join(ROOT, 'work', 'disc0')) for f in fn if not f.endswith('.WAV')]
    rows = []
    for p in sorted(fs):
        ss = strings(open(p, 'rb').read())
        if ss: rows.append((os.path.relpath(p, ROOT), len(ss), sum(len(t) for _, t in ss), ss[:3]))
    for r in sorted(rows, key=lambda r: -r[2])[:40]:
        print('%-40s %5d줄 %7d자  %s' % (r[0], r[1], r[2], ' | '.join(t[:25] for _, t in r[3])))
    print('합계', sum(r[1] for r in rows), '줄', sum(r[2] for r in rows), '자')

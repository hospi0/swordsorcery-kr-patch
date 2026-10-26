# -*- coding: utf-8 -*-
r"""번역 일관성 검사 보고(2026-10-26, 드래곤마스터실크 tools/consist.py 를 옮김 — 소드앤소서리: 이름 = «기록»·짧은 «메뉴» 원문, 제어 코드 @…) — data/번역/텍스트_*.tsv (고치지 않음, 보고만)
  ① 이름표: 원문 「 앞 화자 → 번역 화자 대응, 다르게 옮긴 줄
  ② 용어: «기록»(아이템·마법·적 이름) 원문이 다른 줄에 나오는데 그 번역이 없는 줄
         + 가타카나 낱말(3줄 이상)마다 가장 잘 맞는 한글 낱말을 추정해 빠진 줄
  ③ 말투: 화자별 존댓말 비율 + 원문(です·ます)과 번역(요·니다) 높임이 다른 토막
  python tools/consist.py → work/check/consist_{names,terms,tone}.tsv"""
import collections, glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
CHK = os.path.join(ROOT, 'work', 'check')
# 번역 이름표는 «샘의 정령» 처럼 띄어 씀 · 조사·숫자로 끝나는 건 인용(「독」을 · 私は「…」)이지 이름표가 아님
TAG = re.compile(r'(?:^|\\n|\{0B\}|\{07\})([^「」\\{}\s　『（《）》0-9０-９]{1,8}(?: [^「」\\{}\s　『（《）》]{1,6})?)'
                 r'(?<![をにはでがもとへの은는을를에의게상])「')
KATA = re.compile(r'[ァ-ヴ][ァ-ヴー・]+')
HWORD = re.compile(r'[가-힣]+')
JP_POL = re.compile(r'です|ます|でした|ません|ましょう|ください|下さい|でしょう|ませ')
KR_POL = re.compile(r'(?:요|니다|[습입십됩합갑옵봅]니까|세요|십시오|시오|죠)[오옹우~～ー－=＝]*(?=[\s!?.,…~～」』\\♪☆！？。、{]|$)')
NOSP = lambda s: re.sub(r'\s|　|\\n|\{[0-9A-F]{2}\}|@[Vv][0-9a-z_]{8}|@[a-zA-Z][0-9a-z]?|/[A-Za-z][0-9]?', '', s)
# 소드앤소서리(2026-10-26 드래곤마스터실크에서 옮김): 이름 = «기록» + 짧은 «메뉴»(조사·부호·숫자로 안 끝나는 10자 이하)
NAME_OK = lambda r: (r['kind'].startswith('기록') or r['kind'] == '메뉴') and 2 <= len(r['src']) <= 10 \
    and not re.search(r'\\n|\{|@|%|/|[をはがにでのへ。、！？]$|[0-9０-９＋+＜＞（）]', r['src'])


def load():
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', '번역', '텍스트_*.tsv'))):
        for l in open(p, encoding='utf-8-sig').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) >= 5 and c[4].strip():
                rows.append(dict(no=c[0], kind=c[1], src=c[3], dst=c[4], file=os.path.basename(p)))
    return rows


def segs(t):
    """화자 이름표로 토막 → [(화자, 본문)] (이름표 없는 앞부분은 화자 '')"""
    ms = list(TAG.finditer(t)); out = []
    if not ms: return [('', t)]
    if ms[0].start(1) > 0 and t[:ms[0].start()].strip(): out.append(('', t[:ms[0].start()]))
    for i, m in enumerate(ms):
        out.append((m.group(1), t[m.end():ms[i + 1].start() if i + 1 < len(ms) else len(t)]))
    return out


def w(name, head, rows):
    with open(os.path.join(CHK, name), 'w', encoding='utf-8-sig') as f:
        f.write('\t'.join(head) + '\n')
        for r in rows: f.write('\t'.join(str(x) for x in r) + '\n')


def names(rows):
    mp = collections.defaultdict(collections.Counter); where = collections.defaultdict(list)
    for r in rows:
        a, b = [s for s, _ in segs(r['src']) if s], [s for s, _ in segs(r['dst']) if s]
        if len(a) != len(b):
            if a: where[('?', '')].append((r, '이름표 개수 %d→%d' % (len(a), len(b))))
            continue
        for x, y in zip(a, b):
            mp[x][y] += 1; where[(x, y)].append((r, ''))
    out = []; best = {}
    for x, c in sorted(mp.items(), key=lambda kv: -sum(kv[1].values())):
        top = c.most_common(1)[0][0]; best[x] = top
        out.append(('대응', x, ' / '.join('%s×%d' % kv for kv in c.most_common()), '', '', ''))
        for y, n in c.items():
            if y != top:
                for r, _ in where[(x, y)]:
                    out.append(('다름', x, '%s (보통 %s)' % (y, top), r['no'], r['src'], r['dst']))
    for r, why in where[('?', '')]:
        out.append(('개수', '', why, r['no'], r['src'], r['dst']))
    return out, best


def terms(rows, spk):
    out = []
    # ②-가 기록 이름(아이템·마법·적) → 다른 줄에서 같은 번역인지
    rec = collections.defaultdict(collections.Counter)
    for r in rows:
        if NAME_OK(r):
            rec[r['src']][NOSP(r['dst'])] += 1
    for s, c in rec.items():
        if len(c) > 1:
            out.append(('기록 둘 이상', s, ' / '.join('%s×%d' % kv for kv in c.most_common()), '', '', ''))
    recmap = {s: c.most_common(1)[0][0] for s, c in rec.items()}
    for s, k in spk.items():
        if len(s) >= 2: recmap.setdefault(s, NOSP(k))
    keys = sorted(recmap, key=len, reverse=True)
    for r in rows:
        if NAME_OK(r) and r['src'] in recmap: continue
        body_s = TAG.sub('', r['src']); body_d = NOSP(r['dst'])
        for s in keys:
            if s in body_s and recmap[s] and recmap[s] not in body_d:
                # 더 긴 이름 안에 든 짧은 이름은 긴 쪽이 맞으면 넘김
                if any(s != t and s in t and t in body_s and recmap[t] in body_d for t in keys): continue
                out.append(('기록 이름 빠짐', s, recmap[s], r['no'], r['src'], r['dst']))
    # ②-나 가타카나 낱말 → 추정 한글
    lines = [(set(KATA.findall(TAG.sub('', r['src']))), NOSP(TAG.sub('', r['dst'])), r) for r in rows]
    freq = collections.Counter(k for ks, _, _ in lines for k in ks)
    pre_all = collections.Counter()
    for _, d, _ in lines: pre_all.update({p for wd in HWORD.findall(d) for p in pref(wd)})
    for k, n in freq.most_common():
        if n < 3 or k in recmap: continue
        hit = [(d, r) for ks, d, r in lines if k in ks]
        cnt = collections.Counter(p for d, _ in hit for p in {p for wd in HWORD.findall(d) for p in pref(wd)})
        best, sc = None, 0
        for p, m in cnt.items():
            s = m / n - (pre_all[p] - m) / max(1, len(lines) - n) * 5
            if s > sc or (s == sc and best and len(p) > len(best)): best, sc = p, s
        if not best or cnt[best] / n < 0.6: continue
        miss = [(d, r) for d, r in hit if best not in d]
        out.append(('가타카나', k, '%s (%d/%d줄)' % (best, n - len(miss), n), '', '', ''))
        for d, r in miss:
            out.append(('가타카나 빠짐', k, best, r['no'], r['src'], r['dst']))
    return out


def pref(wd):
    return [wd[:i] for i in range(2, len(wd) + 1)]


def tone(rows):
    st = collections.defaultdict(lambda: [0, 0]); out = []; seen = []
    for r in rows:
        a, b = segs(r['src']), segs(r['dst'])
        if len(a) != len(b): continue
        for (x, ja), (y, ko) in zip(a, b):
            if not y or len(NOSP(ko)) < 4: continue
            kp = bool(KR_POL.search(ko)); st[y][kp] += 1
            seen.append((y, kp, r, ja.strip(), ko.strip()))
    # 한쪽 말투가 88% 넘는 화자(8토막 이상)만 «드문 쪽» 줄을 보고 — 세 하녀처럼 상대 따라 섞는 화자는 비율만
    for y, kp, r, ja, ko in seen:
        v = st[y]; tot = sum(v)
        if tot >= 8 and v[kp] / tot < 0.12:
            out.append(('말투 튐', y, '%s (보통 %s)' % ('높임' if kp else '반말', '반말' if kp else '높임'), r['no'], ja, ko))
    head = [('화자', s, '높임 %d / 반말 %d (%.0f%%)' % (v[1], v[0], 100 * v[1] / max(1, sum(v))), '', '', '')
            for s, v in sorted(st.items(), key=lambda kv: -sum(kv[1]))]
    # 호칭: シルク様 → 번역 표기
    ho = collections.Counter(); hl = collections.defaultdict(list)
    for r in rows:
        if 'シルク様' in r['src']:
            for m in re.findall(r'실크\s?(?:님|공주님|공주|씨|사마|양|아가씨)?', r['dst']) or ['(없음)']:
                ho[m] += 1; hl[m].append(r)
    top = ho.most_common(1)[0][0] if ho else ''
    head.append(('호칭', 'シルク様', ' / '.join('%s×%d' % kv for kv in ho.most_common()), '', '', ''))
    for m, L in hl.items():
        if m != top:
            for r in L: head.append(('호칭 다름', 'シルク様', m, r['no'], r['src'], r['dst']))
    return head + out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = load(); H = ('구분', '원문 낱말/화자', '내용', '번호', '원문', '번역')
    n, spk = names(rows); t = terms(rows, spk); o = tone(rows)
    w('consist_names.tsv', H, n); w('consist_terms.tsv', H, t); w('consist_tone.tsv', H, o)
    for nm, L in (('이름표', n), ('용어', t), ('말투', o)):
        print(nm, dict(collections.Counter(x[0] for x in L)))


if __name__ == '__main__':
    main()

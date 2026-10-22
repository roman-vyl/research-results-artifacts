"""Step 5 (owner 16:43): vote schemes on the owner-checked thresholds (pick2.json after override.py, vetos.json).
Per voter strength r = take-rate reduction at its threshold (v1: pooled over its coins; v2/v3: the coin's own r, <=0 -> 0).
Schemes: ladder (V3: 0 at r .095, 1/3 at .32, cap 1/3), ladder1 (same, up to 1 at .55), linear r/.55 (cap 1), quad (r/.55)^2,
count (1 per voter with r > .095, theta = k of N), noisy-OR 1-prod(1-r). Same-indicator variants merged by max. Vetoes always on."""
import json, numpy as np, zc, vote
P2 = json.load(open('/mnt/project-files/ema200_calib/review/calib/pick2.json'))
def lad(r, cap): return 0.0 if r <= 0.095 else min((r - 0.095) / (0.32 - 0.095) / 3, 1 / 3) if r <= 0.32 or cap else min(1 / 3 + (r - 0.32) / (0.55 - 0.32) * 2 / 3, 1.0)
SCH = {'ladder': lambda r: lad(r, True), 'ladder1': lambda r: lad(r, False), 'linear': lambda r: min(max(r, 0) / 0.55, 1), 'quad': lambda r: min(max(r, 0) / 0.55, 1) ** 2,
       'count': lambda r: 1.0 if r > 0.095 else 0.0, 'nor': lambda r: min(max(r, 0), 0.95)}
GRID = {'ladder': [0.2, 0.33, 0.5, 0.67, 0.75, 1.0], 'ladder1': [0.33, 0.5, 0.75, 1.0, 1.5], 'linear': [0.3, 0.5, 0.75, 1.0, 1.5], 'quad': [0.1, 0.2, 0.4, 0.6, 1.0],
        'count': [1, 2, 3, 4], 'nor': [0.3, 0.4, 0.5, 0.6, 0.7]}
def voters(ver, c):
    A = {(r['m'], r['side']): r for r in P2 if r['set'] == 'ALL'}
    if ver == 'v3':
        for r in P2:
            if r['set'] == ('ES' if c != 'btc' else 'BTC'): A[(r['m'], r['side'])] = r
    return [(m, s, r['T'], (r['r'] if ver == 'v1' and r['set'] == 'ALL' else r['at'][c]['r'])) for (m, s), r in A.items()]
def score(ver, c, sch):
    fam = {}
    for m, s, t, r in voters(ver, c):
        w = SCH[sch](r)
        if w <= 0: continue
        f = vote.FAM(m, s); fam[f] = np.maximum(fam.get(f, 0), np.where(vote.hit(c, m, s, t), w, 0))
    n = zc.B[c]['n']
    if not fam: return np.zeros(n)
    if sch == 'nor':
        P = np.ones(n)
        for v in fam.values(): P *= 1 - v
        return 1 - P
    return sum(fam.values())
def veto(c, ver):
    vt = np.zeros(zc.B[c]['n'], bool)
    for r in vote.VETO:
        if r['set'] == 'ALL' or (ver == 'v3' and c != 'btc'): vt |= vote.hit(c, r['m'], r['side'], r['T'])
    return vt
if __name__ == '__main__':
    base = {c: vote.zone_eval(c, None) for c in zc.C}; IDS = {c: zc.sample(c)[0] for c in zc.C}; out = []
    for ver in ('v1', 'v2', 'v3'):
        for sch in SCH:
            for th in GRID[sch]:
                row = dict(ver=ver, sch=sch, th=th)
                for c in zc.C:
                    bl = (score(ver, c, sch) >= th - 1e-9) | veto(c, ver); e = vote.zone_eval(c, bl)
                    row[c] = dict(blk=int(bl[IDS[c]].sum()), net=e['net'], wr=e['wr'], dd=e['dd'], n=e['n'], better=float(np.mean(np.array(e['allnet']) > np.array(base[c]['allnet']))))
                out.append(row)
                print(ver, sch, th, ' | '.join('%s blk %3d net %5.0f WR %.1f DD %.1f' % (c, row[c]['blk'], row[c]['net'], row[c]['wr'], row[c]['dd']) for c in zc.C), flush=True)
    json.dump(dict(base={c: {k: v for k, v in base[c].items() if k != 'allnet'} for c in zc.C}, runs=out), open('/mnt/project-files/ema200_calib/review/calib/vote2.json', 'w'))

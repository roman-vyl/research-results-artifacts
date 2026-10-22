"""Step 3: vote V3-style on zone cells. Voters from pick2.json (ALL = universal, ES = ETH+SOL thresholds), vetoes from pick.json (ALL set).
Weight capped at 1/3 (V3 ceiling); same-indicator variants (V1.x same side, B1 legs) merged by max; block if score >= theta or any veto.
v1: ALL voters, pooled weights. v2: ALL voters, per-coin weights. v3: BTC as v2 + owner's BTC-only thresholds; ETH/SOL: ALL + ES voters (ES threshold where both exist), per-coin weights."""
import json, sys, numpy as np, zc
P2 = json.load(open('/mnt/project-files/ema200_calib/review/calib/pick2.json')); P1 = json.load(open('/mnt/project-files/ema200_calib/review/calib/pick.json'))
FAM = lambda m, side: ('V1' + side) if m in ('v11', 'v12', 'v13', 'v14') else ('B1' if m.startswith('leg_') else m + side)
VETO = json.load(open('/mnt/project-files/ema200_calib/review/calib/vetos.json'))
def voters(ver, c):
    A = {(r['m'], r['side']): r for r in P2 if r['set'] == 'ALL'}
    if ver == 'v3':
        for r in P2:
            if r['set'] == ('ES' if c != 'btc' else 'BTC'): A[(r['m'], r['side'])] = r
    return [(m, s, r['T'], (r['w'] if ver == 'v1' else r['wc'][c])) for (m, s), r in A.items()]
def hit(c, m, s, t):
    x = zc.feat(c, m); return np.isfinite(x) & ((x <= t) if s == 'low' else (x >= t))
def masks(ver, c):
    fam = {}
    for m, s, t, w in voters(ver, c):
        if w <= 0: continue
        f = FAM(m, s); fam[f] = np.maximum(fam.get(f, 0), np.where(hit(c, m, s, t), min(w, 1 / 3), 0))
    sc = sum(fam.values()) if fam else np.zeros(zc.B[c]['n'])
    vt = np.zeros(zc.B[c]['n'], bool)
    for r in VETO:
        if r['set'] == 'ALL' or (ver == 'v3' and c != 'btc'): vt |= hit(c, r['m'], r['side'], r['T'])
    return sc, vt
def zone_eval(c, bl, cells=None):
    cells = zc.B[c]['cells'] if cells is None else cells
    M = [zc.metrics(c, cell, bl) for cell in cells]
    return dict(net=float(np.median([m['net'] for m in M])), wr=float(np.median([m['wr'] for m in M])), dd=float(np.median([m['dd'] for m in M])),
                n=float(np.median([m['n'] for m in M])), R=float(np.median([m['R'] for m in M])), y7=float(np.mean([min(m['ys'][1:]) > 0 for m in M])), allnet=[m['net'] for m in M])
if __name__ == '__main__':
    TH = [0.1, 0.2, 0.3, 0.4, 0.5, 0.67, 0.75, 1.0, 9]
    base = {c: zone_eval(c, None) for c in zc.C}; out = dict(base={c: {k: v for k, v in base[c].items() if k != 'allnet'} for c in zc.C}, runs=[])
    for c in zc.C: print(c, 'BASE net %.0f WR %.1f DD %.1f n %.0f R %.1f' % (base[c]['net'], base[c]['wr'], base[c]['dd'], base[c]['n'], base[c]['R']))
    for ver in ('v1', 'v2', 'v3'):
        for c in zc.C:
            sc, vt = masks(ver, c)
            for th in TH:
                bl = (sc >= th - 1e-9) | vt; e = zone_eval(c, bl)
                better = float(np.mean(np.array(e['allnet']) > np.array(base[c]['allnet'])))
                ids = zc.sample(c)[0]; nb = int(bl[ids].sum())
                out['runs'].append(dict(ver=ver, c=c, th=th, nblk=nb, share=nb / len(ids), better=better, **{k: v for k, v in e.items() if k != 'allnet'}))
                print(ver, c, 'θ', th, 'blk %d (%.0f%%)' % (nb, 100 * nb / len(ids)), 'net %.0f WR %.1f DD %.1f n %.0f R %.1f cells better %.0f%%' % (e['net'], e['wr'], e['dd'], e['n'], e['R'], 100 * better))
    json.dump(out, open('/mnt/project-files/ema200_calib/review/calib/vote.json', 'w'))

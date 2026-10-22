"""Step 2 (owner rule 'universal or at least harms no coin'): start T = mildest grid threshold where
(a) every coin of the set: cut stop share >= its base and saved R over random >= 0 (harms none);
(b) pooled over the set (n-weighted): take-rate reduction r >= 0.095 (ladder weight > 0) at T and at >= 70% of stricter points with n >= 10.
Weight universal = ladder on pooled r (0 at .095, 1/3 at .32); per coin = ladder on that coin's r (coins with r<.095 get 0)."""
import json
d = json.load(open('/mnt/project-files/ema200_calib/review/calib/curves.json')); B = d['base']
def pooled(f, coins, j):
    n = sum(f['a'][c]['pts'][j][0] for c in coins); 
    if n == 0: return 0, None, None
    k = sum(f['a'][c]['pts'][j][1] for c in coins); p0 = sum(B[c] / 100 * d['n'][c] for c in coins) / sum(d['n'][c] for c in coins)
    s = k / n; return n, s, 1 - (1 - s) / (1 - p0)
def rr(c, s): p = B[c] / 100; return 1 - (1 - s / 100) / (1 - p)
def lad(r): return 0.0 if r <= 0.095 else min((r - 0.095) / (0.32 - 0.095) / 3, 1 / 3)
out = []
for f in d['F']:
    for tag, coins in (('ALL', ('btc', 'eth', 'sol')), ('ES', ('eth', 'sol'))):
        G = f['G']; T = None
        for j in range(len(G)):
            if any(f['a'][c]['pts'][j][0] < 3 or f['a'][c]['pts'][j][2] < B[c] or f['a'][c]['pts'][j][3] - f['a'][c]['pts'][j][4] < 0 for c in coins): continue
            n, s, r = pooled(f, coins, j)
            if r < 0.095: continue
            Q = [pooled(f, coins, i)[2] for i in range(j + 1, len(G)) if pooled(f, coins, i)[0] >= 10]
            if Q and sum(q >= 0.095 for q in Q) < 0.7 * len(Q): continue
            T = j; break
        if T is None: continue
        n, s, r = pooled(f, coins, T)
        at = {c: dict(n=f['a'][c]['pts'][T][0], s=f['a'][c]['pts'][T][2], r=round(rr(c, f['a'][c]['pts'][T][2]), 3), ex=round(f['a'][c]['pts'][T][3] - f['a'][c]['pts'][T][4], 1)) for c in B}
        out.append(dict(name=f['name'], m=f['m'], side=f['side'], grp=f['grp'], set=tag, T=G[T], n=n, s=round(100 * s, 1), r=round(r, 3), w=round(lad(r), 3),
                        wc={c: round(lad(at[c]['r']), 3) if c in coins else 0 for c in B}, at=at))
json.dump(out, open('/mnt/project-files/ema200_calib/review/calib/pick2.json', 'w'), indent=0)
for o in out:
    print('%-3s %-7s %-6s %-4s T=%-7s pool n%-3d %5.1f%% r%.2f w%.2f | ' % (o['set'], o['name'], o['m'], o['side'], o['T'], o['n'], o['s'], o['r'], o['w']) +
          ' '.join('%s n%d %s%% ex%+.1f w%.2f' % (c, v['n'], v['s'], v['ex'], o['wc'][c]) for c, v in o['at'].items()))

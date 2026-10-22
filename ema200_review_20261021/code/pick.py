"""Step 2: per filter 'start of good cut' and veto on the zone curves (curves.json).
Ladder per coin by take-rate reduction r = 1-(1-s)/(1-p0): r 0.095 -> weight 0, 0.32 -> 1/3, 0.55 -> veto (owner: 80/85/90% on BTC base ~78%).
Start T: mildest threshold where, for every coin of the set, the cut pool stop share is >= level r 0.095 at T and at >= 70% of the stricter grid points
with n >= 5, and saved R over the random cut >= 0 at T. Veto Tv: mildest threshold where on every coin of the set all points from Tv to the
extreme (n >= 1) have stop share >= level r 0.55 (~89-90%) and each coin cuts >= 1 entry; no minimum n (owner 15:32)."""
import json, sys
d = json.load(open('/mnt/project-files/ema200_calib/review/calib/curves.json')); B = d['base']
def lvl(c, r): p = B[c] / 100; return 100 * (1 - (1 - p) * (1 - r))
def rr(c, s): p = B[c] / 100; return 1 - (1 - s / 100) / (1 - p)
def pick(f, coins):
    G = f['G']; T = None; Tv = None
    for j in range(len(G)):
        ok = True
        for c in coins:
            P = f['a'][c]['pts']
            if P[j][0] < 5 or P[j][3] - P[j][4] < 0: ok = False; break
            if P[j][2] < lvl(c, 0.095): ok = False; break
            Q = [p for p in P[j + 1:] if p[0] >= 5]
            if Q and sum(p[2] >= lvl(c, 0.095) for p in Q) < 0.7 * len(Q): ok = False; break
        if ok: T = j; break
    for j in range(len(G)):
        ok = True
        for c in coins:
            P = f['a'][c]['pts']
            if P[j][0] < 1 or any(p[0] >= 1 and p[2] < lvl(c, 0.55) for p in P[j:]): ok = False; break
        if ok: Tv = j; break
    return T, Tv
res = []
for f in d['F']:
    for tag, coins in (('ALL', ('btc', 'eth', 'sol')), ('ES', ('eth', 'sol'))):
        T, Tv = pick(f, coins)
        r = dict(name=f['name'], m=f['m'], side=f['side'], grp=f['grp'], set=tag)
        if T is not None:
            r['T'] = f['G'][T]; r['at'] = {c: dict(n=f['a'][c]['pts'][T][0], s=f['a'][c]['pts'][T][2], r=round(rr(c, f['a'][c]['pts'][T][2]), 3), ex=round(f['a'][c]['pts'][T][3] - f['a'][c]['pts'][T][4], 1)) for c in d['base']}
        if Tv is not None:
            r['Tv'] = f['G'][Tv]; r['vat'] = {c: dict(n=f['a'][c]['pts'][Tv][0], s=f['a'][c]['pts'][Tv][2]) for c in d['base']}
        res.append(r)
json.dump(res, open('/mnt/project-files/ema200_calib/review/calib/pick.json', 'w'), indent=0)
print('levels', {c: [round(lvl(c, x), 1) for x in (0.095, 0.32, 0.55)] for c in B})
for r in res:
    if 'T' in r or 'Tv' in r:
        s = '%-4s %-7s %-6s %-5s' % (r['set'], r['name'], r['m'], r['side'])
        if 'T' in r: s += ' T=%-7s ' % r['T'] + ' '.join('%s n%d %s%% ex%+.1f' % (c, v['n'], v['s'], v['ex']) for c, v in r['at'].items())
        if 'Tv' in r: s += ' | VETO %s ' % r['Tv'] + ' '.join('%s n%d %s%%' % (c, v['n'], v['s']) for c, v in r['vat'].items())
        print(s)

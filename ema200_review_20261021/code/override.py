"""Owner-set thresholds (by eye on the curves page) override the automatic pick: (m, side, set) -> T. Recomputes weights at T."""
import json
OVR = {('b3h', 'low', 'ES'): 12.8,      # owner 16:28: B3 for ETH+SOL 12.8 (auto 21.4 rejected)
       ('leg_15m', 'high', 'ALL'): 1.37,  # owner 16:30: B1 15m also for BTC, threshold 1.37
       ('m14', 'low', 'ES'): 0.781,       # owner 16:31: MFI14 not below 0.781
       ('c11', 'low', 'ES'): 0.591,       # owner 16:31: C1 c11 further right, ~0.591
       ('a4', 'high', 'ES'): 5.46,        # owner 16:35: A4 for ETH+SOL cut after 5.5
       ('a4', 'high', 'ALL'): 10.3,       # owner 16:35: A4 after 10 also fits BTC
       ('v13', 'low', 'ES'): 0.335,       # owner 16:40: V1.3 ETH+SOL from 0.335
       ('v14', 'low', 'BTC'): 0.136}      # owner 16:42: V1.4 extra BTC-only threshold 0.136 (ETH+SOL keep their own)
DROP = {('r14', 'low', 'ES'), ('v12', 'high', 'ES'), ('a6', 'high', 'ES'), ('c32', 'high', 'ES')}  # 16:32 A6 ETH+SOL veto only; 16:35 C3.2 veto only; 16:36 V1.2 high no correlation             # owner 16:30: r14 pick 'strange' -> removed until he names a threshold
# owner 16:26-16:29 (C3.1, A2.2, D1): where a universal threshold exists, ETH+SOL use it (no separate ES threshold)
d = json.load(open('curves.json')); B = d['base']; P = json.load(open('pick2_raw.json'))
def rr(c, s): p = B[c] / 100; return 1 - (1 - s / 100) / (1 - p)
def lad(r): return 0.0 if r <= 0.095 else min((r - 0.095) / (0.32 - 0.095) / 3, 1 / 3)
for (m, side, tag), T in OVR.items():
    f = [f for f in d['F'] if f['m'] == m and f['side'] == side][0]; j = f['G'].index(T); coins = {'ALL': ('btc', 'eth', 'sol'), 'ES': ('eth', 'sol'), 'BTC': ('btc',)}[tag]
    at = {c: dict(n=f['a'][c]['pts'][j][0], s=f['a'][c]['pts'][j][2], r=round(rr(c, f['a'][c]['pts'][j][2]), 3), ex=round(f['a'][c]['pts'][j][3] - f['a'][c]['pts'][j][4], 1)) for c in B}
    n = sum(at[c]['n'] for c in coins); k = sum(f['a'][c]['pts'][j][1] for c in coins); p0 = sum(B[c] / 100 * d['n'][c] for c in coins) / sum(d['n'][c] for c in coins)
    r = 1 - (1 - k / n) / (1 - p0)
    rec = dict(name=f['name'], m=m, side=side, grp=f['grp'], set=tag, T=T, n=n, s=round(100 * k / n, 1), r=round(r, 3), w=round(lad(r), 3),
               wc={c: round(lad(at[c]['r']), 3) if c in coins else 0 for c in B}, at=at, owner=True)
    P = [p for p in P if not (p['m'] == m and p['side'] == side and p['set'] == tag)] + [rec]; print(rec)
A = {(r['m'], r['side']) for r in P if r['set'] == 'ALL'}
P = [r for r in P if r.get('owner') or not (r['set'] == 'ES' and ((r['m'], r['side']) in A or (r['m'], r['side'], 'ES') in DROP))]
json.dump(P, open('pick2.json', 'w'), indent=0); print(len(P), sorted((r['set'], r['name'], r['T']) for r in P))

# vetoes: automatic (pick.py, all 3 coins) + owner: C3.2 high veto on 3 coins (16:35; mildest point clean on all 3 = 3.43), A6 high veto ETH+SOL only (16:32; 18.7)
P1 = json.load(open('pick.json'))
V = [dict(m=r['m'], side=r['side'], T=r['Tv'], set='ALL') for r in P1 if r['set'] == 'ALL' and 'Tv' in r]
V += [dict(m='c32', side='high', T=3.43, set='ALL', owner=True), dict(m='a6', side='high', T=18.7, set='ES', owner=True)]
json.dump(V, open('vetos.json', 'w'), indent=0); print(V)

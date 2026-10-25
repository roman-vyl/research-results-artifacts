"""Mac: owner 2026-10-25 17:15: checkbox «подтяжка стопа» on the three w8v7 surfaces. New optional dimension trail (column trail, value 1): after entry, once the 1h ADX(14)
has risen >= 1.75 from its value at entry with DI on the trade's side, stop = max(initial SL, best price - 0.25 R); TP kept (scheme chosen 16:40 on BTC W9 LB30).
Rows with trail for every existing variant (no vote / touch / v6 / v7) from trail_<c>.csv (cloud surf/trail: trail_out.py, points_trail.py, rows_trail.py); old rows get
an empty trail cell. runs.csv and manifest.json rewritten IN PLACE (same inode), backups *.pre_trail_<ts>. Usage: python3 add_trail_w8v7.py <analysis dir> <dir with trail_*.csv.gz>"""
import sys, os, csv, json, gzip, shutil, datetime as dt
AN, SRC = sys.argv[1], sys.argv[2]; NOW = dt.datetime.now(dt.timezone.utc); TS = NOW.strftime("%Y%m%dT%H%M%SZ"); T7 = "width_x_untouched_x_stop_x_ratio_x_touch_x_w8v7_6d"
DIM = {"id": "trail", "label": "Подтяжка стопа: ADX 1ч вырос на 1.75 после входа + DI в сторону сделки, стоп 0.25R за лучшей ценой", "column": "trail", "unit": "", "optional": True, "values": [1]}
plan = {}
for c, tk in (("btc", "BTCUSDT.P"), ("eth", "ETHUSDT.P"), ("sol", "SOLUSDT.P")):
    d = f"{AN}/{tk}/ema200/{T7}"; rows = list(csv.reader(open(f"{d}/runs.csv", newline=""))); H = rows[0]; assert "trail" not in H
    ids = {r[0] for r in rows[1:]}; out = [H + ["trail"]] + [r + [""] for r in rows[1:]]; seen = set(); extra = set(); n = 0
    for f in [f"{SRC}/trail_{c}.csv.gz"] + ([f"{SRC}/trail_solwide.csv.gz"] if c == "sol" else []):
        for r in csv.DictReader(gzip.open(f, "rt", newline="")):
            k = r["candidate_id"]
            if k in seen: continue
            assert k[:-3] in ids and k not in ids, k; seen.add(k); extra |= set(r) - set(H) - {"trail"}
            out.append([r.get(h, "") for h in H] + ["1"]); n += 1
    print(c, "old rows", len(rows) - 1, "trail rows", n, "columns not in surface (dropped)", sorted(extra), flush=True)
    plan[c] = (d, out)
for c, (d, out) in plan.items():
    for f in ("runs.csv", "manifest.json"): shutil.copy2(f"{d}/{f}", f"{d}/{f.split('.')[0]}.pre_trail_{TS}.{f.split('.')[1]}")
    fr = f"{d}/runs.csv"; ino = os.stat(fr).st_ino
    with open(fr, "r+", newline="") as fh: fh.seek(0); w = csv.writer(fh, lineterminator="\n"); w.writerows(out); fh.truncate()
    assert os.stat(fr).st_ino == ino
    fm = f"{d}/manifest.json"; ino = os.stat(fm).st_ino; M = json.load(open(fm)); rs = M["result_schema"]; assert not any(x["id"] == "trail" for x in rs["dimensions"])
    rs["dimensions"].append(DIM)
    for v in rs["view"]: v["controls"].append("trail")
    M["row_count"] = len(out) - 1
    M["notes"] += (" | STOP TRAILING (owner 2026-10-25 17:15): optional dimension trail = 1: after entry, when the 1h ADX(14) (closed 1h bars) has risen >= 1.75 from its "
                   "entry value and DI is on the trade's side, stop = max(initial SL, best price since entry - 0.25 R), TP unchanged; decided on bar N, acts from N+1; win = close above +0.01 R. "
                   "Rows for every variant (cloud ema200_calib/review/surf/trail: trail_out.py, points_trail.py, rows_trail.py, add_trail_w8v7.py).")
    M.setdefault("history", []).append({"at": NOW.isoformat(timespec="seconds"), "event": "added stop trailing checkbox (trail rows for every variant)"})
    s = json.dumps(M, indent=2, ensure_ascii=False)
    with open(fm, "r+", encoding="utf-8") as fh: fh.seek(0); fh.write(s); fh.truncate()
    assert os.stat(fm).st_ino == ino; json.load(open(fm))
    chk = list(csv.reader(open(fr, newline=""))); assert len(chk) == len(out) and chk[0][-1] == "trail"
    print(c, "written", len(out) - 1, "rows, size", os.path.getsize(fr), flush=True)

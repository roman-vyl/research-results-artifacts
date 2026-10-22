# Control check of three votes (owner 2026-10-21 19:37 «Запускай»). Fixed BEFORE any computation on the control areas.

Calibration zones (already seen): BTC/ETH/SOL working zones of 2026-10-21 (curves calib/curves.json).
Control areas (never used for picking): SOL W6 (W5-7 x LB230-300, SL6-6.5, TP4-5R), SOL SL6 (SL5.5-6.5 TP4-5R cells,
no-filter net>=4k, DD>=-40%), ETH LB310-500 (all W, SL4.25-5, TP4-5R), BCH and BNB EMA200 (all W x LB, SL4-5, TP4-5R).

Drop rule (calibration zones only): a V2 core voter is dropped if its stop-share trend vs threshold strictness
(rank corr, points with n>=10) is <= -0.3 on at least one of BTC/ETH/SOL zones.
Result: drop B1 1h (SOL -0.63), D1 (SOL -0.62), A2.3 (SOL -0.60), C5 low (SOL -0.38), V1.3 high (BTC -0.47, ETH -0.67).
Keep A1s, A3, A5, C3.1, C1 c11. Vetoes of V2 (A2.3>=.355, C3.1>=.83) unchanged. Weights r_core/.55 and theta 0.4726 unchanged.

Candidates: V2-2 as is; zone vote B; V2-2 trimmed. Reference: no filter.
Winner rule: highest median net over control cells, provided median WR, median DD and share of cells with all years positive
are not worse than the runner-up by more than 1 pp / 3 pp / 10 pp. Each area reported separately plus the count of areas won.

# Review: OpenSpec b1-candle-ratio-v1 and b2-di-wave-v1 (2026-10-12 14:3x)

What was reviewed:
- strategy_engine, branch `claude/a1-band-filter-o4hb54`, tip 0652edc on top of main e00defc; OpenSpec only, no code.
- Checked against the briefs `b1_candle_ratio_task.md` and `b2_di_wave_task.md`, and against the Engine code on main (`predicates.py` `segment_values`, `adx_dmi.py`).
- The research code on the Mac (`b1_values.py`, `b2/`) is NOT readable from this session. The points that depend on it are listed as open questions, not as findings.

## B2.1 / B2.2 (b2-di-wave-v1): ready to code after one check

Matches the brief:
- **Formulas:** B2.1 = segment `origin→peak`, `from_start`, `max`; B2.2 = the same with `mean_per_bar`. Both give `max(D)−D[S*]` and `mean(D)−D[S*]`. Wave n−1 is `touch: previous`, the same episode only, and empty on the first touch.
- **Trade-side DI:** `by_side` = di_plus for long, di_minus for short, not negated. This is correct; negating +DI would be wrong.
- **Denominator:** `right_floor` 1e-6, so zero, negative and tiny previous-wave values give an empty B2 and pass. A numerator ≤ 0 stays a value and is cut. This matches the D7 answers.
- **Cut:** `range` with `min`, `bounds exclusive`, `empty pass` blocks B2 ≤ threshold inclusive, as the brief requires. The high side is not cut (manifest only).
- **Identity:** the new fields enter identities only when set, so A1/A2 are unchanged.
- **Cost:** reuses the A2 sparse table, with no pass over bars added for `previous`.

Findings:
1. **DI smoothing is not addressed (main parity risk).**
   - The research reference uses `ewm(alpha=1/14, adjust=False)` started from the first bar of its data window, with 0/0 → 0.
   - Engine `di_plus/di_minus` uses `wilder_rma` with an SMA bootstrap over the first 14 values, sets the first `period` bars to NaN, and gives 0/0 → NaN.
   - If the reference DI runs over the whole history, the two converge after a few hundred bars, and 1e-9 should hold away from the data start. If the reference recomputes DI on a local window (for example per episode or per entry), Engine's feature will NOT match.
   - The design should state which case holds and what Engine does: reuse the `di_*` feature as is, or add a smoothing option. Settle this in task 0.2 before code, not at parity.
2. **ETH parity is missing from tasks 4.x.** The brief requires `b2_engine_ref_eth.csv.gz` and `b2_parity_eth.json` (both exported); the tasks list BTC only. Add 4.1–4.3 for ETH (W11 / LB 20 / SL 8 / TP 5.5).
3. **Minor: stale context.** It says the reference is "to be exported on the owner's word", but it is already exported for BTC and ETH. The control cells are missing: BTC W7 / LB 20 / SL 7 / TP 5.5 should give 427 trades / $25,760.99 with no filter, 408 / $36,532.39 for B2.1 ≤ 0.7, and 398 / $38,525.90 for B2.2 ≤ 0.8. Add them to 4.3.
4. **Note:** the D7 answer "D[S*] on the S* bar itself" was inferred from the brief, not read from the code. The reference rows carry DI at S* per wave, so task 0.2 can confirm it cheaply.

## B1 (b1-candle-ratio-v1): sound design, blocked on two reference questions

Matches the brief:
- **Operand:** a new `candle` operand, with impulse S*…P and pullback P+1…t (the peak bar belongs to the impulse only).
- **Candles:** assembled from 5m bars inside the leg, on the epoch grid, clipped at the leg edges and at P. The forming candle is taken at t.
- **Direction:** with/against, mirrored on the short side. No candle against the trade gives 0, a valid value that is not blocked. No candle with the trade on the impulse gives a denominator of 0, so the value is missing and the entry passes.
- **Cut:** `range` with `max`, `bounds exclusive` blocks B1 ≥ threshold, as the brief requires.
- **Other:** the parity targets (365 trades / WR 22.47 % / $40,876.40) are copied correctly; no history requirement beyond ATR is added.

Open questions (only the Mac's `b1_values.py` answers them; both are already flagged in design D5/D2 and task 0.2):
1. **D5, which bar ATR is read on.**
   - If both legs divide by ATR_TF at the current bar t, ATR cancels and B1 is a pure body ratio; ATR then only matters during warm-up.
   - If the research divides the impulse by ATR at P and the pullback by ATR at t, the ratio changes. Then the operand needs an "ATR at leg end" option.
   - This decides the wire format, so it must be answered before code.
2. **D2, where the impulse starts:** at S*, or at the lowest low of S*…P as drawn in the almanac picture. Engine defaults to S*, like A1/A2.

## Verdict
- **B2:** approve after findings 1–3 are written into the change. Finding 1 is a check against the reference, not a redesign.
- **B1:** approve the design; code waits for the two answers from `b1_values.py`.
- Both: PR, merge and deploy only on the owner's word.

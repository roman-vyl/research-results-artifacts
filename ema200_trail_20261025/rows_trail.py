"""points_trail_<c>[wide].csv.gz -> trail_<c>[wide].csv: surface rows (column names as the w8v7 runs.csv: rows_w8h.py columns + side columns) with trail = 1,
candidate_id = <same id as the no-trail row>-tr. Usage: rows_trail.py <c> [wide]"""
import sys, json, numpy as np, pandas as pd
c = sys.argv[1]; WIDE = len(sys.argv) > 2; tag = c + ('wide' if WIDE else ''); D = '/mnt/project-files/ema200_calib/'
P = pd.read_csv(D + f'review/surf/trail/points_trail_{tag}.csv.gz')
YRS = sorted({y for s in P.years.values for y in json.loads(s)})
yr = np.array([[json.loads(s).get(y, np.nan) for y in YRS] for s in P.years.values], float)
R = pd.DataFrame({'candidate_id': [f'w{w:02d}-lb{l:03d}-sl{s:g}-r{r_:g}-{k}-tr' for w, l, s, r_, k in zip(P.w, P.lb, P.sl, P.ratio, P.variant)],
                  'min_current_width_atr': P.w, 'untouched_lookback': P.lb, 'sl_atr_multiplier': P.sl, 'tp_sl_ratio': P.ratio, 'tp_atr_multiplier': (P.sl * P.ratio).round(4),
                  'signals': P.signals, 'blocked_share': (1 - P.kept / P.signals).round(4), 'realised_trade_count': P.trades, 'win_rate': P.wr.round(6),
                  'profit_factor': P.pf.round(6), 'cumulative_net_r': P.netR.round(4), 'net_pnl': P.net.round(2), 'return_pct': (P.net / 10000).round(6),
                  'max_drawdown_pct': P.dd.round(6), 'is_net_pnl': P.is_net.round(2), 'oos_net_pnl': P.oos_net.round(2),
                  'years_up': np.nansum(np.round(yr, 4) > 0, 1).astype(int), 'worst_year': np.round(np.nanmin(np.where(np.isnan(yr), 9, yr), 1), 4)})
R.loc[R.worst_year == 9, 'worst_year'] = np.nan
for j, y in enumerate(YRS): R[f'return_{y}'] = np.round(yr[:, j], 4)
R['provenance'] = 'replay'; R['run_id'] = ''
tm = {'': ''} | {f'{p}t{k}': str(k) for p in ('', 'w8g_', 'w8h_') for k in (1, 2, 3)}
R['touch_max'] = P.variant.map(lambda v: v[-1] if '_t' in v or v in ('t1', 't2', 't3') else '')
R['w8_vote'] = np.where(P.variant.str.startswith('w8h'), '7', np.where(P.variant.str.startswith('w8g'), '6', ''))
R['net_pnl_long'] = P.net_long.round(2); R['net_pnl_short'] = P.net_short.round(2); R['net_r_long'] = P.r_long.round(4); R['net_r_short'] = P.r_short.round(4)
R['trades_long'] = P.n_long; R['trades_short'] = P.n_short; R['trail'] = '1'
R = R.replace([np.inf, -np.inf], np.nan); assert R.candidate_id.is_unique
R.to_csv(D + f'review/surf/trail/trail_{tag}.csv', index=False); print(tag, len(R), R.groupby(['w8_vote', 'touch_max']).size().to_dict())

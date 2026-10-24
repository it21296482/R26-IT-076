"""Reproduce publication figures and audit the preserved Component 1 evidence.

No training, price refresh, external inference or modification of source evidence.
Run from the repository checkout; RESEARCH_REPO can override its location.
"""
from pathlib import Path
import hashlib
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = Path(os.getenv('RESEARCH_REPO', HERE.parents[1]))
ROOT = REPO / 'research/component1'
ARCHIVE = ROOT / 'artifacts/component1'
VALIDATION = ROOT / 'artifacts/validation'
FIG = HERE / 'figures'
FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 9, 'axes.labelsize': 9, 'axes.titlesize': 10, 'legend.fontsize': 8,
    'xtick.labelsize': 8, 'ytick.labelsize': 8, 'axes.spines.top': False,
    'axes.spines.right': False, 'pdf.fonttype': 42, 'ps.fonttype': 42,
    'axes.linewidth': .6, 'lines.linewidth': 1.2, 'savefig.bbox': 'tight'})
BLUE, ORANGE, GRAY = '#215985', '#b86316', '#666666'
sources = {}


def csv(path):
    sources[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return pd.read_csv(path)


def js(path):
    sources[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text())


def save(fig, name):
    fig.savefig(FIG / f'{name}.pdf')
    fig.savefig(FIG / f'{name}.png', dpi=220)
    plt.close(fig)


def confusion(y, p):
    return dict(tn=int(((y == 0) & (p == 0)).sum()), fp=int(((y == 0) & (p == 1)).sum()),
                fn=int(((y == 1) & (p == 0)).sum()), tp=int(((y == 1) & (p == 1)).sum()))


tables = csv(VALIDATION / 'forecast_validation_metrics.csv')
intervals = csv(VALIDATION / 'forecast_interval_validation.csv')
endpoints = csv(VALIDATION / 'forecast_endpoint_validation.csv')
audits = {}
for stock in ['JKH', 'BIL']:
    frame = csv(VALIDATION / f'{stock}_forecast_vs_actual.csv')
    assert len(frame) == 57 and frame.date.is_unique
    mapping = {'Ensemble forecast': 'ensemble_predicted_close', 'LSTM scenario': 'scenario_lstm_close',
               'No-change baseline': 'naive_random_walk_close', 'Moving-average drift': 'moving_average_drift_close'}
    for model, column in mapping.items():
        error = frame[column] - frame.close
        record = tables[(tables.stock == stock) & (tables.model == model)].iloc[0]
        assert np.isclose(error.abs().mean(), record.mae_lkr)
        assert np.isclose(np.sqrt((error ** 2).mean()), record.rmse_lkr)
        assert np.isclose((error.abs() / frame.close.abs()).mean() * 100, record.mape_pct)
    for level in [80, 95]:
        observed = ((frame.close >= frame[f'lower_{level}']) & (frame.close <= frame[f'upper_{level}'])).mean() * 100
        width = (frame[f'upper_{level}'] - frame[f'lower_{level}']).mean()
        row = intervals[(intervals.stock == stock) & (intervals.interval == f'{level}%')].iloc[0]
        assert np.isclose(observed, row.coverage_pct) and np.isclose(width, row.mean_width_lkr)

    history = csv(ROOT / f'data/training/{stock}_history_through_2026-05-07.csv')
    test = csv(ARCHIVE / f'{stock.lower()}_test_results.csv')
    split = csv(ARCHIVE / f'{stock.lower()}_anomaly_method_split_metrics.csv')
    dashboard = js(ARCHIVE / f'{stock.lower()}_dashboard_output.json')
    y = test.proxy_anomaly_label.astype(int)
    p = test.final_anomaly_detected.astype(int)
    counts = confusion(y, p)
    stored = split[(split.method == 'LSTM deviation method') & (split.split == 'test')].iloc[0]
    assert all(counts[k] == int(stored[k]) for k in counts)
    assert np.allclose(test.deviation, (test.actual_price - test.predicted_price).abs())
    assert np.allclose(test.liquidity_aware_anomaly_score,
                       test.deviation / (test.volume / 1e6 + 1e-6))

    # Identify the exact archived proxy-label regime, rather than silently
    # attributing old scores to the newer past-only rolling implementation.
    r = history.close.pct_change()
    sigma = r.rolling(20).std()
    volume_ratio = history.volume / history.volume.rolling(20, min_periods=5).mean()
    dates = pd.to_datetime(history.date)
    event = pd.Series(False, index=history.index)
    for first, last in [('2019-04-22', '2019-05-10'), ('2020-03-09', '2020-05-15'), ('2022-03-01', '2022-07-31')]:
        event |= dates.between(first, last)
    retrospective = (event | ((r.abs() > r.abs().quantile(.975)) &
                     ((sigma > sigma.quantile(.9)) | (volume_ratio > volume_ratio.quantile(.9))))).astype(int)
    joined = test[['date', 'proxy_anomaly_label']].merge(
        pd.DataFrame({'date': history.date, 'reconstructed_label': retrospective}), on='date', validate='one_to_one')
    assert (joined.proxy_anomaly_label == joined.reconstructed_label).all()
    liquidity = test.liquidity_anomaly_flag.astype(bool)
    band = test.prediction_band_anomaly_flag.astype(bool)
    assert np.array_equal(p, (liquidity | band).astype(int))
    audits[stock] = {'raw_observations': len(history), 'first_date': history.date.min(),
        'last_date': history.date.max(), 'test_observations': len(test), 'proxy_positives': int(y.sum()),
        'counts': counts, 'liquidity_flags': int(liquidity.sum()), 'band_flags': int(band.sum()),
        'overlap': int((liquidity & band).sum()), 'retrospective_label_match': True,
        'mean_esi': dashboard['esi_mean'], 'windows': dashboard['number_of_windows_used']}

# Fig. 1: architecture and the boundary between measured output and synthesis.
fig, ax = plt.subplots(figsize=(7.1, 2.45))
ax.set(xlim=(0, 10), ylim=(0, 3)); ax.axis('off')
def box(x, y, w, h, label, fill='#f1f5f8'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.025',
                 facecolor=fill, edgecolor='#526574', linewidth=.7))
    ax.text(x + w / 2, y + h / 2, label, ha='center', va='center', fontsize=8.2)
def arrow(start, end):
    ax.annotate('', xy=end, xytext=start, arrowprops={'arrowstyle': '->', 'lw': .8, 'color': '#364858'})
box(.1, 1.6, 1.55, 1.1, 'Dated OHLCV\nQuality checks\nPast-only inputs')
box(2.05, 1.6, 1.75, 1.1, 'Expected close\nLSTM + baselines\nValidation weights')
box(4.2, 1.6, 1.7, 1.1, 'Observed deviation\nScore and bands\nCalibrated OR rule')
box(6.3, 1.6, 1.6, 1.1, 'Surrogate SHAP\nFactor shares\nRolling top-3 ESI')
box(8.3, 1.6, 1.6, 1.1, 'Dated evidence\nValues and ranges\nCautions and source')
for x1, x2 in [(1.65, 2.05), (3.8, 4.2), (5.9, 6.3), (7.9, 8.3)]: arrow((x1, 2.15), (x2, 2.15))
box(4.2, .12, 3.7, .9, 'Other contributions: report interpretation,\nnews/sentiment, external-market risk', '#faf7ef')
box(8.3, .12, 1.6, .9, 'Unified explanation\nfor human review', '#faf7ef')
arrow((7.9, .57), (8.3, .57)); arrow((9.1, 1.6), (9.1, 1.02))
save(fig, 'architecture')

# Fig. 2: mathematical sensitivity, explicitly an illustrative input pair.
fig, ax = plt.subplots(figsize=(3.4, 2.15), layout='constrained')
vol = np.linspace(.5, 10, 400)
ax.plot(vol, 4.2 / (vol + 1e-6), color=BLUE, label='LKR 4.20 gap')
ax.axhline(.961452, color='#333333', ls='--', label='JKH saved threshold')
ax.scatter([2], [4.2 / (2 + 1e-6)], color=BLUE, s=20)
ax.annotate('2 million shares:\nscore 2.10', (2, 2.1), xytext=(3.8, 3.5), fontsize=8,
            arrowprops={'arrowstyle': '->', 'lw': .6})
ax.set(xlabel='Daily trading volume (million shares)', ylabel='Volume-adjusted score', xlim=(.5, 10), ylim=(0, 9))
ax.legend(frameon=False, loc='upper right'); ax.grid(axis='y', alpha=.2)
save(fig, 'score_sensitivity')

# Fig. 3: exact matched-date forecast evaluation. No missing prices are imputed.
fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.5), layout='constrained')
for stock, ax in zip(['JKH', 'BIL'], axes):
    frame = csv(VALIDATION / f'{stock}_forecast_vs_actual.csv')
    date = pd.to_datetime(frame.date)
    ax.fill_between(date, frame.lower_80, frame.upper_80, color=BLUE, alpha=.12)
    ax.plot(date, frame.close, color='black', label='Actual close')
    ax.plot(date, frame.ensemble_predicted_close, color=ORANGE, ls='--', label='Ensemble')
    ax.plot(date, frame.scenario_lstm_close, color=BLUE, ls=':', label='LSTM scenario')
    ax.plot(date, frame.naive_random_walk_close, color=GRAY, ls='-.', label='No-change')
    ax.set(title=stock, ylabel='Closing price (LKR)')
    ax.set_xticks(pd.to_datetime(['2026-05-08', '2026-06-04', '2026-07-02', '2026-07-30']))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    ax.grid(axis='y', alpha=.2)
axes[0].legend(frameon=False, fontsize=7.5, ncol=2, loc='upper left')
save(fig, 'forecast_paths')

# Fig. 4: coverage is paired with width, not presented as calibration alone.
fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.05), layout='constrained')
labels = ['JKH 80%', 'JKH 95%', 'BIL 80%', 'BIL 95%']
colors = [BLUE, BLUE, ORANGE, ORANGE]
for ax, column, title in [(axes[0], 'coverage_pct', 'Empirical coverage (%)'),
                           (axes[1], 'mean_width_lkr', 'Mean interval width (LKR)')]:
    bars = ax.bar(np.arange(4), intervals[column], width=.6, color=colors)
    ax.set_xticks(np.arange(4), labels); ax.set_ylabel(title); ax.grid(axis='y', alpha=.2)
    ax.bar_label(bars, fmt='%.2f', fontsize=8, padding=2)
axes[0].set_ylim(0, 119)
axes[0].plot(range(4), [80, 95, 80, 95], 'k_', markersize=16, label='Nominal level')
axes[0].legend(frameon=False, loc='upper left', fontsize=7)
axes[1].set_ylim(0, 10.4)
save(fig, 'interval_quality')

# Fig. 5: correctly labelled count matrices, not just a headline accuracy.
fig, axes = plt.subplots(1, 2, figsize=(3.4, 1.9), layout='constrained')
for stock, ax in zip(['JKH', 'BIL'], axes):
    c = audits[stock]['counts']
    matrix = np.array([[c['tn'], c['fp']], [c['fn'], c['tp']]])
    ax.imshow(matrix, cmap='Blues', vmin=0, vmax=max(1, matrix.max()))
    for i in range(2):
        for j in range(2):
            label = [['TN', 'FP'], ['FN', 'TP']][i][j]
            ax.text(j, i, f'{label}\n{matrix[i,j]}', ha='center', va='center', fontsize=8,
                    color='white' if matrix[i,j] > matrix.max()/2 else '#111111')
    ax.set_xticks([0, 1], ['Normal', 'Flag']); ax.set_yticks([0, 1], ['Normal', 'Anomaly'])
    ax.set_title(stock); ax.set_xlabel('Prediction')
    ax.tick_params(length=0, labelsize=7)
axes[0].set_ylabel('Proxy label')
save(fig, 'confusion_matrices')

# Fig. 6: local magnitude shares are not global mean SHAP values or causal effects.
fig, ax = plt.subplots(figsize=(3.4, 2.25), layout='constrained')
features = ['volume_ratio_20d', 'return_1d', 'rsi_14', 'atr_14', 'Other factors']
names = ['Volume / 20-day mean', '1-day return', 'RSI (14)', 'ATR (14)', 'Other factors']
ypos = np.arange(len(features))
for stock, shift, color in [('JKH', -.18, BLUE), ('BIL', .18, ORANGE)]:
    values = csv(ARCHIVE / f'{stock.lower()}_top_factors.csv').set_index('feature').contribution
    amounts = [100 * values.get(key, 0) for key in features[:-1]]
    amounts.append(100 * (values.sum() - sum(values.get(key, 0) for key in features[:-1])))
    ax.barh(ypos + shift, amounts, height=.32, color=color, label=stock)
ax.set_yticks(ypos, names); ax.invert_yaxis(); ax.set(xlim=(0, 104), xlabel='Latest-observation |SHAP| share (%)')
ax.legend(frameon=False, loc='lower right'); ax.grid(axis='x', alpha=.2)
save(fig, 'shap_shares')

manifest = {'scope': 'Preserved May-2026 research outputs; not current runtime model accuracy',
            'stocks': audits, 'source_sha256': sources,
            'verification': 'Recomputed forecast errors, interval coverage/width, confusion counts, score formula and full-series proxy labels.'}
(HERE / 'evidence_manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps(audits, indent=2))
print('Verified evidence and produced six PDF/PNG figures.')

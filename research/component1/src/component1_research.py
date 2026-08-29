from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import (
    GradientBoostingClassifier,
    IsolationForest,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    fbeta_score,
    f1_score,
    precision_recall_fscore_support,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    precision_score,
    recall_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from pandas.tseries.offsets import BDay

try:
    import shap
except Exception:  # pragma: no cover - handled via fallback path
    shap = None


EVENT_WINDOWS = [
    {
        "name": "Post Easter attacks repricing",
        "start": "2019-04-22",
        "end": "2019-05-10",
    },
    {
        "name": "COVID-19 market shock",
        "start": "2020-03-09",
        "end": "2020-05-15",
    },
    {
        "name": "Sri Lanka sovereign and liquidity crisis",
        "start": "2022-03-01",
        "end": "2022-07-31",
    },
]


DEFAULT_FEATURE_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "return_1d",
    "log_return_1d",
    "sma_5",
    "sma_10",
    "sma_20",
    "sma_50",
    "ema_12",
    "ema_26",
    "moving_average_gap",
    "volatility_5",
    "volatility_10",
    "volatility_20",
    "momentum_3",
    "momentum_5",
    "momentum_10",
    "range_pct",
    "oc_change",
    "atr_14",
    "rsi_14",
    "volume_5d_ma",
    "volume_20d_ma",
    "volume_ratio_5d",
    "volume_ratio_20d",
]


EXPLAIN_FEATURE_COLUMNS = [
    "volume_ratio_20d",
    "volatility_20",
    "momentum_10",
    "moving_average_gap",
    "return_1d",
    "range_pct",
    "oc_change",
    "rsi_14",
    "atr_14",
]


DIRECTION_FEATURE_COLUMNS = [
    "return_1d",
    "return_3d",
    "return_5d",
    "log_return_1d",
    "volatility_7",
    "volatility_14",
    "volatility_20",
    "ma_5",
    "ma_10",
    "ma_20",
    "ma_50",
    "ma_gap_5_20",
    "ma_gap_10_50",
    "momentum_5",
    "momentum_10",
    "momentum_20",
    "volume_scaled",
    "volume_ratio_20d",
    "relative_volume",
    "range_pct",
    "thin_trading_flag_numeric",
    "liquidity_aware_anomaly_score_lag1",
    "previous_day_direction",
    "previous_3_day_direction_sum",
]


DIRECTION_LABEL_MAP = {
    -1: "Down",
    0: "Neutral",
    1: "Up",
}


OPTIONAL_EXTERNAL_PROXY_COLUMNS = [
    "market_return_proxy",
    "sector_return_proxy",
    "news_sentiment_score",
    "external_pressure_proxy",
]


FEATURE_LABELS = {
    "open": "Open Price",
    "high": "High Price",
    "low": "Low Price",
    "close": "Close Price",
    "volume": "Trading Volume",
    "return_1d": "1D Return",
    "log_return_1d": "Log Return",
    "sma_5": "SMA 5",
    "sma_10": "SMA 10",
    "sma_20": "SMA 20",
    "sma_50": "SMA 50",
    "ema_12": "EMA 12",
    "ema_26": "EMA 26",
    "moving_average_gap": "Moving Average Gap",
    "volatility_5": "Volatility 5D",
    "volatility_10": "Volatility 10D",
    "volatility_20": "Volatility",
    "momentum_3": "Momentum 3D",
    "momentum_5": "Momentum 5D",
    "momentum_10": "Momentum",
    "range_pct": "Intraday Range",
    "oc_change": "Open-Close Change",
    "atr_14": "ATR 14D",
    "rsi_14": "RSI 14D",
    "volume_5d_ma": "Volume MA 5D",
    "volume_20d_ma": "Volume MA 20D",
    "volume_ratio_5d": "Volume Ratio 5D",
    "volume_ratio_20d": "Trading Volume",
}


FORMULA_TEXT = (
    "Deviation = abs(actual_price - predicted_price); "
    "volume_scaled = volume / 1_000_000; "
    "liquidity_aware_anomaly_score = deviation / (volume_scaled + epsilon)"
)

SOURCE_NOTE_TEXT = (
    "The CSV source column indicates tradingview_cselk_fallback, so this is not a pure Ideabeam-only dataset. "
    "Historical OHLCV was recovered through the TradingView CSELK fallback path when the Ideabeam workflow was unavailable."
)

NOVELTY_STATEMENT = (
    "The novelty of Component 1 is not simply stock price prediction. The contribution is an explainable and "
    "liquidity-aware market modeling framework for CSE stocks that combines LSTM-based expected-price modeling, "
    "deviation-based anomaly scoring adjusted by trading volume, separated anomaly/value-signal logic, SHAP-based "
    "surrogate explanation, and ESI-based explanation stability measurement. This makes the output more suitable "
    "for investor-facing interpretation in a low-liquidity emerging-market context."
)


@dataclass
class ResearchConfig:
    stock_code: str = "JKH"
    data_dir: str = "data"
    artifact_dir: str = "artifacts/component1"
    lookback: int = 20
    test_fraction: float = 0.2
    val_fraction: float = 0.1
    epochs: int = 18
    batch_size: int = 32
    hidden_size: int = 32
    num_layers: int = 2
    dropout: float = 0.15
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    random_seed: int = 42
    anomaly_quantile: float = 0.95
    liquidity_epsilon: float = 1e-6
    volume_scale: float = 1_000_000.0
    top_k_explanation: int = 3
    esi_top_k: int = 3
    esi_window: int = 60
    esi_step: int = 20
    isolation_forest_contamination: float = 0.05
    anomaly_search_min_quantile: float = 0.60
    anomaly_search_max_quantile: float = 0.995
    anomaly_search_grid_size: int = 60
    prediction_band_quantile: float = 0.95
    structural_gap_quantile: float = 0.90
    forecast_horizon_days: int = 60
    forecast_interval_z: float = 1.96
    recent_anomaly_window: int = 60
    surrogate_estimators: int = 300
    walk_forward_folds: int = 3
    low_volume_relative_threshold: float = 0.50
    thin_trading_relative_threshold: float = 0.25
    direction_neutral_scale: float = 0.10
    direction_probability_floor: float = 1e-6
    selective_direction_threshold_candidates: tuple[float, ...] = (0.55, 0.60, 0.65, 0.70)
    selective_direction_min_coverage: float = 0.25
    forecast_weight_epsilon: float = 1e-6
    target_price: float | None = None
    shock_pressure_quantile: float = 0.90
    shock_max_penalty_pct: float = 0.15
    shock_penalty_strength: float = 0.10
    shock_reliability_min_score: float = 5.0
    max_rows: int | None = None
    verbose: bool = False


def set_random_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def normalize_stock_code(stock_code: str) -> str:
    code = stock_code.upper().strip()
    if code.endswith(".N0000"):
        return code[:-6]
    return code


def symbol_from_code(stock_code: str) -> str:
    code = stock_code.upper().strip()
    return code if "." in code else f"{code}.N0000"


def csv_path_for_stock(stock_code: str, data_dir: str | Path) -> Path:
    code = normalize_stock_code(stock_code)
    return Path(data_dir) / f"{code}_ideabeam_historical.csv"


def load_stock_history(stock_code: str, data_dir: str | Path = "data") -> pd.DataFrame:
    path = csv_path_for_stock(stock_code, data_dir)
    if not path.exists():
        raise FileNotFoundError(f"Historical CSV not found for {stock_code}: {path}")

    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    df["stock_code"] = normalize_stock_code(stock_code)
    return df


def detect_data_source(raw_df: pd.DataFrame) -> str:
    if "source" not in raw_df.columns:
        return "unknown"
    values = raw_df["source"].dropna().astype(str).unique().tolist()
    if not values:
        return "unknown"
    return ", ".join(sorted(values))


def build_data_source_note(raw_df: pd.DataFrame) -> str:
    data_source = detect_data_source(raw_df)
    if data_source == "tradingview_cselk_fallback":
        return SOURCE_NOTE_TEXT
    if data_source == "unknown":
        return "The CSV does not expose a source column, so the exact upstream history source could not be confirmed from the file alone."
    return f"The CSV source column reports: {data_source}."


def build_data_quality_summary(raw_df: pd.DataFrame) -> pd.DataFrame:
    ohlcv_cols = [col for col in ["open", "high", "low", "close", "volume"] if col in raw_df.columns]
    missing_ohlcv_count = int(raw_df[ohlcv_cols].isna().sum().sum()) if ohlcv_cols else 0
    duplicate_date_count = int(raw_df.duplicated(subset=["date"]).sum()) if "date" in raw_df.columns else 0
    zero_volume_count = (
        int(pd.to_numeric(raw_df["volume"], errors="coerce").fillna(0).eq(0).sum())
        if "volume" in raw_df.columns
        else 0
    )
    summary = pd.DataFrame(
        [
            {
                "stock": normalize_stock_code(str(raw_df["stock_code"].iloc[0])) if "stock_code" in raw_df.columns else "unknown",
                "rows": int(len(raw_df)),
                "start_date": str(pd.Timestamp(raw_df["date"].min()).date()) if "date" in raw_df.columns else "",
                "end_date": str(pd.Timestamp(raw_df["date"].max()).date()) if "date" in raw_df.columns else "",
                "missing_ohlcv_count": missing_ohlcv_count,
                "duplicate_date_count": duplicate_date_count,
                "zero_volume_count": zero_volume_count,
                "data_source": detect_data_source(raw_df),
            }
        ]
    )
    return summary


def build_data_audit(raw_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    raw_cols = set(raw_df.columns)

    def add_row(field: str, stage: str, status: str, note: str) -> None:
        rows.append(
            {
                "field": field,
                "required_for": stage,
                "status": status,
                "note": note,
            }
        )

    raw_requirements = {
        "date": "temporal ordering",
        "open": "market features",
        "high": "market features",
        "low": "market features",
        "close": "market features and prediction target",
        "volume": "liquidity-aware anomaly scoring",
    }
    for field, note in raw_requirements.items():
        add_row(
            field,
            "core_inputs",
            "available_raw" if field in raw_cols else "missing",
            note,
        )

    derived_requirements = {
        "return_1d": "derived from close prices",
        "moving averages": "derived from close prices",
        "volatility": "derived from rolling returns",
        "momentum": "derived from lagged closes",
        "atr_14": "derived from OHLC range",
        "rsi_14": "derived from directional close changes",
        "liquidity ratios": "derived from volume history",
        "lstm_target_close": "next-step close derived by shifting close",
        "proxy_event_labels": "constructed from known CSE stress windows and extreme market realizations",
    }
    for field, note in derived_requirements.items():
        add_row(field, "feature_engineering", "derived", note)

    add_row(
        "ground_truth_anomaly_labels",
        "evaluation",
        "missing_raw",
        "No manually labeled CSE anomaly file is present; proxy event labels will be constructed for research evaluation.",
    )

    return pd.DataFrame(rows)


def engineer_features(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in OPTIONAL_EXTERNAL_PROXY_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["prev_close"] = df["close"].shift(1)
    df["return_1d"] = df["close"].pct_change()
    df["return_3d"] = df["close"] / df["close"].shift(3) - 1.0
    df["return_5d"] = df["close"] / df["close"].shift(5) - 1.0
    df["log_return_1d"] = np.log(df["close"] / df["close"].shift(1))
    df["sma_5"] = df["close"].rolling(5).mean()
    df["sma_10"] = df["close"].rolling(10).mean()
    df["sma_20"] = df["close"].rolling(20).mean()
    df["sma_50"] = df["close"].rolling(50).mean()
    df["ma_5"] = df["sma_5"]
    df["ma_10"] = df["sma_10"]
    df["ma_20"] = df["sma_20"]
    df["ma_50"] = df["sma_50"]
    df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["moving_average_gap"] = df["sma_20"] - df["sma_50"]
    df["ma_gap_5_20"] = (df["ma_5"] - df["ma_20"]) / df["ma_20"].replace(0, np.nan)
    df["ma_gap_10_50"] = (df["ma_10"] - df["ma_50"]) / df["ma_50"].replace(0, np.nan)
    df["volatility_7"] = df["return_1d"].rolling(7).std()
    df["volatility_5"] = df["return_1d"].rolling(5).std()
    df["volatility_10"] = df["return_1d"].rolling(10).std()
    df["volatility_14"] = df["return_1d"].rolling(14).std()
    df["volatility_20"] = df["return_1d"].rolling(20).std()
    df["momentum_3"] = df["close"] / df["close"].shift(3) - 1.0
    df["momentum_5"] = df["close"] / df["close"].shift(5) - 1.0
    df["momentum_10"] = df["close"] / df["close"].shift(10) - 1.0
    df["momentum_20"] = df["close"] / df["close"].shift(20) - 1.0
    df["range_pct"] = (df["high"] - df["low"]) / df["close"].replace(0, np.nan)
    df["oc_change"] = (df["close"] - df["open"]) / df["open"].replace(0, np.nan)

    prev_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr_14"] = true_range.rolling(14).mean()

    delta = df["close"].diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    avg_gain = up.rolling(14).mean()
    avg_loss = down.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi_14"] = 100.0 - (100.0 / (1.0 + rs))

    df["volume_5d_ma"] = df["volume"].rolling(5, min_periods=3).mean()
    df["volume_20d_ma"] = df["volume"].rolling(20, min_periods=5).mean()
    df["rolling_volume_median_20"] = df["volume"].rolling(20, min_periods=5).median()
    df["volume_ratio_5d"] = df["volume"] / df["volume_5d_ma"].replace(0, np.nan)
    df["volume_ratio_20d"] = df["volume"] / df["volume_20d_ma"].replace(0, np.nan)
    df["relative_volume"] = df["volume"] / df["rolling_volume_median_20"].replace(0, np.nan)
    df["volume_scaled"] = df["volume"] / 1_000_000.0
    df["zero_volume_flag"] = df["volume"].fillna(0).eq(0)
    df["low_volume_flag"] = df["relative_volume"].fillna(0.0) < 0.50
    df["thin_trading_flag"] = df["zero_volume_flag"] | (df["relative_volume"].fillna(0.0) < 0.25)
    df["drift_log_return_20_lag1"] = df["log_return_1d"].shift(1).rolling(20, min_periods=5).mean()
    df["drift_pred_close"] = df["prev_close"] * np.exp(df["drift_log_return_20_lag1"].fillna(0.0))

    df["event_window_flag"] = False
    for window in EVENT_WINDOWS:
        start = pd.Timestamp(window["start"])
        end = pd.Timestamp(window["end"])
        df.loc[df["date"].between(start, end), "event_window_flag"] = True

    abs_return = df["return_1d"].abs()
    return_tail = abs_return >= abs_return.quantile(0.975)
    volatility_tail = df["volatility_20"].fillna(0) >= df["volatility_20"].quantile(0.90)
    volume_spike = df["volume_ratio_20d"].fillna(0) >= df["volume_ratio_20d"].quantile(0.90)
    df["proxy_anomaly_label"] = (
        df["event_window_flag"] | (return_tail & (volatility_tail | volume_spike))
    ).astype(int)

    # One-step-ahead prediction is handled by the sequence builder:
    # the model sees the previous `lookback` rows and predicts the current row's close.
    df["target_close"] = df["close"]
    df["target_date"] = df["date"]

    return df


def prepare_model_frame(
    engineered_df: pd.DataFrame,
    feature_columns: list[str] | None = None,
    max_rows: int | None = None,
) -> pd.DataFrame:
    feature_columns = feature_columns or DEFAULT_FEATURE_COLUMNS
    optional_cols = [col for col in OPTIONAL_EXTERNAL_PROXY_COLUMNS if col in engineered_df.columns]
    cols = [
        "date",
        "target_date",
        "target_close",
        "close",
        "prev_close",
        "volume",
        "volume_scaled",
        "rolling_volume_median_20",
        "relative_volume",
        "zero_volume_flag",
        "low_volume_flag",
        "thin_trading_flag",
        "proxy_anomaly_label",
        "return_3d",
        "return_5d",
        "volatility_7",
        "volatility_14",
        "ma_5",
        "ma_10",
        "ma_20",
        "ma_50",
        "ma_gap_5_20",
        "ma_gap_10_50",
        "momentum_20",
        "drift_pred_close",
    ] + optional_cols + feature_columns
    cols = list(dict.fromkeys(cols))
    model_df = engineered_df[cols].copy()
    model_df = model_df.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    if max_rows is not None and len(model_df) > max_rows:
        model_df = model_df.iloc[-max_rows:].reset_index(drop=True)
    return model_df


def split_indices(n_obs: int, test_fraction: float, val_fraction: float) -> tuple[int, int]:
    test_count = max(1, int(n_obs * test_fraction))
    val_count = max(1, int(n_obs * val_fraction))
    train_end = max(1, n_obs - test_count - val_count)
    val_end = max(train_end + 1, n_obs - test_count)
    return train_end, val_end


def create_sequences(
    model_df: pd.DataFrame,
    feature_columns: list[str],
    lookback: int,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    values = model_df[feature_columns].to_numpy(dtype=np.float32)
    targets = model_df["target_close"].to_numpy(dtype=np.float32)

    sequences = []
    y = []
    rows = []
    for target_idx in range(lookback, len(model_df)):
        sequences.append(values[target_idx - lookback : target_idx])
        y.append(targets[target_idx])
        rows.append(model_df.iloc[target_idx].copy())

    seq_array = np.asarray(sequences, dtype=np.float32)
    target_array = np.asarray(y, dtype=np.float32)
    sequence_rows = pd.DataFrame(rows).reset_index(drop=True)
    return seq_array, target_array, sequence_rows


class LSTMRegressor(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, dropout: float) -> None:
        super().__init__()
        lstm_dropout = dropout if num_layers > 1 else 0.0
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=lstm_dropout,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        last_hidden = out[:, -1, :]
        prediction = self.head(last_hidden)
        return prediction.squeeze(-1)


def train_lstm_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    config: ResearchConfig,
) -> tuple[LSTMRegressor, StandardScaler, StandardScaler, dict[str, list[float]]]:
    set_random_seed(config.random_seed)

    feature_scaler = StandardScaler()
    feature_scaler.fit(X_train.reshape(-1, X_train.shape[-1]))

    target_scaler = StandardScaler()
    target_scaler.fit(y_train.reshape(-1, 1))

    def transform_features(array: np.ndarray) -> np.ndarray:
        transformed = feature_scaler.transform(array.reshape(-1, array.shape[-1]))
        return transformed.reshape(array.shape)

    X_train_scaled = transform_features(X_train)
    X_val_scaled = transform_features(X_val)
    y_train_scaled = target_scaler.transform(y_train.reshape(-1, 1)).ravel()
    y_val_scaled = target_scaler.transform(y_val.reshape(-1, 1)).ravel()

    train_loader = DataLoader(
        TensorDataset(
            torch.tensor(X_train_scaled, dtype=torch.float32),
            torch.tensor(y_train_scaled, dtype=torch.float32),
        ),
        batch_size=config.batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        TensorDataset(
            torch.tensor(X_val_scaled, dtype=torch.float32),
            torch.tensor(y_val_scaled, dtype=torch.float32),
        ),
        batch_size=config.batch_size,
        shuffle=False,
    )

    model = LSTMRegressor(
        input_size=X_train.shape[-1],
        hidden_size=config.hidden_size,
        num_layers=config.num_layers,
        dropout=config.dropout,
    )
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    loss_fn = nn.MSELoss()

    history = {"train_loss": [], "val_loss": []}
    best_state: dict[str, Any] | None = None
    best_val = math.inf
    patience = 4
    stale_epochs = 0

    for _epoch in range(config.epochs):
        model.train()
        train_losses = []
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            preds = model(batch_x)
            loss = loss_fn(preds, batch_y)
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.item()))

        model.eval()
        val_losses = []
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                preds = model(batch_x)
                loss = loss_fn(preds, batch_y)
                val_losses.append(float(loss.item()))

        train_loss = float(np.mean(train_losses)) if train_losses else math.nan
        val_loss = float(np.mean(val_losses)) if val_losses else math.nan
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        if val_loss < best_val:
            best_val = val_loss
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            stale_epochs = 0
        else:
            stale_epochs += 1

        if stale_epochs >= patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    return model, feature_scaler, target_scaler, history


def predict_lstm(
    model: LSTMRegressor,
    X: np.ndarray,
    feature_scaler: StandardScaler,
    target_scaler: StandardScaler,
) -> np.ndarray:
    transformed = feature_scaler.transform(X.reshape(-1, X.shape[-1])).reshape(X.shape)
    tensor = torch.tensor(transformed, dtype=torch.float32)
    model.eval()
    with torch.no_grad():
        preds = model(tensor).cpu().numpy()
    return target_scaler.inverse_transform(preds.reshape(-1, 1)).ravel()


def compute_prediction_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    residual = actual - predicted
    mae = mean_absolute_error(actual, predicted)
    rmse = math.sqrt(mean_squared_error(actual, predicted))
    mape = mean_absolute_percentage_error(actual, predicted)
    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "mape": float(mape),
        "mape_pct": float(mape * 100.0),
        "approximate_price_level_accuracy_pct": float(max(0.0, 100.0 - (mape * 100.0))),
        "residual_mean": float(np.mean(residual)) if len(residual) else math.nan,
        "residual_std": float(np.std(residual, ddof=0)) if len(residual) else math.nan,
        "residual_min": float(np.min(residual)) if len(residual) else math.nan,
        "residual_max": float(np.max(residual)) if len(residual) else math.nan,
        "latest_prediction_error": float(residual[-1]) if len(residual) else math.nan,
    }


def compute_directional_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
    prev_close: np.ndarray,
) -> dict[str, Any]:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    prev_close = np.asarray(prev_close, dtype=float)

    mask = np.isfinite(actual) & np.isfinite(predicted) & np.isfinite(prev_close)
    if not np.any(mask):
        return {
            "directional_accuracy": math.nan,
            "up_day_precision": 0.0,
            "up_day_recall": 0.0,
            "down_day_precision": 0.0,
            "down_day_recall": 0.0,
            "direction_confusion_matrix": {"tn": 0, "fp": 0, "fn": 0, "tp": 0},
            "up_day_support": 0,
            "down_day_support": 0,
        }

    actual_up = (actual[mask] > prev_close[mask]).astype(int)
    predicted_up = (predicted[mask] > prev_close[mask]).astype(int)
    confusion = compute_confusion_counts(actual_up, predicted_up)
    tp = confusion["tp"]
    fp = confusion["fp"]
    fn = confusion["fn"]
    tn = confusion["tn"]
    total = tp + fp + fn + tn

    up_precision = tp / (tp + fp) if (tp + fp) else 0.0
    up_recall = tp / (tp + fn) if (tp + fn) else 0.0
    down_precision = tn / (tn + fn) if (tn + fn) else 0.0
    down_recall = tn / (tn + fp) if (tn + fp) else 0.0

    return {
        "directional_accuracy": float((tp + tn) / total) if total else math.nan,
        "up_day_precision": float(up_precision),
        "up_day_recall": float(up_recall),
        "down_day_precision": float(down_precision),
        "down_day_recall": float(down_recall),
        "direction_confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
        "up_day_support": int(tp + fn),
        "down_day_support": int(tn + fp),
    }


def build_lstm_vs_naive_comparison(
    lstm_metrics: dict[str, Any],
    naive_metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "mae_delta": float(lstm_metrics["mae"] - naive_metrics["mae"]),
        "rmse_delta": float(lstm_metrics["rmse"] - naive_metrics["rmse"]),
        "mape_pct_delta": float(lstm_metrics["mape_pct"] - naive_metrics["mape_pct"]),
        "directional_accuracy_delta": float(
            lstm_metrics.get("directional_accuracy", math.nan) - naive_metrics.get("directional_accuracy", math.nan)
        )
        if math.isfinite(float(lstm_metrics.get("directional_accuracy", math.nan)))
        and math.isfinite(float(naive_metrics.get("directional_accuracy", math.nan)))
        else math.nan,
        "beats_naive_on_mae": bool(lstm_metrics["mae"] < naive_metrics["mae"]),
        "beats_naive_on_rmse": bool(lstm_metrics["rmse"] < naive_metrics["rmse"]),
        "beats_naive_on_mape": bool(lstm_metrics["mape"] < naive_metrics["mape"]),
        "beats_naive_on_directional_accuracy": bool(
            lstm_metrics.get("directional_accuracy", -math.inf) > naive_metrics.get("directional_accuracy", -math.inf)
        ),
    }


def classify_direction_target(forward_return: pd.Series, neutral_threshold: pd.Series) -> pd.Series:
    returns = pd.to_numeric(forward_return, errors="coerce").fillna(0.0)
    threshold = pd.to_numeric(neutral_threshold, errors="coerce").fillna(0.0).abs()
    direction = pd.Series(0, index=returns.index, dtype=int)
    direction = direction.mask(returns > threshold, 1)
    direction = direction.mask(returns < (-threshold), -1)
    return direction.astype(int)


def build_direction_dataset(
    combined_results: pd.DataFrame,
    config: ResearchConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = combined_results.sort_values("date").reset_index(drop=True).copy()
    ordered["next_date"] = ordered["date"].shift(-1)
    ordered["next_split"] = ordered["split"].shift(-1)
    ordered["next_actual_price"] = pd.to_numeric(ordered["actual_price"], errors="coerce").shift(-1)
    ordered["forward_return_1d"] = ordered["next_actual_price"] / pd.to_numeric(
        ordered["actual_price"], errors="coerce"
    ) - 1.0
    ordered["neutral_threshold"] = (
        pd.to_numeric(ordered["volatility_20"], errors="coerce").abs().fillna(0.0) * config.direction_neutral_scale
    )
    ordered["direction_target"] = classify_direction_target(
        ordered["forward_return_1d"],
        ordered["neutral_threshold"],
    )
    ordered["binary_direction_target"] = (
        ordered["forward_return_1d"] > 0.0
    ).astype(int)
    ordered["volume_scaled"] = pd.to_numeric(ordered["volume"], errors="coerce").fillna(0.0) / config.volume_scale
    ordered["liquidity_aware_anomaly_score_lag1"] = pd.to_numeric(
        ordered["liquidity_aware_anomaly_score"], errors="coerce"
    ).shift(1)
    ordered["thin_trading_flag_numeric"] = ordered["thin_trading_flag"].astype(int)
    ordered["previous_day_direction"] = classify_direction_target(
        pd.to_numeric(ordered["return_1d"], errors="coerce").fillna(0.0),
        ordered["neutral_threshold"],
    )
    ordered["previous_3_day_direction_sum"] = (
        pd.to_numeric(ordered["previous_day_direction"], errors="coerce").rolling(3, min_periods=1).sum()
    )
    ordered["previous_day_binary_direction"] = (
        pd.to_numeric(ordered["return_1d"], errors="coerce").fillna(0.0) > 0.0
    ).astype(int)

    latest_feature_row = ordered.tail(1).copy()
    direction_df = ordered[
        ordered["next_actual_price"].notna()
        & ordered["split"].eq(ordered["next_split"])
    ].copy()
    direction_df = direction_df.replace([np.inf, -np.inf], np.nan).dropna(
        subset=DIRECTION_FEATURE_COLUMNS + ["direction_target", "binary_direction_target"]
    )
    direction_df = direction_df.reset_index(drop=True)
    return direction_df, latest_feature_row


def _mode_value(values: pd.Series | np.ndarray) -> int:
    series = pd.Series(values).dropna()
    if series.empty:
        return 0
    modes = series.mode()
    if modes.empty:
        return 0
    return int(modes.iloc[0])


def compute_multiclass_direction_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    labels = [-1, 0, 1]
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    precision, recall, f1_vals, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=labels,
        zero_division=0,
    )
    conf = confusion_matrix(y_true, y_pred, labels=labels)
    return {
        "directional_accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "down_precision": float(precision[0]),
        "down_recall": float(recall[0]),
        "neutral_precision": float(precision[1]),
        "neutral_recall": float(recall[1]),
        "up_precision": float(precision[2]),
        "up_recall": float(recall[2]),
        "support_down": int(support[0]),
        "support_neutral": int(support[1]),
        "support_up": int(support[2]),
        "predicted_down_count": int(np.sum(y_pred == -1)),
        "predicted_neutral_count": int(np.sum(y_pred == 0)),
        "predicted_up_count": int(np.sum(y_pred == 1)),
        "direction_confusion_matrix": {
            "labels": ["Down", "Neutral", "Up"],
            "matrix": conf.tolist(),
        },
    }


def compute_binary_direction_classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    confusion = compute_confusion_counts(y_true, y_pred)
    up_precision, up_recall, _, up_support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=[1],
        zero_division=0,
    )
    down_precision, down_recall, _, down_support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=[0],
        zero_division=0,
    )
    return {
        "directional_accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "up_precision": float(up_precision[0]),
        "up_recall": float(up_recall[0]),
        "down_precision": float(down_precision[0]),
        "down_recall": float(down_recall[0]),
        "support_up": int(up_support[0]),
        "support_down": int(down_support[0]),
        "direction_confusion_matrix": {
            "tn": int(confusion["tn"]),
            "fp": int(confusion["fp"]),
            "fn": int(confusion["fn"]),
            "tp": int(confusion["tp"]),
        },
    }


def extract_positive_class_probability(fitted_model: Any, probs: np.ndarray | None, preds: np.ndarray) -> np.ndarray:
    if probs is None:
        return np.full(len(preds), np.nan, dtype=float)
    classes = getattr(fitted_model, "classes_", None)
    if classes is None and hasattr(fitted_model, "steps") and fitted_model.steps:
        classes = getattr(fitted_model.steps[-1][1], "classes_", None)
    if classes is None:
        positive_index = probs.shape[1] - 1
    else:
        classes = np.asarray(classes)
        positive_matches = np.where(classes == 1)[0]
        positive_index = int(positive_matches[0]) if len(positive_matches) else probs.shape[1] - 1
    return np.asarray(probs[:, positive_index], dtype=float)


def extract_binary_prediction_confidence(
    fitted_model: Any,
    probs: np.ndarray | None,
    preds: np.ndarray,
) -> np.ndarray:
    if probs is None:
        return np.full(len(preds), np.nan, dtype=float)
    positive_prob = extract_positive_class_probability(fitted_model, probs, preds)
    pred_array = np.asarray(preds, dtype=int)
    return np.where(pred_array == 1, positive_prob, 1.0 - positive_prob)


def compute_selective_direction_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    confidence: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    confidence = np.asarray(confidence, dtype=float)
    signal_mask = np.isfinite(confidence) & (confidence >= float(threshold))
    signaled_count = int(signal_mask.sum())
    total_count = int(len(y_true))
    coverage_rate = float(signaled_count / total_count) if total_count else 0.0
    no_signal_rate = float(1.0 - coverage_rate)

    if signaled_count == 0:
        return {
            "signal_accuracy": math.nan,
            "signal_balanced_accuracy": math.nan,
            "signal_macro_f1": math.nan,
            "signal_coverage_rate": coverage_rate,
            "no_signal_rate": no_signal_rate,
            "number_of_up_signals": 0,
            "number_of_down_signals": 0,
            "signaled_count": 0,
            "threshold": float(threshold),
        }

    y_true_signal = y_true[signal_mask]
    y_pred_signal = y_pred[signal_mask]
    signal_metrics = compute_binary_direction_classification_metrics(y_true_signal, y_pred_signal)
    return {
        "signal_accuracy": float(signal_metrics["directional_accuracy"]),
        "signal_balanced_accuracy": float(signal_metrics["balanced_accuracy"]),
        "signal_macro_f1": float(signal_metrics["macro_f1"]),
        "signal_coverage_rate": coverage_rate,
        "no_signal_rate": no_signal_rate,
        "number_of_up_signals": int(np.sum(y_pred_signal == 1)),
        "number_of_down_signals": int(np.sum(y_pred_signal == 0)),
        "signaled_count": signaled_count,
        "threshold": float(threshold),
    }


def calibrate_selective_direction_threshold(
    validation_predictions: pd.DataFrame,
    test_predictions: pd.DataFrame,
    config: ResearchConfig,
) -> dict[str, Any]:
    validation_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []
    y_val = validation_predictions["binary_direction_target"].to_numpy(dtype=int)
    pred_val = validation_predictions["binary_direction_pred"].to_numpy(dtype=int)
    conf_val = validation_predictions["binary_direction_confidence"].to_numpy(dtype=float)
    y_test = test_predictions["binary_direction_target"].to_numpy(dtype=int)
    pred_test = test_predictions["binary_direction_pred"].to_numpy(dtype=int)
    conf_test = test_predictions["binary_direction_confidence"].to_numpy(dtype=float)

    for threshold in config.selective_direction_threshold_candidates:
        val_metrics = compute_selective_direction_metrics(y_val, pred_val, conf_val, threshold)
        val_metrics["split"] = "validation"
        validation_rows.append(val_metrics)
        test_metrics = compute_selective_direction_metrics(y_test, pred_test, conf_test, threshold)
        test_metrics["split"] = "test"
        test_rows.append(test_metrics)

    validation_table = pd.DataFrame(validation_rows)
    test_table = pd.DataFrame(test_rows)
    eligible = validation_table[validation_table["signal_coverage_rate"] >= config.selective_direction_min_coverage].copy()
    coverage_constraint_met = not eligible.empty
    ranked_source = eligible if coverage_constraint_met else validation_table
    ranked = ranked_source.sort_values(
        ["signal_macro_f1", "signal_balanced_accuracy", "signal_accuracy", "signal_coverage_rate"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    selected_row = ranked.iloc[0].to_dict()
    selected_threshold = float(selected_row["threshold"])
    selected_test_row = (
        test_table[np.isclose(test_table["threshold"], selected_threshold)].head(1).to_dict(orient="records")
    )
    return {
        "selected_threshold": selected_threshold,
        "selection_split": "validation",
        "selected_threshold_basis": "validation_macro_f1_with_coverage_floor",
        "coverage_floor": float(config.selective_direction_min_coverage),
        "coverage_constraint_met": bool(coverage_constraint_met),
        "validation_threshold_table": validation_table,
        "test_threshold_table": test_table,
        "selected_validation_metrics": selected_row,
        "selected_test_metrics": selected_test_row[0] if selected_test_row else {},
    }


def _fit_direction_model(
    model_name: str,
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    config: ResearchConfig,
    task: str,
) -> Any:
    if model_name == "Logistic Regression baseline":
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=config.random_seed,
            ),
        ).fit(X_train, y_train)
    if model_name == "Random Forest Classifier":
        return RandomForestClassifier(
            n_estimators=200,
            min_samples_leaf=5,
            random_state=config.random_seed,
            class_weight="balanced_subsample",
        ).fit(X_train, y_train)
    if model_name == "Gradient Boosting Classifier":
        return GradientBoostingClassifier(random_state=config.random_seed).fit(X_train, y_train)
    raise ValueError(f"Unsupported direction model: {model_name}")


def _predict_direction_model(
    model_name: str,
    fitted_model: Any,
    X: pd.DataFrame,
    train_target: np.ndarray,
    baseline_values: pd.Series | np.ndarray,
    task: str,
) -> tuple[np.ndarray, np.ndarray | None]:
    if model_name == "Previous-day direction baseline":
        preds = np.asarray(baseline_values, dtype=int)
        class_probs = np.bincount(np.asarray(train_target, dtype=int) + (1 if task == "three_class" else 0))
        if class_probs.sum() == 0:
            return preds, None
        return preds, None
    if model_name == "Majority-class baseline":
        majority = _mode_value(train_target)
        preds = np.repeat(majority, len(X))
        return preds.astype(int), None

    preds = np.asarray(fitted_model.predict(X), dtype=int)
    if hasattr(fitted_model, "predict_proba"):
        try:
            probs = np.asarray(fitted_model.predict_proba(X), dtype=float)
        except Exception:
            probs = None
    else:
        probs = None
    return preds, probs


def summarize_direction_best_model(comparison: pd.DataFrame, task_label: str) -> dict[str, Any]:
    validation = comparison[comparison["split"] == "validation"].copy()
    if validation.empty:
        return {
            "task": task_label,
            "model": "",
            "selection_metric": "macro_f1",
            "summary_text": "No direction-model comparison results were available.",
        }
    ranked = validation.sort_values(
        ["macro_f1", "balanced_accuracy", "directional_accuracy"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    best_name = str(ranked.iloc[0]["model"])
    best_val = ranked.iloc[0].to_dict()
    best_test = (
        comparison[(comparison["split"] == "test") & (comparison["model"] == best_name)]
        .head(1)
        .to_dict(orient="records")
    )
    best_test_row = best_test[0] if best_test else {}
    return {
        "task": task_label,
        "model": best_name,
        "selection_metric": "validation_macro_f1",
        "validation_macro_f1": float(best_val.get("macro_f1", math.nan)),
        "validation_balanced_accuracy": float(best_val.get("balanced_accuracy", math.nan)),
        "test_macro_f1": float(best_test_row.get("macro_f1", math.nan)),
        "test_balanced_accuracy": float(best_test_row.get("balanced_accuracy", math.nan)),
        "test_directional_accuracy": float(best_test_row.get("directional_accuracy", math.nan)),
        "summary_text": (
            f"{best_name} is the best {task_label.replace('_', ' ')} direction model on validation macro F1. "
            "Direction is evaluated as classification quality only, not as a profitable trading claim."
        ),
    }


def run_direction_model_comparison(
    direction_df: pd.DataFrame,
    config: ResearchConfig,
) -> dict[str, Any]:
    train_df = direction_df[direction_df["split"] == "train"].copy()
    val_df = direction_df[direction_df["split"] == "validation"].copy()
    test_df = direction_df[direction_df["split"] == "test"].copy()

    X_train = train_df[DIRECTION_FEATURE_COLUMNS].astype(float)
    X_val = val_df[DIRECTION_FEATURE_COLUMNS].astype(float)
    X_test = test_df[DIRECTION_FEATURE_COLUMNS].astype(float)

    model_names = [
        "Logistic Regression baseline",
        "Random Forest Classifier",
        "Gradient Boosting Classifier",
        "Previous-day direction baseline",
        "Majority-class baseline",
    ]

    multiclass_rows: list[dict[str, Any]] = []
    binary_rows: list[dict[str, Any]] = []
    best_test_prediction_frame: pd.DataFrame | None = None
    best_test_probability: np.ndarray | None = None

    y_train_multi = train_df["direction_target"].to_numpy(dtype=int)
    y_val_multi = val_df["direction_target"].to_numpy(dtype=int)
    y_test_multi = test_df["direction_target"].to_numpy(dtype=int)
    y_train_binary = train_df["binary_direction_target"].to_numpy(dtype=int)
    y_val_binary = val_df["binary_direction_target"].to_numpy(dtype=int)
    y_test_binary = test_df["binary_direction_target"].to_numpy(dtype=int)

    trained_multiclass_models: dict[str, Any] = {}
    trained_binary_models: dict[str, Any] = {}

    for model_name in model_names:
        multi_model = None
        if model_name not in {"Previous-day direction baseline", "Majority-class baseline"}:
            multi_model = _fit_direction_model(model_name, X_train, y_train_multi, config, task="three_class")
        trained_multiclass_models[model_name] = multi_model
        for split_name, split_df, X_split, y_split, baseline_values in (
            ("validation", val_df, X_val, y_val_multi, val_df["previous_day_direction"]),
            ("test", test_df, X_test, y_test_multi, test_df["previous_day_direction"]),
        ):
            preds, probs = _predict_direction_model(
                model_name=model_name,
                fitted_model=multi_model,
                X=X_split,
                train_target=y_train_multi,
                baseline_values=baseline_values,
                task="three_class",
            )
            row = {"model": model_name, "split": split_name}
            row.update(compute_multiclass_direction_metrics(y_split, preds))
            multiclass_rows.append(row)
            if split_name == "test" and best_test_prediction_frame is None:
                pass

        binary_model = None
        if model_name not in {"Previous-day direction baseline", "Majority-class baseline"}:
            binary_model = _fit_direction_model(model_name, X_train, y_train_binary, config, task="binary")
        trained_binary_models[model_name] = binary_model
        for split_name, split_df, X_split, y_split, baseline_values in (
            ("validation", val_df, X_val, y_val_binary, val_df["previous_day_binary_direction"]),
            ("test", test_df, X_test, y_test_binary, test_df["previous_day_binary_direction"]),
        ):
            preds, _ = _predict_direction_model(
                model_name=model_name,
                fitted_model=binary_model,
                X=X_split,
                train_target=y_train_binary,
                baseline_values=baseline_values,
                task="binary",
            )
            row = {"model": model_name, "split": split_name}
            row.update(compute_binary_direction_classification_metrics(y_split, preds))
            binary_rows.append(row)

    multiclass_comparison = pd.DataFrame(multiclass_rows)
    binary_comparison = pd.DataFrame(binary_rows)
    best_multiclass = summarize_direction_best_model(multiclass_comparison, "three_class")
    best_binary = summarize_direction_best_model(binary_comparison, "binary")

    best_model_name = str(best_multiclass["model"])
    best_model = trained_multiclass_models.get(best_model_name)
    test_preds, test_probs = _predict_direction_model(
        model_name=best_model_name,
        fitted_model=best_model,
        X=X_test,
        train_target=y_train_multi,
        baseline_values=test_df["previous_day_direction"],
        task="three_class",
    )
    best_test_prediction_frame = test_df[["date", "split", "direction_target"]].copy()
    best_test_prediction_frame["direction_pred"] = test_preds
    if test_probs is not None and test_probs.ndim == 2:
        best_test_probability = test_probs.max(axis=1)
    else:
        best_test_probability = np.full(len(test_preds), np.nan)
    best_test_prediction_frame["direction_confidence"] = best_test_probability

    best_binary_model_name = str(best_binary["model"])
    best_binary_model = trained_binary_models.get(best_binary_model_name)
    best_binary_val_preds, best_binary_val_probs = _predict_direction_model(
        model_name=best_binary_model_name,
        fitted_model=best_binary_model,
        X=X_val,
        train_target=y_train_binary,
        baseline_values=val_df["previous_day_binary_direction"],
        task="binary",
    )
    best_binary_test_preds, best_binary_test_probs = _predict_direction_model(
        model_name=best_binary_model_name,
        fitted_model=best_binary_model,
        X=X_test,
        train_target=y_train_binary,
        baseline_values=test_df["previous_day_binary_direction"],
        task="binary",
    )
    best_binary_val_confidence = extract_binary_prediction_confidence(
        best_binary_model,
        best_binary_val_probs,
        best_binary_val_preds,
    )
    best_binary_test_confidence = extract_binary_prediction_confidence(
        best_binary_model,
        best_binary_test_probs,
        best_binary_test_preds,
    )
    best_binary_validation_predictions = val_df[
        ["date", "split", "binary_direction_target", "previous_day_binary_direction"]
    ].copy()
    best_binary_validation_predictions["binary_direction_pred"] = best_binary_val_preds
    best_binary_validation_predictions["binary_direction_confidence"] = best_binary_val_confidence
    best_binary_test_predictions = test_df[
        ["date", "split", "binary_direction_target", "previous_day_binary_direction"]
    ].copy()
    best_binary_test_predictions["binary_direction_pred"] = best_binary_test_preds
    best_binary_test_predictions["binary_direction_confidence"] = best_binary_test_confidence

    refit_y = direction_df["direction_target"].to_numpy(dtype=int)
    refit_X = direction_df[DIRECTION_FEATURE_COLUMNS].astype(float)
    latest_model = None
    if best_model_name not in {"Previous-day direction baseline", "Majority-class baseline"}:
        latest_model = _fit_direction_model(best_model_name, refit_X, refit_y, config, task="three_class")

    refit_binary_y = direction_df["binary_direction_target"].to_numpy(dtype=int)
    refit_binary_X = direction_df[DIRECTION_FEATURE_COLUMNS].astype(float)
    refit_latest_binary_model = None
    if best_binary_model_name not in {"Previous-day direction baseline", "Majority-class baseline"}:
        refit_latest_binary_model = _fit_direction_model(
            best_binary_model_name,
            refit_binary_X,
            refit_binary_y,
            config,
            task="binary",
        )

    return {
        "direction_df": direction_df,
        "multiclass_comparison": multiclass_comparison,
        "binary_comparison": binary_comparison,
        "best_multiclass_model": best_multiclass,
        "best_binary_model": best_binary,
        "best_test_predictions": best_test_prediction_frame,
        "best_binary_validation_predictions": best_binary_validation_predictions,
        "best_binary_test_predictions": best_binary_test_predictions,
        "refit_latest_model": latest_model,
        "refit_latest_target": refit_y,
        "refit_latest_binary_model": refit_latest_binary_model,
        "refit_latest_binary_target": refit_binary_y,
    }


def predict_next_day_direction(
    latest_feature_row: pd.DataFrame,
    direction_results: dict[str, Any],
    config: ResearchConfig,
) -> dict[str, Any]:
    latest = latest_feature_row.copy()
    latest["volume_scaled"] = pd.to_numeric(latest["volume_scaled"], errors="coerce").fillna(0.0)
    latest["liquidity_aware_anomaly_score_lag1"] = pd.to_numeric(
        latest["liquidity_aware_anomaly_score_lag1"], errors="coerce"
    )
    latest["thin_trading_flag_numeric"] = latest["thin_trading_flag"].astype(int)
    latest["previous_day_direction"] = pd.to_numeric(latest["previous_day_direction"], errors="coerce")
    latest["previous_3_day_direction_sum"] = pd.to_numeric(
        latest["previous_3_day_direction_sum"], errors="coerce"
    )
    latest = latest.replace([np.inf, -np.inf], np.nan).dropna(subset=DIRECTION_FEATURE_COLUMNS)
    if latest.empty:
        return {
            "direction_label": "Neutral",
            "direction_code": 0,
            "confidence": math.nan,
        }

    best_model_name = str(direction_results["best_multiclass_model"]["model"])
    refit_model = direction_results["refit_latest_model"]
    X_latest = latest[DIRECTION_FEATURE_COLUMNS].astype(float)

    if best_model_name == "Previous-day direction baseline":
        pred_code = int(latest.iloc[-1]["previous_day_direction"])
        confidence = float(
            pd.Series(direction_results["refit_latest_target"]).value_counts(normalize=True).get(pred_code, 0.0)
        )
    elif best_model_name == "Majority-class baseline":
        pred_code = _mode_value(direction_results["refit_latest_target"])
        confidence = float(
            pd.Series(direction_results["refit_latest_target"]).value_counts(normalize=True).get(pred_code, 0.0)
        )
    else:
        pred_code = int(refit_model.predict(X_latest)[0])
        if hasattr(refit_model, "predict_proba"):
            try:
                confidence = float(np.max(refit_model.predict_proba(X_latest)[0]))
            except Exception:
                confidence = math.nan
        else:
            confidence = math.nan

    return {
        "direction_label": DIRECTION_LABEL_MAP.get(pred_code, "Neutral"),
        "direction_code": pred_code,
        "confidence": confidence,
    }


def predict_next_day_selective_direction_signal(
    latest_feature_row: pd.DataFrame,
    direction_results: dict[str, Any],
    selective_threshold: float,
    config: ResearchConfig,
) -> dict[str, Any]:
    latest = latest_feature_row.copy()
    latest["volume_scaled"] = pd.to_numeric(latest["volume_scaled"], errors="coerce").fillna(0.0)
    latest["liquidity_aware_anomaly_score_lag1"] = pd.to_numeric(
        latest["liquidity_aware_anomaly_score_lag1"], errors="coerce"
    )
    latest["thin_trading_flag_numeric"] = latest["thin_trading_flag"].astype(int)
    latest["previous_day_direction"] = pd.to_numeric(latest["previous_day_direction"], errors="coerce")
    latest["previous_3_day_direction_sum"] = pd.to_numeric(
        latest["previous_3_day_direction_sum"], errors="coerce"
    )
    latest["previous_day_binary_direction"] = pd.to_numeric(
        latest["previous_day_binary_direction"], errors="coerce"
    )
    latest = latest.replace([np.inf, -np.inf], np.nan).dropna(subset=DIRECTION_FEATURE_COLUMNS)
    if latest.empty:
        return {
            "signal_label": "No Signal",
            "signal_code": None,
            "confidence": math.nan,
        }

    best_binary_model_name = str(direction_results["best_binary_model"]["model"])
    refit_binary_model = direction_results["refit_latest_binary_model"]
    X_latest = latest[DIRECTION_FEATURE_COLUMNS].astype(float)

    preds, probs = _predict_direction_model(
        model_name=best_binary_model_name,
        fitted_model=refit_binary_model,
        X=X_latest,
        train_target=direction_results["refit_latest_binary_target"],
        baseline_values=latest["previous_day_binary_direction"],
        task="binary",
    )
    confidence = float(extract_binary_prediction_confidence(refit_binary_model, probs, preds)[0])
    pred_code = int(preds[0])
    if not math.isfinite(confidence) or confidence < float(selective_threshold):
        return {
            "signal_label": "No Signal",
            "signal_code": None,
            "confidence": confidence,
        }
    return {
        "signal_label": "Up" if pred_code == 1 else "Down",
        "signal_code": pred_code,
        "confidence": confidence,
    }


def build_lightweight_walk_forward_summary(
    results_frame: pd.DataFrame,
    fold_count: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = results_frame.sort_values("date").reset_index(drop=True).copy()
    index_splits = [idx for idx in np.array_split(np.arange(len(ordered)), max(1, fold_count)) if len(idx) > 0]
    fold_rows: list[dict[str, Any]] = []

    for fold_number, idx in enumerate(index_splits, start=1):
        fold = ordered.iloc[idx].copy()
        fold_start = str(pd.Timestamp(fold["date"].min()).date())
        fold_end = str(pd.Timestamp(fold["date"].max()).date())
        for model_name, pred_col in (
            ("LSTM expected-price baseline", "predicted_price"),
            ("Naive previous-close baseline", "naive_baseline_predicted_price"),
        ):
            metrics = compute_prediction_metrics(
                fold["actual_price"].to_numpy(dtype=float),
                fold[pred_col].to_numpy(dtype=float),
            )
            directional = compute_directional_metrics(
                fold["actual_price"].to_numpy(dtype=float),
                fold[pred_col].to_numpy(dtype=float),
                fold["prev_close"].to_numpy(dtype=float),
            )
            fold_rows.append(
                {
                    "fold": fold_number,
                    "model": model_name,
                    "start_date": fold_start,
                    "end_date": fold_end,
                    "rows": int(len(fold)),
                    "mae": float(metrics["mae"]),
                    "rmse": float(metrics["rmse"]),
                    "mape": float(metrics["mape"]),
                    "mape_pct": float(metrics["mape_pct"]),
                    "directional_accuracy": float(directional["directional_accuracy"]),
                }
            )

    fold_df = pd.DataFrame(fold_rows)
    aggregate = (
        fold_df.groupby("model")[["mae", "rmse", "mape", "mape_pct", "directional_accuracy"]]
        .agg(["mean", "std"])
        .reset_index()
    )
    aggregate.columns = [
        "_".join(col).strip("_") if isinstance(col, tuple) else str(col) for col in aggregate.columns.to_flat_index()
    ]
    return fold_df, aggregate


def compute_classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "predicted_positive_rate": float(np.mean(y_pred)) if len(y_pred) else 0.0,
    }


def compute_confusion_counts(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, int]:
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    return {
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "support_positive": int(tp + fn),
        "support_negative": int(tn + fp),
        "predicted_positive_count": int(tp + fp),
    }


def _native_records(frame: pd.DataFrame, float_digits: int = 6) -> list[dict[str, Any]]:
    safe = frame.copy()
    float_cols = safe.select_dtypes(include=["float32", "float64"]).columns.tolist()
    if float_cols:
        safe[float_cols] = safe[float_cols].round(float_digits)
    return json.loads(safe.to_json(orient="records"))


def _join_labels(labels: list[str]) -> str:
    labels = [str(label) for label in labels]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def summarize_best_anomaly_method(
    comparison: pd.DataFrame,
    test_support_positive: int,
) -> dict[str, Any]:
    if comparison.empty:
        return {
            "metric": "f1_score",
            "f1_score": math.nan,
            "method_list": [],
            "method_text": "",
            "tie": False,
            "summary_text": "No anomaly comparison results were available.",
        }

    max_f1 = float(comparison["f1_score"].max())
    best_rows = comparison[np.isclose(comparison["f1_score"], max_f1)].copy().reset_index(drop=True)
    method_list = best_rows["method"].astype(str).tolist()
    method_text = _join_labels(method_list)
    tie = len(method_list) > 1

    if tie and test_support_positive <= 2:
        summary_text = (
            f"{method_text} tie by test F1, but the result is based on only "
            f"{test_support_positive} proxy-positive anomaly cases."
        )
    elif tie:
        summary_text = f"{method_text} tie by test F1 score {max_f1:.4f}."
    else:
        summary_text = f"{method_text} is the best-performing anomaly method on the test split with F1 score {max_f1:.4f}."

    representative = best_rows.iloc[0].to_dict()
    return {
        "metric": "f1_score",
        "f1_score": round(max_f1, 6),
        "method_list": method_list,
        "method_text": method_text,
        "tie": tie,
        "support_positive": int(test_support_positive),
        "summary_text": summary_text,
        "records": _native_records(best_rows),
        "representative_method": str(representative["method"]),
    }


def build_support_warning(test_support_positive: int) -> str:
    if test_support_positive <= 2:
        return (
            f"The test split contains only {test_support_positive} proxy-positive anomaly cases, "
            "so anomaly F1 estimates should be interpreted cautiously."
        )
    if test_support_positive <= 10:
        return (
            f"The test split contains only {test_support_positive} proxy-positive anomaly cases, "
            "so anomaly metrics remain sensitive to a small number of events."
        )
    return ""


def compute_fbeta_metric(y_true: np.ndarray, y_pred: np.ndarray, beta: float = 0.5) -> float:
    return float(fbeta_score(y_true, y_pred, beta=beta, zero_division=0))


def add_anomaly_columns(
    frame: pd.DataFrame,
    volume_scale: float,
    epsilon: float,
    downside_band: float | None = None,
    upside_band: float | None = None,
    structural_gap_threshold_pct: float = 0.0,
    liquidity_threshold: float | None = None,
    prediction_band_threshold: float | None = None,
) -> pd.DataFrame:
    out = frame.copy()
    downside_band = max(float(downside_band or 0.0), epsilon)
    upside_band = max(float(upside_band or 0.0), epsilon)
    liquidity_threshold = None if liquidity_threshold is None else float(liquidity_threshold)
    prediction_band_threshold = (
        math.inf if prediction_band_threshold is None else float(prediction_band_threshold)
    )
    out["predicted_price"] = pd.to_numeric(out["predicted_price"], errors="coerce").astype(float)
    out["actual_price"] = pd.to_numeric(out["actual_price"], errors="coerce").astype(float)
    out["signed_residual"] = out["actual_price"] - out["predicted_price"]
    out["deviation"] = (out["actual_price"] - out["predicted_price"]).abs()
    out["downside_gap"] = (out["predicted_price"] - out["actual_price"]).clip(lower=0.0)
    out["upside_gap"] = (out["actual_price"] - out["predicted_price"]).clip(lower=0.0)
    out["volume_scaled"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0.0) / volume_scale
    out["liquidity_aware_anomaly_score"] = out["deviation"] / (out["volume_scaled"] + epsilon)
    out["market_confirmed_score"] = out["deviation"] * np.log1p(out["volume_scaled"].clip(lower=0.0))
    if "rolling_volume_median_20" in out.columns:
        out["rolling_volume_median_20"] = pd.to_numeric(out["rolling_volume_median_20"], errors="coerce")
    else:
        out["rolling_volume_median_20"] = pd.NA
    if "relative_volume" in out.columns:
        out["relative_volume"] = pd.to_numeric(out["relative_volume"], errors="coerce")
    else:
        out["relative_volume"] = pd.to_numeric(out["volume"], errors="coerce") / out["rolling_volume_median_20"].replace(0, np.nan)
    out["relative_volume"] = out["relative_volume"].replace([np.inf, -np.inf], np.nan)
    relative_volume_filled = pd.to_numeric(out["relative_volume"], errors="coerce").fillna(0.0)
    out["zero_volume_flag"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0.0).eq(0.0)
    out["low_volume_flag"] = relative_volume_filled < 0.50
    out["thin_trading_flag"] = out["zero_volume_flag"] | (relative_volume_filled < 0.25)
    out["prediction_band_lower"] = out["predicted_price"] - downside_band
    out["prediction_band_upper"] = out["predicted_price"] + upside_band
    out["downside_band_break"] = out["downside_gap"] >= downside_band
    out["upside_band_break"] = out["upside_gap"] >= upside_band
    out["outside_prediction_band"] = out["downside_band_break"] | out["upside_band_break"]
    out["downside_gap_ratio"] = out["downside_gap"] / downside_band
    out["upside_gap_ratio"] = out["upside_gap"] / upside_band
    out["prediction_band_severity"] = out[["downside_gap_ratio", "upside_gap_ratio"]].max(axis=1)
    out["structural_expected_price"] = (
        0.35 * out["sma_20"].fillna(out["predicted_price"])
        + 0.25 * out["sma_50"].fillna(out["predicted_price"])
        + 0.25 * out["ema_12"].fillna(out["predicted_price"])
        + 0.15 * out["predicted_price"]
    )
    out["structural_discount"] = (out["structural_expected_price"] - out["actual_price"]).clip(lower=0.0)
    out["structural_discount_pct"] = out["structural_discount"] / out["structural_expected_price"].replace(0, np.nan)
    out["structural_discount_pct"] = out["structural_discount_pct"].fillna(0.0)
    out["structural_value_signal"] = out["structural_discount_pct"] >= max(structural_gap_threshold_pct, 0.0)
    out["liquidity_anomaly_flag"] = (
        out["liquidity_aware_anomaly_score"] >= liquidity_threshold
        if liquidity_threshold is not None
        else False
    )
    out["downside_band_signal"] = out["downside_gap_ratio"] >= prediction_band_threshold
    out["upside_band_signal"] = out["upside_gap_ratio"] >= prediction_band_threshold
    out["prediction_band_anomaly_flag"] = out["downside_band_signal"] | out["upside_band_signal"]
    out["final_anomaly_detected"] = (
        out["liquidity_anomaly_flag"] | out["prediction_band_anomaly_flag"]
    )
    out["anomaly_detected"] = out["final_anomaly_detected"]
    out["anomaly_side"] = np.select(
        [
            out["liquidity_anomaly_flag"] & out["prediction_band_anomaly_flag"],
            out["downside_band_signal"] & out["upside_band_signal"],
            out["downside_band_signal"],
            out["upside_band_signal"],
            out["liquidity_anomaly_flag"],
        ],
        [
            "liquidity_and_band",
            "two_sided",
            "downside_band",
            "upside_band",
            "liquidity",
        ],
        default="none",
    )
    return out


def calibrate_prediction_bands(
    train_results: pd.DataFrame,
    val_results: pd.DataFrame,
    config: ResearchConfig,
) -> dict[str, float]:
    residuals = (val_results["actual_price"] - val_results["predicted_price"]).astype(float)
    abs_residual = residuals.abs()
    downside_gap = (val_results["predicted_price"] - val_results["actual_price"]).clip(lower=0.0)
    upside_gap = (val_results["actual_price"] - val_results["predicted_price"]).clip(lower=0.0)

    base_band = float(abs_residual.quantile(config.prediction_band_quantile))
    base_band = max(base_band, float(abs_residual.std(ddof=0)), 1e-6)
    downside_band = float(downside_gap.quantile(config.prediction_band_quantile))
    upside_band = float(upside_gap.quantile(config.prediction_band_quantile))
    downside_band = max(downside_band, base_band, 1e-6)
    upside_band = max(upside_band, base_band, 1e-6)

    return {
        "base_band": base_band,
        "downside_band": downside_band,
        "upside_band": upside_band,
    }


def calibrate_structural_gap_threshold(
    train_results: pd.DataFrame,
    val_results: pd.DataFrame,
    config: ResearchConfig,
) -> float:
    positive_gaps = pd.concat(
        [
            train_results["structural_discount_pct"],
            val_results["structural_discount_pct"],
        ],
        ignore_index=True,
    )
    positive_gaps = positive_gaps[positive_gaps > 0].dropna()
    if positive_gaps.empty:
        return 0.0
    return float(positive_gaps.quantile(config.structural_gap_quantile))


def calibrate_final_anomaly_logic(
    train_results: pd.DataFrame,
    val_results: pd.DataFrame,
    config: ResearchConfig,
) -> dict[str, Any]:
    train_liquidity_scores = train_results["liquidity_aware_anomaly_score"].astype(float).to_numpy()
    val_liquidity_scores = val_results["liquidity_aware_anomaly_score"].astype(float).to_numpy()
    train_band_scores = (
        train_results["prediction_band_severity"].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float).to_numpy()
    )
    val_band_scores = (
        val_results["prediction_band_severity"].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float).to_numpy()
    )
    y_val = val_results["proxy_anomaly_label"].astype(int).to_numpy()

    liquidity_quantiles = np.linspace(
        config.anomaly_search_min_quantile,
        config.anomaly_search_max_quantile,
        config.anomaly_search_grid_size,
    )
    band_quantiles = np.linspace(
        max(config.prediction_band_quantile, 0.95),
        config.anomaly_search_max_quantile,
        max(12, config.anomaly_search_grid_size // 2),
    )
    liquidity_thresholds = np.unique(
        np.concatenate(
            [
                np.quantile(train_liquidity_scores, liquidity_quantiles),
                np.quantile(val_liquidity_scores, liquidity_quantiles),
                np.asarray([np.quantile(train_liquidity_scores, config.anomaly_quantile)]),
            ]
        )
    )
    band_thresholds = np.unique(
        np.concatenate(
            [
                np.quantile(train_band_scores, band_quantiles),
                np.quantile(val_band_scores, band_quantiles),
                np.asarray([1.05]),
            ]
        )
    )
    band_thresholds = band_thresholds[band_thresholds >= 1.05]
    if len(band_thresholds) == 0:
        band_thresholds = np.asarray([1.05])

    search_rows: list[dict[str, Any]] = []
    best_row: dict[str, Any] | None = None
    train_positive_rate = float(train_results["proxy_anomaly_label"].mean()) if len(train_results) else 0.0
    val_positive_rate = float(y_val.mean()) if len(y_val) else 0.0
    if train_positive_rate > 0 and val_positive_rate > 0:
        target_positive_rate = math.sqrt(train_positive_rate * val_positive_rate)
    else:
        target_positive_rate = max(train_positive_rate, val_positive_rate)
    max_reasonable_positive_rate = max(target_positive_rate * 2.0, 0.03) if target_positive_rate > 0 else 0.03

    for liquidity_threshold in liquidity_thresholds:
        for prediction_band_threshold in band_thresholds:
            y_pred = (
                (val_liquidity_scores >= liquidity_threshold)
                | (val_band_scores >= prediction_band_threshold)
            ).astype(int)
            metrics = compute_classification_metrics(y_val, y_pred)
            f0_5 = compute_fbeta_metric(y_val, y_pred, beta=0.5)
            row = {
                "liquidity_threshold": float(liquidity_threshold),
                "prediction_band_threshold": float(prediction_band_threshold),
                "f0_5_score": f0_5,
                "target_positive_rate": float(target_positive_rate),
                "positive_rate_gap": float(abs(metrics["predicted_positive_rate"] - target_positive_rate)),
                "positive_rate_over_cap": float(
                    max(0.0, metrics["predicted_positive_rate"] - max_reasonable_positive_rate)
                ),
                **metrics,
            }
            row.update(compute_confusion_counts(y_val, y_pred))
            search_rows.append(row)

            if best_row is None:
                best_row = row
                continue

            current_key = (
                row["f0_5_score"],
                row["precision"],
                -row["positive_rate_over_cap"],
                -row["positive_rate_gap"],
                row["accuracy"],
                row["recall"],
            )
            best_key = (
                best_row["f0_5_score"],
                best_row["precision"],
                -best_row["positive_rate_over_cap"],
                -best_row["positive_rate_gap"],
                best_row["accuracy"],
                best_row["recall"],
            )
            if current_key > best_key:
                best_row = row

    if best_row is None:
        fallback = float(np.quantile(train_liquidity_scores, config.anomaly_quantile))
        best_row = {
            "liquidity_threshold": fallback,
            "prediction_band_threshold": 1.05,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "f0_5_score": 0.0,
            "predicted_positive_rate": 0.0,
            "target_positive_rate": float(target_positive_rate),
            "positive_rate_gap": float(target_positive_rate),
            "positive_rate_over_cap": 0.0,
            "tn": 0,
            "fp": 0,
            "fn": 0,
            "tp": 0,
        }

    return {
        "liquidity_threshold": float(best_row["liquidity_threshold"]),
        "prediction_band_threshold": float(best_row["prediction_band_threshold"]),
        "validation_metrics": {
            "accuracy": float(best_row["accuracy"]),
            "precision": float(best_row["precision"]),
            "recall": float(best_row["recall"]),
            "f1_score": float(best_row["f1_score"]),
            "f0_5_score": float(best_row["f0_5_score"]),
            "predicted_positive_rate": float(best_row["predicted_positive_rate"]),
            "target_positive_rate": float(best_row["target_positive_rate"]),
            "positive_rate_gap": float(best_row["positive_rate_gap"]),
            "positive_rate_over_cap": float(best_row["positive_rate_over_cap"]),
            "tn": int(best_row["tn"]),
            "fp": int(best_row["fp"]),
            "fn": int(best_row["fn"]),
            "tp": int(best_row["tp"]),
        },
        "search_table": pd.DataFrame(search_rows).sort_values(
            [
                "f0_5_score",
                "precision",
                "positive_rate_over_cap",
                "positive_rate_gap",
                "accuracy",
                "recall",
            ],
            ascending=[False, False, True, True, False, False],
        ).reset_index(drop=True),
    }


def classify_risk(
    score: float,
    low_threshold: float,
    high_threshold: float,
    band_severity: float = 0.0,
) -> str:
    if score >= high_threshold or band_severity >= 1.5:
        return "High"
    if score >= low_threshold or band_severity >= 1.0:
        return "Medium"
    return "Low"


def enforce_anomaly_risk_floor(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out.loc[out["anomaly_detected"] & (out["risk_level"] == "Low"), "risk_level"] = "Medium"
    return out


def summarize_recent_anomalies(
    test_results: pd.DataFrame,
    recent_window: int,
) -> dict[str, Any]:
    ordered = test_results.sort_values("date").reset_index(drop=True)
    recent = ordered.tail(recent_window).copy()
    recent_anomalies = recent[recent["final_anomaly_detected"]].copy()
    downside_recent = recent[recent["downside_band_signal"]].copy()
    structural_recent = recent[recent["structural_value_signal"]].copy()

    def row_to_summary(row: pd.Series | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "date": str(pd.Timestamp(row["date"]).date()),
            "predicted_price": round(float(row["predicted_price"]), 4),
            "actual_price": round(float(row["actual_price"]), 4),
            "deviation": round(float(row["deviation"]), 4),
            "liquidity_aware_anomaly_score": round(float(row["liquidity_aware_anomaly_score"]), 6),
            "risk_level": str(row["risk_level"]),
            "anomaly_side": str(row["anomaly_side"]),
            "structural_discount_pct": round(float(row["structural_discount_pct"]) * 100.0, 4),
        }

    latest_anomaly = row_to_summary(recent_anomalies.iloc[-1]) if not recent_anomalies.empty else None
    latest_downside = row_to_summary(downside_recent.iloc[-1]) if not downside_recent.empty else None
    latest_structural = row_to_summary(structural_recent.iloc[-1]) if not structural_recent.empty else None

    return {
        "recent_window_start": str(pd.Timestamp(recent["date"].min()).date()),
        "recent_window_end": str(pd.Timestamp(recent["date"].max()).date()),
        "recent_window_rows": int(len(recent)),
        "recent_anomaly_count": int(recent["final_anomaly_detected"].sum()),
        "recent_liquidity_anomaly_count": int(recent["liquidity_anomaly_flag"].sum()),
        "recent_prediction_band_anomaly_count": int(recent["prediction_band_anomaly_flag"].sum()),
        "recent_downside_count": int(recent["downside_band_signal"].sum()),
        "recent_structural_discount_count": int(recent["structural_value_signal"].sum()),
        "latest_recent_anomaly": latest_anomaly,
        "latest_recent_downside_anomaly": latest_downside,
        "latest_recent_structural_anomaly": latest_structural,
    }


def build_anomaly_method_comparison(
    train_results: pd.DataFrame,
    val_results: pd.DataFrame,
    test_results: pd.DataFrame,
    feature_columns: list[str],
    config: ResearchConfig,
    lstm_threshold: float,
    prediction_band_threshold: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    split_frames = {
        "train": train_results,
        "validation": val_results,
        "test": test_results,
    }
    train_return = train_results["return_1d"].dropna()
    return_mean = train_return.mean()
    return_std = train_return.std(ddof=0) or 1.0
    train_z_scores = ((train_results["return_1d"] - return_mean) / return_std).abs()
    z_threshold = max(3.0, float(train_z_scores.quantile(config.anomaly_quantile)))

    scaler = StandardScaler()
    train_features = scaler.fit_transform(train_results[feature_columns])
    iso = IsolationForest(
        contamination=config.isolation_forest_contamination,
        random_state=config.random_seed,
    )
    iso.fit(train_features)
    iso_train_scores = -iso.score_samples(train_features)
    iso_threshold = float(np.quantile(iso_train_scores, config.anomaly_quantile))

    method_predictions: dict[str, dict[str, Any]] = {
        "Z-score baseline": {
            "purpose": "Simple statistical anomaly detection",
            "threshold": z_threshold,
            "prediction_band_threshold": math.nan,
            "predictions": {
                split: (((frame["return_1d"] - return_mean) / return_std).abs() >= z_threshold).astype(int).to_numpy()
                for split, frame in split_frames.items()
            },
        },
        "Isolation Forest": {
            "purpose": "Machine-learning anomaly detection",
            "threshold": iso_threshold,
            "prediction_band_threshold": math.nan,
            "predictions": {
                split: (
                    -iso.score_samples(scaler.transform(frame[feature_columns])) >= iso_threshold
                ).astype(int)
                for split, frame in split_frames.items()
            },
        },
        "LSTM deviation method": {
            "purpose": "Time-series expected-vs-actual anomaly detection",
            "threshold": lstm_threshold,
            "prediction_band_threshold": prediction_band_threshold,
            "predictions": {
                split: frame["final_anomaly_detected"].astype(int).to_numpy()
                for split, frame in split_frames.items()
            },
        },
    }

    split_rows: list[dict[str, Any]] = []
    for method, method_info in method_predictions.items():
        for split, frame in split_frames.items():
            y_true = frame["proxy_anomaly_label"].astype(int).to_numpy()
            y_pred = np.asarray(method_info["predictions"][split], dtype=int)
            row = {
                "method": method,
                "purpose": method_info["purpose"],
                "split": split,
                "threshold": float(method_info["threshold"]),
                "prediction_band_threshold": (
                    float(method_info["prediction_band_threshold"])
                    if not pd.isna(method_info["prediction_band_threshold"])
                    else math.nan
                ),
            }
            row.update(compute_classification_metrics(y_true, y_pred))
            row.update(compute_confusion_counts(y_true, y_pred))
            split_rows.append(row)

    split_metrics = pd.DataFrame(split_rows)
    comparison = (
        split_metrics[split_metrics["split"] == "test"]
        .drop(columns=["split"])
        .sort_values(["f1_score", "precision", "recall"], ascending=[False, False, False])
        .reset_index(drop=True)
    )
    confusion = split_metrics[["method", "split", "tn", "fp", "fn", "tp"]].copy()
    return comparison, split_metrics, confusion


def calibrate_forecast_ensemble(
    val_results: pd.DataFrame,
    test_results: pd.DataFrame,
    config: ResearchConfig,
) -> dict[str, Any]:
    val_frame = val_results.sort_values("date").reset_index(drop=True).copy()
    test_frame = test_results.sort_values("date").reset_index(drop=True).copy()

    for frame in (val_frame, test_frame):
        frame["scenario_lstm_forecast"] = pd.to_numeric(frame["predicted_price"], errors="coerce")
        frame["naive_random_walk_forecast"] = pd.to_numeric(
            frame["naive_baseline_predicted_price"], errors="coerce"
        )
        frame["moving_average_drift_forecast"] = pd.to_numeric(frame["drift_pred_close"], errors="coerce").fillna(
            pd.to_numeric(frame["prev_close"], errors="coerce")
        )

    component_map = {
        "scenario_lstm_forecast": "scenario_lstm_forecast",
        "naive_random_walk_forecast": "naive_random_walk_forecast",
        "moving_average_drift_forecast": "moving_average_drift_forecast",
    }
    validation_errors: dict[str, float] = {}
    for key, column in component_map.items():
        validation_errors[key] = float(
            mean_absolute_error(
                val_frame["actual_price"].to_numpy(dtype=float),
                val_frame[column].to_numpy(dtype=float),
            )
        )
    raw_weights = {
        key: 1.0 / max(error, config.forecast_weight_epsilon)
        for key, error in validation_errors.items()
    }
    weight_sum = sum(raw_weights.values()) or 1.0
    weights = {key: float(value / weight_sum) for key, value in raw_weights.items()}

    for frame in (val_frame, test_frame):
        frame["ensemble_forecast"] = (
            weights["scenario_lstm_forecast"] * frame["scenario_lstm_forecast"]
            + weights["naive_random_walk_forecast"] * frame["naive_random_walk_forecast"]
            + weights["moving_average_drift_forecast"] * frame["moving_average_drift_forecast"]
        )

    val_abs_residual = (val_frame["actual_price"] - val_frame["ensemble_forecast"]).abs().to_numpy(dtype=float)
    q80 = float(np.quantile(val_abs_residual, 0.80)) if len(val_abs_residual) else 0.0
    q95 = float(np.quantile(val_abs_residual, 0.95)) if len(val_abs_residual) else 0.0

    for frame in (val_frame, test_frame):
        frame["lower_80"] = frame["ensemble_forecast"] - q80
        frame["upper_80"] = frame["ensemble_forecast"] + q80
        frame["lower_95"] = frame["ensemble_forecast"] - q95
        frame["upper_95"] = frame["ensemble_forecast"] + q95
        frame["interval_80_contains_actual"] = (
            (frame["actual_price"] >= frame["lower_80"]) & (frame["actual_price"] <= frame["upper_80"])
        )
        frame["interval_95_contains_actual"] = (
            (frame["actual_price"] >= frame["lower_95"]) & (frame["actual_price"] <= frame["upper_95"])
        )
        frame["forecast_signed_residual"] = frame["actual_price"] - frame["ensemble_forecast"]

    component_rows = []
    for split_name, frame in (("validation", val_frame), ("test", test_frame)):
        for key, column in component_map.items():
            metrics = compute_prediction_metrics(
                frame["actual_price"].to_numpy(dtype=float),
                frame[column].to_numpy(dtype=float),
            )
            component_rows.append(
                {
                    "split": split_name,
                    "model": key,
                    "mae": float(metrics["mae"]),
                    "rmse": float(metrics["rmse"]),
                    "mape": float(metrics["mape"]),
                    "mape_pct": float(metrics["mape_pct"]),
                }
            )
        ensemble_metrics = compute_prediction_metrics(
            frame["actual_price"].to_numpy(dtype=float),
            frame["ensemble_forecast"].to_numpy(dtype=float),
        )
        component_rows.append(
            {
                "split": split_name,
                "model": "ensemble_forecast",
                "mae": float(ensemble_metrics["mae"]),
                "rmse": float(ensemble_metrics["rmse"]),
                "mape": float(ensemble_metrics["mape"]),
                "mape_pct": float(ensemble_metrics["mape_pct"]),
            }
        )

    return {
        "validation_backtest": val_frame,
        "test_backtest": test_frame,
        "weights": weights,
        "validation_errors": validation_errors,
        "conformal_q80": q80,
        "conformal_q95": q95,
        "component_backtest": pd.DataFrame(component_rows),
    }


def build_forecast_walk_forward_validation(
    history_frame: pd.DataFrame,
    evaluation_frame: pd.DataFrame,
    direction_prediction_frame: pd.DataFrame,
    fold_count: int,
) -> pd.DataFrame:
    ordered = evaluation_frame.sort_values("date").reset_index(drop=True).copy()
    direction_frame = direction_prediction_frame.sort_values("date").reset_index(drop=True).copy()
    merged = ordered.merge(
        direction_frame[["date", "direction_target", "direction_pred"]],
        on="date",
        how="left",
    )
    fold_rows: list[dict[str, Any]] = []
    index_splits = [idx for idx in np.array_split(np.arange(len(merged)), max(1, fold_count)) if len(idx) > 0]

    for fold_number, idx in enumerate(index_splits, start=1):
        fold = merged.iloc[idx].copy()
        fold_start = pd.Timestamp(fold["date"].min())
        fold_end = pd.Timestamp(fold["date"].max())
        prior = history_frame[history_frame["date"] < fold_start].copy()
        train_start = pd.Timestamp(history_frame["date"].min())
        train_end = pd.Timestamp(prior["date"].max()) if not prior.empty else fold_start
        metrics = compute_prediction_metrics(
            fold["actual_price"].to_numpy(dtype=float),
            fold["ensemble_forecast"].to_numpy(dtype=float),
        )
        direction_mask = fold["direction_target"].notna() & fold["direction_pred"].notna()
        if direction_mask.any():
            y_true = fold.loc[direction_mask, "direction_target"].to_numpy(dtype=int)
            y_pred = fold.loc[direction_mask, "direction_pred"].to_numpy(dtype=int)
            fold_direction_accuracy = float(accuracy_score(y_true, y_pred))
            fold_balanced_accuracy = float(balanced_accuracy_score(y_true, y_pred))
        else:
            fold_direction_accuracy = math.nan
            fold_balanced_accuracy = math.nan
        fold_rows.append(
            {
                "fold": fold_number,
                "train_period_start": str(train_start.date()),
                "train_period_end": str(train_end.date()),
                "validation_period_start": str(fold_start.date()),
                "validation_period_end": str(fold_end.date()),
                "rows": int(len(fold)),
                "mae": float(metrics["mae"]),
                "rmse": float(metrics["rmse"]),
                "mape": float(metrics["mape"]),
                "mape_pct": float(metrics["mape_pct"]),
                "directional_accuracy": fold_direction_accuracy,
                "balanced_directional_accuracy": fold_balanced_accuracy,
                "interval_95_coverage": float(fold["interval_95_contains_actual"].mean()),
            }
        )

    return pd.DataFrame(fold_rows)


def compute_forecast_reliability_metrics(
    forecast_backtest: pd.DataFrame,
    walk_forward_validation: pd.DataFrame,
) -> dict[str, Any]:
    metrics = compute_prediction_metrics(
        forecast_backtest["actual_price"].to_numpy(dtype=float),
        forecast_backtest["ensemble_forecast"].to_numpy(dtype=float),
    )
    interval_80_coverage = float(forecast_backtest["interval_80_contains_actual"].mean())
    interval_95_coverage = float(forecast_backtest["interval_95_contains_actual"].mean())
    average_interval_width_95 = float(
        (forecast_backtest["upper_95"] - forecast_backtest["lower_95"]).mean()
    )
    forecast_bias = float(
        np.mean(
            forecast_backtest["actual_price"].to_numpy(dtype=float)
            - forecast_backtest["ensemble_forecast"].to_numpy(dtype=float)
        )
    )
    actual_direction = (
        forecast_backtest["actual_price"].to_numpy(dtype=float)
        > forecast_backtest["prev_close"].to_numpy(dtype=float)
    ).astype(int)
    predicted_direction = (
        forecast_backtest["ensemble_forecast"].to_numpy(dtype=float)
        > forecast_backtest["prev_close"].to_numpy(dtype=float)
    ).astype(int)
    direction_hit_rate = float(np.mean(actual_direction == predicted_direction))
    fold_mape_mean = float(walk_forward_validation["mape"].mean()) if not walk_forward_validation.empty else math.nan
    fold_mape_std = float(walk_forward_validation["mape"].std(ddof=0)) if not walk_forward_validation.empty else math.nan

    price_error_score = float(np.clip(10.0 * (1.0 - float(metrics["mape"]) / 0.10), 0.0, 10.0))
    interval_coverage_score = float(
        np.clip(10.0 * (1.0 - abs(interval_95_coverage - 0.95) / 0.95), 0.0, 10.0)
    )
    average_price_level = max(float(np.mean(forecast_backtest["actual_price"])), 1e-6)
    bias_score = float(np.clip(10.0 * (1.0 - abs(forecast_bias) / (average_price_level * 0.10)), 0.0, 10.0))
    if math.isfinite(fold_mape_mean) and math.isfinite(fold_mape_std) and fold_mape_mean > 0:
        stability_score = float(np.clip(10.0 * (1.0 - fold_mape_std / fold_mape_mean), 0.0, 10.0))
    else:
        stability_score = 0.0

    reliability_score = (
        0.35 * price_error_score
        + 0.35 * interval_coverage_score
        + 0.20 * bias_score
        + 0.10 * stability_score
    )
    if reliability_score >= 7.0:
        interpretation = "High"
    elif reliability_score >= 5.0:
        interpretation = "Moderate"
    else:
        interpretation = "Low"

    return {
        "forecast_mae_backtest": float(metrics["mae"]),
        "forecast_rmse_backtest": float(metrics["rmse"]),
        "forecast_mape_backtest": float(metrics["mape"]),
        "forecast_mape_backtest_pct": float(metrics["mape_pct"]),
        "interval_80_coverage": interval_80_coverage,
        "interval_95_coverage": interval_95_coverage,
        "average_interval_width_95": average_interval_width_95,
        "coverage_error_95": float(abs(interval_95_coverage - 0.95)),
        "forecast_bias": forecast_bias,
        "direction_hit_rate_for_forecast_horizon": direction_hit_rate,
        "price_error_score": price_error_score,
        "interval_coverage_score": interval_coverage_score,
        "bias_score": bias_score,
        "stability_score": stability_score,
        "forecast_reliability_score": float(reliability_score),
        "forecast_reliability_interpretation": interpretation,
        "fold_mape_mean": fold_mape_mean,
        "fold_mape_std": fold_mape_std,
    }


def _resolve_target_price(
    config: ResearchConfig,
    stock_code: str,
    current_price: float,
    structural_forecast_3m: float,
) -> tuple[float, str]:
    if config.target_price is not None:
        return float(config.target_price), "config_supplied_target_price"
    if normalize_stock_code(stock_code) == "BIL":
        return 7.0, "default_bil_scenario_target"
    auto_target = round(max(current_price, structural_forecast_3m) * 1.05, 2)
    return float(auto_target), "auto_structural_plus_5pct_target"


def _safe_upper_tail_probability(mean_value: float, std_value: float, target_value: float) -> float:
    std_safe = max(float(std_value), 1e-6)
    z_score = (float(target_value) - float(mean_value)) / std_safe
    return float(0.5 * math.erfc(z_score / math.sqrt(2.0)))


def apply_anomaly_pressure_scores(
    train_results: pd.DataFrame,
    val_results: pd.DataFrame,
    test_results: pd.DataFrame,
    config: ResearchConfig,
) -> dict[str, Any]:
    reference = pd.concat([train_results, val_results], ignore_index=True).copy()
    base_features = [
        "return_1d",
        "return_5d",
        "volatility_20",
        "volume_ratio_20d",
        "liquidity_aware_anomaly_score",
    ]
    available_optional = [
        col
        for col in OPTIONAL_EXTERNAL_PROXY_COLUMNS
        if col in reference.columns and pd.to_numeric(reference[col], errors="coerce").notna().any()
    ]
    component_columns = base_features + available_optional
    zscore_stats: dict[str, tuple[float, float]] = {}

    for column in component_columns:
        series = pd.to_numeric(reference[column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        mean_value = float(series.mean()) if not series.empty else 0.0
        std_value = float(series.std(ddof=0)) if not series.empty else 0.0
        if not math.isfinite(std_value) or std_value <= 0:
            std_value = 1.0
        zscore_stats[column] = (mean_value, std_value)

    def score_frame(frame: pd.DataFrame) -> pd.DataFrame:
        out = frame.copy()
        pressure_components: list[pd.Series] = []
        for column in component_columns:
            mean_value, std_value = zscore_stats[column]
            values = pd.to_numeric(out[column], errors="coerce")
            z_values = ((values - mean_value) / std_value).abs()
            out[f"anomaly_pressure_component_{column}"] = z_values
            pressure_components.append(z_values.fillna(0.0))
        out["anomaly_pressure_score"] = sum(pressure_components) if pressure_components else 0.0
        return out

    scored_train = score_frame(train_results)
    scored_val = score_frame(val_results)
    scored_test = score_frame(test_results)
    reference_scored = pd.concat([scored_train, scored_val], ignore_index=True)

    anomaly_pressure_threshold = float(
        reference_scored["anomaly_pressure_score"].quantile(config.shock_pressure_quantile)
    )
    anomaly_pressure_p95 = float(reference_scored["anomaly_pressure_score"].quantile(0.95))
    threshold_basis = (
        "Train/validation only 90th-percentile threshold over anomaly_pressure_score, with component z-scores "
        "standardized from train/validation statistics only. No test rows are used in threshold selection."
    )
    external_available = available_optional
    missing_optional = [col for col in OPTIONAL_EXTERNAL_PROXY_COLUMNS if col not in external_available]
    if missing_optional:
        external_data_limitations = (
            "The following optional external/proxy inputs were unavailable: "
            + ", ".join(missing_optional)
            + ". Shock-adjusted interpretation therefore relies on stock-level anomaly and stress proxies only."
        )
    else:
        external_data_limitations = (
            "Optional external/proxy inputs were available and included alongside stock-level anomaly features."
        )

    return {
        "train_results": scored_train,
        "val_results": scored_val,
        "test_results": scored_test,
        "reference_scored": reference_scored,
        "anomaly_pressure_threshold": anomaly_pressure_threshold,
        "anomaly_pressure_p95": anomaly_pressure_p95,
        "anomaly_pressure_threshold_basis": threshold_basis,
        "external_available": external_available,
        "external_missing": missing_optional,
        "external_data_limitations": external_data_limitations,
        "component_columns": component_columns,
        "zscore_stats": zscore_stats,
    }


def build_shock_adjusted_anomaly_layer(
    latest_row: pd.Series,
    forecast_summary: dict[str, Any],
    forecast_reliability_metrics: dict[str, Any],
    config: ResearchConfig,
) -> dict[str, Any]:
    current_price = float(latest_row["actual_price"])
    structural_forecast_3m = float(forecast_summary["forecast_end_price"])
    recovery_gap = structural_forecast_3m - current_price
    recovery_gap_pct = recovery_gap / current_price if current_price else math.nan
    target_price, target_price_basis = _resolve_target_price(
        config=config,
        stock_code=str(latest_row["stock_code"]) if "stock_code" in latest_row else str(config.stock_code),
        current_price=current_price,
        structural_forecast_3m=structural_forecast_3m,
    )

    anomaly_pressure_score = float(latest_row["anomaly_pressure_score"])
    anomaly_pressure_threshold = float(latest_row["anomaly_pressure_threshold"])
    anomaly_pressure_p95 = float(latest_row["anomaly_pressure_p95"])
    forecast_reliability_score = float(forecast_reliability_metrics["forecast_reliability_score"])
    recent_stock_return = float(
        latest_row["return_5d"] if pd.notna(latest_row["return_5d"]) else latest_row["return_1d"]
    )
    weak_return_threshold = float(max(0.0, abs(float(latest_row["volatility_20"])) * 0.25))
    temporary_anomaly_drag_flag = bool(
        (structural_forecast_3m > current_price)
        and (recovery_gap > 0.0)
        and (anomaly_pressure_score >= anomaly_pressure_threshold)
        and (recent_stock_return <= weak_return_threshold)
        and (forecast_reliability_score >= config.shock_reliability_min_score)
    )

    if temporary_anomaly_drag_flag or anomaly_pressure_score >= anomaly_pressure_threshold:
        denom = max(anomaly_pressure_p95 - anomaly_pressure_threshold, 1e-6)
        normalized_excess = float(
            np.clip((anomaly_pressure_score - anomaly_pressure_threshold) / denom, 0.0, 1.0)
        )
        reliability_scale = float(np.clip(forecast_reliability_score / 10.0, 0.0, 1.0))
        anomaly_penalty_pct = float(
            min(
                config.shock_max_penalty_pct,
                config.shock_penalty_strength
                * max(0.25, normalized_excess)
                * max(0.50, reliability_scale),
            )
        )
    else:
        anomaly_penalty_pct = 0.0

    anomaly_adjusted_forecast_3m = structural_forecast_3m * (1.0 - anomaly_penalty_pct)
    interval_std = max(
        (float(forecast_summary["forecast_end_upper_95"]) - float(forecast_summary["forecast_end_lower_95"]))
        / (2.0 * 1.96),
        1e-6,
    )
    target_breakout_probability = _safe_upper_tail_probability(
        mean_value=structural_forecast_3m,
        std_value=interval_std,
        target_value=target_price,
    )
    anomaly_adjusted_breakout_probability = _safe_upper_tail_probability(
        mean_value=anomaly_adjusted_forecast_3m,
        std_value=interval_std,
        target_value=target_price,
    )

    if target_breakout_probability >= 0.70:
        target_breakout_interpretation = "High breakout potential"
    elif target_breakout_probability >= 0.50:
        target_breakout_interpretation = "Moderate breakout potential"
    else:
        target_breakout_interpretation = "Weak breakout potential"
    if target_breakout_probability - anomaly_adjusted_breakout_probability >= 0.15:
        target_breakout_interpretation += (
            ". The structural forecast supports a possible move above the target, but anomaly-adjusted probability "
            "is lower because recent abnormal pressure indicators are elevated."
        )

    if temporary_anomaly_drag_flag:
        anomaly_type = "Temporary anomaly-driven price suppression"
    elif bool(latest_row["final_anomaly_detected"]) and bool(latest_row["thin_trading_flag"]):
        anomaly_type = "Low-liquidity anomaly"
    elif bool(latest_row["final_anomaly_detected"]):
        anomaly_type = "Price deviation anomaly"
    else:
        anomaly_type = "Normal movement"

    if temporary_anomaly_drag_flag:
        shock_adjusted_explanation = (
            "The stock's structural trend remains positive, but recent anomaly pressure indicators suggest the price "
            "may be temporarily suppressed. The recovery gap shows the difference between the current price and the "
            "structural 3-month forecast."
        )
    elif target_breakout_probability >= 0.70:
        shock_adjusted_explanation = (
            "The stock has a high model-based probability of moving above the selected target, but this should be "
            "treated as a scenario forecast, not a guaranteed outcome."
        )
    elif target_breakout_probability >= 0.50:
        shock_adjusted_explanation = (
            "The stock may reach the selected target, but uncertainty remains because the forecast interval still "
            "includes prices below the target."
        )
    else:
        shock_adjusted_explanation = (
            "The model does not currently show strong evidence that the stock will break above the selected target "
            "within the forecast period."
        )

    return {
        "structural_forecast_3m": float(structural_forecast_3m),
        "anomaly_adjusted_forecast_3m": float(anomaly_adjusted_forecast_3m),
        "current_price": float(current_price),
        "recovery_gap": float(recovery_gap),
        "recovery_gap_pct": float(recovery_gap_pct),
        "target_price": float(target_price),
        "target_price_basis": target_price_basis,
        "target_breakout_probability": float(target_breakout_probability),
        "anomaly_adjusted_breakout_probability": float(anomaly_adjusted_breakout_probability),
        "target_breakout_interpretation": target_breakout_interpretation,
        "anomaly_pressure_score": float(anomaly_pressure_score),
        "anomaly_pressure_threshold": float(anomaly_pressure_threshold),
        "anomaly_pressure_threshold_basis": str(latest_row["anomaly_pressure_threshold_basis"]),
        "temporary_anomaly_drag_flag": bool(temporary_anomaly_drag_flag),
        "anomaly_penalty_pct": float(anomaly_penalty_pct),
        "anomaly_type": anomaly_type,
        "shock_adjusted_explanation": shock_adjusted_explanation,
        "external_data_limitations": str(latest_row["external_data_limitations"]),
    }


def apply_regime_shift_scores(
    train_results: pd.DataFrame,
    val_results: pd.DataFrame,
    test_results: pd.DataFrame,
    config: ResearchConfig,
) -> dict[str, Any]:
    combined = pd.concat([train_results, val_results, test_results], ignore_index=True).sort_values("date").reset_index(drop=True)
    price = pd.to_numeric(combined["actual_price"], errors="coerce")
    returns = pd.to_numeric(combined["return_1d"], errors="coerce").replace([np.inf, -np.inf], np.nan)

    mean_20 = price.rolling(20, min_periods=10).mean()
    mean_60 = price.rolling(60, min_periods=20).mean()
    vol_20 = returns.rolling(20, min_periods=10).std()
    vol_60 = returns.rolling(60, min_periods=20).std()
    prior_peak_120 = price.shift(1).rolling(120, min_periods=30).max()
    return_mean_60 = returns.shift(1).rolling(60, min_periods=20).mean()
    return_std_60 = returns.shift(1).rolling(60, min_periods=20).std().replace(0, np.nan)
    relative_volume = pd.to_numeric(combined["relative_volume"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    relative_volume_median_60 = relative_volume.shift(1).rolling(60, min_periods=20).median()

    components = pd.DataFrame(
        {
            "rolling_mean_shift": (mean_20 / mean_60.replace(0, np.nan) - 1.0).abs(),
            "rolling_volatility_shift": (vol_20 / vol_60.replace(0, np.nan) - 1.0).abs(),
            "drawdown_from_prior_trend": ((prior_peak_120 - price) / prior_peak_120.replace(0, np.nan)).clip(lower=0.0),
            "long_ma_deviation": (price / pd.to_numeric(combined["sma_50"], errors="coerce").replace(0, np.nan) - 1.0).abs(),
            "return_distribution_shift": ((returns - return_mean_60) / return_std_60).abs(),
            "relative_volume_shift": (relative_volume / relative_volume_median_60.replace(0, np.nan) - 1.0).abs(),
        }
    ).replace([np.inf, -np.inf], np.nan)

    reference_mask = combined["split"].isin(["train", "validation"])
    robust_components = []
    for column in components.columns:
        reference_values = components.loc[reference_mask, column].dropna()
        median_value = float(reference_values.median()) if not reference_values.empty else 0.0
        iqr_value = float(reference_values.quantile(0.75) - reference_values.quantile(0.25)) if len(reference_values) else 1.0
        if not math.isfinite(iqr_value) or iqr_value <= 0:
            iqr_value = 1.0
        robust = ((components[column] - median_value) / iqr_value).clip(lower=0.0).fillna(0.0)
        combined[f"regime_component_{column}"] = robust
        robust_components.append(robust)

    combined["regime_shift_score"] = sum(robust_components) if robust_components else 0.0
    reference_scores = combined.loc[reference_mask, "regime_shift_score"].dropna()
    threshold = float(reference_scores.quantile(0.90)) if not reference_scores.empty else 0.0
    combined["regime_shift_flag"] = combined["regime_shift_score"] >= threshold

    gap_reference = (
        (
            pd.to_numeric(combined.loc[reference_mask, "sma_50"], errors="coerce")
            - pd.to_numeric(combined.loc[reference_mask, "actual_price"], errors="coerce")
        )
        / pd.to_numeric(combined.loc[reference_mask, "actual_price"], errors="coerce").replace(0, np.nan)
    ).clip(lower=0.0).replace([np.inf, -np.inf], np.nan).dropna()
    materiality_threshold = float(gap_reference.quantile(0.75)) if not gap_reference.empty else 0.05

    split_frames = {
        split_name: combined[combined["split"] == split_name].reset_index(drop=True)
        for split_name in ["train", "validation", "test"]
    }
    return {
        "combined": combined,
        "train_results": split_frames["train"],
        "val_results": split_frames["validation"],
        "test_results": split_frames["test"],
        "regime_shift_threshold": threshold,
        "regime_shift_threshold_basis": (
            "Train/validation only 90th-percentile threshold over trailing regime-shift components. "
            "Components use historical rolling windows and no future rows."
        ),
        "suppression_materiality_threshold_pct": materiality_threshold,
        "suppression_materiality_threshold_basis": (
            "Train/validation only 75th percentile of positive price gaps below the 50-day moving average."
        ),
    }


def build_counterfactual_structural_suppression_layer(
    combined_regime_results: pd.DataFrame,
    latest_row: pd.Series,
    current_regime_forecast_3m: float,
    regime_shift_threshold: float,
    regime_shift_threshold_basis: str,
    materiality_threshold_pct: float,
) -> dict[str, Any]:
    ordered = combined_regime_results.sort_values("date").reset_index(drop=True).copy()
    current_price = float(latest_row["actual_price"])
    latest_date = pd.Timestamp(latest_row["date"])
    latest_position = int(ordered.index[ordered["date"] == latest_row["date"]][-1])
    history_until_latest = ordered.iloc[: latest_position + 1].copy()

    flagged_positions = history_until_latest.index[history_until_latest["regime_shift_flag"].astype(bool)].tolist()
    anchor_limitation = ""
    if flagged_positions:
        shift_start = flagged_positions[-1]
        while shift_start > 0 and bool(history_until_latest.loc[shift_start - 1, "regime_shift_flag"]):
            shift_start -= 1
        stable_candidates = history_until_latest.iloc[:shift_start].copy()
    else:
        stable_candidates = history_until_latest.iloc[:-20].copy()
        anchor_limitation = "No strong historical regime-shift cluster was detected before the latest row, so a stable pre-shift anchor was selected from trailing historical stability scores."

    stable_candidates = stable_candidates[
        stable_candidates["actual_price"].notna()
        & stable_candidates["regime_shift_score"].notna()
        & stable_candidates["return_1d"].notna()
    ].copy()
    if stable_candidates.empty:
        anchor_row = history_until_latest.iloc[max(0, len(history_until_latest) - 61)].copy()
        anchor_limitation = "A reliable stable anchor was not available, so the counterfactual layer used a fallback historical anchor."
    else:
        stable_cutoff = stable_candidates["regime_shift_score"].quantile(0.40)
        low_stress = stable_candidates[stable_candidates["regime_shift_score"] <= stable_cutoff].copy()
        anchor_pool = low_stress if not low_stress.empty else stable_candidates
        anchor_row = anchor_pool.iloc[-1].copy()

    anchor_date = pd.Timestamp(anchor_row["date"])
    anchor_price = float(anchor_row["actual_price"])
    pre_anchor_returns = history_until_latest[
        (history_until_latest["date"] < anchor_date)
        & history_until_latest["return_1d"].notna()
    ]["return_1d"].tail(60)
    if pre_anchor_returns.empty:
        pre_anchor_returns = history_until_latest[
            (history_until_latest["date"] <= anchor_date)
            & history_until_latest["return_1d"].notna()
        ]["return_1d"].tail(60)
    drift = float(pre_anchor_returns.mean()) if not pre_anchor_returns.empty else 0.0
    drift = float(np.clip(drift, -0.003, 0.003))

    days_from_anchor_to_latest = max(0, int(np.busday_count(anchor_date.date(), latest_date.date())))
    forecast_horizon_days = 60
    counterfactual_structural_forecast_3m = max(
        0.01,
        anchor_price * math.exp(drift * (days_from_anchor_to_latest + forecast_horizon_days)),
    )
    structural_suppression_gap = counterfactual_structural_forecast_3m - current_price
    structural_suppression_gap_pct = structural_suppression_gap / current_price if current_price else math.nan
    regime_shift_flag = bool(float(latest_row["regime_shift_score"]) >= float(regime_shift_threshold))
    suppressed_flag = bool(
        (not bool(latest_row["final_anomaly_detected"]))
        and regime_shift_flag
        and structural_suppression_gap > 0.0
        and structural_suppression_gap_pct > float(materiality_threshold_pct)
        and current_price < counterfactual_structural_forecast_3m
    )

    if suppressed_flag:
        interpretation = (
            "The latest movement is not abnormal compared with the current market regime, but the stock remains "
            "materially below its earlier structural path. This suggests structural suppression rather than a fresh "
            "daily anomaly."
        )
    else:
        interpretation = (
            "The latest movement does not show current anomaly behavior, and the model does not detect a strong "
            "structural suppression gap based on the available historical path."
        )

    limitations = [
        "Counterfactual forecast is model-based, not guaranteed.",
        "It estimates an alternative no-shock structural path using historical trend behavior.",
        "It does not prove the exact external cause of the suppression.",
        "It should be validated with external news, market, and fundamental evidence.",
        "It should not be treated as financial advice.",
    ]
    if anchor_limitation:
        limitations.append(anchor_limitation)

    return {
        "counterfactual_structural_forecast_3m": float(counterfactual_structural_forecast_3m),
        "current_regime_forecast_3m": float(current_regime_forecast_3m),
        "structural_suppression_gap": float(structural_suppression_gap),
        "structural_suppression_gap_pct": float(structural_suppression_gap_pct),
        "pre_shock_anchor_price": float(anchor_price),
        "pre_shock_anchor_date": str(anchor_date.date()),
        "regime_shift_score": float(latest_row["regime_shift_score"]),
        "regime_shift_flag": regime_shift_flag,
        "regime_shift_threshold": float(regime_shift_threshold),
        "regime_shift_threshold_basis": regime_shift_threshold_basis,
        "suppression_materiality_threshold_pct": float(materiality_threshold_pct),
        "suppressed_but_not_currently_anomalous_flag": suppressed_flag,
        "structural_suppression_interpretation": interpretation,
        "counterfactual_layer_limitations": limitations,
    }


def generate_three_month_forecast(
    raw_df: pd.DataFrame,
    reference_results: pd.DataFrame,
    config: ResearchConfig,
    residual_std: float,
    forecast_weights: dict[str, float],
    conformal_q80: float,
    conformal_q95: float,
) -> pd.DataFrame:
    history = reference_results.sort_values("date").reset_index(drop=True).copy()
    latest = history.iloc[-1]
    recent = history.tail(max(40, min(120, len(history)))).copy()

    last_date = pd.Timestamp(raw_df["date"].max())
    scenario_price = float(latest["actual_price"])
    latest_close = float(latest["actual_price"])
    fair_value_level = float(latest["structural_expected_price"])

    fair_series = recent["structural_expected_price"].replace(0, np.nan).dropna()
    if len(fair_series) >= 2:
        fair_drift = np.log(fair_series / fair_series.shift(1)).dropna().tail(20).mean()
    else:
        fair_drift = 0.0
    fair_drift = float(np.clip(fair_drift, -0.0015, 0.0015))

    market_returns = recent["return_1d"].replace([np.inf, -np.inf], np.nan).dropna().tail(20)
    market_drift = float(np.clip(market_returns.mean() if not market_returns.empty else 0.0, -0.0010, 0.0010))

    if bool(latest["structural_value_signal"]) or bool(latest["downside_band_break"]):
        reversion_speed = 0.08
    elif recent["downside_band_break"].tail(15).any():
        reversion_speed = 0.06
    else:
        reversion_speed = 0.03

    sigma = max(float(residual_std), 1e-6)
    drift_log_return = float(
        np.clip(recent["log_return_1d"].replace([np.inf, -np.inf], np.nan).dropna().tail(20).mean(), -0.0030, 0.0030)
        if recent["log_return_1d"].replace([np.inf, -np.inf], np.nan).dropna().shape[0] > 0
        else 0.0
    )
    forecast_rows: list[dict[str, Any]] = []

    for step in range(1, config.forecast_horizon_days + 1):
        next_date = (last_date + BDay(1)).normalize()
        fair_value_level *= math.exp(fair_drift)
        gap = fair_value_level - scenario_price
        price_change = market_drift * scenario_price + reversion_speed * gap
        scenario_price = max(0.01, scenario_price + price_change)

        naive_price = latest_close
        drift_price = max(0.01, latest_close * math.exp(drift_log_return * step))
        ensemble_price = (
            forecast_weights["scenario_lstm_forecast"] * scenario_price
            + forecast_weights["naive_random_walk_forecast"] * naive_price
            + forecast_weights["moving_average_drift_forecast"] * drift_price
        )

        scaled_q80 = conformal_q80 * math.sqrt(step)
        scaled_q95 = max(conformal_q95 * math.sqrt(step), config.forecast_interval_z * sigma * math.sqrt(step))
        lower_80 = max(0.01, ensemble_price - scaled_q80)
        upper_80 = ensemble_price + scaled_q80
        lower_95 = max(0.01, ensemble_price - scaled_q95)
        upper_95 = ensemble_price + scaled_q95

        forecast_rows.append(
            {
                "date": next_date,
                "scenario_lstm_close": scenario_price,
                "naive_random_walk_close": naive_price,
                "moving_average_drift_close": drift_price,
                "ensemble_predicted_close": ensemble_price,
                "predicted_close": ensemble_price,
                "fair_value_anchor": fair_value_level,
                "lower_80": lower_80,
                "upper_80": upper_80,
                "lower_95": lower_95,
                "upper_95": upper_95,
                "forecast_step": step,
            }
        )
        last_date = next_date

    return pd.DataFrame(forecast_rows)


def _fallback_local_contributions(
    model: RandomForestRegressor,
    latest_row: pd.Series,
    train_features: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    importances = pd.Series(model.feature_importances_, index=feature_columns)
    centered = latest_row[feature_columns] - train_features[feature_columns].median()
    scores = importances * centered.abs()
    signs = np.sign(centered).replace(0, 1)
    contributions = scores * signs
    result = (
        contributions.sort_values(key=np.abs, ascending=False)
        .rename_axis("feature")
        .reset_index(name="raw_contribution")
    )
    return result


def compute_shap_explanations(
    model: RandomForestRegressor,
    train_features: pd.DataFrame,
    test_features: pd.DataFrame,
    config: ResearchConfig,
) -> dict[str, Any]:
    latest_row = test_features.iloc[-1]
    feature_columns = list(train_features.columns)

    if shap is None:
        local_df = _fallback_local_contributions(model, latest_row, train_features, feature_columns)
        top_factors = local_df.head(config.top_k_explanation)
        rolling_top_features = []
        for start in range(0, max(1, len(test_features) - config.esi_window + 1), config.esi_step):
            window = test_features.iloc[start : start + config.esi_window]
            if window.empty:
                continue
            weighted = pd.Series(model.feature_importances_, index=feature_columns) * window.std().fillna(0)
            rolling_top_features.append(weighted.sort_values(ascending=False).head(config.esi_top_k).index.tolist())
        method = "feature_importance_fallback"
        window_overlap_scores = []
    else:
        explainer = shap.TreeExplainer(model)
        latest_explanation = explainer(test_features.tail(1))
        latest_values = np.asarray(latest_explanation.values)[0]
        local_df = pd.DataFrame(
            {
                "feature": feature_columns,
                "raw_contribution": latest_values,
            }
        ).sort_values("raw_contribution", key=np.abs, ascending=False)
        top_factors = local_df.head(config.top_k_explanation)
        rolling_top_features = []
        window_overlap_scores = []
        max_start = max(1, len(test_features) - config.esi_window + 1)
        for start in range(0, max_start, config.esi_step):
            window = test_features.iloc[start : start + config.esi_window]
            if window.empty:
                continue
            window_exp = explainer(window)
            window_values = np.asarray(window_exp.values)
            mean_abs = np.abs(window_values).mean(axis=0)
            top = pd.Series(mean_abs, index=feature_columns).sort_values(ascending=False).head(config.esi_top_k).index.tolist()
            rolling_top_features.append(top)
        method = "tree_shap"

    if shap is None:
        for idx in range(1, len(rolling_top_features)):
            prev = set(rolling_top_features[idx - 1])
            cur = set(rolling_top_features[idx])
            window_overlap_scores.append(len(prev & cur) / max(1, config.esi_top_k))
    else:
        for idx in range(1, len(rolling_top_features)):
            prev = set(rolling_top_features[idx - 1])
            cur = set(rolling_top_features[idx])
            window_overlap_scores.append(len(prev & cur) / max(1, config.esi_top_k))

    latest_esi = float(window_overlap_scores[-1]) if window_overlap_scores else float("nan")
    mean_esi = float(np.mean(window_overlap_scores)) if window_overlap_scores else float("nan")
    min_esi = float(np.min(window_overlap_scores)) if window_overlap_scores else float("nan")
    max_esi = float(np.max(window_overlap_scores)) if window_overlap_scores else float("nan")
    number_of_windows_used = int(len(rolling_top_features))

    abs_total = float(local_df["raw_contribution"].abs().sum()) or 1.0
    local_df["contribution"] = local_df["raw_contribution"].abs() / abs_total
    top_factors = local_df.head(config.top_k_explanation)
    explanation_stability_score = latest_esi if not math.isnan(latest_esi) else mean_esi
    if math.isnan(explanation_stability_score):
        explanation_stability_comment = "Low"
    elif explanation_stability_score >= 0.80:
        explanation_stability_comment = "High"
    elif explanation_stability_score >= 0.50:
        explanation_stability_comment = "Moderate"
    else:
        explanation_stability_comment = "Low"
    if math.isnan(explanation_stability_score):
        esi_interpretation = "unstable"
    elif explanation_stability_score >= 0.80:
        esi_interpretation = "highly stable"
    elif explanation_stability_score >= 0.50:
        esi_interpretation = "moderately stable"
    else:
        esi_interpretation = "unstable"
    dominance_warning = ""
    if not top_factors.empty and float(top_factors.iloc[0]["contribution"]) > 0.80:
        dominant_label = FEATURE_LABELS.get(str(top_factors.iloc[0]["feature"]), str(top_factors.iloc[0]["feature"]))
        dominance_warning = (
            f"Explanation is stable, but dominated by {dominant_label.lower()}, so interpretation should be treated as volume-led."
            if dominant_label == "Trading Volume"
            else f"Explanation is stable, but dominated by {dominant_label.lower()}, so interpretation should be treated as factor-led."
        )

    return {
        "method": method,
        "shap_backend": method,
        "shap_explanation_target": "surrogate_liquidity_anomaly_score",
        "shap_explanation_note": "SHAP explains the surrogate anomaly-score model, not the LSTM internals directly.",
        "top_factors": [
            {
                "feature": FEATURE_LABELS.get(str(row["feature"]), str(row["feature"])),
                "feature_key": str(row["feature"]),
                "contribution": float(row["contribution"]),
                "raw_contribution": float(row["raw_contribution"]),
            }
            for _, row in top_factors.iterrows()
        ],
        "local_contributions": local_df.reset_index(drop=True),
        "rolling_top_features": rolling_top_features,
        "esi_latest": latest_esi,
        "esi_mean": mean_esi,
        "esi_min": min_esi,
        "esi_max": max_esi,
        "number_of_windows_used": number_of_windows_used,
        "esi_interpretation": esi_interpretation,
        "explanation_stability_comment": explanation_stability_comment,
        "dominance_warning": dominance_warning,
        "top_feature_contribution_percentage": (
            float(top_factors.iloc[0]["contribution"] * 100.0) if not top_factors.empty else math.nan
        ),
    }


def build_simple_explanation(top_factors: list[dict[str, Any]], anomaly_detected: bool) -> str:
    if not top_factors:
        if anomaly_detected:
            return "The abnormal movement did not produce a stable explainability profile."
        return "The latest movement is within the model's normal range, but the explainability profile was unavailable."

    preferred_phrases = {
        "Trading Volume": ("higher trading volume", "lower trading volume"),
        "Liquidity Volume Ratio": ("higher trading volume", "lower trading volume"),
        "Volatility": ("increased volatility", "lower volatility"),
        "Volatility 10D": ("increased volatility", "lower volatility"),
        "Volatility 5D": ("increased volatility", "lower volatility"),
        "Momentum": ("stronger momentum", "weaker momentum"),
        "Momentum 5D": ("stronger momentum", "weaker momentum"),
        "Momentum 3D": ("stronger momentum", "weaker momentum"),
        "Moving Average Gap": ("a wider moving-average gap", "a narrower moving-average gap"),
        "1D Return": ("strong recent returns", "weaker recent returns"),
        "Intraday Range": ("a wider intraday range", "a narrower intraday range"),
        "Open-Close Change": ("a stronger open-close move", "a weaker open-close move"),
        "ATR 14D": ("a higher average true range", "a lower average true range"),
        "RSI 14D": ("stronger relative strength", "weaker relative strength"),
    }

    def phrase(item: dict[str, Any]) -> str:
        feature = str(item["feature"])
        contribution = float(item.get("raw_contribution", item["contribution"]))
        if feature in preferred_phrases:
            positive, negative = preferred_phrases[feature]
            return positive if contribution >= 0 else negative
        direction = "higher" if contribution >= 0 else "lower"
        return f"{direction} {feature.lower()}"

    if len(top_factors) == 1:
        joined = phrase(top_factors[0])
    elif len(top_factors) == 2:
        joined = f"{phrase(top_factors[0])} and {phrase(top_factors[1])}"
    else:
        joined = ", ".join(phrase(item) for item in top_factors[:-1])
        joined += f", and {phrase(top_factors[-1])}"

    prefix = (
        "The abnormal movement was mainly influenced by "
        if anomaly_detected
        else "The latest movement is within the model's normal range. The score behaviour was mainly influenced by "
    )
    return prefix + f"{joined}."


def run_research_pipeline(config: ResearchConfig) -> dict[str, Any]:
    set_random_seed(config.random_seed)

    raw_df = load_stock_history(config.stock_code, config.data_dir)
    audit_df = build_data_audit(raw_df)
    data_quality_summary = build_data_quality_summary(raw_df)
    data_source_note = build_data_source_note(raw_df)
    engineered_df = engineer_features(raw_df)
    model_df = prepare_model_frame(
        engineered_df,
        feature_columns=DEFAULT_FEATURE_COLUMNS,
        max_rows=config.max_rows,
    )

    X_all, y_all, rows_all = create_sequences(
        model_df,
        feature_columns=DEFAULT_FEATURE_COLUMNS,
        lookback=config.lookback,
    )
    if len(X_all) < 100:
        raise ValueError("Not enough sequence observations to run the research pipeline.")

    train_end, val_end = split_indices(
        n_obs=len(X_all),
        test_fraction=config.test_fraction,
        val_fraction=config.val_fraction,
    )

    X_train, X_val, X_test = X_all[:train_end], X_all[train_end:val_end], X_all[val_end:]
    y_train, y_val, y_test = y_all[:train_end], y_all[train_end:val_end], y_all[val_end:]
    rows_train = rows_all.iloc[:train_end].reset_index(drop=True)
    rows_val = rows_all.iloc[train_end:val_end].reset_index(drop=True)
    rows_test = rows_all.iloc[val_end:].reset_index(drop=True)
    naive_train = pd.to_numeric(rows_train["prev_close"], errors="coerce").astype(float).to_numpy()
    naive_val = pd.to_numeric(rows_val["prev_close"], errors="coerce").astype(float).to_numpy()
    naive_test = pd.to_numeric(rows_test["prev_close"], errors="coerce").astype(float).to_numpy()

    model, feature_scaler, target_scaler, history = train_lstm_model(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        config=config,
    )

    pred_train = predict_lstm(model, X_train, feature_scaler, target_scaler)
    pred_val = predict_lstm(model, X_val, feature_scaler, target_scaler)
    pred_test = predict_lstm(model, X_test, feature_scaler, target_scaler)

    train_results = rows_train.copy()
    train_results["predicted_price"] = pred_train
    train_results["actual_price"] = y_train
    train_results["naive_baseline_predicted_price"] = naive_train
    train_results = add_anomaly_columns(
        train_results,
        volume_scale=config.volume_scale,
        epsilon=config.liquidity_epsilon,
    )

    val_results = rows_val.copy()
    val_results["predicted_price"] = pred_val
    val_results["actual_price"] = y_val
    val_results["naive_baseline_predicted_price"] = naive_val
    val_results = add_anomaly_columns(
        val_results,
        volume_scale=config.volume_scale,
        epsilon=config.liquidity_epsilon,
    )

    prediction_band_selection = calibrate_prediction_bands(
        train_results=train_results,
        val_results=val_results,
        config=config,
    )
    downside_band = float(prediction_band_selection["downside_band"])
    upside_band = float(prediction_band_selection["upside_band"])

    train_results = add_anomaly_columns(
        rows_train.assign(
            predicted_price=pred_train,
            actual_price=y_train,
            naive_baseline_predicted_price=naive_train,
        ),
        volume_scale=config.volume_scale,
        epsilon=config.liquidity_epsilon,
        downside_band=downside_band,
        upside_band=upside_band,
        structural_gap_threshold_pct=0.0,
    )
    val_results = add_anomaly_columns(
        rows_val.assign(
            predicted_price=pred_val,
            actual_price=y_val,
            naive_baseline_predicted_price=naive_val,
        ),
        volume_scale=config.volume_scale,
        epsilon=config.liquidity_epsilon,
        downside_band=downside_band,
        upside_band=upside_band,
        structural_gap_threshold_pct=0.0,
    )
    structural_gap_threshold_pct = calibrate_structural_gap_threshold(
        train_results=train_results,
        val_results=val_results,
        config=config,
    )
    train_results = add_anomaly_columns(
        rows_train.assign(
            predicted_price=pred_train,
            actual_price=y_train,
            naive_baseline_predicted_price=naive_train,
        ),
        volume_scale=config.volume_scale,
        epsilon=config.liquidity_epsilon,
        downside_band=downside_band,
        upside_band=upside_band,
        structural_gap_threshold_pct=structural_gap_threshold_pct,
    )
    val_results = add_anomaly_columns(
        rows_val.assign(
            predicted_price=pred_val,
            actual_price=y_val,
            naive_baseline_predicted_price=naive_val,
        ),
        volume_scale=config.volume_scale,
        epsilon=config.liquidity_epsilon,
        downside_band=downside_band,
        upside_band=upside_band,
        structural_gap_threshold_pct=structural_gap_threshold_pct,
    )

    threshold_selection = calibrate_final_anomaly_logic(
        train_results=train_results,
        val_results=val_results,
        config=config,
    )
    anomaly_threshold = float(threshold_selection["liquidity_threshold"])
    prediction_band_threshold = float(threshold_selection["prediction_band_threshold"])
    medium_threshold = float(train_results["liquidity_aware_anomaly_score"].quantile(0.75))
    high_threshold = float(train_results["liquidity_aware_anomaly_score"].quantile(0.90))

    train_results = add_anomaly_columns(
        rows_train.assign(
            predicted_price=pred_train,
            actual_price=y_train,
            naive_baseline_predicted_price=naive_train,
        ),
        volume_scale=config.volume_scale,
        epsilon=config.liquidity_epsilon,
        downside_band=downside_band,
        upside_band=upside_band,
        structural_gap_threshold_pct=structural_gap_threshold_pct,
        liquidity_threshold=anomaly_threshold,
        prediction_band_threshold=prediction_band_threshold,
    )
    train_results["risk_level"] = train_results.apply(
        lambda row: classify_risk(
            float(row["liquidity_aware_anomaly_score"]),
            medium_threshold,
            high_threshold,
            float(row["prediction_band_severity"]),
        ),
        axis=1,
    )
    train_results = enforce_anomaly_risk_floor(train_results)

    val_results = add_anomaly_columns(
        rows_val.assign(
            predicted_price=pred_val,
            actual_price=y_val,
            naive_baseline_predicted_price=naive_val,
        ),
        volume_scale=config.volume_scale,
        epsilon=config.liquidity_epsilon,
        downside_band=downside_band,
        upside_band=upside_band,
        structural_gap_threshold_pct=structural_gap_threshold_pct,
        liquidity_threshold=anomaly_threshold,
        prediction_band_threshold=prediction_band_threshold,
    )
    val_results["risk_level"] = val_results.apply(
        lambda row: classify_risk(
            float(row["liquidity_aware_anomaly_score"]),
            medium_threshold,
            high_threshold,
            float(row["prediction_band_severity"]),
        ),
        axis=1,
    )
    val_results = enforce_anomaly_risk_floor(val_results)

    test_results = rows_test.copy()
    test_results["predicted_price"] = pred_test
    test_results["actual_price"] = y_test
    test_results["naive_baseline_predicted_price"] = naive_test
    test_results = add_anomaly_columns(
        test_results,
        volume_scale=config.volume_scale,
        epsilon=config.liquidity_epsilon,
        downside_band=downside_band,
        upside_band=upside_band,
        structural_gap_threshold_pct=structural_gap_threshold_pct,
        liquidity_threshold=anomaly_threshold,
        prediction_band_threshold=prediction_band_threshold,
    )
    test_results["risk_level"] = test_results.apply(
        lambda row: classify_risk(
            float(row["liquidity_aware_anomaly_score"]),
            medium_threshold,
            high_threshold,
            float(row["prediction_band_severity"]),
        ),
        axis=1,
    )
    test_results = enforce_anomaly_risk_floor(test_results)
    anomaly_pressure_layer = apply_anomaly_pressure_scores(
        train_results=train_results,
        val_results=val_results,
        test_results=test_results,
        config=config,
    )
    train_results = anomaly_pressure_layer["train_results"]
    val_results = anomaly_pressure_layer["val_results"]
    test_results = anomaly_pressure_layer["test_results"]
    for frame in (train_results, val_results, test_results):
        frame["anomaly_pressure_threshold"] = anomaly_pressure_layer["anomaly_pressure_threshold"]
        frame["anomaly_pressure_p95"] = anomaly_pressure_layer["anomaly_pressure_p95"]
        frame["anomaly_pressure_threshold_basis"] = anomaly_pressure_layer["anomaly_pressure_threshold_basis"]
        frame["external_data_limitations"] = anomaly_pressure_layer["external_data_limitations"]

    train_results["split"] = "train"
    val_results["split"] = "validation"
    test_results["split"] = "test"
    regime_shift_layer = apply_regime_shift_scores(
        train_results=train_results,
        val_results=val_results,
        test_results=test_results,
        config=config,
    )
    train_results = regime_shift_layer["train_results"]
    val_results = regime_shift_layer["val_results"]
    test_results = regime_shift_layer["test_results"]

    prediction_metrics = compute_prediction_metrics(y_test, pred_test)
    price_regression_directional_metrics = compute_directional_metrics(
        y_test,
        pred_test,
        test_results["prev_close"].to_numpy(dtype=float),
    )
    prediction_metrics["directional_accuracy"] = price_regression_directional_metrics["directional_accuracy"]
    naive_baseline_metrics = compute_prediction_metrics(y_test, naive_test)
    naive_directional_metrics = compute_directional_metrics(
        y_test,
        naive_test,
        test_results["prev_close"].to_numpy(dtype=float),
    )
    naive_baseline_metrics["directional_accuracy"] = naive_directional_metrics["directional_accuracy"]
    lstm_vs_naive_comparison = build_lstm_vs_naive_comparison(
        prediction_metrics,
        naive_baseline_metrics,
    )
    combined_results = pd.concat([train_results, val_results, test_results], ignore_index=True)
    direction_df, latest_direction_feature_row = build_direction_dataset(combined_results, config)
    direction_results = run_direction_model_comparison(direction_df, config)
    direction_model_comparison = direction_results["multiclass_comparison"].copy()
    binary_direction_model_comparison = direction_results["binary_comparison"].copy()
    best_direction_model = direction_results["best_multiclass_model"]
    best_binary_direction_model = direction_results["best_binary_model"]
    best_direction_model_name = str(best_direction_model["model"])
    best_direction_test_record = (
        direction_model_comparison[
            (direction_model_comparison["split"] == "test")
            & (direction_model_comparison["model"] == best_direction_model_name)
        ]
        .head(1)
        .to_dict(orient="records")
    )
    best_direction_test_metrics = best_direction_test_record[0] if best_direction_test_record else {}
    best_binary_direction_model_name = str(best_binary_direction_model["model"])
    best_binary_test_record = (
        binary_direction_model_comparison[
            (binary_direction_model_comparison["split"] == "test")
            & (binary_direction_model_comparison["model"] == best_binary_direction_model_name)
        ]
        .head(1)
        .to_dict(orient="records")
    )
    best_binary_test_metrics = best_binary_test_record[0] if best_binary_test_record else {}
    selective_direction_results = calibrate_selective_direction_threshold(
        direction_results["best_binary_validation_predictions"],
        direction_results["best_binary_test_predictions"],
        config,
    )
    selective_direction_threshold = float(selective_direction_results["selected_threshold"])
    selective_direction_test_metrics = selective_direction_results["selected_test_metrics"]
    next_day_direction_prediction = predict_next_day_direction(
        latest_direction_feature_row,
        direction_results,
        config,
    )
    selective_direction_signal = predict_next_day_selective_direction_signal(
        latest_direction_feature_row,
        direction_results,
        selective_direction_threshold,
        config,
    )
    directional_metrics = {
        "task": "three_class",
        "neutral_threshold_basis": "rolling_volatility_20 * 0.10",
        "directional_accuracy": float(best_direction_test_metrics.get("directional_accuracy", math.nan)),
        "balanced_accuracy": float(best_direction_test_metrics.get("balanced_accuracy", math.nan)),
        "macro_f1": float(best_direction_test_metrics.get("macro_f1", math.nan)),
        "down_precision": float(best_direction_test_metrics.get("down_precision", math.nan)),
        "down_recall": float(best_direction_test_metrics.get("down_recall", math.nan)),
        "neutral_precision": float(best_direction_test_metrics.get("neutral_precision", math.nan)),
        "neutral_recall": float(best_direction_test_metrics.get("neutral_recall", math.nan)),
        "up_precision": float(best_direction_test_metrics.get("up_precision", math.nan)),
        "up_recall": float(best_direction_test_metrics.get("up_recall", math.nan)),
        "support_down": int(best_direction_test_metrics.get("support_down", 0)),
        "support_neutral": int(best_direction_test_metrics.get("support_neutral", 0)),
        "support_up": int(best_direction_test_metrics.get("support_up", 0)),
        "predicted_down_count": int(best_direction_test_metrics.get("predicted_down_count", 0)),
        "predicted_neutral_count": int(best_direction_test_metrics.get("predicted_neutral_count", 0)),
        "predicted_up_count": int(best_direction_test_metrics.get("predicted_up_count", 0)),
        "direction_confusion_matrix": best_direction_test_metrics.get("direction_confusion_matrix", {}),
        "binary_direction_comparison": {
            "best_model": best_binary_direction_model,
            "test_metrics": best_binary_test_metrics,
        },
    }
    direction_prediction_note = (
        "Directional prediction was improved by adding a dedicated classification layer instead of relying only on "
        "next-price regression. Because daily stock returns contain noise, a neutral movement class was introduced "
        "to avoid forcing very small movements into up/down predictions. Direction is evaluated as classification "
        "quality only and does not imply profitable trading accuracy."
    )
    selective_direction_note = (
        "The model does not force a direction every day. Directional output is provided only when the model "
        "confidence exceeds the validation-selected threshold; otherwise the dashboard reports No Signal."
    )
    anomaly_comparison, anomaly_method_split_metrics, anomaly_confusion_matrices = build_anomaly_method_comparison(
        train_results=train_results,
        val_results=val_results,
        test_results=test_results,
        feature_columns=DEFAULT_FEATURE_COLUMNS,
        config=config,
        lstm_threshold=anomaly_threshold,
        prediction_band_threshold=prediction_band_threshold,
    )
    test_support_positive = int(test_results["proxy_anomaly_label"].sum())
    best_anomaly_method = summarize_best_anomaly_method(
        anomaly_comparison,
        test_support_positive=test_support_positive,
    )
    support_warning = build_support_warning(test_support_positive)
    price_baseline_walk_forward_folds, price_baseline_walk_forward_aggregate = build_lightweight_walk_forward_summary(
        test_results,
        fold_count=config.walk_forward_folds,
    )
    threshold_basis = (
        "Validation-only calibration on the chronological validation split using a train/validation quantile grid. "
        "Thresholds are selected before the test split is evaluated."
    )
    threshold_calibration_summary = {
        "threshold_basis": threshold_basis,
        "threshold_percentile": round(
            float((train_results["liquidity_aware_anomaly_score"] <= anomaly_threshold).mean()) * 100.0,
            4,
        ),
        "prediction_band_threshold_percentile": round(
            float((train_results["prediction_band_severity"] <= prediction_band_threshold).mean()) * 100.0,
            4,
        ),
        "validation_split_used_for_threshold": "chronological_validation_split",
        "predicted_positive_rate_validation": round(
            float(threshold_selection["validation_metrics"]["predicted_positive_rate"]),
            6,
        ),
        "actual_proxy_positive_rate_validation": round(
            float(val_results["proxy_anomaly_label"].mean()),
            6,
        ),
        "actual_proxy_positive_rate_test": round(
            float(test_results["proxy_anomaly_label"].mean()),
            6,
        ),
    }
    formula_validation_diff = (
        test_results["liquidity_aware_anomaly_score"].astype(float)
        - (
            test_results["deviation"].astype(float)
            / (test_results["volume_scaled"].astype(float) + float(config.liquidity_epsilon))
        )
    ).abs()
    zero_volume_rows = test_results[test_results["zero_volume_flag"]].copy()
    zero_volume_formula_pass = bool(
        zero_volume_rows.empty
        or (
            (
                zero_volume_rows["liquidity_aware_anomaly_score"].astype(float)
                - (
                    zero_volume_rows["deviation"].astype(float)
                    / (
                        zero_volume_rows["volume_scaled"].astype(float)
                        + float(config.liquidity_epsilon)
                    )
                )
            ).abs().max()
            < 1e-9
        )
    )
    proxy_anomaly_label_construction = (
        "Proxy labels are generated from market-stress windows plus extreme realized price, volatility, and volume conditions. "
        "They are not manually verified CSE event labels, so anomaly evaluation is proxy-label evaluation rather than real-world ground truth."
    )

    explain_train = pd.concat([rows_train, rows_val], ignore_index=True)
    explain_target = pd.concat([train_results, val_results], ignore_index=True)[
        "liquidity_aware_anomaly_score"
    ]
    explain_model = RandomForestRegressor(
        n_estimators=config.surrogate_estimators,
        random_state=config.random_seed,
        min_samples_leaf=5,
    )
    explain_model.fit(explain_train[EXPLAIN_FEATURE_COLUMNS], explain_target)
    explanation = compute_shap_explanations(
        model=explain_model,
        train_features=explain_train[EXPLAIN_FEATURE_COLUMNS],
        test_features=test_results[EXPLAIN_FEATURE_COLUMNS],
        config=config,
    )

    forecast_backtest_bundle = calibrate_forecast_ensemble(
        val_results=val_results,
        test_results=test_results,
        config=config,
    )
    val_forecast_backtest = forecast_backtest_bundle["validation_backtest"]
    test_forecast_backtest = forecast_backtest_bundle["test_backtest"]
    for base_frame, forecast_frame in (
        (val_results, val_forecast_backtest),
        (test_results, test_forecast_backtest),
    ):
        for column in [
            "scenario_lstm_forecast",
            "naive_random_walk_forecast",
            "moving_average_drift_forecast",
            "ensemble_forecast",
            "lower_80",
            "upper_80",
            "lower_95",
            "upper_95",
            "interval_80_contains_actual",
            "interval_95_contains_actual",
            "forecast_signed_residual",
        ]:
            base_frame[column] = forecast_frame[column].to_numpy()
    walk_forward_validation = build_forecast_walk_forward_validation(
        history_frame=combined_results,
        evaluation_frame=test_forecast_backtest,
        direction_prediction_frame=direction_results["best_test_predictions"],
        fold_count=config.walk_forward_folds,
    )
    walk_forward_aggregate = pd.DataFrame(
        [
            {
                "mae_mean": float(walk_forward_validation["mae"].mean()),
                "mae_std": float(walk_forward_validation["mae"].std(ddof=0)),
                "rmse_mean": float(walk_forward_validation["rmse"].mean()),
                "rmse_std": float(walk_forward_validation["rmse"].std(ddof=0)),
                "mape_mean": float(walk_forward_validation["mape"].mean()),
                "mape_std": float(walk_forward_validation["mape"].std(ddof=0)),
                "directional_accuracy_mean": float(walk_forward_validation["directional_accuracy"].mean()),
                "directional_accuracy_std": float(walk_forward_validation["directional_accuracy"].std(ddof=0)),
                "balanced_directional_accuracy_mean": float(
                    walk_forward_validation["balanced_directional_accuracy"].mean()
                ),
                "balanced_directional_accuracy_std": float(
                    walk_forward_validation["balanced_directional_accuracy"].std(ddof=0)
                ),
                "interval_95_coverage_mean": float(walk_forward_validation["interval_95_coverage"].mean()),
                "interval_95_coverage_std": float(walk_forward_validation["interval_95_coverage"].std(ddof=0)),
            }
        ]
    )
    forecast_reliability_metrics = compute_forecast_reliability_metrics(
        test_forecast_backtest,
        walk_forward_validation,
    )
    forecast_reliability_note = (
        "Forecast reliability was improved by adding backtested conformal prediction intervals and ensemble "
        "scenario forecasting. Therefore reliability is evaluated not only by point forecast error, but also by "
        "whether the forecast intervals contain actual prices at the expected rate."
    )

    residual_std = float(
        np.std(
            np.concatenate(
                [
                    val_results["actual_price"].to_numpy() - val_results["predicted_price"].to_numpy(),
                    test_results["actual_price"].to_numpy() - test_results["predicted_price"].to_numpy(),
                ]
            ),
            ddof=0,
        )
    )
    forecast_3m = generate_three_month_forecast(
        raw_df=raw_df,
        reference_results=test_results,
        config=config,
        residual_std=residual_std,
        forecast_weights=forecast_backtest_bundle["weights"],
        conformal_q80=forecast_backtest_bundle["conformal_q80"],
        conformal_q95=forecast_backtest_bundle["conformal_q95"],
    )

    latest_row = test_results.iloc[-1]
    top_shap_factors = explanation["top_factors"]
    recent_anomaly_summary = summarize_recent_anomalies(
        test_results=test_results,
        recent_window=config.recent_anomaly_window,
    )
    if forecast_reliability_metrics["forecast_reliability_score"] >= 7.0:
        forecast_risk_warning = (
            "Backtested interval coverage is reasonably calibrated, but the 3-month path remains a scenario rather "
            "than a guaranteed future price."
        )
    elif forecast_reliability_metrics["forecast_reliability_score"] >= 5.0:
        forecast_risk_warning = (
            "Forecast reliability is moderate: interval calibration is informative, but the path still carries "
            "meaningful uncertainty and should be interpreted cautiously."
        )
    else:
        forecast_risk_warning = (
            "Forecast reliability remains limited: the intervals are informative, but uncertainty is high and the "
            "path should not be treated as a precise future outcome."
        )
    forecast_summary = {
        "forecast_basis": "anomaly_adjusted_structural_reversion_scenario",
        "forecast_heading": "3-Month Model-Based Scenario Forecast",
        "forecast_start_date": str(forecast_3m.iloc[0]["date"].date()),
        "forecast_end_date": str(forecast_3m.iloc[-1]["date"].date()),
        "forecast_start_price": round(float(forecast_3m.iloc[0]["predicted_close"]), 4),
        "forecast_end_price": round(float(forecast_3m.iloc[-1]["predicted_close"]), 4),
        "forecast_end_fair_value_anchor": round(float(forecast_3m.iloc[-1]["fair_value_anchor"]), 4),
        "lower_80": round(float(forecast_3m.iloc[-1]["lower_80"]), 4),
        "upper_80": round(float(forecast_3m.iloc[-1]["upper_80"]), 4),
        "lower_95": round(float(forecast_3m.iloc[-1]["lower_95"]), 4),
        "upper_95": round(float(forecast_3m.iloc[-1]["upper_95"]), 4),
        "forecast_end_lower_80": round(float(forecast_3m.iloc[-1]["lower_80"]), 4),
        "forecast_end_upper_80": round(float(forecast_3m.iloc[-1]["upper_80"]), 4),
        "forecast_end_lower_95": round(float(forecast_3m.iloc[-1]["lower_95"]), 4),
        "forecast_end_upper_95": round(float(forecast_3m.iloc[-1]["upper_95"]), 4),
        "forecast_3m_return_pct": round(
            float(forecast_3m.iloc[-1]["predicted_close"] / latest_row["actual_price"] - 1.0) * 100.0,
            4,
        ),
        "uncertainty_width": round(float(forecast_3m.iloc[-1]["upper_95"] - forecast_3m.iloc[-1]["lower_95"]), 4),
        "forecast_model_weights": {
            key: round(float(value), 6) for key, value in forecast_backtest_bundle["weights"].items()
        },
        "forecast_note": (
            "This is a model-based scenario forecast, not guaranteed, and not financial advice."
        ),
        "risk_warning": forecast_risk_warning,
    }
    latest_row = test_results.iloc[-1].copy()
    latest_row["anomaly_pressure_threshold"] = anomaly_pressure_layer["anomaly_pressure_threshold"]
    latest_row["anomaly_pressure_p95"] = anomaly_pressure_layer["anomaly_pressure_p95"]
    latest_row["anomaly_pressure_threshold_basis"] = anomaly_pressure_layer["anomaly_pressure_threshold_basis"]
    latest_row["external_data_limitations"] = anomaly_pressure_layer["external_data_limitations"]
    shock_adjusted_layer = build_shock_adjusted_anomaly_layer(
        latest_row=latest_row,
        forecast_summary=forecast_summary,
        forecast_reliability_metrics=forecast_reliability_metrics,
        config=config,
    )
    counterfactual_layer = build_counterfactual_structural_suppression_layer(
        combined_regime_results=regime_shift_layer["combined"],
        latest_row=latest_row,
        current_regime_forecast_3m=shock_adjusted_layer["anomaly_adjusted_forecast_3m"],
        regime_shift_threshold=regime_shift_layer["regime_shift_threshold"],
        regime_shift_threshold_basis=regime_shift_layer["regime_shift_threshold_basis"],
        materiality_threshold_pct=regime_shift_layer["suppression_materiality_threshold_pct"],
    )
    output_payload = {
        "selected_stock": normalize_stock_code(config.stock_code),
        "analysis_date": str(pd.Timestamp(raw_df["date"].max()).date()),
        "formula": FORMULA_TEXT,
        "predicted_price": round(float(latest_row["predicted_price"]), 4),
        "actual_price": round(float(latest_row["actual_price"]), 4),
        "signed_residual": round(float(latest_row["signed_residual"]), 4),
        "deviation": round(float(latest_row["deviation"]), 4),
        "volume": int(latest_row["volume"]),
        "volume_scaled": round(float(latest_row["volume_scaled"]), 6),
        "epsilon": float(config.liquidity_epsilon),
        "anomaly_threshold": round(anomaly_threshold, 6),
        "prediction_band_threshold": round(prediction_band_threshold, 6),
        "structural_gap_threshold_pct": round(float(structural_gap_threshold_pct) * 100.0, 4),
        "threshold_basis": threshold_basis,
        "anomaly_threshold_basis": (
            "Validation-calibrated final anomaly logic. "
            "liquidity_anomaly_flag uses the liquidity-aware anomaly score threshold below; "
            "final_anomaly_detected = liquidity_anomaly_flag OR prediction_band_anomaly_flag. "
            "structural_value_signal is reported separately and is not OR-ed into final_anomaly_detected."
        ),
        "anomaly_detected": bool(latest_row["final_anomaly_detected"]),
        "final_anomaly_detected": bool(latest_row["final_anomaly_detected"]),
        "direction_signal": (
            selective_direction_signal["signal_label"]
            if selective_direction_signal["signal_label"] != "No Signal"
            else next_day_direction_prediction["direction_label"]
        ),
        "anomaly_side": str(latest_row["anomaly_side"]),
        "liquidity_anomaly_flag": bool(latest_row["liquidity_anomaly_flag"]),
        "prediction_band_anomaly_flag": bool(latest_row["prediction_band_anomaly_flag"]),
        "structural_value_signal": bool(latest_row["structural_value_signal"]),
        "liquidity_aware_anomaly_score": round(
            float(latest_row["liquidity_aware_anomaly_score"]), 6
        ),
        "structural_expected_price": round(float(latest_row["structural_expected_price"]), 4),
        "structural_discount": round(float(latest_row["structural_discount"]), 4),
        "structural_discount_pct": round(float(latest_row["structural_discount_pct"]) * 100.0, 4),
        "value_opportunity_flag": bool(latest_row["structural_value_signal"]),
        "market_confirmed_score": round(float(latest_row["market_confirmed_score"]), 6),
        "prediction_band_lower": round(float(latest_row["prediction_band_lower"]), 4),
        "prediction_band_upper": round(float(latest_row["prediction_band_upper"]), 4),
        "downside_band_break": bool(latest_row["downside_band_break"]),
        "upside_band_break": bool(latest_row["upside_band_break"]),
        "risk_level": str(latest_row["risk_level"]),
        "data_source_note": data_source_note,
        "data_quality_summary": data_quality_summary.iloc[0].to_dict(),
        "prediction_metrics": {
            key: round(float(value), 6) if isinstance(value, (float, np.floating)) and not math.isnan(float(value)) else value
            for key, value in prediction_metrics.items()
        },
        "naive_baseline_metrics": {
            key: round(float(value), 6) if isinstance(value, (float, np.floating)) and not math.isnan(float(value)) else value
            for key, value in naive_baseline_metrics.items()
        },
        "lstm_vs_naive_comparison": {
            key: round(float(value), 6) if isinstance(value, (float, np.floating)) and not math.isnan(float(value)) else value
            for key, value in lstm_vs_naive_comparison.items()
        },
        "price_regression_directional_metrics": price_regression_directional_metrics,
        "directional_metrics": directional_metrics,
        "best_direction_model": {
            **best_direction_model,
            "binary_reference": best_binary_direction_model,
        },
        "direction_model_comparison": {
            "three_class": _native_records(direction_model_comparison),
            "binary": _native_records(binary_direction_model_comparison),
        },
        "direction_confusion_matrix": directional_metrics["direction_confusion_matrix"],
        "next_day_direction_prediction": next_day_direction_prediction["direction_label"],
        "next_day_direction_confidence": (
            round(float(next_day_direction_prediction["confidence"]), 6)
            if math.isfinite(float(next_day_direction_prediction["confidence"]))
            else None
        ),
        "direction_prediction_note": direction_prediction_note,
        "selective_direction_signal": selective_direction_signal["signal_label"],
        "selective_direction_confidence": (
            round(float(selective_direction_signal["confidence"]), 6)
            if math.isfinite(float(selective_direction_signal["confidence"]))
            else None
        ),
        "selective_direction_threshold": round(float(selective_direction_threshold), 6),
        "selective_direction_metrics": {
            "selection_split": selective_direction_results["selection_split"],
            "selected_threshold_basis": selective_direction_results["selected_threshold_basis"],
            "coverage_floor": round(float(selective_direction_results["coverage_floor"]), 6),
            "coverage_constraint_met": bool(selective_direction_results["coverage_constraint_met"]),
            "selected_validation_metrics": {
                key: round(float(value), 6) if isinstance(value, (float, np.floating)) and not math.isnan(float(value)) else value
                for key, value in selective_direction_results["selected_validation_metrics"].items()
            },
            "selected_test_metrics": {
                key: round(float(value), 6) if isinstance(value, (float, np.floating)) and not math.isnan(float(value)) else value
                for key, value in selective_direction_test_metrics.items()
            },
            "validation_threshold_table": _native_records(selective_direction_results["validation_threshold_table"]),
            "test_threshold_table": _native_records(selective_direction_results["test_threshold_table"]),
            "note": selective_direction_note,
        },
        "signal_coverage_rate": (
            round(float(selective_direction_test_metrics.get("signal_coverage_rate", math.nan)), 6)
            if isinstance(selective_direction_test_metrics, dict)
            and math.isfinite(float(selective_direction_test_metrics.get("signal_coverage_rate", math.nan)))
            else None
        ),
        "no_signal_rate": (
            round(float(selective_direction_test_metrics.get("no_signal_rate", math.nan)), 6)
            if isinstance(selective_direction_test_metrics, dict)
            and math.isfinite(float(selective_direction_test_metrics.get("no_signal_rate", math.nan)))
            else None
        ),
        "anomaly_comparison": _native_records(anomaly_comparison),
        "best_anomaly_method": best_anomaly_method,
        "anomaly_method_split_metrics_summary": _native_records(anomaly_method_split_metrics),
        "support_warning": support_warning,
        "threshold_calibration": threshold_calibration_summary,
        "walk_forward_validation": {
            "method_note": (
                "This is a lightweight chronological backtest summary across contiguous folds of the saved test window. "
                "It preserves time order and reports ensemble price error, direction-classification accuracy, and 95% "
                "interval coverage without fully retraining the LSTM in every fold."
            ),
            "fold_count": int(config.walk_forward_folds),
            "fold_metrics": _native_records(walk_forward_validation),
            "aggregate_metrics": _native_records(walk_forward_aggregate),
            "price_baseline_fold_metrics": _native_records(price_baseline_walk_forward_folds),
            "price_baseline_aggregate_metrics": _native_records(price_baseline_walk_forward_aggregate),
        },
        "top_shap_factors": [
            {
                "feature": factor["feature"],
                "contribution": round(float(factor["contribution"]), 6),
            }
            for factor in top_shap_factors
        ],
        "shap_backend": explanation["shap_backend"],
        "shap_explanation_target": explanation["shap_explanation_target"],
        "shap_explanation_note": explanation["shap_explanation_note"],
        "top_feature_contribution_percentage": round(
            float(explanation["top_feature_contribution_percentage"])
            if not math.isnan(float(explanation["top_feature_contribution_percentage"]))
            else float("nan"),
            6,
        ),
        "esi_latest": round(
            float(explanation["esi_latest"]) if not math.isnan(explanation["esi_latest"]) else float("nan"),
            6,
        ),
        "esi_mean": round(
            float(explanation["esi_mean"]) if not math.isnan(explanation["esi_mean"]) else float("nan"),
            6,
        ),
        "esi_min": round(
            float(explanation["esi_min"]) if not math.isnan(explanation["esi_min"]) else float("nan"),
            6,
        ),
        "esi_max": round(
            float(explanation["esi_max"]) if not math.isnan(explanation["esi_max"]) else float("nan"),
            6,
        ),
        "number_of_windows_used": int(explanation["number_of_windows_used"]),
        "esi_score": round(
            float(explanation["esi_latest"]) if not math.isnan(explanation["esi_latest"]) else float(explanation["esi_mean"]),
            6,
        ),
        "esi_interpretation": explanation["esi_interpretation"],
        "explanation_stability_comment": explanation["explanation_stability_comment"],
        "dominance_warning": explanation["dominance_warning"],
        "simple_explanation": build_simple_explanation(
            top_shap_factors,
            anomaly_detected=bool(latest_row["final_anomaly_detected"]),
        ),
        "thin_trading_diagnostics": {
            "zero_volume_flag": bool(latest_row["zero_volume_flag"]),
            "low_volume_flag": bool(latest_row["low_volume_flag"]),
            "thin_trading_flag": bool(latest_row["thin_trading_flag"]),
            "rolling_volume_median_20": (
                round(float(latest_row["rolling_volume_median_20"]), 4)
                if pd.notna(latest_row["rolling_volume_median_20"])
                else None
            ),
            "relative_volume": (
                round(float(latest_row["relative_volume"]), 6)
                if pd.notna(latest_row["relative_volume"])
                else None
            ),
            "zero_volume_count": int(data_quality_summary.iloc[0]["zero_volume_count"]),
            "formula_validation_max_diff": float(formula_validation_diff.max()) if len(formula_validation_diff) else 0.0,
            "zero_volume_formula_validation_pass": zero_volume_formula_pass,
        },
        "proxy_anomaly_label_construction": proxy_anomaly_label_construction,
        "recent_anomaly_summary": recent_anomaly_summary,
        "forecast_basis": forecast_summary["forecast_basis"],
        "forecast_reliability_metrics": {
            key: round(float(value), 6) if isinstance(value, (float, np.floating)) and not math.isnan(float(value)) else value
            for key, value in forecast_reliability_metrics.items()
        },
        "forecast_reliability_score": round(float(forecast_reliability_metrics["forecast_reliability_score"]), 6),
        "forecast_reliability_interpretation": forecast_reliability_metrics["forecast_reliability_interpretation"],
        "forecast_interval_coverage": {
            "interval_80_coverage": round(float(forecast_reliability_metrics["interval_80_coverage"]), 6),
            "interval_95_coverage": round(float(forecast_reliability_metrics["interval_95_coverage"]), 6),
        },
        "forecast_bias": round(float(forecast_reliability_metrics["forecast_bias"]), 6),
        "forecast_model_weights": {
            key: round(float(value), 6) for key, value in forecast_backtest_bundle["weights"].items()
        },
        "forecast_reliability_note": forecast_reliability_note,
        "forecast_3m": forecast_summary,
        "ensemble_forecast_3m": {
            "forecast_start_price": forecast_summary["forecast_start_price"],
            "forecast_end_price": forecast_summary["forecast_end_price"],
            "lower_80": forecast_summary["lower_80"],
            "upper_80": forecast_summary["upper_80"],
            "lower_95": forecast_summary["lower_95"],
            "upper_95": forecast_summary["upper_95"],
        },
        "structural_forecast_3m": round(float(shock_adjusted_layer["structural_forecast_3m"]), 6),
        "anomaly_adjusted_forecast_3m": round(float(shock_adjusted_layer["anomaly_adjusted_forecast_3m"]), 6),
        "current_price": round(float(shock_adjusted_layer["current_price"]), 6),
        "recovery_gap": round(float(shock_adjusted_layer["recovery_gap"]), 6),
        "recovery_gap_pct": round(float(shock_adjusted_layer["recovery_gap_pct"]), 6),
        "target_price": round(float(shock_adjusted_layer["target_price"]), 6),
        "target_price_basis": shock_adjusted_layer["target_price_basis"],
        "target_breakout_probability": round(float(shock_adjusted_layer["target_breakout_probability"]), 6),
        "anomaly_adjusted_breakout_probability": round(
            float(shock_adjusted_layer["anomaly_adjusted_breakout_probability"]), 6
        ),
        "target_breakout_interpretation": shock_adjusted_layer["target_breakout_interpretation"],
        "anomaly_pressure_score": round(float(shock_adjusted_layer["anomaly_pressure_score"]), 6),
        "anomaly_pressure_threshold": round(float(shock_adjusted_layer["anomaly_pressure_threshold"]), 6),
        "anomaly_pressure_threshold_basis": shock_adjusted_layer["anomaly_pressure_threshold_basis"],
        "temporary_anomaly_drag_flag": bool(shock_adjusted_layer["temporary_anomaly_drag_flag"]),
        "anomaly_penalty_pct": round(float(shock_adjusted_layer["anomaly_penalty_pct"]), 6),
        "anomaly_type": shock_adjusted_layer["anomaly_type"],
        "shock_adjusted_explanation": shock_adjusted_layer["shock_adjusted_explanation"],
        "external_data_limitations": shock_adjusted_layer["external_data_limitations"],
        "counterfactual_structural_forecast_3m": round(
            float(counterfactual_layer["counterfactual_structural_forecast_3m"]), 6
        ),
        "current_regime_forecast_3m": round(float(counterfactual_layer["current_regime_forecast_3m"]), 6),
        "structural_suppression_gap": round(float(counterfactual_layer["structural_suppression_gap"]), 6),
        "structural_suppression_gap_pct": round(
            float(counterfactual_layer["structural_suppression_gap_pct"]), 6
        ),
        "pre_shock_anchor_price": round(float(counterfactual_layer["pre_shock_anchor_price"]), 6),
        "pre_shock_anchor_date": counterfactual_layer["pre_shock_anchor_date"],
        "regime_shift_score": round(float(counterfactual_layer["regime_shift_score"]), 6),
        "regime_shift_flag": bool(counterfactual_layer["regime_shift_flag"]),
        "regime_shift_threshold": round(float(counterfactual_layer["regime_shift_threshold"]), 6),
        "regime_shift_threshold_basis": counterfactual_layer["regime_shift_threshold_basis"],
        "suppression_materiality_threshold_pct": round(
            float(counterfactual_layer["suppression_materiality_threshold_pct"]), 6
        ),
        "suppressed_but_not_currently_anomalous_flag": bool(
            counterfactual_layer["suppressed_but_not_currently_anomalous_flag"]
        ),
        "structural_suppression_interpretation": counterfactual_layer[
            "structural_suppression_interpretation"
        ],
        "counterfactual_layer_limitations": counterfactual_layer["counterfactual_layer_limitations"],
        "novelty_statement": NOVELTY_STATEMENT,
        "limitations": [
            "Anomaly labels are proxy labels, not manually verified CSE event labels.",
            support_warning if support_warning else None,
            data_source_note,
            "Low MAPE does not guarantee profitable trading performance.",
            "Directional prediction is evaluated as classification quality only; it should not be presented as guaranteed trading accuracy.",
            "SHAP explains a surrogate anomaly-score model, not internal LSTM gates.",
            "The forecast is scenario-based, interval-calibrated, not guaranteed, and not financial advice.",
            shock_adjusted_layer["external_data_limitations"],
            "Counterfactual structural suppression is model-based and should be validated with external market, news, and fundamental evidence.",
            "Data source should be validated against official CSE/MyCSE when possible.",
        ],
    }
    output_payload["limitations"] = [item for item in output_payload["limitations"] if item]

    return {
        "config": asdict(config),
        "data_audit": audit_df,
        "data_quality_summary": data_quality_summary,
        "data_source_note": data_source_note,
        "raw_data": raw_df,
        "engineered_data": engineered_df,
        "model_frame": model_df,
        "train_results": train_results,
        "val_results": val_results,
        "test_results": test_results,
        "prediction_metrics": prediction_metrics,
        "naive_baseline_metrics": naive_baseline_metrics,
        "price_regression_directional_metrics": price_regression_directional_metrics,
        "directional_metrics": directional_metrics,
        "direction_model_comparison": direction_model_comparison,
        "binary_direction_model_comparison": binary_direction_model_comparison,
        "best_direction_model": best_direction_model,
        "best_binary_direction_model": best_binary_direction_model,
        "selective_direction_results": selective_direction_results,
        "lstm_vs_naive_comparison": lstm_vs_naive_comparison,
        "anomaly_comparison": anomaly_comparison,
        "anomaly_method_split_metrics": anomaly_method_split_metrics,
        "anomaly_confusion_matrices": anomaly_confusion_matrices,
        "forecast_component_backtest": forecast_backtest_bundle["component_backtest"],
        "forecast_reliability_metrics": forecast_reliability_metrics,
        "forecast_backtest_validation": val_forecast_backtest,
        "forecast_backtest_test": test_forecast_backtest,
        "forecast_model_weights": forecast_backtest_bundle["weights"],
        "shock_adjusted_layer": shock_adjusted_layer,
        "counterfactual_layer": counterfactual_layer,
        "regime_shift_layer": regime_shift_layer,
        "anomaly_threshold_selection": threshold_selection,
        "threshold_calibration": threshold_calibration_summary,
        "prediction_band_selection": {
            **prediction_band_selection,
            "structural_gap_threshold_pct": structural_gap_threshold_pct,
            "prediction_band_threshold": prediction_band_threshold,
        },
        "training_history": history,
        "explanation": explanation,
        "walk_forward_validation": walk_forward_validation,
        "walk_forward_fold_metrics": walk_forward_validation,
        "walk_forward_aggregate_metrics": walk_forward_aggregate,
        "price_baseline_walk_forward_fold_metrics": price_baseline_walk_forward_folds,
        "price_baseline_walk_forward_aggregate_metrics": price_baseline_walk_forward_aggregate,
        "forecast_3m": forecast_3m,
        "dashboard_output": output_payload,
    }


def save_research_artifacts(results: dict[str, Any], artifact_dir: str | Path | None = None) -> dict[str, Path]:
    config = results["config"]
    stock_code = normalize_stock_code(config["stock_code"])
    base_dir = Path(artifact_dir or config["artifact_dir"])
    base_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "dashboard_output": base_dir / f"{stock_code.lower()}_dashboard_output.json",
        "prediction_metrics": base_dir / f"{stock_code.lower()}_prediction_metrics.json",
        "naive_baseline_metrics": base_dir / f"{stock_code.lower()}_naive_baseline_metrics.json",
        "direction_model_comparison": base_dir / f"{stock_code.lower()}_direction_model_comparison.csv",
        "binary_direction_model_comparison": base_dir / f"{stock_code.lower()}_binary_direction_model_comparison.csv",
        "selective_direction_threshold_search": base_dir / f"{stock_code.lower()}_selective_direction_threshold_search.csv",
        "anomaly_comparison": base_dir / f"{stock_code.lower()}_anomaly_comparison.csv",
        "anomaly_method_split_metrics": base_dir / f"{stock_code.lower()}_anomaly_method_split_metrics.csv",
        "anomaly_confusion_matrices": base_dir / f"{stock_code.lower()}_anomaly_confusion_matrices.csv",
        "anomaly_threshold_search": base_dir / f"{stock_code.lower()}_anomaly_threshold_search.csv",
        "prediction_band_selection": base_dir / f"{stock_code.lower()}_prediction_band_selection.json",
        "test_results": base_dir / f"{stock_code.lower()}_test_results.csv",
        "forecast_3m": base_dir / f"{stock_code.lower()}_forecast_3m.csv",
        "forecast_component_backtest": base_dir / f"{stock_code.lower()}_forecast_component_backtest.csv",
        "forecast_reliability_metrics": base_dir / f"{stock_code.lower()}_forecast_reliability_metrics.json",
        "walk_forward_validation": base_dir / f"{stock_code.lower()}_walk_forward_validation.csv",
        "walk_forward_fold_metrics": base_dir / f"{stock_code.lower()}_walk_forward_fold_metrics.csv",
        "walk_forward_aggregate_metrics": base_dir / f"{stock_code.lower()}_walk_forward_aggregate_metrics.csv",
        "threshold_calibration": base_dir / f"{stock_code.lower()}_threshold_calibration.json",
        "data_audit": base_dir / f"{stock_code.lower()}_data_audit.csv",
        "data_quality_summary": base_dir / f"{stock_code.lower()}_data_quality_summary.csv",
        "top_factors": base_dir / f"{stock_code.lower()}_top_factors.csv",
    }

    paths["dashboard_output"].write_text(
        json.dumps(results["dashboard_output"], indent=2),
        encoding="utf-8",
    )
    paths["prediction_metrics"].write_text(
        json.dumps(results["prediction_metrics"], indent=2),
        encoding="utf-8",
    )
    paths["naive_baseline_metrics"].write_text(
        json.dumps(results["naive_baseline_metrics"], indent=2),
        encoding="utf-8",
    )
    results["direction_model_comparison"].to_csv(paths["direction_model_comparison"], index=False)
    results["binary_direction_model_comparison"].to_csv(paths["binary_direction_model_comparison"], index=False)
    results["selective_direction_results"]["validation_threshold_table"].to_csv(
        paths["selective_direction_threshold_search"],
        index=False,
    )
    results["anomaly_comparison"].to_csv(paths["anomaly_comparison"], index=False)
    results["anomaly_method_split_metrics"].to_csv(paths["anomaly_method_split_metrics"], index=False)
    results["anomaly_confusion_matrices"].to_csv(paths["anomaly_confusion_matrices"], index=False)
    results["anomaly_threshold_selection"]["search_table"].to_csv(
        paths["anomaly_threshold_search"],
        index=False,
    )
    paths["prediction_band_selection"].write_text(
        json.dumps(results["prediction_band_selection"], indent=2),
        encoding="utf-8",
    )
    results["test_results"].to_csv(paths["test_results"], index=False)
    results["forecast_3m"].to_csv(paths["forecast_3m"], index=False)
    results["forecast_component_backtest"].to_csv(paths["forecast_component_backtest"], index=False)
    paths["forecast_reliability_metrics"].write_text(
        json.dumps(results["forecast_reliability_metrics"], indent=2),
        encoding="utf-8",
    )
    results["walk_forward_validation"].to_csv(paths["walk_forward_validation"], index=False)
    results["walk_forward_fold_metrics"].to_csv(paths["walk_forward_fold_metrics"], index=False)
    results["walk_forward_aggregate_metrics"].to_csv(paths["walk_forward_aggregate_metrics"], index=False)
    paths["threshold_calibration"].write_text(
        json.dumps(results["threshold_calibration"], indent=2),
        encoding="utf-8",
    )
    results["data_audit"].to_csv(paths["data_audit"], index=False)
    results["data_quality_summary"].to_csv(paths["data_quality_summary"], index=False)
    results["explanation"]["local_contributions"].to_csv(paths["top_factors"], index=False)

    return paths

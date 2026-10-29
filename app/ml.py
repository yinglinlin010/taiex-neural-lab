"""PyTorch models, purged walk-forward evaluation, and NumPy teaching trace."""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge

MODEL_NAMES = {"mlp": "MLP", "rnn": "RNN", "lstm": "LSTM", "gru": "GRU", "tcn": "TCN"}


@dataclass
class TrainingConfig:
    epochs: int = 25
    batch_size: int = 64
    hidden_units: int = 32
    hidden_layers: int = 2
    hidden_sizes: list[int] | None = None
    dropout: float = 0.1
    learning_rate: float = 0.001
    optimizer: str = "adam"
    loss: str = "mse"
    seed: int = 42


def _model(kind: str, n_features: int, lookback: int, config: TrainingConfig) -> nn.Module:
    if kind == "mlp":
        widths = config.hidden_sizes or [config.hidden_units] * config.hidden_layers
        layers: list[nn.Module] = [nn.Flatten(), nn.Linear(n_features * lookback, widths[0]), nn.ReLU()]
        for previous, width in zip(widths, widths[1:]):
            layers += [nn.Dropout(config.dropout), nn.Linear(previous, width), nn.ReLU()]
        layers += [nn.Dropout(config.dropout), nn.Linear(widths[-1], 1)]
        return _MlpRegressor(nn.Sequential(*layers))
    if kind == "tcn":
        # Fixed two-block causal TCN; deliberately independent of recurrent
        # depth/hidden-width controls so comparisons use a stable small budget.
        channels = 16
        return _TcnRegressor(n_features, channels, dropout=config.dropout)
    module = {"rnn": nn.RNN, "lstm": nn.LSTM, "gru": nn.GRU}[kind]
    core = module(
        input_size=n_features,
        hidden_size=config.hidden_units,
        num_layers=config.hidden_layers,
        batch_first=True,
        dropout=config.dropout if config.hidden_layers > 1 else 0.0,
    )
    return _RecurrentRegressor(core, config.hidden_units, kind)


class _RecurrentRegressor(nn.Module):
    def __init__(self, core: nn.Module, hidden_units: int, kind: str):
        super().__init__()
        self.core = core
        self.kind = kind
        self.output = nn.Linear(hidden_units, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output = self.core(x)
        sequence = output[0]
        return self.output(sequence[:, -1, :]).squeeze(-1)


class _MlpRegressor(nn.Module):
    def __init__(self, network: nn.Module):
        super().__init__()
        self.network = network

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x).squeeze(-1)


class _CausalConv1d(nn.Module):
    def __init__(self, channels: int, kernel_size: int, dilation: int):
        super().__init__()
        self.left_padding = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(channels, channels, kernel_size, dilation=dilation)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(nn.functional.pad(x, (self.left_padding, 0)))


class _TcnBlock(nn.Module):
    def __init__(self, channels: int, dilation: int, dropout: float):
        super().__init__()
        self.first = _CausalConv1d(channels, kernel_size=3, dilation=dilation)
        self.second = _CausalConv1d(channels, kernel_size=3, dilation=dilation)
        self.dropout = nn.Dropout(dropout)
        self.activation = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.dropout(self.activation(self.first(x)))
        x = self.dropout(self.activation(self.second(x)))
        return self.activation(x + residual)

    def forward_prefix(self, x: torch.Tensor, end: int) -> torch.Tensor:
        residual = x[:, :, :end]
        x = self.dropout(self.activation(self.first(x)[:, :, :end]))
        x = self.dropout(self.activation(self.second(x)[:, :, :end]))
        return self.activation(x + residual)


class _TcnRegressor(nn.Module):
    def __init__(self, n_features: int, channels: int, dropout: float):
        super().__init__()
        self.input = nn.Conv1d(n_features, channels, kernel_size=1)
        self.blocks = nn.Sequential(_TcnBlock(channels, 1, dropout), _TcnBlock(channels, 2, dropout))
        self.output = nn.Linear(channels, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        sequence = self.blocks(self.input(x.transpose(1, 2)))
        return self.output(sequence[:, :, -1]).squeeze(-1)

    def prefix_representation(self, x: torch.Tensor, end: int) -> torch.Tensor:
        """Return hidden state at an earlier time; used to verify causality."""
        if end < 1 or end > x.shape[1]:
            raise ValueError("prefix end must be within the sequence")
        values = self.input(x.transpose(1, 2))
        for block in self.blocks:
            values = block.forward_prefix(values, end)
        return values[:, :, end - 1]


def _seed_everything(seed: int) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.set_num_threads(1)


def _rank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    sorted_values = values[order]
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and sorted_values[j] == sorted_values[i]:
            j += 1
        ranks[order[i:j]] = (i + j - 1) / 2 + 1
        i = j
    return ranks


def _metrics(actual: np.ndarray, predicted: np.ndarray, benchmark: float | np.ndarray | None = None) -> dict[str, float]:
    error = predicted.astype(float) - actual.astype(float)
    mae = float(np.mean(np.abs(error)))
    rmse = float(np.sqrt(np.mean(error**2)))
    denom_baseline = np.mean(actual) if benchmark is None else benchmark
    denominator = float(np.sum((actual - denom_baseline) ** 2))
    r2 = 1.0 - float(np.sum(error**2)) / denominator if denominator > 1e-15 else 0.0
    rank_a, rank_p = _rank(actual), _rank(predicted)
    rank_a -= rank_a.mean(); rank_p -= rank_p.mean()
    rank_denominator = float(np.linalg.norm(rank_a) * np.linalg.norm(rank_p))
    spearman = float(np.dot(rank_a, rank_p) / rank_denominator) if rank_denominator > 1e-15 else 0.0
    # A flat (zero) forecast is treated as neutral and receives half credit,
    # rather than an automatic miss because sign(0) is neither up nor down.
    actual_sign = np.sign(actual)
    predicted_sign = np.sign(predicted)
    direction_score = np.where(predicted_sign == 0, 0.5, (actual_sign == predicted_sign).astype(float))
    direction = float(np.mean(direction_score))
    return {"mae": mae, "rmse": rmse, "r2": r2, "spearman": spearman, "directionAccuracy": direction}


def _traditional_predictions(x_train: np.ndarray, y_train: np.ndarray, x_eval: np.ndarray, seed: int) -> dict[str, np.ndarray]:
    train = x_train.reshape(len(x_train), -1).astype(np.float64)
    evaluate = x_eval.reshape(len(x_eval), -1).astype(np.float64)
    mean = train.mean(axis=0, keepdims=True)
    scale = train.std(axis=0, keepdims=True)
    scale = np.where(scale < 1e-8, 1.0, scale)
    ridge = Ridge(alpha=1.0)
    ridge.fit((train - mean) / scale, y_train)
    forest = RandomForestRegressor(
        n_estimators=80, max_features=0.8, min_samples_leaf=3,
        random_state=seed, n_jobs=1,
    )
    forest.fit(train, y_train)
    return {"ridge": ridge.predict((evaluate - mean) / scale), "forest": forest.predict(evaluate)}


def _fit_predict(
    kind: str,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    x_eval_targets: np.ndarray | None,
    config: TrainingConfig,
    seed: int,
    cancel: threading.Event | None = None,
    epoch_callback: Callable[[int, float], None] | None = None,
    trace_callback: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[np.ndarray, list[float], list[float], int]:
    _seed_everything(seed)
    n_features = x_train.shape[-1]
    lookback = x_train.shape[1]
    mean = x_train.reshape(-1, n_features).mean(axis=0, keepdims=True)
    scale = x_train.reshape(-1, n_features).std(axis=0, keepdims=True)
    scale = np.where(scale < 1e-8, 1.0, scale)
    x_train_scaled = ((x_train - mean.reshape(1, 1, -1)) / scale.reshape(1, 1, -1)).astype(np.float32)
    x_eval_scaled = ((x_eval - mean.reshape(1, 1, -1)) / scale.reshape(1, 1, -1)).astype(np.float32)
    # Target return scaling (Gu, Kelly, Xiu 2020 / LeCun 1998): scale percentage targets
    # to avoid vanishing gradients in small return variance (~10^-4) and unscale at inference.
    target_scale = 100.0
    validation_history: list[float] = []
    train_x = torch.from_numpy(x_train_scaled)
    train_y = torch.from_numpy((y_train * target_scale).astype(np.float32))
    dataset = TensorDataset(train_x, train_y)
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(dataset, batch_size=min(config.batch_size, len(dataset)), shuffle=True, generator=generator)
    model = _model(kind, n_features, lookback, config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate) if config.optimizer == "adam" else torch.optim.SGD(model.parameters(), lr=config.learning_rate, momentum=0.9)
    loss_fn: nn.Module = nn.MSELoss() if config.loss == "mse" else nn.SmoothL1Loss()
    history: list[float] = []
    for epoch in range(config.epochs):
        if cancel and cancel.is_set():
            raise InterruptedError("實驗已取消。")
        model.train()
        total_loss = 0.0
        seen = 0
        for batch_x, batch_y in loader:
            optimizer.zero_grad(set_to_none=True)
            prediction = model(batch_x)
            loss = loss_fn(prediction, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            total_loss += float(loss.detach()) * len(batch_y)
            seen += len(batch_y)
        # Record loss in original unscaled variance units
        mean_loss = (total_loss / max(seen, 1)) / (target_scale**2)
        history.append(mean_loss)
        model.eval()
        if x_eval_targets is not None:
            with torch.no_grad():
                evaluated = model(torch.from_numpy(x_eval_scaled))
                val_loss = float(loss_fn(evaluated, torch.from_numpy((x_eval_targets * target_scale).astype(np.float32)))) / (target_scale**2)
            validation_history.append(val_loss)
        if epoch_callback:
            epoch_callback(epoch + 1, mean_loss)
    model.eval()
    with torch.no_grad():
        eval_tensor = torch.from_numpy(x_eval_scaled)
        prediction = (model(eval_tensor).cpu().numpy()) / target_scale
        if trace_callback and len(eval_tensor):
            captured: list[dict[str, Any]] = []
            hooks = []

            def capture(name: str):
                def hook(_module: nn.Module, _inputs: tuple[torch.Tensor, ...], output: Any) -> None:
                    value = output[0] if isinstance(output, tuple) else output
                    if isinstance(value, torch.Tensor):
                        if value.ndim == 3:
                            value = value[:, -1, :]
                        captured.append({"name": name, "type": type(_module).__name__, "values": value[0].detach().cpu().flatten().tolist()})
                return hook

            for name, module in model.named_modules():
                if isinstance(module, (nn.Linear, nn.ReLU)):
                    hooks.append(module.register_forward_hook(capture(name or "output")))
            with torch.no_grad():
                trace_prediction = model(eval_tensor[:1]).item() / target_scale
            for hook in hooks:
                hook.remove()
            learned_weights = [
                {"name": name, "values": module.weight.detach().cpu().tolist()}
                for name, module in model.named_modules() if isinstance(module, nn.Linear)
            ]
            learned_biases = [
                {"name": name, "values": module.bias.detach().cpu().tolist() if module.bias is not None else []}
                for name, module in model.named_modules() if isinstance(module, nn.Linear)
            ]
            trace_callback({
                "input": x_eval_scaled[0].flatten().astype(float).tolist(),
                "inputShape": list(x_eval_scaled[0].shape),
                "layers": captured,
                "weights": learned_weights,
                "biases": learned_biases,
                "prediction": float(trace_prediction),
                "actual": float(x_eval_targets[0]) if x_eval_targets is not None else None,
                "targetScale": target_scale,
            })
    return prediction.astype(np.float64), history, validation_history, sum(p.numel() for p in model.parameters())


def pre_test_training_indices(samples: dict[str, Any]) -> np.ndarray:
    """Use only labels fully observed before the locked final-test boundary."""
    return np.flatnonzero(samples["targets"] < int(samples["split_index"]))


def fit_deployment_artifact(samples: dict[str, Any], kind: str, config: TrainingConfig,
                            cancel: threading.Event | None = None) -> dict[str, Any]:
    """Fit the selected network before the locked boundary and serialize inference state."""
    split = int(samples["split_index"])
    train_idx = pre_test_training_indices(samples)
    if len(train_idx) < 250:
        raise ValueError("鎖定測試邊界前的訓練樣本不足，無法建立紙上推論模型。")
    _seed_everything(config.seed)
    x_train, y_train = samples["x"][train_idx], samples["y"][train_idx]
    n_features, lookback = x_train.shape[-1], x_train.shape[1]
    mean = x_train.reshape(-1, n_features).mean(axis=0, keepdims=True)
    scale = x_train.reshape(-1, n_features).std(axis=0, keepdims=True)
    scale = np.where(scale < 1e-8, 1.0, scale)
    scaled = ((x_train - mean.reshape(1, 1, -1)) / scale.reshape(1, 1, -1)).astype(np.float32)
    model = _model(kind, n_features, lookback, config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate) if config.optimizer == "adam" else torch.optim.SGD(model.parameters(), lr=config.learning_rate, momentum=0.9)
    loss_fn: nn.Module = nn.MSELoss() if config.loss == "mse" else nn.SmoothL1Loss()
    generator = torch.Generator().manual_seed(config.seed)
    loader = DataLoader(TensorDataset(torch.from_numpy(scaled), torch.from_numpy((y_train * 100).astype(np.float32))),
                        batch_size=min(config.batch_size, len(train_idx)), shuffle=True, generator=generator)
    for _ in range(config.epochs):
        if cancel and cancel.is_set():
            raise InterruptedError("實驗已取消。")
        model.train()
        for batch_x, batch_y in loader:
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(batch_x), batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
    latest_training_target = int(samples["targets"][train_idx].max())
    return {
        "model": kind, "lookback": lookback, "features": list(samples["selected_features"]),
        "horizon": int(samples["horizon"]), "returnType": samples["return_type"],
        "trainingThrough": samples["dates"][latest_training_target], "targetScale": 100.0,
        "testBoundary": samples["dates"][split],
        "featureMean": mean.flatten().astype(float).tolist(), "featureScale": scale.flatten().astype(float).tolist(),
        "state": {key: value.detach().cpu().tolist() for key, value in model.state_dict().items()},
        "architecture": {"hiddenUnits": config.hidden_units, "hiddenLayers": config.hidden_layers,
                         "hiddenSizes": config.hidden_sizes, "dropout": config.dropout},
    }


def predict_with_artifact(artifact: dict[str, Any], feature_window: np.ndarray) -> float:
    """Run one frozen model prediction over [lookback, feature] causal inputs."""
    x = np.asarray(feature_window, dtype=np.float32)
    mean, scale = np.asarray(artifact["featureMean"], dtype=np.float32), np.asarray(artifact["featureScale"], dtype=np.float32)
    if x.shape != (int(artifact["lookback"]), len(artifact["features"])) or not np.isfinite(x).all():
        raise ValueError("神經網路輸入視窗形狀錯誤或含非有限值。")
    if mean.shape != (x.shape[1],) or scale.shape != mean.shape or not np.isfinite(mean).all() or not np.isfinite(scale).all() or (scale <= 0).any():
        raise ValueError("模型特徵標準化參數無效。")
    architecture = artifact["architecture"]
    config = TrainingConfig(hidden_units=int(architecture["hiddenUnits"]), hidden_layers=int(architecture["hiddenLayers"]),
                            hidden_sizes=list(architecture["hiddenSizes"]), dropout=float(architecture["dropout"]))
    model = _model(artifact["model"], x.shape[1], x.shape[0], config)
    model.load_state_dict({key: torch.tensor(value, dtype=torch.float32) for key, value in artifact["state"].items()}, strict=True)
    model.eval()
    scaled = ((x - mean) / scale).astype(np.float32)
    with torch.no_grad():
        prediction = float(model(torch.from_numpy(scaled[None, ...])).item() / float(artifact["targetScale"]))
    if not math.isfinite(prediction):
        raise ValueError("神經網路產生非有限預測值。")
    return prediction


def config_from_request(request: dict[str, Any]) -> TrainingConfig:
    return TrainingConfig(
        epochs=int(request.get("epochs", 25)),
        batch_size=int(request.get("batchSize", 64)),
        hidden_units=int(request.get("hiddenUnits", 32)),
        hidden_layers=int(request.get("hiddenLayers", 2)),
        hidden_sizes=[int(value) for value in request.get("hiddenSizes", [64, 32, 16])],
        dropout=float(request.get("dropout", 0.1)),
        learning_rate=float(request.get("learningRate", 0.001)),
        optimizer=str(request.get("optimizer", "adam")),
        loss=str(request.get("loss", "mse")),
        seed=int(request.get("seed", 42)),
    )


def run_validation(
    samples: dict[str, Any],
    model_types: list[str],
    config: TrainingConfig,
    cancel: threading.Event,
    progress: Callable[[int, str], None],
) -> dict[str, Any]:
    from .data import walk_forward_folds

    folds = walk_forward_folds(samples)
    result: dict[str, Any] = {"models": [], "folds": len(folds), "comparisons": []}
    total = len(model_types) * len(folds)
    step = 0
    target_indices = samples["targets"]
    actual_all = samples["y"]
    comparison_actual: list[float] | None = None
    comparison_mean: list[float] = []
    comparison_zero: list[float] = []
    comparison_ridge: list[float] = []
    comparison_forest: list[float] = []
    forward_trace: dict[str, Any] | None = None
    for model_index, kind in enumerate(model_types):
        model_folds = []
        all_actual: list[float] = []
        all_predicted: list[float] = []
        all_zero: list[float] = []
        all_mean: list[float] = []
        all_ridge: list[float] = []
        all_forest: list[float] = []
        all_validation_loss: list[list[float]] = []
        curves: list[list[float]] = []
        parameter_count = 0
        for fold_index, (train_idx, val_idx) in enumerate(folds, 1):
            if cancel.is_set():
                raise InterruptedError("實驗已取消。")
            step += 1
            progress(round((step - 1) / total * 88), f"{MODEL_NAMES[kind]}：訓練驗證折 {fold_index}/{len(folds)}")
            def fold_progress(epoch: int, loss: float) -> None:
                fraction = (step - 1 + epoch / config.epochs) / total
                progress(round(fraction * 88), f"{MODEL_NAMES[kind]}：驗證折 {fold_index}/{len(folds)} · epoch {epoch}/{config.epochs}")
            def capture_trace(trace: dict[str, Any]) -> None:
                nonlocal forward_trace
                if forward_trace is None:
                    forward_trace = {**trace, "model": kind, "fold": fold_index,
                        "sampleDate": samples["dates"][int(target_indices[val_idx[0]])],
                        "originDate": samples["dates"][int(samples["origins"][val_idx[0]])],
                        "features": samples["selected_features"], "lookback": samples["lookback"],
                        "returnType": samples["return_type"]}

            pred, history, validation_history, parameter_count = _fit_predict(
                kind,
                samples["x"][train_idx],
                samples["y"][train_idx],
                samples["x"][val_idx],
                samples["y"][val_idx],
                config,
                config.seed + model_index * 100 + fold_index,
                cancel,
                fold_progress,
                capture_trace if kind == "mlp" and fold_index == 1 else None,
            )
            actual = actual_all[val_idx].astype(float)
            train_mean = float(np.mean(samples["y"][train_idx]))
            metrics = _metrics(actual, pred)
            prediction_rows = [
                {
                    "date": samples["dates"][int(target_indices[target_index])],
                    "originDate": samples["dates"][int(samples["origins"][target_index])],
                    "actual": float(actual_value),
                    "predicted": float(predicted_value),
                    "residual": float(predicted_value - actual_value),
                }
                for target_index, actual_value, predicted_value in zip(val_idx, actual, pred)
            ]
            model_folds.append({
                "fold": fold_index,
                "trainSamples": len(train_idx),
                "validationSamples": len(val_idx),
                "from": samples["dates"][int(target_indices[val_idx[0]])],
                "to": samples["dates"][int(target_indices[val_idx[-1]])],
                **metrics,
                "trainLoss": history,
                "predictions": prediction_rows,
            })
            all_actual.extend(actual.tolist())
            all_predicted.extend(pred.tolist())
            all_zero.extend(np.zeros_like(actual).tolist())
            all_mean.extend(np.full_like(actual, train_mean).tolist())
            if model_index == 0:
                if comparison_actual is None:
                    comparison_actual = []
                comparison_actual.extend(actual.tolist())
                comparison_zero.extend(np.zeros_like(actual).tolist())
                comparison_mean.extend(np.full_like(actual, train_mean).tolist())
                traditional = _traditional_predictions(samples["x"][train_idx], samples["y"][train_idx], samples["x"][val_idx], config.seed + fold_index)
                comparison_ridge.extend(traditional["ridge"].astype(float).tolist())
                comparison_forest.extend(traditional["forest"].astype(float).tolist())
            curves.append(history)
            all_validation_loss.append(validation_history)
        aggregate = _metrics(np.asarray(all_actual), np.asarray(all_predicted))
        result["models"].append({
            "key": kind,
            "name": MODEL_NAMES[kind],
            "parameters": parameter_count,
            "folds": model_folds,
            **aggregate,
            "zeroBaseline": _metrics(np.asarray(all_actual), np.asarray(all_zero)),
            "meanBaseline": _metrics(np.asarray(all_actual), np.asarray(all_mean)),
            "meanTrainLoss": [float(np.mean([curve[i] for curve in curves])) for i in range(config.epochs)],
            "meanValidationLoss": [float(np.mean([curve[i] for curve in all_validation_loss])) for i in range(config.epochs)],
        })
        result["comparisons"].append({"key": kind, "name": MODEL_NAMES[kind], **_metrics(np.asarray(all_actual), np.asarray(all_predicted))})
    # Baselines use one shared chronological fold set; append every requested network.
    baseline_actual = np.asarray(comparison_actual or [], dtype=float)
    baselines = [
        ("historical_mean", "歷史平均", comparison_mean),
        ("naive", "預測零報酬", comparison_zero),
        ("ridge", "Ridge 線性迴歸", comparison_ridge),
        ("forest", "Random Forest", comparison_forest),
    ]
    result["comparisons"] = [
        {"key": key, "name": name, **_metrics(baseline_actual, np.asarray(predicted, dtype=float))}
        for key, name, predicted in baselines
    ] + result["comparisons"]
    progress(90, "整理驗證集結果與基準模型比較")
    result["validationSamples"] = sum(len(v) for _, v in folds)
    result["testBoundary"] = samples["dates"][samples["split_index"]]
    result["selectedFeatures"] = samples["selected_features"]
    result["lookback"] = samples["lookback"]
    result["horizon"] = samples["horizon"]
    result["execution"] = samples["execution"]
    result["targetDefinition"] = "close[t+1] to close[t+horizon+1]"
    result["returnType"] = samples["return_type"]
    result["forwardTrace"] = forward_trace
    result["targetRange"] = {"from": samples["dates"][int(target_indices[np.flatnonzero(target_indices < samples['split_index'])[0]])], "to": samples["dates"][samples["split_index"] - 1]}
    return result


def run_final_test(
    samples: dict[str, Any],
    model_type: str,
    config: TrainingConfig,
    cancel: threading.Event,
    progress: Callable[[int, str], None],
) -> dict[str, Any]:
    split = samples["split_index"]
    origins = samples["origins"]
    targets = samples["targets"]
    train_idx = pre_test_training_indices(samples)
    # A test label starts at origin+1, so its full target window must stay
    # beyond the locked split; samples crossing the boundary remain purged.
    test_idx = np.flatnonzero((origins >= split) & (targets > split))
    if len(train_idx) < 250 or len(test_idx) < 50:
        raise ValueError("鎖定測試集樣本不足，不能執行最終評估。")
    progress(4, f"使用前 80% 日期訓練凍結的 {MODEL_NAMES[model_type]}")
    def epoch_update(epoch: int, loss: float) -> None:
        progress(5 + round(epoch / config.epochs * 70), f"最終訓練 {epoch}/{config.epochs} · loss {loss:.6f}")
    pred, history, _, parameter_count = _fit_predict(
        model_type, samples["x"][train_idx], samples["y"][train_idx], samples["x"][test_idx],
        None,
        config, config.seed, cancel, epoch_update,
    )
    if cancel.is_set():
        raise InterruptedError("最終測試已取消，沒有揭露測試結果。")
    actual = samples["y"][test_idx].astype(float)
    zero = np.zeros_like(actual)
    historical_mean = np.full_like(actual, float(samples["y"][train_idx].mean()))
    test_dates = [samples["dates"][int(i)] for i in targets[test_idx]]
    progress(92, "計算鎖定測試指標")
    stride = max(1, len(test_idx) // 100)
    return {
        "model": model_type,
        "name": MODEL_NAMES[model_type],
        "metrics": _metrics(actual, pred),
        "zeroBaseline": _metrics(actual, zero),
        "meanBaseline": _metrics(actual, historical_mean),
        "testSamples": len(test_idx),
        "testRange": {"from": test_dates[0], "to": test_dates[-1]},
        "parameters": parameter_count,
        "trainLoss": history,
        "predictions": [
            {"date": test_dates[i], "originDate": samples["dates"][int(samples["origins"][test_idx[i]])], "actual": float(actual[i]), "predicted": float(pred[i])}
            for i in range(0, len(test_idx), stride)
        ],
        "features": samples["selected_features"],
        "horizon": samples["horizon"],
        "returnType": samples["return_type"],
    }


def numpy_mlp_trace() -> dict[str, Any]:
    """One tiny 3-2-1 tanh MLP step, with NumPy and PyTorch parity check."""
    x = np.asarray([0.02, -0.01, 0.015], dtype=np.float64)
    target = 0.01
    w1 = np.asarray([[0.2, -0.3, 0.1], [-0.4, 0.25, 0.3]], dtype=np.float64)
    b1 = np.asarray([0.01, -0.02], dtype=np.float64)
    w2 = np.asarray([[0.35, -0.2]], dtype=np.float64)
    b2 = np.asarray([0.005], dtype=np.float64)
    z1 = w1 @ x + b1
    a1 = np.tanh(z1)
    yhat = float((w2 @ a1 + b2)[0])
    # Match PyTorch MSELoss on the one-sample teaching batch (mean of squared errors).
    loss = (yhat - target) ** 2
    delta2 = 2.0 * (yhat - target)
    grad_w2 = delta2 * a1.reshape(1, -1)
    delta1 = (w2.reshape(-1) * delta2) * (1.0 - a1**2)
    grad_w1 = delta1.reshape(-1, 1) @ x.reshape(1, -1)
    lr = 0.1
    next_w1 = w1 - lr * grad_w1
    next_b1 = b1 - lr * delta1
    next_w2 = w2 - lr * grad_w2
    next_b2 = b2 - lr * delta2

    tx = torch.tensor(x, dtype=torch.float64)
    tw1 = torch.tensor(w1, dtype=torch.float64, requires_grad=True)
    tb1 = torch.tensor(b1, dtype=torch.float64, requires_grad=True)
    tw2 = torch.tensor(w2, dtype=torch.float64, requires_grad=True)
    tb2 = torch.tensor(b2, dtype=torch.float64, requires_grad=True)
    tout = tw2 @ torch.tanh(tw1 @ tx + tb1) + tb2
    tloss = torch.nn.functional.mse_loss(tout.reshape(1), torch.tensor([target], dtype=torch.float64))
    tloss.backward()
    gradient_error = max(
        float(np.max(np.abs(grad_w1 - tw1.grad.numpy()))),
        float(np.max(np.abs(grad_w2 - tw2.grad.numpy()))),
        float(np.max(np.abs(delta1 - tb1.grad.numpy()))),
        float(np.max(np.abs(np.asarray([delta2]) - tb2.grad.numpy()))),
    )
    return {
        "input": x.tolist(), "target": target,
        "equations": ["z⁽¹⁾ = W⁽¹⁾x + b⁽¹⁾", "a⁽¹⁾ = tanh(z⁽¹⁾)", "ŷ = W⁽²⁾a⁽¹⁾ + b⁽²⁾", "L = (ŷ − y)²"],
        "hiddenPreActivation": z1.tolist(), "hiddenActivation": a1.tolist(), "prediction": yhat,
        "loss": float(loss), "outputDelta": float(delta2), "hiddenDelta": delta1.tolist(),
        "gradients": {"dW1": grad_w1.tolist(), "db1": delta1.tolist(), "dW2": grad_w2.tolist(), "db2": float(delta2)},
        "learningRate": lr,
        "updatedWeights": {"W1": next_w1.tolist(), "b1": next_b1.tolist(), "W2": next_w2.tolist(), "b2": float(next_b2[0])},
        "pytorchPrediction": float(tout.detach()), "pytorchLoss": float(tloss.detach()),
        "gradientMaxAbsError": gradient_error,
    }

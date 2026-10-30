"""Discrete-event bank queue simulation with exponential inter-arrival/service times.

All times are in seconds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

COLUMNS = ["customer_id", "arrival_time", "service_time", "waiting_time",
           "service_start", "departure_time", "counter_id"]


@dataclass(frozen=True)
class SimulationConfig:
    counters: int = 3
    duration: float = 240.0
    mean_arrival_interval: float = 3.0
    mean_service_time: float = 7.0
    seed: int = 42


def _validate(config: SimulationConfig) -> None:
    if int(config.counters) < 1:
        raise ValueError("At least one service counter is required.")
    for name in ("duration", "mean_arrival_interval", "mean_service_time"):
        value = getattr(config, name)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a finite number greater than zero.")


def run_simulation(config: SimulationConfig) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    """Simulate a first-come-first-served, pooled queue.

    Arrivals stop at ``duration``. The simulation then drains the queue so every
    generated customer has a complete service record. An event timeline is
    returned for the browser animation.
    """
    _validate(config)
    rng = np.random.default_rng(config.seed)

    arrivals: list[dict[str, float | int]] = []
    t = 0.0
    cid = 1
    while True:
        t += float(rng.exponential(config.mean_arrival_interval))
        if t > config.duration:
            break
        arrivals.append({"customer_id": cid, "arrival_time": t,
                         "service_time": float(rng.exponential(config.mean_service_time))})
        cid += 1

    # Each counter remembers when it becomes free; the earliest-free counter
    # (lowest number on ties) serves the next customer in line.
    available_at = [0.0] * int(config.counters)
    records: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = [{"time": 0.0, "type": "init"}]
    for customer in arrivals:
        k = min(range(len(available_at)), key=lambda i: (available_at[i], i))
        arrival = float(customer["arrival_time"])
        start = max(arrival, available_at[k])
        departure = start + float(customer["service_time"])
        available_at[k] = departure
        records.append({**customer, "service_start": start, "waiting_time": start - arrival,
                        "departure_time": departure, "counter_id": k + 1})
        cid_ = customer["customer_id"]
        events.extend([
            {"time": arrival, "type": "arrival", "customer_id": cid_},
            {"time": start, "type": "service_start", "customer_id": cid_, "counter_id": k + 1},
            {"time": departure, "type": "departure", "customer_id": cid_, "counter_id": k + 1},
        ])

    # At equal times: init, then departures (free the counter), arrivals, service starts.
    order = {"init": 0, "departure": 1, "arrival": 2, "service_start": 3}
    events.sort(key=lambda e: (e["time"], order[e["type"]]))

    df = pd.DataFrame(records, columns=COLUMNS)
    summary = {
        "customers": int(len(df)),
        "duration": float(config.duration),
        "end_time": float(df["departure_time"].max()) if not df.empty else float(config.duration),
        "counters": int(config.counters),
        "seed": int(config.seed),
    }
    return df, events, summary


def one_sample_t_test(waiting_times: pd.Series | np.ndarray, benchmark: float, alpha: float) -> dict[str, Any]:
    """Two-sided one-sample t-test of the mean waiting time against a benchmark."""
    from scipy import stats

    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")

    values = np.asarray(waiting_times, dtype=float)
    values = values[np.isfinite(values)]
    n = int(len(values))
    base = {
        "n": n,
        "mean": float(np.mean(values)) if n else 0.0,
        "median": float(np.median(values)) if n else 0.0,
        "maximum": float(np.max(values)) if n else 0.0,
        "std": float(np.std(values, ddof=1)) if n > 1 else 0.0,
        "benchmark": float(benchmark),
        "alpha": float(alpha),
    }
    if n < 2:
        return {**base, "t_statistic": None, "p_value": None, "confidence_interval": None,
                "decision": "Insufficient data: at least two customers are needed."}

    mean, std = base["mean"], base["std"]
    if std == 0:
        # Zero variance: the t statistic is undefined, so decide directly.
        t_stat = None
        p_value = 1.0 if mean == benchmark else 0.0
        ci = [mean, mean]
    else:
        result = stats.ttest_1samp(values, popmean=benchmark, alternative="two-sided")
        t_stat, p_value = float(result.statistic), float(result.pvalue)
        margin = float(stats.t.ppf(1 - alpha / 2, df=n - 1)) * std / math.sqrt(n)
        ci = [mean - margin, mean + margin]

    decision = ("Reject H₀: the mean waiting time differs from the benchmark."
                if p_value < alpha else
                "Do not reject H₀: there is not enough evidence of a difference.")
    return {**base, "t_statistic": t_stat, "p_value": p_value,
            "confidence_interval": ci, "decision": decision}

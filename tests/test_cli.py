"""__main__.py CLI 烟雾测试 —— 验证子命令端到端不抛错。"""
from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_cli_module():
    """加载顶层 __main__.py 作为常规模块 cli。"""
    import importlib.util
    p = Path(__file__).resolve().parent.parent / "__main__.py"
    spec = importlib.util.spec_from_file_location("traffic_cli", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cli = _load_cli_module()


@pytest.fixture
def sample_csv_path(tmp_path) -> str:
    """构造一份用于 CLI 测试的小流量 CSV（跨多周，方便留存/预测出活）。"""
    import numpy as np
    rng = np.random.RandomState(42)
    n = 400
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    df = pd.DataFrame({
        "date": rng.choice(dates, n),
        "user_id": rng.randint(1, 50, n),
        "session_id": [f"s_{i}" for i in rng.randint(1, 100, n)],
        "page": rng.choice(["home", "product", "cart", "checkout"], n),
        "source": rng.choice(["google", "facebook", "direct"], n),
        "device": rng.choice(["desktop", "mobile", "tablet"], n),
        "country": rng.choice(["China", "USA", "UK"], n),
        "duration": rng.uniform(10, 300, n),
        "visits": rng.poisson(5, n) + 1,
    })
    p = tmp_path / "traffic.csv"
    df.to_csv(p, index=False)
    return str(p)


@pytest.fixture
def sample_event_csv_path(tmp_path) -> str:
    """构造一份用于 funnel / path 测试的事件流 CSV。"""
    rows = [
        (1, "page_view", "2024-01-01 08:00:00"),
        (1, "sign_up", "2024-01-01 08:10:00"),
        (1, "purchase", "2024-01-01 09:00:00"),
        (2, "page_view", "2024-01-01 09:00:00"),
        (2, "sign_up", "2024-01-01 09:05:00"),
        (3, "page_view", "2024-01-02 10:00:00"),
        (4, "page_view", "2024-01-03 10:00:00"),
        (4, "sign_up", "2024-01-03 10:05:00"),
        (4, "purchase", "2024-01-03 10:30:00"),
    ]
    df = pd.DataFrame(rows, columns=["user_id", "event", "timestamp"])
    p = tmp_path / "events.csv"
    df.to_csv(p, index=False)
    return str(p)


# --- _to_jsonable ---------------------------------------------------------

def test_to_jsonable_handles_dataframe():
    df = pd.DataFrame({"a": [1, 2], "date": pd.date_range("2024-01-01", periods=2)})
    out = cli._to_jsonable(df)
    assert isinstance(out, list)
    assert out[0]["date"] == "2024-01-01"


def test_to_jsonable_handles_series():
    s = pd.Series({"x": 1, "y": 2})
    out = cli._to_jsonable(s)
    assert out == {"x": 1, "y": 2}


def test_to_jsonable_handles_nested_dict():
    nested = {"outer": {"inner_df": pd.DataFrame({"a": [1]})}}
    out = cli._to_jsonable(nested)
    assert out["outer"]["inner_df"] == [{"a": 1}]


def test_to_jsonable_handles_numpy_types():
    import numpy as np
    obj = {"int": np.int64(5), "float": np.float64(3.14),
           "array": np.array([1, 2, 3])}
    out = cli._to_jsonable(obj)
    assert out["int"] == 5
    assert out["float"] == 3.14
    assert out["array"] == [1, 2, 3]


# --- CLI 子命令端到端 ----------------------------------------------------

def _run_cli(cmd_args):
    """跑 CLI 并捕获 stdout，返回 (exit_code, parsed_json)。"""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(cmd_args)
    output = buf.getvalue()
    try:
        return code, json.loads(output)
    except json.JSONDecodeError:
        return code, output


def test_cli_traffic(sample_csv_path):
    code, payload = _run_cli(["traffic", sample_csv_path])
    assert code == 0
    assert "summary" in payload
    assert payload["summary"]["metrics"]["pv"] == 400


def test_cli_behavior(sample_csv_path):
    code, payload = _run_cli(["behavior", sample_csv_path])
    assert code == 0
    assert "page_metrics" in payload


def test_cli_anomalies_with_visits(sample_csv_path):
    code, payload = _run_cli(["anomalies", sample_csv_path,
                               "--metric", "visits", "--threshold", "2.0"])
    assert code == 0
    assert "statistical" in payload


def test_cli_anomalies_fallback_when_metric_missing(sample_csv_path):
    """传一个 CSV 没有的列名 → 自动 fallback 到数值列。"""
    code, payload = _run_cli(["anomalies", sample_csv_path,
                               "--metric", "nonexistent_column"])
    # 仍然成功（fallback 到 visits 或 duration 这种数值列）
    assert code == 0


def test_cli_output_writes_json_file(sample_csv_path, tmp_path):
    out_file = tmp_path / "report.json"
    code, _ = _run_cli(["traffic", sample_csv_path, "-o", str(out_file)])
    assert code == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "summary" in data


def test_cli_output_creates_nested_dirs(sample_csv_path, tmp_path):
    """-o nested/dir/file.json 应自动建目录。"""
    out_file = tmp_path / "nested" / "deep" / "report.json"
    code, _ = _run_cli(["traffic", sample_csv_path, "-o", str(out_file)])
    assert code == 0
    assert out_file.exists()


# --- 新增：funnel / path 事件流子命令 ------------------------------------

def test_cli_funnel(sample_event_csv_path):
    code, payload = _run_cli(["funnel", sample_event_csv_path,
                              "--steps", "page_view,sign_up,purchase"])
    assert code == 0
    assert "steps" in payload
    assert len(payload["steps"]) == 3
    assert payload["steps"][0]["n_users"] == 4         # 4 个 page_view
    # weakest_step 应被定位出来（非起点）
    assert payload["weakest_step"] in {"sign_up", "purchase"}


def test_cli_funnel_window_flag(sample_event_csv_path):
    code, payload = _run_cli(["funnel", sample_event_csv_path,
                              "--steps", "page_view,purchase", "--window", "48"])
    assert code == 0
    assert payload["steps"][-1]["name"] == "purchase"


def test_cli_path(sample_event_csv_path):
    code, payload = _run_cli(["path", sample_event_csv_path,
                              "--max-steps", "3", "--top-k", "5"])
    assert code == 0
    assert "top_sequences" in payload
    assert len(payload["top_sequences"]) <= 5
    assert all("sequence" in s and "count" in s for s in payload["top_sequences"])


def test_cli_funnel_missing_event_columns(sample_csv_path):
    """funnel 喂流量 CSV（无 event 列）→ 返回 error 字段而非崩溃。"""
    code, payload = _run_cli(["funnel", sample_csv_path,
                              "--steps", "home,product"])
    assert code == 0
    assert "error" in payload


# --- 回归：修过的 3 个 CLI bug -------------------------------------------

def test_cli_retention_serializes_timestamp_keys(sample_csv_path):
    """bug1 回归：留存矩阵的 cohort 日期键（Timestamp）能被 json 序列化。"""
    code, payload = _run_cli(["retention", sample_csv_path,
                              "--granularity", "week"])
    assert code == 0
    assert "retention_matrix" in payload
    # 首期（period 0）的所有 cohort 键应是字符串日期，且留存率 100
    matrix = payload["retention_matrix"]
    assert "0" in matrix
    for cohort_key, rate in matrix["0"].items():
        assert isinstance(cohort_key, str)
        assert rate == 100.0


def test_cli_forecast_runs_without_freq_kwarg(sample_csv_path):
    """bug2 回归：forecast 不再向 prepare_time_series 传 freq=，能跑通。"""
    code, payload = _run_cli(["forecast", sample_csv_path,
                              "--metric", "visits", "--steps", "7"])
    assert code == 0
    # 指数平滑成功 → 有 forecast_values；否则回退 trend forecast → 有 forecast
    assert ("forecast_values" in payload) or ("forecast" in payload)


def test_cli_forecast_no_freq_argument():
    """bug2 回归：--freq 参数已移除，传入应被 argparse 拒绝。"""
    with pytest.raises(SystemExit):
        cli.main(["forecast", "x.csv", "--freq", "D"])


def test_cli_segments_uses_rfm_segmentation(sample_csv_path):
    """bug3 回归：segments 调用 rfm_segmentation（而非不存在的 calculate_rfm）。"""
    code, payload = _run_cli(["segments", sample_csv_path])
    assert code == 0
    assert "rfm" in payload
    assert "error" not in payload["rfm"]
    assert "segment_counts" in payload["rfm"]
    assert payload["rfm"]["n_users"] > 0


def test_cli_jsonable_key_handles_timestamp():
    """_jsonable_key 把 Timestamp 键转成日期字符串。"""
    ts = pd.Timestamp("2024-03-15")
    assert cli._jsonable_key(ts) == "2024-03-15"
    assert cli._jsonable_key("plain") == "plain"
    assert cli._jsonable_key(7) == 7

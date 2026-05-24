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
    """构造一份用于 CLI 测试的小 CSV。"""
    import numpy as np
    rng = np.random.RandomState(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    df = pd.DataFrame({
        "date": rng.choice(dates, n),
        "user_id": rng.randint(1, 50, n),
        "session_id": [f"s_{i}" for i in rng.randint(1, 100, n)],
        "page": rng.choice(["home", "product", "cart", "checkout"], n),
        "source": rng.choice(["google", "facebook", "direct"], n),
        "device": rng.choice(["desktop", "mobile", "tablet"], n),
        "country": rng.choice(["China", "USA", "UK"], n),
        "duration": rng.uniform(10, 300, n),
        "visits": rng.poisson(5, n),
    })
    p = tmp_path / "traffic.csv"
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
    assert payload["summary"]["metrics"]["pv"] == 200


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

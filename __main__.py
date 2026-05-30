"""event-lens 统一命令行入口。

自托管、纯 pandas 的产品/网站事件分析：吃任意事件 CSV
（user_id + event + timestamp）→ 漏斗 + 留存 + 路径 + 异常 + 预测 + 分群，
全部输出 JSON，方便脚本 / cron / 下游消费。

事件流子命令（输入需含 user_id / event / timestamp）：
    funnel      漏斗转化 + 自动定位最弱环节
    path        最常见用户路径序列

流量/会话子命令（输入需含 date / user_id，可选 page / session_id 等）：
    traffic     PV/UV + 来源 + 设备 + 地理分布
    behavior    页面指标 + 跳出率 + 访问深度
    retention   Cohort 留存矩阵
    anomalies   统计 / 趋势异常检测
    forecast    时间序列预测（指数平滑 / 趋势外推）
    segments    RFM 用户价值分群
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd


def _load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def _jsonable_key(k):
    """把 dict 键转成 JSON 合法类型（str / int / float / bool / None）。

    json.dumps 只接受这些类型作为对象键；Timestamp / datetime / numpy 标量
    会直接抛 TypeError，所以在序列化前统一转换。
    """
    if isinstance(k, (str, int, float, bool)) or k is None:
        return k
    if isinstance(k, pd.Timestamp):
        return str(k.date())
    try:
        import numpy as np
        if isinstance(k, np.integer):
            return int(k)
        if isinstance(k, np.floating):
            return float(k)
    except ImportError:
        pass
    return str(k)


def _to_jsonable(obj):
    """递归把 DataFrame / np 类型转 JSON 可序列化值。"""
    if isinstance(obj, pd.DataFrame):
        df = obj.copy()
        for c in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                df[c] = df[c].dt.strftime("%Y-%m-%d")
        return df.to_dict(orient="records")
    if isinstance(obj, pd.Series):
        return _to_jsonable(obj.to_dict())
    if isinstance(obj, dict):
        # 注意：dict 的「键」也可能是 Timestamp / np 类型（如留存矩阵的
        # cohort 日期键），json.dumps 的 default= 只兜底「值」不兜底「键」，
        # 所以这里把键也转成 JSON 合法的字符串 / 数字。
        return {_jsonable_key(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, (pd.Timestamp,)):
        return str(obj.date())
    try:
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    return obj


def _emit(payload, output: str | None) -> int:
    serializable = _to_jsonable(payload)
    print(json.dumps(serializable, ensure_ascii=False, indent=2, default=str))
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")
    return 0


def cmd_traffic(args) -> int:
    from traffic_analyzer import TrafficAnalyzer
    df = _load_csv(args.csv)
    analyzer = TrafficAnalyzer(df)
    payload = {}
    try:
        analyzer.calculate_pv_uv()
        payload["summary"] = analyzer.get_summary()
    except Exception as e:
        payload["summary"] = {"error": str(e)}
    try:
        payload["sources"] = analyzer.analyze_traffic_sources("source")
    except Exception as e:
        payload["sources"] = {"error": str(e)}
    if "device" in df.columns:
        try:
            payload["devices"] = analyzer.analyze_device_distribution("device")
        except Exception as e:
            payload["devices"] = {"error": str(e)}
    if "country" in df.columns:
        try:
            payload["geography"] = analyzer.analyze_geography("country")
        except Exception as e:
            payload["geography"] = {"error": str(e)}
    return _emit(payload, args.output)


def cmd_behavior(args) -> int:
    from behavior_analyzer import BehaviorAnalyzer
    df = _load_csv(args.csv)
    analyzer = BehaviorAnalyzer(df)
    payload = {}
    try:
        payload["page_metrics"] = analyzer.calculate_page_metrics()
    except Exception as e:
        payload["page_metrics"] = {"error": str(e)}
    try:
        payload["bounce_rate"] = analyzer.calculate_bounce_rate()
    except Exception as e:
        payload["bounce_rate"] = {"error": str(e)}
    try:
        payload["visit_depth"] = analyzer.calculate_visit_depth()
    except Exception as e:
        payload["visit_depth"] = {"error": str(e)}
    return _emit(payload, args.output)


def cmd_retention(args) -> int:
    from retention_analyzer import RetentionAnalyzer
    df = _load_csv(args.csv)
    analyzer = RetentionAnalyzer(df)
    analyzer.create_cohorts("date", "user_id", args.granularity)
    matrix = analyzer.calculate_retention_matrix()
    payload = {
        "cohort_granularity": args.granularity,
        "retention_matrix": matrix.to_dict() if hasattr(matrix, "to_dict") else matrix,
    }
    return _emit(payload, args.output)


def cmd_anomalies(args) -> int:
    from anomaly_detector import AnomalyDetector
    df = _load_csv(args.csv)
    if args.metric not in df.columns:
        # 没有 metric 列时，从其他数值列里挑一个
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if not numeric_cols:
            sys.stderr.write(f"[error] 找不到 {args.metric} 也没有数值列\n")
            return 1
        sys.stderr.write(f"[warn] 找不到 {args.metric}，改用 {numeric_cols[0]}\n")
        args.metric = numeric_cols[0]

    detector = AnomalyDetector(df)
    payload = {}
    try:
        payload["statistical"] = detector.detect_statistical_anomalies(
            args.metric, threshold=args.threshold)
    except Exception as e:
        payload["statistical"] = {"error": str(e)}
    try:
        payload["alerts"] = detector.create_alerts(alert_threshold=args.threshold)
    except Exception as e:
        payload["alerts"] = {"error": str(e)}
    return _emit(payload, args.output)


def cmd_forecast(args) -> int:
    from forecaster import Forecaster
    df = _load_csv(args.csv)
    forecaster = Forecaster(df)
    ts = forecaster.prepare_time_series(date_column="date",
                                         metric_column=args.metric)
    try:
        forecaster.fit_exponential_smoothing(ts)
    except Exception as e:
        sys.stderr.write(f"[warn] 指数平滑失败：{e}；改用 trend forecast\n")
        result = forecaster.forecast_trend(ts, steps=args.steps)
        return _emit(result, args.output)

    payload = forecaster.forecast(steps=args.steps, confidence=args.confidence)
    return _emit(payload, args.output)


def _build_rfm_table(df: pd.DataFrame) -> pd.DataFrame:
    """从原始明细按 user_id 聚合出 recency / frequency / monetary。

    - recency：距数据中最近日期的天数（越小越近）
    - frequency：该用户的事件 / 访问条数
    - monetary：金额列（value / amount / revenue / duration）求和，
      没有金额列时退化为停留时长，再退化为 frequency
    """
    data = df.copy()
    date_col = next((c for c in ("date", "timestamp") if c in data.columns), None)
    if date_col is None:
        raise ValueError("缺少 date / timestamp 列，无法计算 recency")
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")

    money_col = next((c for c in ("value", "amount", "revenue", "duration")
                      if c in data.columns), None)

    snapshot = data[date_col].max()
    grouped = data.groupby("user_id")
    rfm = pd.DataFrame({
        "recency": (snapshot - grouped[date_col].max()).dt.days,
        "frequency": grouped.size(),
    })
    if money_col is not None:
        rfm["monetary"] = grouped[money_col].sum()
    else:
        rfm["monetary"] = rfm["frequency"]
    return rfm.reset_index()


def cmd_segments(args) -> int:
    from segmentation_analyzer import SegmentationAnalyzer
    df = _load_csv(args.csv)
    payload = {}

    # 已经带 recency/frequency/monetary 就直接用，否则从明细派生
    needed = {"recency", "frequency", "monetary"}
    if needed.issubset(df.columns):
        rfm_input = df
    else:
        try:
            rfm_input = _build_rfm_table(df)
        except Exception as e:
            return _emit({"rfm": {"error": str(e)}}, args.output)

    analyzer = SegmentationAnalyzer(rfm_input)
    try:
        scored = analyzer.rfm_segmentation()
        seg_counts = scored["RFM_segment"].value_counts().to_dict()
        payload["rfm"] = {
            "n_users": int(len(scored)),
            "segment_counts": seg_counts,
            "users": scored[["user_id", "recency", "frequency",
                             "monetary", "RFM_score", "RFM_segment"]]
            if "user_id" in scored.columns else scored,
        }
    except Exception as e:
        payload["rfm"] = {"error": str(e)}
    return _emit(payload, args.output)


def cmd_funnel(args) -> int:
    from event_analytics import compute_funnel
    df = _load_csv(args.csv)
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    try:
        report = compute_funnel(df, steps=steps, time_window_hours=args.window)
        payload = report.to_dict()
    except Exception as e:
        payload = {"error": str(e)}
    return _emit(payload, args.output)


def cmd_path(args) -> int:
    from event_analytics import compute_top_paths
    df = _load_csv(args.csv)
    try:
        report = compute_top_paths(df, max_steps=args.max_steps, top_k=args.top_k)
        payload = report.to_dict()
    except Exception as e:
        payload = {"error": str(e)}
    return _emit(payload, args.output)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="event-lens",
        description="自托管纯 pandas 事件分析：漏斗 / 留存 / 路径 / 异常 / 预测 / 分群",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- 事件流子命令 ---
    sp = sub.add_parser("funnel", help="漏斗转化 + 自动定位最弱环节")
    sp.add_argument("csv")
    sp.add_argument("--steps", required=True,
                    help="逗号分隔的有序事件，如 page_view,sign_up,purchase")
    sp.add_argument("--window", type=int, default=24,
                    help="相邻步骤的时间窗口（小时），默认 24")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_funnel)

    sp = sub.add_parser("path", help="最常见用户路径序列")
    sp.add_argument("csv")
    sp.add_argument("--max-steps", type=int, default=5,
                    help="每个用户最多取前几步事件，默认 5")
    sp.add_argument("--top-k", type=int, default=10,
                    help="返回最常见的前几条路径，默认 10")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_path)

    # --- 流量/会话子命令 ---
    for name, fn, help_text in [
        ("traffic", cmd_traffic, "PV/UV + 来源 + 设备 + 地理"),
        ("behavior", cmd_behavior, "页面指标 + 跳出率 + 访问深度"),
        ("segments", cmd_segments, "用户分群 RFM"),
    ]:
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("csv")
        sp.add_argument("-o", "--output")
        sp.set_defaults(func=fn)

    sp = sub.add_parser("retention", help="Cohort 留存矩阵")
    sp.add_argument("csv")
    sp.add_argument("--granularity", default="week",
                    choices=["day", "week", "month"])
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_retention)

    sp = sub.add_parser("anomalies", help="统计 / 趋势异常检测")
    sp.add_argument("csv")
    sp.add_argument("--metric", default="visits")
    sp.add_argument("--threshold", type=float, default=2.5)
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_anomalies)

    sp = sub.add_parser("forecast", help="时间序列预测")
    sp.add_argument("csv")
    sp.add_argument("--metric", default="visits")
    sp.add_argument("--steps", type=int, default=7)
    sp.add_argument("--confidence", type=float, default=0.95)
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_forecast)

    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

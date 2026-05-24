"""Traffic-Analytics-Platform CLI（v2）。

子命令：
    traffic     PV/UV + 来源 + 设备 + 地理分布
    behavior    页面指标 + 跳出率 + 访问深度
    retention   Cohort 留存矩阵
    anomalies   统计 / 趋势异常检测
    forecast    时间序列预测（ARIMA / 指数平滑）
    segments    用户分群
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


def _to_jsonable(obj):
    """递归把 DataFrame / np 类型转 JSON 可序列化值。"""
    if isinstance(obj, pd.DataFrame):
        df = obj.copy()
        for c in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                df[c] = df[c].dt.strftime("%Y-%m-%d")
        return df.to_dict(orient="records")
    if isinstance(obj, pd.Series):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
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
                                         metric_column=args.metric,
                                         freq=args.freq)
    try:
        forecaster.fit_exponential_smoothing(ts)
    except Exception as e:
        sys.stderr.write(f"[warn] 指数平滑失败：{e}；改用 trend forecast\n")
        result = forecaster.forecast_trend(ts, steps=args.steps)
        return _emit(result, args.output)

    payload = forecaster.forecast(steps=args.steps, confidence=args.confidence)
    return _emit(payload, args.output)


def cmd_segments(args) -> int:
    from segmentation_analyzer import SegmentationAnalyzer
    df = _load_csv(args.csv)
    analyzer = SegmentationAnalyzer(df)
    payload = {}
    try:
        payload["rfm"] = analyzer.calculate_rfm()
    except Exception as e:
        payload["rfm"] = {"error": str(e)}
    return _emit(payload, args.output)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="traffic", description="流量分析 headless CLI"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

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
    sp.add_argument("--freq", default="D")
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

"""生成流量/会话示例数据（date / user_id / session_id / page / source /
device / country / duration / visits / timestamp）。

用于让 traffic / behavior / retention / anomalies / forecast / segments
等命令离线即可跑通。日期跨多周，方便 cohort 留存与时间序列预测产出有意义的结果。
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def generate_sample_data(n_records: int = 2000,
                         n_days: int = 90,
                         output_file: str = "sample_data.csv") -> pd.DataFrame:
    """生成流量明细示例数据并写 CSV。"""
    rng = np.random.RandomState(42)
    start_date = datetime(2025, 1, 1)

    # 日期：跨 n_days，带轻微上升趋势 + 周末波动，方便预测/异常检测出活
    day_weights = 1.0 + 0.4 * np.sin(np.arange(n_days) / 7.0) + np.linspace(0, 0.6, n_days)
    day_weights = day_weights / day_weights.sum()
    day_offsets = rng.choice(np.arange(n_days), size=n_records, p=day_weights)
    dates = [start_date + timedelta(days=int(o)) for o in day_offsets]

    user_ids = rng.randint(1, 401, n_records)            # 400 个独立用户
    session_ids = [f"sess_{i}" for i in rng.randint(1, 1201, n_records)]

    pages = rng.choice(
        ["home", "product", "cart", "checkout", "about", "contact", "blog"],
        n_records, p=[0.30, 0.25, 0.15, 0.10, 0.08, 0.07, 0.05])
    sources = rng.choice(
        ["google", "facebook", "direct", "email", "twitter", "linkedin"],
        n_records, p=[0.35, 0.25, 0.20, 0.10, 0.05, 0.05])
    devices = rng.choice(["desktop", "mobile", "tablet"],
                         n_records, p=[0.50, 0.40, 0.10])
    countries = rng.choice(
        ["China", "USA", "UK", "Japan", "Germany", "France", "Other"],
        n_records, p=[0.30, 0.25, 0.15, 0.10, 0.08, 0.07, 0.05])
    durations = rng.exponential(120, n_records).clip(5, 600).round(1)
    visits = rng.poisson(5, n_records) + 1               # 每行的访问次数

    timestamps = [dates[i] + timedelta(minutes=int(rng.randint(0, 1440)))
                  for i in range(n_records)]

    df = pd.DataFrame({
        "date": [d.date() for d in dates],
        "user_id": user_ids,
        "session_id": session_ids,
        "page": pages,
        "source": sources,
        "device": devices,
        "country": countries,
        "duration": durations,
        "visits": visits,
        "timestamp": timestamps,
    }).sort_values("timestamp").reset_index(drop=True)

    df.to_csv(output_file, index=False)
    print(f"已生成 {n_records:,} 条记录，覆盖 {df['user_id'].nunique():,} 个用户")
    print(f"日期范围：{df['date'].min()} 至 {df['date'].max()}")
    print(f"文件保存至：{output_file}")
    return df


if __name__ == "__main__":
    generate_sample_data()

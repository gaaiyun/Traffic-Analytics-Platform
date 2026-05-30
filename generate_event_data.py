"""生成事件流示例数据（user_id + event + timestamp + value）。

用于让 funnel / path / 事件留存 / 活跃度分群等命令离线即可跑通。
模拟一个电商转化漏斗：page_view -> sign_up -> add_to_cart -> checkout -> purchase，
每一步按固定概率流失，并掺入一些浏览类事件让路径更真实。
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


FUNNEL = ["page_view", "sign_up", "add_to_cart", "checkout", "purchase"]
# 每一步相对上一步的留存概率
KEEP_PROB = {"sign_up": 0.6, "add_to_cart": 0.45, "checkout": 0.7, "purchase": 0.8}
BROWSE_EVENTS = ["search", "product_view", "category_view"]


def generate_event_data(n_users: int = 600,
                        output_file: str = "sample_events.csv") -> pd.DataFrame:
    """生成事件流示例数据并写 CSV。"""
    rng = np.random.RandomState(42)
    base = datetime(2024, 1, 1)
    rows = []

    for user_id in range(1, n_users + 1):
        t = base + timedelta(days=int(rng.randint(0, 35)),
                             hours=int(rng.randint(0, 24)),
                             minutes=int(rng.randint(0, 60)))

        # 所有用户都从 page_view 起步
        rows.append((user_id, "page_view", t, 0.0))

        # 一部分用户在第一步后随便逛逛（丰富路径）
        for _ in range(int(rng.randint(0, 3))):
            t += timedelta(minutes=int(rng.randint(1, 30)))
            rows.append((user_id, rng.choice(BROWSE_EVENTS), t, 0.0))

        # 沿漏斗逐步推进，任意一步流失即停止
        reached = True
        for step in FUNNEL[1:]:
            if not reached or rng.random() > KEEP_PROB[step]:
                reached = False
                break
            t += timedelta(minutes=int(rng.randint(2, 90)))
            value = round(float(rng.uniform(20, 400)), 2) if step == "purchase" else 0.0
            rows.append((user_id, step, t, value))

    df = pd.DataFrame(rows, columns=["user_id", "event", "timestamp", "value"])
    df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)
    df.to_csv(output_file, index=False)
    print(f"已生成 {len(df):,} 条事件，覆盖 {df['user_id'].nunique():,} 个用户")
    print(f"文件保存至：{output_file}")
    return df


if __name__ == "__main__":
    generate_event_data()

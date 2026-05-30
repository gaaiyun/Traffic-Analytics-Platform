"""event_analytics.py 测试 —— 漏斗 / 路径 / 事件留存 / 活跃度分群。

数据来自 User-Behavior-Analytics 移植进来的纯 pandas 事件流分析能力。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from event_analytics import (
    FunnelReport, PathReport, RetentionReport, SegmentReport,
    compute_funnel, compute_retention, compute_segments, compute_top_paths,
)


@pytest.fixture
def behavior_df() -> pd.DataFrame:
    """5 个用户、多事件、跨多天的事件流。"""
    rows = [
        # user 1：完整漏斗 + day 1/7 留存
        (1, "page_view", "2024-01-01 08:00:00"),
        (1, "sign_up", "2024-01-01 08:10:00"),
        (1, "add_to_cart", "2024-01-01 08:30:00"),
        (1, "purchase", "2024-01-01 09:00:00"),
        (1, "page_view", "2024-01-02 10:00:00"),    # day 1
        (1, "page_view", "2024-01-08 10:00:00"),    # day 7
        # user 2：漏斗到 cart 流失
        (2, "page_view", "2024-01-01 09:00:00"),
        (2, "sign_up", "2024-01-01 09:05:00"),
        (2, "add_to_cart", "2024-01-01 09:30:00"),
        # user 3：只浏览不注册
        (3, "page_view", "2024-01-02 10:00:00"),
        (3, "page_view", "2024-01-02 11:00:00"),
        # user 4：注册后没下文
        (4, "page_view", "2024-01-03 10:00:00"),
        (4, "sign_up", "2024-01-03 10:05:00"),
        # user 5：heavy 用户
        (5, "page_view", "2024-01-04 10:00:00"),
        (5, "sign_up", "2024-01-04 10:05:00"),
        (5, "add_to_cart", "2024-01-04 11:00:00"),
        (5, "purchase", "2024-01-04 12:00:00"),
        (5, "page_view", "2024-01-04 13:00:00"),
        (5, "page_view", "2024-01-04 14:00:00"),
        (5, "page_view", "2024-01-04 15:00:00"),
    ]
    return pd.DataFrame(rows, columns=["user_id", "event", "timestamp"])


# --- 漏斗 -------------------------------------------------------------------

def test_funnel_basic_conversion(behavior_df):
    report = compute_funnel(behavior_df,
                            steps=["page_view", "sign_up", "purchase"])
    assert isinstance(report, FunnelReport)
    assert len(report.steps) == 3
    assert report.steps[0].n_users == 5     # 5 个都做过 page_view
    assert report.steps[1].n_users == 4     # 4 个注册（1,2,4,5）
    assert report.steps[2].n_users == 2     # 2 个购买（1,5）


def test_funnel_overall_conversion_pct(behavior_df):
    report = compute_funnel(behavior_df,
                            steps=["page_view", "sign_up", "purchase"])
    assert report.overall_conversion_pct == 40.0   # 2/5


def test_funnel_weakest_step_identified(behavior_df):
    report = compute_funnel(behavior_df,
                            steps=["page_view", "sign_up", "purchase"])
    # sign_up(4)→purchase(2) 流失 50%；page_view(5)→sign_up(4) 流失 20%
    assert report.weakest_step == "purchase"
    assert report.weakest_drop_pct == 50.0


def test_funnel_time_window_enforces_24h(behavior_df):
    """超过 24h 才购买的用户不算入。"""
    extra = pd.DataFrame([
        (6, "page_view", "2024-01-01 08:00:00"),
        (6, "purchase", "2024-01-03 08:00:00"),  # 48h 后
    ], columns=["user_id", "event", "timestamp"])
    df = pd.concat([behavior_df, extra])
    report = compute_funnel(df, steps=["page_view", "purchase"],
                            time_window_hours=24)
    assert report.steps[1].n_users == 2     # user 1, 5（不含 6）


def test_funnel_empty_steps_raises(behavior_df):
    with pytest.raises(ValueError, match="steps"):
        compute_funnel(behavior_df, steps=[])


def test_funnel_missing_columns_raises():
    df = pd.DataFrame({"foo": [1], "bar": [2]})
    with pytest.raises(ValueError, match="缺必要列"):
        compute_funnel(df, steps=["page_view"])


def test_funnel_no_starting_users(behavior_df):
    report = compute_funnel(behavior_df,
                            steps=["nonexistent_event", "page_view"])
    assert report.steps[0].n_users == 0
    assert report.steps[1].n_users == 0


def test_funnel_to_dict_serializable(behavior_df):
    report = compute_funnel(behavior_df, steps=["page_view", "sign_up"])
    json.dumps(report.to_dict(), ensure_ascii=False)


# --- 路径 -------------------------------------------------------------------

def test_paths_returns_top_sequences(behavior_df):
    report = compute_top_paths(behavior_df, max_steps=3, top_k=5)
    assert isinstance(report, PathReport)
    assert len(report.top_sequences) <= 5
    assert all(isinstance(seq, str) for seq, _ in report.top_sequences)


def test_paths_n_unique_paths(behavior_df):
    report = compute_top_paths(behavior_df, max_steps=3)
    assert 1 <= report.n_unique_paths <= 5


def test_paths_avg_length(behavior_df):
    report = compute_top_paths(behavior_df, max_steps=3)
    assert report.avg_path_length <= 3.0


def test_paths_first_sequence_starts_with_page_view(behavior_df):
    report = compute_top_paths(behavior_df, max_steps=3, top_k=1)
    seq, count = report.top_sequences[0]
    assert seq.startswith("page_view")
    assert count >= 1


def test_paths_to_dict_serializable(behavior_df):
    report = compute_top_paths(behavior_df)
    json.dumps(report.to_dict(), ensure_ascii=False)


# --- 留存 -------------------------------------------------------------------

def test_retention_basic(behavior_df):
    report = compute_retention(behavior_df)
    assert isinstance(report, RetentionReport)
    assert report.cohort_size == 5


def test_retention_day_1_some_users(behavior_df):
    report = compute_retention(behavior_df)
    assert report.day_1_retention == 20.0   # user 1 在 day 1 回来


def test_retention_day_7_user1_returns(behavior_df):
    report = compute_retention(behavior_df)
    assert report.day_7_retention == 20.0


def test_retention_with_first_event_filter(behavior_df):
    report = compute_retention(behavior_df, first_event_filter="sign_up")
    assert report.cohort_size == 4          # 1,2,4,5 注册


def test_retention_empty_df_raises():
    with pytest.raises(ValueError):
        compute_retention(pd.DataFrame())


def test_retention_no_first_event_match(behavior_df):
    report = compute_retention(behavior_df, first_event_filter="nonexistent")
    assert report.cohort_size == 0
    assert report.day_1_retention == 0


def test_retention_cohort_dates_are_strings(behavior_df):
    report = compute_retention(behavior_df)
    assert all(isinstance(d, str) for d in report.cohort_dates)


def test_retention_to_dict_serializable(behavior_df):
    report = compute_retention(behavior_df)
    json.dumps(report.to_dict(), ensure_ascii=False)


# --- 活跃度分群 -------------------------------------------------------------

def test_segments_classifies_correctly(behavior_df):
    report = compute_segments(behavior_df,
                              high_threshold=5, medium_threshold=2)
    assert isinstance(report, SegmentReport)
    # user 1: 6 → heavy; user 5: 7 → heavy
    # user 2/3/4: 3/2/2 → regular
    assert report.segments["heavy"] == 2
    assert report.segments["regular"] == 3
    assert report.segments["light"] == 0


def test_segments_n_users_matches(behavior_df):
    report = compute_segments(behavior_df)
    assert report.n_users == 5


def test_segments_avg_events_computed(behavior_df):
    report = compute_segments(behavior_df)
    assert report.avg_events_per_user == 4.0    # 20 事件 / 5 用户


def test_segments_empty_df_raises():
    with pytest.raises(ValueError):
        compute_segments(pd.DataFrame())


def test_segments_to_dict_serializable(behavior_df):
    report = compute_segments(behavior_df)
    json.dumps(report.to_dict(), ensure_ascii=False)

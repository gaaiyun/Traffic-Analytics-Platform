# Traffic-Analytics-Platform

网站 / APP 流量分析平台：Streamlit 仪表板（v1）+ headless CLI（v2）。

v1 提供 6 个 analyzer（流量 / 行为 / 留存 / 异常 / 预测 / 分群）+ Streamlit
仪表板 + 60+ 单元测试。6 个 analyzer 已经是纯 pandas（只有 dashboard.py 依赖
Streamlit），但**v1 有 3 个 bug**导致原始测试无法全跑通：

| Bug | 位置 | 修复 |
|---|---|---|
| 语法错误（未闭合 `[`） | `traffic_analyzer.py:91` `analyze_device_distribution` | 重写为可读三行 |
| 测试 fixture 缺参数 | `tests/test_retention.py:65` | 加 `sample_traffic_data` 参数 |
| std 期望值用错 ddof | `tests/test_anomaly.py:128` | 改 `df.std(ddof=0)` 与 numpy 一致 |

v2 在修这些 bug 的基础上加 CLI 入口，10 个新 CLI 烟雾测试。

## v2 新增 / 修复

| 文件 | 干什么 |
|---|---|
| `__main__.py` | CLI 6 子命令：traffic / behavior / retention / anomalies / forecast / segments |
| `tests/test_cli.py` | 10 个 CLI 端到端 + `_to_jsonable` 单元测试 |
| `traffic_analyzer.py` | **修 v1 syntax error** `analyze_device_distribution` |
| `tests/test_retention.py` | **修 fixture 漏参** test_calculate_retention_matrix_no_cohort |
| `tests/test_anomaly.py` | **修 std ddof 不一致** test_z_score_calculation |

总测试 71 个（61 v1 + 10 v2），2.5 秒跑完。

## v1 仍保留

| 模块 | 干什么 |
|---|---|
| `dashboard.py` | Streamlit 交互式主界面 |
| `traffic_analyzer.py` | PV/UV / 来源 / 设备 / 地理 |
| `behavior_analyzer.py` | 页面 / 跳出率 / 访问深度 / 用户路径 |
| `retention_analyzer.py` | Cohort 留存 |
| `anomaly_detector.py` | Z-Score / Isolation Forest / 趋势异常 |
| `forecaster.py` | ARIMA / 指数平滑 |
| `segmentation_analyzer.py` | RFM 分群 |
| `generate_sample_data.py` / `sample_data.csv` | 示例数据 |

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

### v2 headless CLI

```bash
# 流量概览：PV/UV + 来源 + 设备 + 地理
python __main__.py traffic sample_data.csv

# 用户行为：页面 + 跳出 + 深度
python __main__.py behavior sample_data.csv

# 周 cohort 留存矩阵
python __main__.py retention sample_data.csv --granularity week

# 异常检测（z-score）
python __main__.py anomalies sample_data.csv --metric duration --threshold 2.5

# 时间序列预测
python __main__.py forecast sample_data.csv --metric visits --steps 7

# RFM 用户分群
python __main__.py segments sample_data.csv

# 所有命令支持 -o report.json
python __main__.py traffic sample_data.csv -o report.json
```

### v1 Streamlit 仪表板

```bash
streamlit run dashboard.py
```

### 库调用

```python
import pandas as pd
from traffic_analyzer import TrafficAnalyzer
from behavior_analyzer import BehaviorAnalyzer
from retention_analyzer import RetentionAnalyzer

df = pd.read_csv("traffic.csv")
df["date"] = pd.to_datetime(df["date"])

# 流量
ta = TrafficAnalyzer(df)
ta.calculate_pv_uv()
print(ta.get_summary())     # {'metrics': {'pv': N, 'uv': N, ...}, 'data_shape': ...}

# 行为
ba = BehaviorAnalyzer(df)
print(ba.calculate_page_metrics())
print(ba.calculate_bounce_rate())

# 留存
ra = RetentionAnalyzer(df)
ra.create_cohorts("date", "user_id", "week")
matrix = ra.calculate_retention_matrix()
```

## 数据 schema

| 列 | 必需 | 说明 |
|---|---|---|
| date | **是** | datetime-parseable |
| user_id | **是** | 用户 ID |
| session_id | 否 | 会话 ID（行为 / 跳出率分析需要） |
| page | 否 | 页面名（行为分析需要） |
| source | 否 | 来源（utm_source 类） |
| device | 否 | desktop / mobile / tablet |
| country / city | 否 | 地理分析需要 |
| duration | 否 | 停留时长（秒） |
| visits | 否 | 异常检测默认 metric 列 |

## v1 bug 修复细节

### 1. `traffic_analyzer.py` 行 91 语法错误

```python
# v1 原版（无法 import）：
'mobile_percentage': device_stats[device_stats[...]]['percentage'].sum()
                   if device_stats[device_stats[...].any() else 0   # 漏 ]
}
```

修成：

```python
mobile_mask = device_stats[device_column].str.contains('mobile', case=False, na=False)
mobile_pct = (device_stats[mobile_mask]['percentage'].sum()
              if mobile_mask.any() else 0.0)
return {
    'device_distribution': device_stats,
    'mobile_percentage': float(mobile_pct),
}
```

### 2. test_retention 漏参

```python
# v1 原版（NameError）：
def test_calculate_retention_matrix_no_cohort(self):
    analyzer = RetentionAnalyzer(sample_traffic_data)   # 没传 fixture
```

修成：

```python
def test_calculate_retention_matrix_no_cohort(self, sample_traffic_data):
```

### 3. test_anomaly std ddof 不一致

`anomaly_detector` 用 `numpy.std(values)` 默认 `ddof=0`（总体），但测试期望
`df.std()` 默认 `ddof=1`（样本）—— 600 个数据点上差 ~0.5%。改成测试也用
`ddof=0`，与 detector 实现保持一致。

## 设计取舍

- **CLI 不做画图**：图表归 Streamlit dashboard，CLI 只输出 JSON / 写文件 —— 让
  脚本和 cron 任务能消费。
- **`_to_jsonable` 递归转换**：DataFrame / Series / numpy 类型 / datetime 全部
  转 JSON 可序列化值，避免每个子命令各自处理。
- **anomalies 子命令 fallback**：用户传一个 CSV 里没有的 metric 列，自动 fallback
  到第一个数值列（带 warning），而不是直接报错。

## 项目结构

```
Traffic-Analytics-Platform/
├── __main__.py                  # v2 CLI
├── dashboard.py                 # v1 Streamlit
├── traffic_analyzer.py          # v1（已修 syntax error）
├── behavior_analyzer.py         # v1
├── retention_analyzer.py        # v1
├── anomaly_detector.py          # v1
├── forecaster.py                # v1
├── segmentation_analyzer.py     # v1
├── generate_sample_data.py
├── tests/                       # 71 测试
│   ├── conftest.py
│   ├── test_traffic.py
│   ├── test_behavior.py
│   ├── test_retention.py        # 修 fixture 参数
│   ├── test_anomaly.py          # 修 std ddof
│   ├── test_forecaster.py
│   └── test_cli.py              # v2 新增
├── sample_data.csv
└── requirements.txt
```

## 测试

```bash
pytest tests/ --no-cov
```

71 个测试，2.5 秒跑完。

## 已知限制

- `forecast` 子命令默认用指数平滑，statsmodels 装失败时回退到简单 trend
  forecast（最后两个点的线性外推），不精确但能跑。
- `retention` 默认按 week 切 cohort；按 day 切会产生很多小 cohort，可读性差。
- `traffic` 的设备 / 地理分析只在数据有对应列时跑，缺列就跳过该字段。

## 许可

MIT

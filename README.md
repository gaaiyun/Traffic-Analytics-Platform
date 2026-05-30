# event-lens

自托管、纯 pandas 的产品/网站事件分析。给一份事件 CSV（至少含
`user_id`、`event`、`timestamp` 三列），一条命令就能算出漏斗转化、留存
cohort、用户路径、异常、预测和 RFM 分群——不需要埋点 SDK，不需要数据库，
不需要起服务。可以理解为 PostHog / Mixpanel 的一个轻量、可离线、可塞进 cron
的自托管子集。

所有分析都是纯 pandas 实现，输出统一是 JSON，方便脚本、定时任务和下游程序直接消费。
另带一个可选的 Streamlit 仪表板做交互式探索。

## 它能回答的问题

- 用户从 `page_view` 到 `purchase`，每一步漏掉多少人？**最该优化的是哪一步？**
- 新用户的次日 / 7 日 / 30 日留存是多少？
- 用户进站后最常走哪几条路径？
- 哪些天的流量是统计意义上的异常？
- 未来 N 天的趋势大概什么样？
- 用户按价值（RFM）分成哪几档，各有多少人？

## 安装

```bash
pip install -r requirements.txt
```

只跑命令行的话，核心依赖是 pandas / numpy / scipy / statsmodels / scikit-learn；
Streamlit 和 plotly 只有仪表板才需要。

## 快速开始

仓库自带两份示例数据，克隆下来即可离线跑通所有命令：

- `sample_events.csv`——事件流（`user_id` / `event` / `timestamp` / `value`），
  给 `funnel`、`path` 用。
- `sample_data.csv`——流量明细（`date` / `user_id` / `session_id` / `page` / …），
  给 `traffic`、`behavior`、`retention`、`anomalies`、`forecast`、`segments` 用。

```bash
# 漏斗转化 + 自动定位最弱环节
python -m event_lens funnel sample_events.csv --steps page_view,sign_up,add_to_cart,checkout,purchase

# 最常见的用户路径序列
python -m event_lens path sample_events.csv --max-steps 5 --top-k 10

# PV/UV + 来源 + 设备 + 地理
python -m event_lens traffic sample_data.csv

# 页面指标 + 跳出率 + 访问深度
python -m event_lens behavior sample_data.csv

# 周 cohort 留存矩阵
python -m event_lens retention sample_data.csv --granularity week

# Z-Score 异常检测
python -m event_lens anomalies sample_data.csv --metric visits --threshold 2.5

# 时间序列预测（指数平滑，自动回退趋势外推）
python -m event_lens forecast sample_data.csv --metric visits --steps 7

# RFM 用户价值分群
python -m event_lens segments sample_data.csv

# 任意命令都支持 -o 写文件
python -m event_lens funnel sample_events.csv --steps page_view,purchase -o report.json
```

> `python -m event_lens <cmd>` 与 `python __main__.py <cmd>` 等价；下面统一用前者。

## 子命令

### 事件流（输入需含 `user_id` / `event` / `timestamp`）

| 命令 | 作用 | 关键参数 |
|---|---|---|
| `funnel` | 漏斗转化，逐步算转化率，并自动定位 step-to-step 流失最高的 `weakest_step` | `--steps`（逗号分隔有序事件，必填）、`--window`（相邻步骤时间窗口小时数，默认 24） |
| `path` | 每个用户前 N 步事件拼成序列，统计最常见的路径模式 | `--max-steps`（默认 5）、`--top-k`（默认 10） |

`funnel` 的转化是带时间窗口约束的：只有在 `--window` 小时内、且晚于上一步发生的
事件才算转化到下一步，更贴近真实漏斗口径。

### 流量 / 会话（输入需含 `date` / `user_id`，其余列可选）

| 命令 | 作用 |
|---|---|
| `traffic` | PV/UV、来源质量、设备分布、地理分布 |
| `behavior` | 页面指标、跳出率、访问深度分布 |
| `retention` | Cohort 留存矩阵（`--granularity day/week/month`） |
| `anomalies` | Z-Score 统计异常（`--metric` / `--threshold`，找不到指标列会自动回退到首个数值列） |
| `forecast` | 时间序列预测（`--metric` / `--steps` / `--confidence`） |
| `segments` | RFM 用户价值分群（自动从明细派生 recency / frequency / monetary） |

## 输入数据 schema

事件流命令只认三列，其余列忽略：

| 列 | 必需 | 说明 |
|---|---|---|
| `user_id` | 是 | 用户标识 |
| `event` | 是 | 事件名，如 `page_view` / `sign_up` / `purchase` |
| `timestamp` | 是 | 可被 `pandas` 解析的时间 |
| `value` | 否 | 金额等数值，`segments` 会用作 monetary |

流量 / 会话命令的列：

| 列 | 必需 | 说明 |
|---|---|---|
| `date` | 是 | 可解析日期 |
| `user_id` | 是 | 用户 ID |
| `session_id` | 否 | 会话 ID（行为 / 跳出率分析需要） |
| `page` | 否 | 页面名 |
| `source` | 否 | 来源（utm_source 类） |
| `device` | 否 | desktop / mobile / tablet |
| `country` | 否 | 地理分析需要 |
| `duration` | 否 | 停留时长（秒），无金额列时作 monetary 兜底 |
| `visits` | 否 | 异常检测 / 预测的默认指标列 |

## 库调用

命令行只是薄封装，分析逻辑都可以直接 import。

```python
import pandas as pd
from event_analytics import compute_funnel, compute_top_paths

df = pd.read_csv("sample_events.csv")

report = compute_funnel(df, steps=["page_view", "sign_up", "purchase"])
print(report.overall_conversion_pct)   # 端到端转化率
print(report.weakest_step)             # 流失最严重的一步
print(report.to_dict())                # JSON 可序列化结构

paths = compute_top_paths(df, max_steps=5, top_k=10)
print(paths.top_sequences)             # [("page_view -> sign_up -> ...", count), ...]
```

流量类分析器同样可单独用：

```python
from traffic_analyzer import TrafficAnalyzer
from retention_analyzer import RetentionAnalyzer

df = pd.read_csv("sample_data.csv")
df["date"] = pd.to_datetime(df["date"])

ta = TrafficAnalyzer(df)
ta.calculate_pv_uv()
print(ta.get_summary())

ra = RetentionAnalyzer(df)
ra.create_cohorts("date", "user_id", "week")
print(ra.calculate_retention_matrix())
```

## Streamlit 仪表板

```bash
streamlit run dashboard.py
```

支持上传 CSV 或使用内置示例数据，覆盖流量 / 行为 / 留存 / 异常 / 预测 / 细分
六个交互模块。命令行不画图——图表归仪表板，命令行只产出 JSON，方便自动化消费。

## 重新生成示例数据

```bash
python generate_event_data.py     # -> sample_events.csv（事件流）
python generate_sample_data.py    # -> sample_data.csv（流量明细）
```

两个脚本都用固定随机种子，结果可复现。

## 项目结构

```
event-lens/
├── __main__.py                # 统一 CLI 入口（8 个子命令）
├── event_analytics.py         # 事件流分析：漏斗 / 路径 / 留存 / 分群（纯 pandas）
├── traffic_analyzer.py        # PV/UV / 来源 / 设备 / 地理
├── behavior_analyzer.py       # 页面 / 跳出率 / 访问深度
├── retention_analyzer.py      # Cohort 留存矩阵
├── anomaly_detector.py        # Z-Score / 孤立森林 / 趋势异常
├── forecaster.py              # ARIMA / 指数平滑 / 趋势外推
├── segmentation_analyzer.py   # RFM / K-Means 分群
├── dashboard.py               # Streamlit 仪表板
├── generate_event_data.py     # 事件流示例数据生成器
├── generate_sample_data.py    # 流量明细示例数据生成器
├── sample_events.csv          # 自带事件流示例
├── sample_data.csv            # 自带流量明细示例
└── tests/                     # pytest 套件
```

## 测试

```bash
python -m pytest tests/ -q
```

## 设计取舍

- **命令行不画图**：图表交给 Streamlit 仪表板，命令行只输出 JSON / 写文件，
  让脚本和 cron 任务能直接消费结果。
- **JSON 序列化统一兜底**：留存矩阵的 cohort 日期键是 `Timestamp`，DataFrame /
  numpy 标量也常见，`__main__.py` 在序列化前把键和值都转成 JSON 合法类型，
  避免每个子命令各自处理。
- **`funnel` 带时间窗口**：相邻步骤必须在窗口内先后发生才算转化，比单纯"做过某事件"
  更接近真实漏斗。
- **`anomalies` 自动回退**：传入 CSV 里不存在的指标列时，自动回退到第一个数值列
  并给出告警，而不是直接报错。
- **`segments` 自动派生 RFM**：明细里没有 recency/frequency/monetary 时，按
  `user_id` 从原始数据现算，让命令在任意事件 / 流量 CSV 上都能跑。

## 许可

MIT

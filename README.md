# 📊 流量分析平台 (Traffic Analytics Platform)

专业的网站/APP 流量分析和用户行为洞察平台

## ✨ 功能特性

### 核心分析模块

1. **📈 流量分析**
   - PV/UV 统计与趋势分析
   - 多渠道流量来源拆解
   - 流量质量评估评分
   - 设备分布分析
   - 地域分布热力图

2. **🎯 用户行为分析**
   - 页面停留时长分析
   - 跳出率计算
   - 访问深度分布
   - 用户行为路径追踪
   - 桑基图可视化

3. **🔄 留存分析**
   - Cohort 分析（按周/月）
   - 次日/7 日/30 日留存率
   - 留存矩阵热力图
   - 留存曲线对比
   - 留存驱动因素分析

4. **⚠️ 异常检测**
   - Z-Score 统计异常检测
   - 孤立森林机器学习检测
   - 趋势异常识别
   - 自动告警系统

5. **🔮 预测模型**
   - ARIMA 时间序列预测
   - 指数平滑预测
   - 趋势分析与预测
   - 置信区间展示

6. **🎯 细分分析**
   - RFM 用户价值细分
   - K-Means 用户聚类
   - 多维度交叉分析
   - 细分群体对比

## 🚀 快速开始

### 安装依赖

```bash
cd traffic-analytics-platform
pip install -r requirements.txt
```

### 运行平台

```bash
# 使用示例数据运行
streamlit run dashboard.py

# 或使用自定义数据生成脚本
python generate_sample_data.py
streamlit run dashboard.py
```

### 访问界面

浏览器打开：`http://localhost:8501`

## 📁 项目结构

```
traffic-analytics-platform/
├── dashboard.py              # 主界面（Streamlit）
├── traffic_analyzer.py       # 流量分析模块
├── behavior_analyzer.py      # 行为分析模块
├── retention_analyzer.py     # 留存分析模块
├── anomaly_detector.py       # 异常检测模块
├── forecaster.py             # 预测模块
├── segmentation_analyzer.py  # 细分分析模块
├── generate_sample_data.py   # 示例数据生成
├── sample_data.csv           # 示例数据文件
├── requirements.txt          # 依赖列表
├── README.md                 # 项目文档
└── tests/                    # 单元测试
    ├── test_traffic.py
    ├── test_behavior.py
    ├── test_retention.py
    ├── test_anomaly.py
    ├── test_forecaster.py
    └── test_segmentation.py
```

## 📊 数据格式

支持导入 CSV 文件，需包含以下列：

| 列名 | 说明 | 必填 |
|------|------|------|
| date | 日期 (YYYY-MM-DD) | ✅ |
| user_id | 用户 ID | ✅ |
| session_id | 会话 ID | ✅ |
| page | 页面名称 | ✅ |
| source | 流量来源 | ✅ |
| device | 设备类型 | ✅ |
| country | 国家/地区 | ✅ |
| duration | 停留时长 (秒) | ✅ |
| timestamp | 时间戳 | ✅ |

## 🧪 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行测试并生成覆盖率报告
pytest tests/ -v --cov=. --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html  # macOS/Linux
start htmlcov\index.html  # Windows
```

## 🎨 界面截图

### 主界面概览
- 关键指标卡片（PV、UV、会话数、平均停留）
- 数据质量检查
- 数据预览表格

### 流量分析
- PV/UV 趋势图
- 流量来源饼图
- 设备分布柱状图
- 地域分布热力图

### 行为分析
- 页面表现分析
- 跳出率与访问深度
- 用户路径桑基图

### 留存分析
- Cohort 留存矩阵
- 留存率指标
- 留存曲线对比

### 异常检测
- 时间序列异常点标记
- 统计阈值可视化
- 告警列表

### 预测模型
- ARIMA/指数平滑模型选择
- 未来趋势预测
- 置信区间展示

### 细分分析
- RFM 用户价值分群
- K-Means 聚类分析
- 细分群体特征对比

## 🔧 配置选项

### 环境变量

```bash
# 可选：自定义端口
STREAMLIPT_SERVER_PORT=8502

# 可选：自定义主机
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

### Streamlit 配置

创建 `.streamlit/config.toml`:

```toml
[server]
port = 8501
headless = true

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
```

## 📈 性能优化建议

1. **大数据集处理**
   - 建议使用数据采样（>100 万条记录时）
   - 启用数据缓存
   - 使用数据库而非 CSV

2. **内存优化**
   - 按需加载数据
   - 使用数据类型优化（如 category）
   - 定期清理缓存

3. **响应速度**
   - 使用 `@st.cache_data` 装饰器
   - 预计算常用指标
   - 异步加载大型图表

## 🔌 扩展开发

### 添加新分析模块

1. 创建新的分析器类（参考现有模块）
2. 在 `dashboard.py` 中导入
3. 在侧边栏添加导航选项
4. 实现可视化逻辑

### 示例：添加转化漏斗分析

```python
# conversion_analyzer.py
class ConversionAnalyzer:
    def calculate_funnel(self, steps):
        # 实现转化漏斗逻辑
        pass

# dashboard.py
from conversion_analyzer import ConversionAnalyzer
```

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请提交 Issue。

---

**版本**: v1.0  
**最后更新**: 2026-03-04  
**技术栈**: Streamlit + Pandas + Plotly + Scikit-learn

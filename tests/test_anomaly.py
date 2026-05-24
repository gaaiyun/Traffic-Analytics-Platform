"""
异常检测模块测试 - Anomaly Detector Tests
"""

import pytest
import pandas as pd
import numpy as np
from anomaly_detector import AnomalyDetector


class TestAnomalyDetector:
    """异常检测器测试类"""
    
    def test_initialization(self):
        """测试初始化"""
        detector = AnomalyDetector()
        assert detector.data is None
        assert detector.anomalies == []
        assert detector.alerts == []
    
    def test_load_data(self, sample_traffic_data):
        """测试数据加载"""
        detector = AnomalyDetector()
        detector.load_data(sample_traffic_data)
        assert detector.data is not None
    
    def test_detect_statistical_anomalies(self, sample_time_series_data):
        """测试统计异常检测"""
        detector = AnomalyDetector(sample_time_series_data)
        result = detector.detect_statistical_anomalies('visits', threshold=2.5)
        
        assert 'anomaly_count' in result
        assert 'anomaly_indices' in result
        assert 'threshold' in result
        assert 'mean' in result
        assert 'std' in result
        assert result['threshold'] == 2.5
    
    def test_detect_statistical_anomalies_no_data(self):
        """测试无数据时的统计异常检测"""
        detector = AnomalyDetector()
        with pytest.raises(ValueError):
            detector.detect_statistical_anomalies()
    
    def test_detect_statistical_anomalies_no_column(self, sample_traffic_data):
        """测试缺少指标列时的处理"""
        detector = AnomalyDetector(sample_traffic_data)
        with pytest.raises(ValueError):
            detector.detect_statistical_anomalies('nonexistent_column')
    
    def test_detect_isolation_forest_anomalies(self, sample_traffic_data):
        """测试孤立森林异常检测"""
        detector = AnomalyDetector(sample_traffic_data)
        feature_cols = ['duration']
        result = detector.detect_isolation_forest_anomalies(feature_cols, contamination=0.1)
        
        assert 'anomaly_count' in result
        assert 'anomaly_indices' in result
        assert 'contamination' in result
        assert 'features_used' in result
        assert result['contamination'] == 0.1
    
    def test_detect_isolation_forest_no_features(self, sample_traffic_data):
        """测试无可用特征时的孤立森林检测"""
        detector = AnomalyDetector(sample_traffic_data)
        with pytest.raises(ValueError):
            detector.detect_isolation_forest_anomalies(['nonexistent_column'])
    
    def test_detect_trend_anomalies(self, sample_time_series_data):
        """测试趋势异常检测"""
        detector = AnomalyDetector(sample_time_series_data)
        result = detector.detect_trend_anomalies('date', 'visits', window=7)
        
        assert 'anomaly_count' in result
        assert 'anomalies' in result
        assert 'avg_deviation' in result
    
    def test_create_alerts(self, sample_time_series_data):
        """测试告警生成"""
        detector = AnomalyDetector(sample_time_series_data)
        detector.detect_statistical_anomalies('visits', threshold=2.0)
        alerts = detector.create_alerts()
        
        assert isinstance(alerts, list)
        if len(alerts) > 0:
            alert = alerts[0]
            assert 'index' in alert
            assert 'severity' in alert
            assert 'message' in alert
            assert alert['severity'] in ['high', 'medium']
    
    def test_get_summary(self, sample_time_series_data):
        """测试摘要获取"""
        detector = AnomalyDetector(sample_time_series_data)
        detector.detect_statistical_anomalies('visits')
        detector.create_alerts()
        result = detector.get_summary()
        
        assert 'total_anomalies' in result
        assert 'total_alerts' in result
        assert 'anomaly_rate' in result
    
    def test_anomaly_detection_with_outliers(self):
        """测试带明显异常值的数据"""
        # 创建带明显异常值的数据
        np.random.seed(42)
        normal_data = np.random.normal(100, 10, 95)
        outliers = [200, 250, 300]  # 明显异常值
        data = np.concatenate([normal_data, outliers])
        
        df = pd.DataFrame({'visits': data})
        detector = AnomalyDetector(df)
        result = detector.detect_statistical_anomalies('visits', threshold=2.0)
        
        # 应检测到至少 2 个异常
        assert result['anomaly_count'] >= 2
    
    def test_z_score_calculation(self, sample_time_series_data):
        """测试 Z-Score 计算正确性"""
        detector = AnomalyDetector(sample_time_series_data)
        result = detector.detect_statistical_anomalies('visits', threshold=3.0)
        
        # 验证均值和标准差计算
        # 注意：detector 用 numpy.std 默认 ddof=0（总体标准差），
        # pandas.Series.std 默认 ddof=1（样本标准差）—— 两者会有微小差异
        expected_mean = sample_time_series_data['visits'].mean()
        expected_std = sample_time_series_data['visits'].std(ddof=0)

        assert abs(result['mean'] - expected_mean) < 0.01
        assert abs(result['std'] - expected_std) < 0.01
    
    def test_alert_severity_assignment(self, sample_time_series_data):
        """测试告警严重程度分配"""
        detector = AnomalyDetector(sample_time_series_data)
        detector.detect_statistical_anomalies('visits', threshold=2.0)
        alerts = detector.create_alerts()
        
        if len(alerts) > 3:
            # 前 3 个应为 high severity
            assert all(alert['severity'] == 'high' for alert in alerts[:3])
            assert all(alert['severity'] == 'medium' for alert in alerts[3:])

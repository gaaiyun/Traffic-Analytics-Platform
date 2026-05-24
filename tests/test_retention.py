"""
留存分析模块测试 - Retention Analyzer Tests
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from retention_analyzer import RetentionAnalyzer


class TestRetentionAnalyzer:
    """留存分析器测试类"""
    
    def test_initialization(self):
        """测试初始化"""
        analyzer = RetentionAnalyzer()
        assert analyzer.data is None
        assert analyzer.cohort_data is None
    
    def test_load_data(self, sample_traffic_data):
        """测试数据加载"""
        analyzer = RetentionAnalyzer()
        analyzer.load_data(sample_traffic_data)
        assert analyzer.data is not None
    
    def test_create_cohorts_weekly(self, sample_traffic_data):
        """测试按周创建 Cohort"""
        analyzer = RetentionAnalyzer(sample_traffic_data)
        cohort_data = analyzer.create_cohorts('date', 'user_id', 'week')
        
        assert analyzer.cohort_data is not None
        assert 'cohort' in cohort_data.columns
        assert 'period' in cohort_data.columns
        assert len(cohort_data) == len(sample_traffic_data)
    
    def test_create_cohorts_monthly(self, sample_traffic_data):
        """测试按月创建 Cohort"""
        analyzer = RetentionAnalyzer(sample_traffic_data)
        cohort_data = analyzer.create_cohorts('date', 'user_id', 'month')
        
        assert 'cohort' in cohort_data.columns
        assert 'period' in cohort_data.columns
    
    def test_create_cohorts_no_data(self):
        """测试无数据时创建 Cohort"""
        analyzer = RetentionAnalyzer()
        with pytest.raises(ValueError):
            analyzer.create_cohorts()
    
    def test_calculate_retention_matrix(self, sample_traffic_data):
        """测试留存矩阵计算"""
        analyzer = RetentionAnalyzer(sample_traffic_data)
        analyzer.create_cohorts('date', 'user_id', 'week')
        retention_matrix = analyzer.calculate_retention_matrix()
        
        assert isinstance(retention_matrix, pd.DataFrame)
        assert len(retention_matrix) > 0
        # 留存率应在 0-100 之间
        assert retention_matrix.min().min() >= 0
        assert retention_matrix.max().max() <= 100
    
    def test_calculate_retention_matrix_no_cohort(self, sample_traffic_data):
        """测试未创建 Cohort 时的留存矩阵"""
        analyzer = RetentionAnalyzer(sample_traffic_data)
        with pytest.raises(ValueError):
            analyzer.calculate_retention_matrix()
    
    def test_calculate_retention_rates(self, sample_traffic_data):
        """测试留存率计算"""
        analyzer = RetentionAnalyzer(sample_traffic_data)
        analyzer.create_cohorts('date', 'user_id', 'week')
        retention_matrix = analyzer.calculate_retention_matrix()
        rates = analyzer.calculate_retention_rates(retention_matrix)
        
        assert 'day1_retention' in rates
        assert 'day7_retention' in rates
        assert 'day30_retention' in rates
        assert all(0 <= v <= 100 for v in rates.values())
    
    def test_analyze_retention_drivers(self, sample_traffic_data):
        """测试留存驱动因素分析"""
        analyzer = RetentionAnalyzer(sample_traffic_data)
        analyzer.create_cohorts('date', 'user_id', 'week')
        
        feature_cols = ['source', 'device', 'country']
        result = analyzer.analyze_retention_drivers(feature_cols, 'user_id', 7)
        
        assert isinstance(result, pd.DataFrame)
        assert 'feature' in result.columns
        assert 'retention_by_group' in result.columns
    
    def test_get_summary(self, sample_traffic_data):
        """测试摘要获取"""
        analyzer = RetentionAnalyzer(sample_traffic_data)
        analyzer.create_cohorts('date', 'user_id', 'week')
        result = analyzer.get_summary()
        
        assert 'retention_rates' in result
        assert 'cohort_count' in result
        assert 'matrix_shape' in result
    
    def test_get_summary_not_initialized(self):
        """测试未初始化时的摘要"""
        analyzer = RetentionAnalyzer()
        result = analyzer.get_summary()
        
        assert 'status' in result
        assert result['status'] == '未初始化'
    
    def test_cohort_period_calculation(self, sample_traffic_data):
        """测试 Cohort 周期计算"""
        analyzer = RetentionAnalyzer(sample_traffic_data)
        cohort_data = analyzer.create_cohorts('date', 'user_id', 'week')
        
        # period 应为非负数
        assert (cohort_data['period'] >= 0).all()
    
    def test_retention_matrix_first_period(self, sample_traffic_data):
        """测试留存矩阵首期留存率"""
        analyzer = RetentionAnalyzer(sample_traffic_data)
        analyzer.create_cohorts('date', 'user_id', 'week')
        retention_matrix = analyzer.calculate_retention_matrix()
        
        # 首期留存率应接近 100%
        first_period = retention_matrix.iloc[:, 0]
        assert first_period.min() >= 95  # 允许小误差

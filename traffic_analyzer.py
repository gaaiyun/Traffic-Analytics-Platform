"""
流量分析模块 - Traffic Analyzer Module
负责 PV/UV、来源、设备、地域等流量指标分析
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime


class TrafficAnalyzer:
    """流量分析器"""
    
    def __init__(self, data: Optional[pd.DataFrame] = None):
        self.data = data
        self.metrics = {}
    
    def load_data(self, data: pd.DataFrame) -> None:
        """加载数据"""
        self.data = data
    
    def calculate_pv_uv(self, date_column: str = 'date') -> Dict[str, Any]:
        """计算 PV (页面浏览量) 和 UV (独立访客数)"""
        if self.data is None:
            raise ValueError("未加载数据")
        
        pv = len(self.data)
        uv = self.data['user_id'].nunique() if 'user_id' in self.data.columns else 0
        
        # 按日期分组
        if date_column in self.data.columns:
            daily_stats = self.data.groupby(date_column).agg(
                pv=('user_id', 'count'),
                uv=('user_id', 'nunique')
            ).reset_index()
        else:
            daily_stats = None
        
        self.metrics['pv'] = pv
        self.metrics['uv'] = uv
        self.metrics['daily_stats'] = daily_stats
        
        return {
            'pv': pv,
            'uv': uv,
            'pv_uv_ratio': pv / uv if uv > 0 else 0,
            'daily_stats': daily_stats
        }
    
    def analyze_traffic_sources(self, source_column: str = 'source') -> Dict[str, Any]:
        """分析流量来源"""
        if self.data is None or source_column not in self.data.columns:
            raise ValueError("数据无效或缺少来源列")
        
        source_stats = self.data.groupby(source_column).agg(
            visits=('user_id', 'count'),
            unique_users=('user_id', 'nunique'),
            avg_duration=('duration', 'mean') if 'duration' in self.data.columns else ('user_id', 'count')
        ).reset_index()
        
        # 计算来源质量评分
        source_stats['quality_score'] = (
            source_stats['visits'] / source_stats['visits'].sum() * 0.4 +
            source_stats['unique_users'] / source_stats['unique_users'].sum() * 0.4 +
            (source_stats['avg_duration'] / source_stats['avg_duration'].max() * 0.2 
             if source_stats['avg_duration'].max() > 0 else 0)
        )
        
        source_stats = source_stats.sort_values('quality_score', ascending=False)
        
        return {
            'source_distribution': source_stats,
            'top_source': source_stats.iloc[0][source_column] if len(source_stats) > 0 else None,
            'source_count': len(source_stats)
        }
    
    def analyze_devices(self, device_column: str = 'device') -> Dict[str, Any]:
        """分析设备分布"""
        if self.data is None or device_column not in self.data.columns:
            raise ValueError("数据无效或缺少设备列")
        
        device_stats = self.data.groupby(device_column).agg(
            visits=('user_id', 'count'),
            percentage=('user_id', lambda x: len(x) / len(self.data) * 100)
        ).reset_index()
        
        mobile_mask = device_stats[device_column].str.contains('mobile', case=False, na=False)
        mobile_pct = (device_stats[mobile_mask]['percentage'].sum()
                      if mobile_mask.any() else 0.0)
        return {
            'device_distribution': device_stats,
            'mobile_percentage': float(mobile_pct),
        }
    
    def analyze_geography(self, geo_column: str = 'country') -> Dict[str, Any]:
        """分析地域分布"""
        if self.data is None or geo_column not in self.data.columns:
            raise ValueError("数据无效或缺少地域列")
        
        geo_stats = self.data.groupby(geo_column).agg(
            visits=('user_id', 'count'),
            unique_users=('user_id', 'nunique')
        ).reset_index().sort_values('visits', ascending=False)
        
        return {
            'geo_distribution': geo_stats,
            'top_countries': geo_stats.head(10),
            'country_count': len(geo_stats)
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取流量分析摘要"""
        return {
            'metrics': self.metrics,
            'data_shape': self.data.shape if self.data is not None else None,
            'columns': list(self.data.columns) if self.data is not None else None
        }

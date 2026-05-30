"""
预测模块 - Forecaster Module
负责 ARIMA/Prophet 流量预测、趋势预测
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings
warnings.filterwarnings('ignore')


class Forecaster:
    """流量预测器"""
    
    def __init__(self, data: Optional[pd.DataFrame] = None):
        self.data = data
        self.model = None
        self.forecast_results = None
    
    def load_data(self, data: pd.DataFrame) -> None:
        """加载数据"""
        self.data = data
    
    def prepare_time_series(self, date_column: str = 'date',
                           metric_column: str = 'visits') -> pd.Series:
        """准备时间序列数据"""
        if self.data is None:
            raise ValueError("未加载数据")
        
        data = self.data.copy()
        data[date_column] = pd.to_datetime(data[date_column])
        data = data.sort_values(date_column)
        
        # 按日期聚合
        ts = data.groupby(date_column)[metric_column].sum()
        
        # 填充缺失日期
        ts = ts.asfreq('D', fill_value=0)
        
        return ts
    
    def fit_arima(self, ts: pd.Series, order: Tuple[int, int, int] = (1, 1, 1)) -> Dict[str, Any]:
        """拟合 ARIMA 模型"""
        try:
            model = ARIMA(ts, order=order)
            self.model = model.fit()
            
            return {
                'model_type': 'ARIMA',
                'order': order,
                'aic': self.model.aic,
                'bic': self.model.bic,
                'status': 'success'
            }
        except Exception as e:
            return {
                'model_type': 'ARIMA',
                'status': 'error',
                'error': str(e)
            }
    
    def fit_exponential_smoothing(self, ts: pd.Series) -> Dict[str, Any]:
        """拟合指数平滑模型"""
        try:
            model = ExponentialSmoothing(ts, trend='add', seasonal='add', seasonal_periods=7)
            self.model = model.fit()
            
            return {
                'model_type': 'ExponentialSmoothing',
                'aic': self.model.aic,
                'bic': self.model.bic,
                'status': 'success'
            }
        except Exception as e:
            return {
                'model_type': 'ExponentialSmoothing',
                'status': 'error',
                'error': str(e)
            }
    
    def forecast(self, steps: int = 7, confidence: float = 0.95) -> Dict[str, Any]:
        """进行预测"""
        if self.model is None:
            raise ValueError("未拟合模型")

        try:
            if hasattr(self.model, 'get_forecast'):
                # ARIMA / SARIMAX：自带带置信区间的 get_forecast
                forecast = self.model.get_forecast(steps=steps)
                forecast_values = forecast.predicted_mean
                conf_int = forecast.conf_int(alpha=1 - confidence)
                lower = conf_int.iloc[:, 0]
                upper = conf_int.iloc[:, 1]
            else:
                # Holt-Winters / ExponentialSmoothing：只有 forecast()，
                # 没有解析置信区间，用残差标准差近似一个对称区间
                forecast_values = self.model.forecast(steps)
                resid = getattr(self.model, 'resid', None)
                sigma = float(np.std(resid)) if resid is not None else 0.0
                from scipy.stats import norm
                z = norm.ppf(1 - (1 - confidence) / 2)
                margin = z * sigma
                lower = forecast_values - margin
                upper = forecast_values + margin

            self.forecast_results = {
                'forecast': forecast_values,
                'lower_bound': lower,
                'upper_bound': upper
            }

            return {
                'forecast_values': forecast_values.tolist(),
                'lower_bound': lower.tolist(),
                'upper_bound': upper.tolist(),
                'steps': steps,
                'confidence': confidence
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def forecast_trend(self, ts: pd.Series, steps: int = 30) -> Dict[str, Any]:
        """趋势预测（使用简单线性回归）"""
        from scipy.stats import linregress
        
        # 准备数据
        x = np.arange(len(ts))
        y = ts.values
        
        # 拟合线性回归
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        
        # 预测
        future_x = np.arange(len(ts), len(ts) + steps)
        forecast = slope * future_x + intercept
        
        return {
            'trend': 'increasing' if slope > 0 else 'decreasing',
            'slope': slope,
            'r_squared': r_value ** 2,
            'forecast': forecast.tolist(),
            'steps': steps
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取预测摘要"""
        return {
            'model_fitted': self.model is not None,
            'model_type': type(self.model).__name__ if self.model else None,
            'forecast_available': self.forecast_results is not None
        }

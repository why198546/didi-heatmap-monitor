"""
热力图预测器
Heatmap Predictor using machine learning for order zone prediction
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import joblib
import os

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("scikit-learn not available, ML features will be limited")

from config.settings import Config
from src.database.data_manager import DataManager

logger = logging.getLogger(__name__)


class HeatmapPredictor:
    """热力图预测器"""
    
    def __init__(self):
        self.config = Config()
        self.data_manager = DataManager()
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.model_version = "v1.0"
        self.model_path = "data/models/heatmap_predictor.joblib"
        self.scaler_path = "data/models/scaler.joblib"
        self.is_trained = False
        
        # 加载已有模型
        self._load_model()
    
    def update_model(self) -> bool:
        """
        更新预测模型
        
        Returns:
            更新成功标志
        """
        try:
            logger.info("开始更新预测模型")
            
            # 获取训练数据
            ml_data = self.data_manager.get_data_for_ml(days=30)
            
            if not ml_data or not ml_data.get('heatmap_records'):
                logger.warning("没有足够的数据进行模型训练")
                return False
            
            # 检查数据量是否足够
            data_count = len(ml_data['heatmap_records'])
            if data_count < self.config.ML_CONFIG['min_data_points']:
                logger.warning(f"数据量不足，需要至少{self.config.ML_CONFIG['min_data_points']}条，"
                              f"当前只有{data_count}条")
                return False
            
            # 准备训练数据
            features, targets = self._prepare_training_data(ml_data)
            
            if features is None or targets is None:
                logger.error("训练数据准备失败")
                return False
            
            # 训练模型
            success = self._train_model(features, targets)
            
            if success:
                # 保存模型
                self._save_model()
                logger.info("预测模型更新完成")
                return True
            else:
                logger.error("模型训练失败")
                return False
                
        except Exception as e:
            logger.error(f"模型更新异常: {e}")
            return False
    
    def predict_heatmap(self, target_time: datetime, 
                       current_location: Dict[str, float]) -> Optional[Dict]:
        """
        预测指定时间的热力图
        
        Args:
            target_time: 目标预测时间
            current_location: 当前位置
            
        Returns:
            预测结果字典 或 None
        """
        try:
            if not self.is_trained:
                logger.warning("模型尚未训练，无法进行预测")
                return None
            
            logger.info(f"预测目标时间: {target_time}")
            
            # 准备预测特征
            prediction_features = self._prepare_prediction_features(target_time, current_location)
            
            if prediction_features is None:
                logger.error("预测特征准备失败")
                return None
            
            # 执行预测
            predictions = self._make_prediction(prediction_features)
            
            if predictions is None:
                logger.error("预测执行失败")
                return None
            
            # 生成预测结果
            result = {
                'target_time': target_time.isoformat(),
                'prediction_time': datetime.now().isoformat(),
                'predicted_hexagon_count': predictions[0],
                'confidence_level': self._calculate_prediction_confidence(prediction_features),
                'predicted_zones': self._generate_predicted_zones(
                    predictions[0], current_location
                ),
                'model_version': self.model_version,
                'location': current_location
            }
            
            # 保存预测结果
            self.data_manager.save_prediction(result, self.model_version)
            
            return result
            
        except Exception as e:
            logger.error(f"热力图预测异常: {e}")
            return None
    
    def predict_multiple_times(self, base_time: datetime, 
                              intervals_minutes: List[int],
                              current_location: Dict[str, float]) -> List[Dict]:
        """
        预测多个时间点的热力图
        
        Args:
            base_time: 基准时间
            intervals_minutes: 时间间隔列表（分钟）
            current_location: 当前位置
            
        Returns:
            预测结果列表
        """
        predictions = []
        
        for interval in intervals_minutes:
            target_time = base_time + timedelta(minutes=interval)
            prediction = self.predict_heatmap(target_time, current_location)
            
            if prediction:
                prediction['interval_minutes'] = interval
                predictions.append(prediction)
        
        return predictions
    
    def _prepare_training_data(self, ml_data: Dict) -> Tuple[Optional[pd.DataFrame], Optional[np.ndarray]]:
        """
        准备训练数据
        
        Args:
            ml_data: 机器学习数据
            
        Returns:
            (特征数据框, 目标数组)
        """
        try:
            # 转换为DataFrame
            heatmap_df = pd.DataFrame(ml_data['heatmap_records'], columns=[
                'timestamp', 'latitude', 'longitude', 'hexagon_count',
                'is_holiday', 'day_of_week', 'hour_of_day'
            ])
            
            if heatmap_df.empty:
                logger.error("热力图数据为空")
                return None, None
            
            # 时间特征工程
            heatmap_df['timestamp'] = pd.to_datetime(heatmap_df['timestamp'])
            heatmap_df = heatmap_df.sort_values('timestamp')
            
            # 添加滞后特征（前1小时、前2小时的数据）
            heatmap_df['hexagon_count_lag1'] = heatmap_df['hexagon_count'].shift(1)
            heatmap_df['hexagon_count_lag2'] = heatmap_df['hexagon_count'].shift(2)
            
            # 添加移动平均特征
            heatmap_df['hexagon_count_ma3'] = heatmap_df['hexagon_count'].rolling(window=3).mean()
            heatmap_df['hexagon_count_ma6'] = heatmap_df['hexagon_count'].rolling(window=6).mean()
            
            # 添加时间周期特征
            heatmap_df['hour_sin'] = np.sin(2 * np.pi * heatmap_df['hour_of_day'] / 24)
            heatmap_df['hour_cos'] = np.cos(2 * np.pi * heatmap_df['hour_of_day'] / 24)
            heatmap_df['day_sin'] = np.sin(2 * np.pi * heatmap_df['day_of_week'] / 7)
            heatmap_df['day_cos'] = np.cos(2 * np.pi * heatmap_df['day_of_week'] / 7)
            
            # 添加位置特征（距离拉萨中心的距离）
            lhasa_center_lat = (self.config.LHASA_BOUNDS['north'] + self.config.LHASA_BOUNDS['south']) / 2
            lhasa_center_lng = (self.config.LHASA_BOUNDS['east'] + self.config.LHASA_BOUNDS['west']) / 2
            
            heatmap_df['distance_to_center'] = np.sqrt(
                (heatmap_df['latitude'] - lhasa_center_lat) ** 2 +
                (heatmap_df['longitude'] - lhasa_center_lng) ** 2
            )
            
            # 选择特征列
            feature_columns = [
                'latitude', 'longitude', 'is_holiday', 'day_of_week', 'hour_of_day',
                'hexagon_count_lag1', 'hexagon_count_lag2',
                'hexagon_count_ma3', 'hexagon_count_ma6',
                'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
                'distance_to_center'
            ]
            
            # 去除包含NaN的行
            heatmap_df = heatmap_df.dropna()
            
            if heatmap_df.empty:
                logger.error("去除NaN后数据为空")
                return None, None
            
            # 提取特征和目标
            X = heatmap_df[feature_columns]
            y = heatmap_df['hexagon_count'].values
            
            self.feature_columns = feature_columns
            
            logger.info(f"训练数据准备完成: {len(X)} 条样本, {len(feature_columns)} 个特征")
            return X, y
            
        except Exception as e:
            logger.error(f"训练数据准备异常: {e}")
            return None, None
    
    def _train_model(self, features: pd.DataFrame, targets: np.ndarray) -> bool:
        """
        训练预测模型
        
        Args:
            features: 特征数据
            targets: 目标数据
            
        Returns:
            训练成功标志
        """
        try:
            logger.info("开始训练预测模型")
            
            # 数据分割
            X_train, X_test, y_train, y_test = train_test_split(
                features, targets, test_size=0.2, random_state=42
            )
            
            # 特征标准化
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # 训练随机森林模型
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # 评估模型
            y_pred = self.model.predict(X_test_scaled)
            
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            
            logger.info(f"模型训练完成 - MAE: {mae:.3f}, RMSE: {rmse:.3f}, R²: {r2:.3f}")
            
            # 特征重要性
            feature_importance = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            logger.info("特征重要性排序:")
            for _, row in feature_importance.head(5).iterrows():
                logger.info(f"  {row['feature']}: {row['importance']:.3f}")
            
            self.is_trained = True
            return True
            
        except Exception as e:
            logger.error(f"模型训练异常: {e}")
            return False
    
    def _prepare_prediction_features(self, target_time: datetime, 
                                   current_location: Dict[str, float]) -> Optional[np.ndarray]:
        """
        准备预测特征
        
        Args:
            target_time: 目标时间
            current_location: 当前位置
            
        Returns:
            预测特征数组 或 None
        """
        try:
            if not self.feature_columns:
                logger.error("特征列未定义")
                return None
            
            # 获取最近的历史数据用于滞后特征
            recent_data = self.data_manager.get_recent_heatmap_data(hours=6)
            
            # 计算滞后特征
            lag1 = recent_data[0]['hexagon_count'] if recent_data else 0
            lag2 = recent_data[1]['hexagon_count'] if len(recent_data) > 1 else 0
            
            # 计算移动平均
            recent_counts = [d['hexagon_count'] for d in recent_data[:6]]
            ma3 = np.mean(recent_counts[:3]) if len(recent_counts) >= 3 else 0
            ma6 = np.mean(recent_counts) if len(recent_counts) >= 6 else 0
            
            # 时间特征
            hour = target_time.hour
            day_of_week = target_time.weekday()
            is_holiday = target_time.weekday() >= 5  # 简化的节假日判断
            
            # 周期特征
            hour_sin = np.sin(2 * np.pi * hour / 24)
            hour_cos = np.cos(2 * np.pi * hour / 24)
            day_sin = np.sin(2 * np.pi * day_of_week / 7)
            day_cos = np.cos(2 * np.pi * day_of_week / 7)
            
            # 位置特征
            lhasa_center_lat = (self.config.LHASA_BOUNDS['north'] + self.config.LHASA_BOUNDS['south']) / 2
            lhasa_center_lng = (self.config.LHASA_BOUNDS['east'] + self.config.LHASA_BOUNDS['west']) / 2
            
            distance_to_center = np.sqrt(
                (current_location['latitude'] - lhasa_center_lat) ** 2 +
                (current_location['longitude'] - lhasa_center_lng) ** 2
            )
            
            # 构建特征向量
            features = [
                current_location['latitude'],
                current_location['longitude'],
                float(is_holiday),
                float(day_of_week),
                float(hour),
                lag1,
                lag2,
                ma3,
                ma6,
                hour_sin,
                hour_cos,
                day_sin,
                day_cos,
                distance_to_center
            ]
            
            return np.array(features).reshape(1, -1)
            
        except Exception as e:
            logger.error(f"预测特征准备异常: {e}")
            return None
    
    def _make_prediction(self, features: np.ndarray) -> Optional[np.ndarray]:
        """
        执行预测
        
        Args:
            features: 特征数组
            
        Returns:
            预测结果 或 None
        """
        try:
            if not self.is_trained or self.model is None or self.scaler is None:
                logger.error("模型未训练或未加载")
                return None
            
            # 特征标准化
            features_scaled = self.scaler.transform(features)
            
            # 执行预测
            predictions = self.model.predict(features_scaled)
            
            # 确保预测值非负
            predictions = np.maximum(predictions, 0)
            
            return predictions
            
        except Exception as e:
            logger.error(f"预测执行异常: {e}")
            return None
    
    def _calculate_prediction_confidence(self, features: np.ndarray) -> float:
        """
        计算预测置信度
        
        Args:
            features: 特征数组
            
        Returns:
            置信度分数 (0-1)
        """
        try:
            # 简化的置信度计算，基于训练数据的相似性
            base_confidence = 0.7
            
            # 如果是工作日的工作时间，置信度更高
            hour = features[0, 4]  # hour_of_day特征
            if 7 <= hour <= 19:  # 工作时间
                base_confidence += 0.1
            
            # 如果有足够的历史数据，置信度更高
            recent_data_count = len(self.data_manager.get_recent_heatmap_data(hours=24))
            if recent_data_count > 10:
                base_confidence += 0.1
            
            return min(1.0, base_confidence)
            
        except Exception as e:
            logger.error(f"置信度计算异常: {e}")
            return 0.5
    
    def _generate_predicted_zones(self, predicted_count: float, 
                                 location: Dict[str, float]) -> List[Dict]:
        """
        根据预测的六边形数量生成预测区域
        
        Args:
            predicted_count: 预测的六边形数量
            location: 当前位置
            
        Returns:
            预测区域列表
        """
        zones = []
        
        # 简化实现：根据历史热点区域生成预测
        try:
            # 获取历史热点区域
            recent_data = self.data_manager.get_recent_heatmap_data(hours=48)
            
            # 统计历史热点位置
            zone_frequency = {}
            for data in recent_data:
                for hexagon in data.get('hexagons', []):
                    geo_center = hexagon.get('geo_center', {})
                    if geo_center:
                        # 简化的位置聚类（按0.01度网格）
                        lat_grid = round(geo_center['latitude'], 2)
                        lng_grid = round(geo_center['longitude'], 2)
                        key = f"{lat_grid},{lng_grid}"
                        
                        zone_frequency[key] = zone_frequency.get(key, 0) + 1
            
            # 选择最热门的区域
            sorted_zones = sorted(zone_frequency.items(), key=lambda x: x[1], reverse=True)
            
            for i, (zone_key, frequency) in enumerate(sorted_zones[:int(predicted_count)]):
                lat, lng = map(float, zone_key.split(','))
                
                zones.append({
                    'center': {'latitude': lat, 'longitude': lng},
                    'predicted_intensity': min(1.0, frequency / 10),  # 归一化强度
                    'confidence': 0.8 - (i * 0.1)  # 递减置信度
                })
            
            return zones
            
        except Exception as e:
            logger.error(f"预测区域生成异常: {e}")
            return []
    
    def _load_model(self):
        """加载已保存的模型"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                
                # 加载特征列信息
                feature_info_path = "data/models/feature_info.joblib"
                if os.path.exists(feature_info_path):
                    feature_info = joblib.load(feature_info_path)
                    self.feature_columns = feature_info.get('columns')
                    self.model_version = feature_info.get('version', 'v1.0')
                
                self.is_trained = True
                logger.info(f"模型加载成功: {self.model_version}")
            else:
                logger.info("未找到已保存的模型，需要训练新模型")
                
        except Exception as e:
            logger.error(f"模型加载异常: {e}")
    
    def _save_model(self):
        """保存模型"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            # 保存模型和标准化器
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            
            # 保存特征信息
            feature_info = {
                'columns': self.feature_columns,
                'version': self.model_version,
                'save_time': datetime.now().isoformat()
            }
            
            feature_info_path = "data/models/feature_info.joblib"
            joblib.dump(feature_info, feature_info_path)
            
            logger.info("模型保存成功")
            
        except Exception as e:
            logger.error(f"模型保存异常: {e}")
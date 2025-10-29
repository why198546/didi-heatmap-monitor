"""
数据管理器
Data Manager for storing and retrieving heatmap data
"""

import sqlite3
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import threading

from config.settings import Config

logger = logging.getLogger(__name__)


class DataManager:
    """数据管理器"""
    
    def __init__(self):
        self.config = Config()
        self.db_path = self.config.DATABASE_CONFIG['path']
        self.lock = threading.Lock()
        
    def initialize_database(self):
        """初始化数据库表结构"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建热力图数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS heatmap_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        latitude REAL NOT NULL,
                        longitude REAL NOT NULL,
                        map_image_path TEXT,
                        hexagon_count INTEGER DEFAULT 0,
                        hexagons_data TEXT,  -- JSON格式存储六边形数据
                        weather_info TEXT,   -- JSON格式存储天气信息
                        is_holiday BOOLEAN DEFAULT 0,
                        day_of_week INTEGER,
                        hour_of_day INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建六边形详细数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS hexagon_details (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        heatmap_id INTEGER NOT NULL,
                        center_lat REAL NOT NULL,
                        center_lng REAL NOT NULL,
                        area_pixels INTEGER,
                        area_m2 REAL,
                        confidence REAL,
                        color_type TEXT,
                        vertices_count INTEGER,
                        bounds_north REAL,
                        bounds_south REAL,
                        bounds_east REAL,
                        bounds_west REAL,
                        FOREIGN KEY (heatmap_id) REFERENCES heatmap_data (id)
                    )
                ''')
                
                # 创建预测结果表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS predictions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        prediction_time DATETIME NOT NULL,
                        target_time DATETIME NOT NULL,
                        prediction_data TEXT,  -- JSON格式存储预测结果
                        model_version TEXT,
                        accuracy_score REAL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建模型性能表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS model_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_version TEXT NOT NULL,
                        training_date DATETIME NOT NULL,
                        training_samples INTEGER,
                        validation_accuracy REAL,
                        test_accuracy REAL,
                        features_used TEXT,  -- JSON格式
                        hyperparameters TEXT,  -- JSON格式
                        performance_metrics TEXT  -- JSON格式
                    )
                ''')
                
                # 创建索引提高查询性能
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_heatmap_timestamp 
                    ON heatmap_data (timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_heatmap_location 
                    ON heatmap_data (latitude, longitude)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_hexagon_location 
                    ON hexagon_details (center_lat, center_lng)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_predictions_time 
                    ON predictions (prediction_time, target_time)
                ''')
                
                conn.commit()
                logger.info("数据库初始化完成")
                
        except Exception as e:
            logger.error(f"数据库初始化异常: {e}")
    
    def save_heatmap_data(self, data_record: Dict) -> Optional[int]:
        """
        保存热力图数据
        
        Args:
            data_record: 数据记录字典
            
        Returns:
            插入的记录ID 或 None
        """
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 提取基本信息
                    timestamp = data_record['timestamp']
                    location = data_record['location']
                    hexagons = data_record.get('hexagons', [])
                    map_image_path = data_record.get('map_image_path', '')
                    
                    # 计算时间相关特征
                    dt = timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(str(timestamp))
                    day_of_week = dt.weekday()  # 0=周一, 6=周日
                    hour_of_day = dt.hour
                    
                    # 检查是否为节假日（这里简化处理，实际可以接入节假日API）
                    is_holiday = self._check_if_holiday(dt)
                    
                    # 插入主记录
                    cursor.execute('''
                        INSERT INTO heatmap_data (
                            timestamp, latitude, longitude, map_image_path,
                            hexagon_count, hexagons_data, is_holiday,
                            day_of_week, hour_of_day
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        dt.isoformat(),
                        location['latitude'],
                        location['longitude'],
                        map_image_path,
                        len(hexagons),
                        json.dumps(hexagons, ensure_ascii=False),
                        is_holiday,
                        day_of_week,
                        hour_of_day
                    ))
                    
                    heatmap_id = cursor.lastrowid
                    
                    # 插入六边形详细数据
                    for hexagon in hexagons:
                        geo_center = hexagon.get('geo_center', {})
                        geo_bounds = hexagon.get('geo_bounds', {})
                        
                        cursor.execute('''
                            INSERT INTO hexagon_details (
                                heatmap_id, center_lat, center_lng, area_pixels,
                                area_m2, confidence, color_type, vertices_count,
                                bounds_north, bounds_south, bounds_east, bounds_west
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            heatmap_id,
                            geo_center.get('latitude', 0),
                            geo_center.get('longitude', 0),
                            hexagon.get('area', 0),
                            hexagon.get('geo_area_m2', 0),
                            hexagon.get('confidence', 0),
                            hexagon.get('color_type', ''),
                            hexagon.get('vertices_count', 0),
                            geo_bounds.get('north', 0),
                            geo_bounds.get('south', 0),
                            geo_bounds.get('east', 0),
                            geo_bounds.get('west', 0)
                        ))
                    
                    conn.commit()
                    logger.info(f"热力图数据已保存，ID: {heatmap_id}")
                    return heatmap_id
                    
        except Exception as e:
            logger.error(f"热力图数据保存异常: {e}")
            return None
    
    def get_heatmap_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        获取指定时间范围的热力图数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            热力图数据列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM heatmap_data 
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                ''', (start_time.isoformat(), end_time.isoformat()))
                
                columns = [description[0] for description in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    record = dict(zip(columns, row))
                    # 解析JSON数据
                    if record['hexagons_data']:
                        record['hexagons'] = json.loads(record['hexagons_data'])
                    else:
                        record['hexagons'] = []
                    
                    results.append(record)
                
                logger.debug(f"获取到 {len(results)} 条热力图数据")
                return results
                
        except Exception as e:
            logger.error(f"热力图数据获取异常: {e}")
            return []
    
    def get_recent_heatmap_data(self, hours: int = 24) -> List[Dict]:
        """
        获取最近N小时的热力图数据
        
        Args:
            hours: 小时数
            
        Returns:
            热力图数据列表
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        return self.get_heatmap_data(start_time, end_time)
    
    def get_hexagon_statistics(self, start_time: datetime, end_time: datetime) -> Dict:
        """
        获取六边形统计信息
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            统计信息字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 基本统计
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_records,
                        AVG(hexagon_count) as avg_hexagons,
                        MAX(hexagon_count) as max_hexagons,
                        MIN(hexagon_count) as min_hexagons
                    FROM heatmap_data 
                    WHERE timestamp BETWEEN ? AND ?
                ''', (start_time.isoformat(), end_time.isoformat()))
                
                basic_stats = cursor.fetchone()
                
                # 按小时统计
                cursor.execute('''
                    SELECT 
                        hour_of_day,
                        AVG(hexagon_count) as avg_hexagons,
                        COUNT(*) as records_count
                    FROM heatmap_data 
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY hour_of_day
                    ORDER BY hour_of_day
                ''', (start_time.isoformat(), end_time.isoformat()))
                
                hourly_stats = cursor.fetchall()
                
                # 按工作日统计
                cursor.execute('''
                    SELECT 
                        day_of_week,
                        AVG(hexagon_count) as avg_hexagons,
                        COUNT(*) as records_count
                    FROM heatmap_data 
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY day_of_week
                    ORDER BY day_of_week
                ''', (start_time.isoformat(), end_time.isoformat()))
                
                daily_stats = cursor.fetchall()
                
                return {
                    'basic': {
                        'total_records': basic_stats[0],
                        'avg_hexagons': basic_stats[1] or 0,
                        'max_hexagons': basic_stats[2] or 0,
                        'min_hexagons': basic_stats[3] or 0
                    },
                    'hourly': [
                        {'hour': row[0], 'avg_hexagons': row[1], 'count': row[2]}
                        for row in hourly_stats
                    ],
                    'daily': [
                        {'day': row[0], 'avg_hexagons': row[1], 'count': row[2]}
                        for row in daily_stats
                    ]
                }
                
        except Exception as e:
            logger.error(f"六边形统计异常: {e}")
            return {}
    
    def save_prediction(self, prediction_data: Dict, model_version: str) -> bool:
        """
        保存预测结果
        
        Args:
            prediction_data: 预测数据
            model_version: 模型版本
            
        Returns:
            保存成功标志
        """
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO predictions (
                            prediction_time, target_time, prediction_data, model_version
                        ) VALUES (?, ?, ?, ?)
                    ''', (
                        datetime.now().isoformat(),
                        prediction_data['target_time'],
                        json.dumps(prediction_data, ensure_ascii=False),
                        model_version
                    ))
                    
                    conn.commit()
                    logger.info("预测结果已保存")
                    return True
                    
        except Exception as e:
            logger.error(f"预测结果保存异常: {e}")
            return False
    
    def get_latest_predictions(self, limit: int = 10) -> List[Dict]:
        """
        获取最新的预测结果
        
        Args:
            limit: 返回数量限制
            
        Returns:
            预测结果列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM predictions 
                    ORDER BY prediction_time DESC 
                    LIMIT ?
                ''', (limit,))
                
                columns = [description[0] for description in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    record = dict(zip(columns, row))
                    if record['prediction_data']:
                        record['prediction'] = json.loads(record['prediction_data'])
                    results.append(record)
                
                return results
                
        except Exception as e:
            logger.error(f"预测结果获取异常: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 30):
        """
        清理旧数据
        
        Args:
            days: 保留天数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 删除旧的热力图数据
                    cursor.execute('''
                        DELETE FROM heatmap_data 
                        WHERE timestamp < ?
                    ''', (cutoff_date.isoformat(),))
                    
                    deleted_heatmap = cursor.rowcount
                    
                    # 删除旧的预测数据
                    cursor.execute('''
                        DELETE FROM predictions 
                        WHERE prediction_time < ?
                    ''', (cutoff_date.isoformat(),))
                    
                    deleted_predictions = cursor.rowcount
                    
                    conn.commit()
                    
                    logger.info(f"数据清理完成: 删除了{deleted_heatmap}条热力图数据, "
                               f"{deleted_predictions}条预测数据")
                    
        except Exception as e:
            logger.error(f"数据清理异常: {e}")
    
    def _check_if_holiday(self, date: datetime) -> bool:
        """
        检查是否为节假日
        
        Args:
            date: 日期
            
        Returns:
            是否为节假日
        """
        # 简化实现，实际可以接入节假日API
        # 这里只判断周末
        return date.weekday() >= 5  # 周六和周日
    
    def get_data_for_ml(self, days: int = 30) -> Dict[str, Any]:
        """
        获取用于机器学习的数据
        
        Args:
            days: 获取最近N天的数据
            
        Returns:
            ML数据字典
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取热力图数据
                cursor.execute('''
                    SELECT 
                        timestamp, latitude, longitude, hexagon_count,
                        is_holiday, day_of_week, hour_of_day
                    FROM heatmap_data 
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp
                ''', (start_time.isoformat(), end_time.isoformat()))
                
                heatmap_data = cursor.fetchall()
                
                # 获取六边形详细数据
                cursor.execute('''
                    SELECT 
                        h.timestamp, hd.center_lat, hd.center_lng, 
                        hd.area_m2, hd.confidence, hd.color_type
                    FROM heatmap_data h
                    JOIN hexagon_details hd ON h.id = hd.heatmap_id
                    WHERE h.timestamp BETWEEN ? AND ?
                    ORDER BY h.timestamp
                ''', (start_time.isoformat(), end_time.isoformat()))
                
                hexagon_data = cursor.fetchall()
                
                return {
                    'heatmap_records': heatmap_data,
                    'hexagon_records': hexagon_data,
                    'data_range': {
                        'start': start_time.isoformat(),
                        'end': end_time.isoformat()
                    }
                }
                
        except Exception as e:
            logger.error(f"ML数据获取异常: {e}")
            return {}
    
    def backup_database(self, backup_path: Optional[str] = None):
        """
        备份数据库
        
        Args:
            backup_path: 备份文件路径
        """
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"data/backups/didi_heatmap_backup_{timestamp}.db"
            
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"数据库备份完成: {backup_path}")
            
        except Exception as e:
            logger.error(f"数据库备份异常: {e}")
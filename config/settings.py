"""
系统配置设置
System Configuration Settings
"""

import os
from typing import Dict, Any


class Config:
    """配置管理类"""
    
    # ADB设置
    ADB_PATH = "/opt/homebrew/bin/adb"  # ADB工具路径，根据实际安装位置调整
    DEVICE_ID = None  # 设备ID，None表示自动检测
    
    # 地图设置
    MAP_ZOOM_LEVEL = 14  # 地图缩放级别（14级）
    SCREEN_WIDTH = 1080  # 手机屏幕宽度
    SCREEN_HEIGHT = 2340  # 手机屏幕高度
    
    # 拉萨主城区坐标边界 (WGS84坐标系)
    LHASA_BOUNDS = {
        'north': 29.7000,   # 北边界
        'south': 29.6000,   # 南边界  
        'east': 91.2000,    # 东边界
        'west': 91.0500     # 西边界
    }
    
    # 地图界面设置
    MAP_UI_MARGINS = {
        'top': 200,     # 顶部状态栏、导航栏等
        'bottom': 150,  # 底部按钮栏等
        'left': 50,     # 左侧边距
        'right': 50     # 右侧边距
    }
    
    # 地图实际显示区域（去除UI元素后）
    MAP_DISPLAY_WIDTH = SCREEN_WIDTH - MAP_UI_MARGINS['left'] - MAP_UI_MARGINS['right']
    MAP_DISPLAY_HEIGHT = SCREEN_HEIGHT - MAP_UI_MARGINS['top'] - MAP_UI_MARGINS['bottom']
    
    # 滑动设置
    SWIPE_OVERLAP = 0.2  # 滑动时的重叠比例，避免漏掉边界区域
    SWIPE_DURATION = 500  # 滑动持续时间（毫秒）
    
    # 图像处理设置
    HEXAGON_COLOR_RANGES = {
        'orange_dark': {
            'lower': [10, 100, 100],   # HSV下界
            'upper': [25, 255, 255]    # HSV上界
        },
        'orange_light': {
            'lower': [15, 50, 150],
            'upper': [35, 255, 255]
        }
    }
    
    # GPS定位点检测设置
    GPS_ICON_TEMPLATES = {
        'blue_dot': 'config/templates/blue_dot.png',           # 蓝色圆点模板
        'blue_dot_pin': 'config/templates/blue_dot_pin.png'    # 蓝色圆点+📍模板
    }
    
    # 数据库设置
    DATABASE_CONFIG = {
        'type': 'sqlite',
        'path': 'data/didi_heatmap.db',
        'backup_interval': 24 * 60 * 60  # 备份间隔（秒）
    }
    
    # 机器学习设置
    ML_CONFIG = {
        'min_data_points': 100,        # 开始训练模型的最小数据点数
        'retrain_interval': 6 * 60 * 60,  # 重新训练间隔（秒）
        'prediction_window': [30, 60]     # 预测窗口（分钟）：30分钟和1小时
    }
    
    # Web仪表板设置
    WEB_CONFIG = {
        'host': '0.0.0.0',
        'port': 5000,
        'debug': False,
        'auto_refresh_interval': 30  # 自动刷新间隔（秒）
    }
    
    # 监控设置
    MONITORING_CONFIG = {
        'capture_interval': 5 * 60,    # 捕获间隔（秒）
        'max_retry_attempts': 3,       # 最大重试次数
        'retry_delay': 30,             # 重试延迟（秒）
        'cleanup_old_data_days': 30    # 清理旧数据的天数
    }
    
    # 日志设置
    LOGGING_CONFIG = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_path': 'data/logs/didi_monitor.log',
        'max_size': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    }
    
    @classmethod
    def get_meters_per_pixel(cls, zoom_level: int = None) -> float:
        """
        根据缩放级别计算每像素对应的米数
        基于Web墨卡托投影，在拉萨纬度（约29.65°）计算
        """
        if zoom_level is None:
            zoom_level = cls.MAP_ZOOM_LEVEL
            
        # 地球周长（米）
        earth_circumference = 40075016.686
        
        # 拉萨纬度的余弦值（用于墨卡托投影校正）
        import math
        lhasa_lat_rad = math.radians(29.65)
        lat_correction = math.cos(lhasa_lat_rad)
        
        # 计算每像素米数
        meters_per_pixel = (earth_circumference * lat_correction) / (256 * (2 ** zoom_level))
        return meters_per_pixel
    
    @classmethod
    def get_coordinate_per_pixel(cls, zoom_level: int = None) -> Dict[str, float]:
        """
        计算每像素对应的经纬度变化
        """
        if zoom_level is None:
            zoom_level = cls.MAP_ZOOM_LEVEL
            
        # 每像素对应的米数
        meters_per_pixel = cls.get_meters_per_pixel(zoom_level)
        
        # 转换为经纬度（在拉萨附近的近似值）
        lat_per_pixel = meters_per_pixel / 111320  # 1度纬度约等于111320米
        
        # 经度需要根据纬度调整
        import math
        lhasa_lat_rad = math.radians(29.65)
        lng_per_pixel = meters_per_pixel / (111320 * math.cos(lhasa_lat_rad))
        
        return {
            'lat_per_pixel': lat_per_pixel,
            'lng_per_pixel': lng_per_pixel
        }
    
    @classmethod
    def get_swipe_distance_pixels(cls) -> Dict[str, int]:
        """
        计算滑动距离（像素）
        考虑重叠比例，确保完整覆盖区域
        """
        return {
            'horizontal': int(cls.MAP_DISPLAY_WIDTH * (1 - cls.SWIPE_OVERLAP)),
            'vertical': int(cls.MAP_DISPLAY_HEIGHT * (1 - cls.SWIPE_OVERLAP))
        }
    
    @classmethod
    def load_from_file(cls, config_path: str = 'config/settings.json'):
        """从配置文件加载设置"""
        import json
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                # 更新类属性
                for key, value in config_data.items():
                    if hasattr(cls, key):
                        setattr(cls, key, value)
                        
            except Exception as e:
                print(f"配置文件加载失败: {e}")
    
    @classmethod
    def save_to_file(cls, config_path: str = 'config/settings.json'):
        """保存设置到配置文件"""
        import json
        
        # 收集所有大写的类属性（配置项）
        config_data = {}
        for attr_name in dir(cls):
            if attr_name.isupper() and not attr_name.startswith('_'):
                config_data[attr_name] = getattr(cls, attr_name)
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"配置文件保存失败: {e}")


# 在模块加载时尝试加载配置文件
if __name__ != "__main__":
    Config.load_from_file()
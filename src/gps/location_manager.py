"""
GPS位置管理器
GPS Location Manager for handling location data
"""

import cv2
import numpy as np
import logging
from typing import Optional, Dict, Tuple
import json
import os
from datetime import datetime

from config.settings import Config

logger = logging.getLogger(__name__)


class LocationManager:
    """GPS位置管理器"""
    
    def __init__(self):
        self.config = Config()
        self.location_cache_file = "data/location_cache.json"
        self.gps_templates = self._load_gps_templates()
        
    def _load_gps_templates(self) -> Dict:
        """加载GPS定位点模板图像"""
        templates = {}
        try:
            for template_name, template_path in self.config.GPS_ICON_TEMPLATES.items():
                if os.path.exists(template_path):
                    template = cv2.imread(template_path)
                    if template is not None:
                        templates[template_name] = template
                        logger.debug(f"GPS模板已加载: {template_name}")
                else:
                    logger.warning(f"GPS模板文件不存在: {template_path}")
            
            return templates
            
        except Exception as e:
            logger.error(f"GPS模板加载异常: {e}")
            return {}
    
    def get_current_location(self) -> Optional[Dict[str, float]]:
        """
        获取当前GPS位置
        
        Returns:
            GPS坐标字典 {'latitude': float, 'longitude': float} 或 None
        """
        try:
            # 首先尝试从缓存获取最近的位置
            cached_location = self._get_cached_location()
            
            # 这里可以添加多种GPS获取方式
            # 1. 从Android设备获取
            # 2. 从图像分析获取
            # 3. 手动输入的位置
            # 4. 缓存的位置
            
            # 如果有缓存位置且时间较新（比如10分钟内），则使用缓存
            if cached_location and self._is_location_recent(cached_location):
                logger.debug("使用缓存的GPS位置")
                return {
                    'latitude': cached_location['latitude'],
                    'longitude': cached_location['longitude']
                }
            
            # 生成模拟的拉萨位置（开发测试用）
            # 实际使用时应该通过ADB从设备获取真实GPS位置
            mock_location = self._get_mock_lhasa_location()
            
            # 缓存位置
            if mock_location:
                self._cache_location(mock_location)
            
            return mock_location
            
        except Exception as e:
            logger.error(f"GPS位置获取异常: {e}")
            return None
    
    def find_gps_icon_in_screenshot(self, screenshot_path: str) -> Optional[Tuple[int, int]]:
        """
        在截图中查找GPS定位图标
        
        Args:
            screenshot_path: 截图文件路径
            
        Returns:
            GPS图标中心坐标 (x, y) 或 None
        """
        try:
            if not self.gps_templates:
                logger.warning("没有GPS模板图像，无法进行图标匹配")
                return None
            
            # 读取截图
            screenshot = cv2.imread(screenshot_path)
            if screenshot is None:
                logger.error(f"无法读取截图: {screenshot_path}")
                return None
            
            best_match = None
            best_confidence = 0.0
            
            # 尝试匹配每个GPS模板
            for template_name, template in self.gps_templates.items():
                match_result = self._match_template(screenshot, template)
                
                if match_result and match_result['confidence'] > best_confidence:
                    best_confidence = match_result['confidence']
                    best_match = match_result
                    logger.debug(f"GPS图标匹配: {template_name}, 置信度: {best_confidence:.3f}")
            
            if best_match and best_confidence > 0.7:  # 置信度阈值
                return (best_match['center_x'], best_match['center_y'])
            else:
                logger.warning("未找到GPS定位图标")
                return None
                
        except Exception as e:
            logger.error(f"GPS图标查找异常: {e}")
            return None
    
    def _match_template(self, image: np.ndarray, template: np.ndarray) -> Optional[Dict]:
        """
        模板匹配
        
        Args:
            image: 目标图像
            template: 模板图像
            
        Returns:
            匹配结果字典 或 None
        """
        try:
            # 模板匹配
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            
            # 找到最佳匹配位置
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > 0.5:  # 基本置信度阈值
                # 计算中心点坐标
                template_h, template_w = template.shape[:2]
                center_x = max_loc[0] + template_w // 2
                center_y = max_loc[1] + template_h // 2
                
                return {
                    'center_x': center_x,
                    'center_y': center_y,
                    'confidence': max_val,
                    'top_left': max_loc
                }
            
            return None
            
        except Exception as e:
            logger.error(f"模板匹配异常: {e}")
            return None
    
    def calculate_location_from_image(self, screenshot_path: str, 
                                    reference_location: Dict[str, float]) -> Optional[Dict[str, float]]:
        """
        基于截图和参考位置计算准确的GPS坐标
        
        Args:
            screenshot_path: 截图路径
            reference_location: 参考GPS位置
            
        Returns:
            计算得到的GPS位置 或 None
        """
        try:
            # 在截图中查找GPS图标
            gps_icon_pos = self.find_gps_icon_in_screenshot(screenshot_path)
            
            if not gps_icon_pos:
                logger.warning("无法在截图中找到GPS图标，使用参考位置")
                return reference_location
            
            # 计算GPS图标相对于屏幕中心的偏移
            screen_center_x = self.config.SCREEN_WIDTH // 2
            screen_center_y = self.config.SCREEN_HEIGHT // 2
            
            offset_x = gps_icon_pos[0] - screen_center_x
            offset_y = gps_icon_pos[1] - screen_center_y
            
            # 转换像素偏移为地理坐标偏移
            coord_per_pixel = self.config.get_coordinate_per_pixel()
            
            lat_offset = -offset_y * coord_per_pixel['lat_per_pixel']  # Y轴向上为正
            lng_offset = offset_x * coord_per_pixel['lng_per_pixel']
            
            # 计算实际GPS位置
            actual_location = {
                'latitude': reference_location['latitude'] + lat_offset,
                'longitude': reference_location['longitude'] + lng_offset
            }
            
            # 验证位置是否在拉萨范围内
            if self._is_location_in_lhasa(actual_location):
                logger.debug(f"基于图像计算的GPS位置: {actual_location}")
                return actual_location
            else:
                logger.warning("计算的GPS位置超出拉萨范围，使用参考位置")
                return reference_location
                
        except Exception as e:
            logger.error(f"基于图像的位置计算异常: {e}")
            return reference_location
    
    def _get_mock_lhasa_location(self) -> Dict[str, float]:
        """
        生成模拟的拉萨GPS位置（开发测试用）
        
        Returns:
            模拟GPS位置
        """
        # 拉萨市中心附近的坐标（布达拉宫附近）
        return {
            'latitude': 29.6516,
            'longitude': 91.1175
        }
    
    def _is_location_in_lhasa(self, location: Dict[str, float]) -> bool:
        """
        检查GPS位置是否在拉萨范围内
        
        Args:
            location: GPS位置
            
        Returns:
            是否在拉萨范围内
        """
        lat = location['latitude']
        lng = location['longitude']
        
        return (self.config.LHASA_BOUNDS['south'] <= lat <= self.config.LHASA_BOUNDS['north'] and
                self.config.LHASA_BOUNDS['west'] <= lng <= self.config.LHASA_BOUNDS['east'])
    
    def _get_cached_location(self) -> Optional[Dict]:
        """从缓存获取GPS位置"""
        try:
            if os.path.exists(self.location_cache_file):
                with open(self.location_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    return cache_data.get('last_location')
            return None
            
        except Exception as e:
            logger.error(f"GPS缓存读取异常: {e}")
            return None
    
    def _cache_location(self, location: Dict[str, float]):
        """缓存GPS位置"""
        try:
            cache_data = {
                'last_location': location,
                'timestamp': datetime.now().isoformat(),
                'source': 'mock'  # 可以标识位置来源
            }
            
            os.makedirs(os.path.dirname(self.location_cache_file), exist_ok=True)
            
            with open(self.location_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"GPS缓存保存异常: {e}")
    
    def _is_location_recent(self, cached_location: Dict, max_age_minutes: int = 10) -> bool:
        """检查缓存位置是否足够新"""
        try:
            if 'timestamp' not in cached_location:
                return False
            
            from datetime import timedelta
            cache_time = datetime.fromisoformat(cached_location['timestamp'])
            age = datetime.now() - cache_time
            
            return age < timedelta(minutes=max_age_minutes)
            
        except Exception as e:
            logger.error(f"位置时间检查异常: {e}")
            return False
    
    def convert_pixel_to_coords(self, pixel_x: int, pixel_y: int, 
                               reference_location: Dict[str, float]) -> Dict[str, float]:
        """
        将像素坐标转换为地理坐标
        
        Args:
            pixel_x: 像素X坐标
            pixel_y: 像素Y坐标
            reference_location: 参考点GPS坐标
            
        Returns:
            地理坐标
        """
        try:
            coord_per_pixel = self.config.get_coordinate_per_pixel()
            
            # 计算相对于参考点的地理偏移
            lat_offset = -pixel_y * coord_per_pixel['lat_per_pixel']
            lng_offset = pixel_x * coord_per_pixel['lng_per_pixel']
            
            return {
                'latitude': reference_location['latitude'] + lat_offset,
                'longitude': reference_location['longitude'] + lng_offset
            }
            
        except Exception as e:
            logger.error(f"像素坐标转换异常: {e}")
            return reference_location
    
    def convert_coords_to_pixel(self, target_location: Dict[str, float],
                               reference_location: Dict[str, float]) -> Tuple[int, int]:
        """
        将地理坐标转换为像素坐标
        
        Args:
            target_location: 目标GPS坐标
            reference_location: 参考点GPS坐标
            
        Returns:
            像素坐标 (x, y)
        """
        try:
            coord_per_pixel = self.config.get_coordinate_per_pixel()
            
            # 计算地理坐标差
            lat_diff = target_location['latitude'] - reference_location['latitude']
            lng_diff = target_location['longitude'] - reference_location['longitude']
            
            # 转换为像素差
            pixel_y = -int(lat_diff / coord_per_pixel['lat_per_pixel'])
            pixel_x = int(lng_diff / coord_per_pixel['lng_per_pixel'])
            
            return pixel_x, pixel_y
            
        except Exception as e:
            logger.error(f"地理坐标转换异常: {e}")
            return 0, 0
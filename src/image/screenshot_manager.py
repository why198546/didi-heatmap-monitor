"""
截图管理器
Screenshot Manager for capturing map screenshots
"""

import os
import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from config.settings import Config

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """截图管理器"""
    
    def __init__(self):
        self.config = Config()
        self.screenshot_dir = "data/screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def capture_lhasa_area(self, current_location: Dict[str, float], 
                          android_controller) -> List[Dict]:
        """
        捕获拉萨主城区的完整地图截图
        
        Args:
            current_location: 当前GPS位置 {'latitude': float, 'longitude': float}
            android_controller: Android控制器实例
            
        Returns:
            截图信息列表，每个元素包含文件路径和地理坐标信息
        """
        try:
            logger.info("开始捕获拉萨主城区地图截图")
            
            # 计算需要覆盖的网格
            grid_plan = self._calculate_capture_grid(current_location)
            
            if not grid_plan:
                logger.error("无法计算截图网格")
                return []
            
            screenshots = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 移动到起始位置（左上角）
            if not self._move_to_start_position(current_location, android_controller):
                logger.error("无法移动到起始位置")
                return []
            
            # 等待地图稳定
            time.sleep(2)
            
            # 按网格逐行截图
            for row_idx, row in enumerate(grid_plan['grid']):
                for col_idx, cell in enumerate(row):
                    try:
                        # 截图文件名
                        screenshot_filename = f"{timestamp}_r{row_idx}_c{col_idx}.png"
                        screenshot_path = os.path.join(self.screenshot_dir, screenshot_filename)
                        
                        # 执行截图
                        if android_controller.capture_screenshot(screenshot_path):
                            screenshot_info = {
                                'file_path': screenshot_path,
                                'row': row_idx,
                                'col': col_idx,
                                'center_lat': cell['center_lat'],
                                'center_lng': cell['center_lng'],
                                'bounds': cell['bounds'],
                                'timestamp': datetime.now()
                            }
                            screenshots.append(screenshot_info)
                            logger.debug(f"截图完成: 第{row_idx}行第{col_idx}列")
                        else:
                            logger.error(f"截图失败: 第{row_idx}行第{col_idx}列")
                        
                        # 移动到下一个位置
                        if col_idx < len(row) - 1:  # 不是行的最后一列
                            self._move_horizontal(android_controller, 'right')
                            time.sleep(1)  # 等待地图稳定
                        
                    except Exception as e:
                        logger.error(f"截图过程异常 (第{row_idx}行第{col_idx}列): {e}")
                        continue
                
                # 移动到下一行
                if row_idx < len(grid_plan['grid']) - 1:  # 不是最后一行
                    # 移动到行首
                    self._move_to_row_start(android_controller, len(row))
                    # 向下移动一行
                    self._move_vertical(android_controller, 'down')
                    time.sleep(1)
            
            logger.info(f"截图完成，共捕获 {len(screenshots)} 张图片")
            return screenshots
            
        except Exception as e:
            logger.error(f"截图捕获异常: {e}")
            return []
    
    def _calculate_capture_grid(self, current_location: Dict[str, float]) -> Optional[Dict]:
        """
        计算截图网格
        
        Args:
            current_location: 当前位置
            
        Returns:
            网格计划字典
        """
        try:
            # 获取每像素对应的坐标变化
            coord_per_pixel = self.config.get_coordinate_per_pixel()
            
            # 计算实际地图显示区域对应的地理范围
            map_width_degrees = self.config.MAP_DISPLAY_WIDTH * coord_per_pixel['lng_per_pixel']
            map_height_degrees = self.config.MAP_DISPLAY_HEIGHT * coord_per_pixel['lat_per_pixel']
            
            # 计算滑动距离对应的地理范围
            swipe_distances = self.config.get_swipe_distance_pixels()
            swipe_width_degrees = swipe_distances['horizontal'] * coord_per_pixel['lng_per_pixel']
            swipe_height_degrees = swipe_distances['vertical'] * coord_per_pixel['lat_per_pixel']
            
            # 计算需要的网格尺寸
            total_width = self.config.LHASA_BOUNDS['east'] - self.config.LHASA_BOUNDS['west']
            total_height = self.config.LHASA_BOUNDS['north'] - self.config.LHASA_BOUNDS['south']
            
            cols = max(1, int(total_width / swipe_width_degrees) + 1)
            rows = max(1, int(total_height / swipe_height_degrees) + 1)
            
            logger.info(f"计算网格尺寸: {rows}行 x {cols}列")
            
            # 生成网格坐标
            grid = []
            for row in range(rows):
                grid_row = []
                for col in range(cols):
                    # 计算每个网格单元的中心坐标
                    center_lng = self.config.LHASA_BOUNDS['west'] + (col + 0.5) * swipe_width_degrees
                    center_lat = self.config.LHASA_BOUNDS['north'] - (row + 0.5) * swipe_height_degrees
                    
                    # 计算边界
                    bounds = {
                        'west': center_lng - map_width_degrees / 2,
                        'east': center_lng + map_width_degrees / 2,
                        'north': center_lat + map_height_degrees / 2,
                        'south': center_lat - map_height_degrees / 2
                    }
                    
                    grid_row.append({
                        'center_lat': center_lat,
                        'center_lng': center_lng,
                        'bounds': bounds
                    })
                
                grid.append(grid_row)
            
            return {
                'grid': grid,
                'rows': rows,
                'cols': cols,
                'swipe_width_degrees': swipe_width_degrees,
                'swipe_height_degrees': swipe_height_degrees
            }
            
        except Exception as e:
            logger.error(f"网格计算异常: {e}")
            return None
    
    def _move_to_start_position(self, current_location: Dict[str, float], 
                               android_controller) -> bool:
        """
        移动到截图起始位置（拉萨区域左上角）
        
        Args:
            current_location: 当前位置
            android_controller: Android控制器
            
        Returns:
            移动成功标志
        """
        try:
            # 计算当前位置到左上角的距离
            target_lat = self.config.LHASA_BOUNDS['north']
            target_lng = self.config.LHASA_BOUNDS['west']
            
            coord_per_pixel = self.config.get_coordinate_per_pixel()
            
            # 计算需要移动的像素距离
            lat_diff = current_location['latitude'] - target_lat
            lng_diff = current_location['longitude'] - target_lng
            
            pixel_x = int(lng_diff / coord_per_pixel['lng_per_pixel'])
            pixel_y = int(lat_diff / coord_per_pixel['lat_per_pixel'])
            
            logger.debug(f"移动到起始位置，像素偏移: ({pixel_x}, {pixel_y})")
            
            # 分步移动，避免单次移动距离过大
            screen_center_x = self.config.SCREEN_WIDTH // 2
            screen_center_y = self.config.SCREEN_HEIGHT // 2
            
            max_swipe_distance = min(self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT) // 3
            
            # 水平移动
            while abs(pixel_x) > 50:  # 50像素的容差
                move_x = max(-max_swipe_distance, min(max_swipe_distance, pixel_x))
                
                start_x = screen_center_x
                end_x = screen_center_x - move_x  # 向左移动为正值
                
                if not android_controller.swipe(start_x, screen_center_y, end_x, screen_center_y):
                    logger.error("水平移动失败")
                    return False
                
                pixel_x -= move_x
                time.sleep(1)
            
            # 垂直移动
            while abs(pixel_y) > 50:
                move_y = max(-max_swipe_distance, min(max_swipe_distance, pixel_y))
                
                start_y = screen_center_y
                end_y = screen_center_y + move_y  # 向上移动为负值，向下为正值
                
                if not android_controller.swipe(screen_center_x, start_y, screen_center_x, end_y):
                    logger.error("垂直移动失败")
                    return False
                
                pixel_y -= move_y
                time.sleep(1)
            
            logger.info("成功移动到起始位置")
            return True
            
        except Exception as e:
            logger.error(f"移动到起始位置异常: {e}")
            return False
    
    def _move_horizontal(self, android_controller, direction: str) -> bool:
        """
        水平移动
        
        Args:
            android_controller: Android控制器
            direction: 'left' 或 'right'
            
        Returns:
            移动成功标志
        """
        try:
            swipe_distance = self.config.get_swipe_distance_pixels()['horizontal']
            
            center_x = self.config.SCREEN_WIDTH // 2
            center_y = self.config.SCREEN_HEIGHT // 2
            
            if direction == 'right':
                start_x = center_x + swipe_distance // 2
                end_x = center_x - swipe_distance // 2
            else:  # left
                start_x = center_x - swipe_distance // 2
                end_x = center_x + swipe_distance // 2
            
            return android_controller.swipe(
                start_x, center_y, end_x, center_y, 
                self.config.SWIPE_DURATION
            )
            
        except Exception as e:
            logger.error(f"水平移动异常: {e}")
            return False
    
    def _move_vertical(self, android_controller, direction: str) -> bool:
        """
        垂直移动
        
        Args:
            android_controller: Android控制器
            direction: 'up' 或 'down'
            
        Returns:
            移动成功标志
        """
        try:
            swipe_distance = self.config.get_swipe_distance_pixels()['vertical']
            
            center_x = self.config.SCREEN_WIDTH // 2
            center_y = self.config.SCREEN_HEIGHT // 2
            
            if direction == 'down':
                start_y = center_y - swipe_distance // 2
                end_y = center_y + swipe_distance // 2
            else:  # up
                start_y = center_y + swipe_distance // 2
                end_y = center_y - swipe_distance // 2
            
            return android_controller.swipe(
                center_x, start_y, center_x, end_y,
                self.config.SWIPE_DURATION
            )
            
        except Exception as e:
            logger.error(f"垂直移动异常: {e}")
            return False
    
    def _move_to_row_start(self, android_controller, cols_in_row: int) -> bool:
        """
        移动到行首
        
        Args:
            android_controller: Android控制器
            cols_in_row: 当前行的列数
            
        Returns:
            移动成功标志
        """
        try:
            # 向左移动到行首
            for _ in range(cols_in_row - 1):
                if not self._move_horizontal(android_controller, 'left'):
                    return False
                time.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.error(f"移动到行首异常: {e}")
            return False
    
    def cleanup_old_screenshots(self, days: int = 7):
        """
        清理旧的截图文件
        
        Args:
            days: 保留天数
        """
        try:
            import glob
            from datetime import timedelta
            
            cutoff_time = datetime.now() - timedelta(days=days)
            
            screenshot_files = glob.glob(os.path.join(self.screenshot_dir, "*.png"))
            
            deleted_count = 0
            for file_path in screenshot_files:
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 个旧截图文件")
                
        except Exception as e:
            logger.error(f"清理截图文件异常: {e}")
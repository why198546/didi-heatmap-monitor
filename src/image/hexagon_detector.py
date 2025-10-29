"""
六边形检测器
Hexagon Detector for identifying orange order zones in DiDi heatmap
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional

from config.settings import Config

logger = logging.getLogger(__name__)


class HexagonDetector:
    """橙色六边形检测器"""
    
    def __init__(self):
        self.config = Config()
        
    def detect_hexagons(self, map_image: np.ndarray) -> List[Dict]:
        """
        检测地图中的橙色六边形热点区域
        
        Args:
            map_image: 拼接后的地图图像
            
        Returns:
            检测到的六边形列表，每个元素包含位置、面积等信息
        """
        try:
            if map_image is None:
                logger.error("输入地图图像为空")
                return []
            
            logger.info("开始检测橙色六边形热点区域")
            
            # 1. 检测深色橙色六边形
            dark_hexagons = self._detect_color_hexagons(
                map_image, 
                self.config.HEXAGON_COLOR_RANGES['orange_dark'],
                'dark_orange'
            )
            
            # 2. 检测浅色橙色六边形
            light_hexagons = self._detect_color_hexagons(
                map_image,
                self.config.HEXAGON_COLOR_RANGES['orange_light'],
                'light_orange'
            )
            
            # 3. 合并结果并去重
            all_hexagons = dark_hexagons + light_hexagons
            filtered_hexagons = self._filter_and_merge_hexagons(all_hexagons)
            
            # 4. 提取地理坐标信息
            geo_hexagons = self._add_geographic_info(filtered_hexagons, map_image.shape)
            
            logger.info(f"检测完成，找到 {len(geo_hexagons)} 个橙色六边形区域")
            return geo_hexagons
            
        except Exception as e:
            logger.error(f"六边形检测异常: {e}")
            return []
    
    def _detect_color_hexagons(self, image: np.ndarray, color_range: Dict, 
                              color_type: str) -> List[Dict]:
        """
        检测特定颜色的六边形
        
        Args:
            image: 输入图像
            color_range: 颜色范围字典 {'lower': [h,s,v], 'upper': [h,s,v]}
            color_type: 颜色类型标识
            
        Returns:
            检测到的六边形列表
        """
        try:
            # 转换到HSV色彩空间
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # 创建颜色掩码
            lower = np.array(color_range['lower'])
            upper = np.array(color_range['upper'])
            mask = cv2.inRange(hsv, lower, upper)
            
            # 形态学操作，去除噪声
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # 查找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            hexagons = []
            for contour in contours:
                hexagon_info = self._analyze_contour(contour, color_type)
                if hexagon_info:
                    hexagons.append(hexagon_info)
            
            logger.debug(f"检测到 {len(hexagons)} 个{color_type}六边形")
            return hexagons
            
        except Exception as e:
            logger.error(f"{color_type}六边形检测异常: {e}")
            return []
    
    def _analyze_contour(self, contour: np.ndarray, color_type: str) -> Optional[Dict]:
        """
        分析轮廓是否为六边形
        
        Args:
            contour: 轮廓点
            color_type: 颜色类型
            
        Returns:
            六边形信息字典 或 None
        """
        try:
            # 计算轮廓面积
            area = cv2.contourArea(contour)
            
            # 过滤太小的区域
            if area < 50:  # 最小面积阈值
                return None
            
            # 轮廓近似
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # 检查边数（六边形应该有6个顶点，但允许一定误差）
            vertices_count = len(approx)
            if vertices_count < 4 or vertices_count > 8:
                return None
            
            # 计算轮廓的外接矩形
            x, y, w, h = cv2.boundingRect(contour)
            
            # 计算宽高比，六边形应该接近正方形
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                return None
            
            # 计算轮廓的凸包
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            
            # 计算凸包面积比，六边形应该比较规整
            if hull_area > 0:
                solidity = area / hull_area
                if solidity < 0.7:  # 凸包面积比阈值
                    return None
            
            # 计算中心点
            M = cv2.moments(contour)
            if M["m00"] != 0:
                center_x = int(M["m10"] / M["m00"])
                center_y = int(M["m01"] / M["m00"])
            else:
                center_x, center_y = x + w//2, y + h//2
            
            # 计算圆度 (周长^2 / 面积)，用于判断形状规整度
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
            else:
                circularity = 0
            
            # 六边形的圆度应该在一定范围内
            if circularity < 0.3 or circularity > 1.0:
                return None
            
            return {
                'contour': contour.tolist(),  # 转为列表便于序列化
                'center': (center_x, center_y),
                'area': area,
                'bounding_box': (x, y, w, h),
                'vertices_count': vertices_count,
                'aspect_ratio': aspect_ratio,
                'solidity': solidity,
                'circularity': circularity,
                'color_type': color_type,
                'perimeter': perimeter
            }
            
        except Exception as e:
            logger.error(f"轮廓分析异常: {e}")
            return None
    
    def _filter_and_merge_hexagons(self, hexagons: List[Dict]) -> List[Dict]:
        """
        过滤和合并重复的六边形
        
        Args:
            hexagons: 原始六边形列表
            
        Returns:
            过滤后的六边形列表
        """
        try:
            if not hexagons:
                return []
            
            # 按面积排序（大的优先）
            sorted_hexagons = sorted(hexagons, key=lambda x: x['area'], reverse=True)
            
            filtered = []
            distance_threshold = 50  # 中心点距离阈值（像素）
            
            for hexagon in sorted_hexagons:
                is_duplicate = False
                current_center = hexagon['center']
                
                # 检查是否与已有六边形重叠
                for existing in filtered:
                    existing_center = existing['center']
                    distance = np.sqrt(
                        (current_center[0] - existing_center[0])**2 + 
                        (current_center[1] - existing_center[1])**2
                    )
                    
                    if distance < distance_threshold:
                        is_duplicate = True
                        # 如果当前六边形面积更大，替换已有的
                        if hexagon['area'] > existing['area']:
                            filtered.remove(existing)
                            filtered.append(hexagon)
                        break
                
                if not is_duplicate:
                    filtered.append(hexagon)
            
            logger.debug(f"过滤前: {len(hexagons)} 个，过滤后: {len(filtered)} 个")
            return filtered
            
        except Exception as e:
            logger.error(f"六边形过滤异常: {e}")
            return hexagons
    
    def _add_geographic_info(self, hexagons: List[Dict], image_shape: Tuple) -> List[Dict]:
        """
        为六边形添加地理坐标信息
        
        Args:
            hexagons: 六边形列表
            image_shape: 地图图像尺寸 (height, width, channels)
            
        Returns:
            包含地理信息的六边形列表
        """
        try:
            if not hexagons:
                return []
            
            height, width = image_shape[:2]
            
            # 获取每像素对应的地理坐标变化
            coord_per_pixel = self.config.get_coordinate_per_pixel()
            
            # 计算地图图像的地理边界
            # 假设地图图像覆盖了整个拉萨区域
            total_lat_span = self.config.LHASA_BOUNDS['north'] - self.config.LHASA_BOUNDS['south']
            total_lng_span = self.config.LHASA_BOUNDS['east'] - self.config.LHASA_BOUNDS['west']
            
            lat_per_pixel = total_lat_span / height
            lng_per_pixel = total_lng_span / width
            
            geo_hexagons = []
            for hexagon in hexagons:
                # 复制原有信息
                geo_hexagon = hexagon.copy()
                
                # 计算中心点地理坐标
                center_x, center_y = hexagon['center']
                
                # 从左上角开始计算
                latitude = self.config.LHASA_BOUNDS['north'] - (center_y * lat_per_pixel)
                longitude = self.config.LHASA_BOUNDS['west'] + (center_x * lng_per_pixel)
                
                geo_hexagon['geo_center'] = {
                    'latitude': latitude,
                    'longitude': longitude
                }
                
                # 计算地理范围（边界框）
                x, y, w, h = hexagon['bounding_box']
                
                north = self.config.LHASA_BOUNDS['north'] - (y * lat_per_pixel)
                south = self.config.LHASA_BOUNDS['north'] - ((y + h) * lat_per_pixel)
                west = self.config.LHASA_BOUNDS['west'] + (x * lng_per_pixel)
                east = self.config.LHASA_BOUNDS['west'] + ((x + w) * lng_per_pixel)
                
                geo_hexagon['geo_bounds'] = {
                    'north': north,
                    'south': south,
                    'west': west,
                    'east': east
                }
                
                # 估算实际面积（平方米）
                # 简化计算，假设为矩形区域
                lat_distance = abs(north - south) * 111320  # 1度纬度约111320米
                lng_distance = abs(east - west) * 111320 * np.cos(np.radians(latitude))
                geo_area = lat_distance * lng_distance  # 平方米
                
                geo_hexagon['geo_area_m2'] = geo_area
                
                # 添加置信度评分
                confidence = self._calculate_confidence(hexagon)
                geo_hexagon['confidence'] = confidence
                
                geo_hexagons.append(geo_hexagon)
            
            return geo_hexagons
            
        except Exception as e:
            logger.error(f"地理信息添加异常: {e}")
            return hexagons
    
    def _calculate_confidence(self, hexagon: Dict) -> float:
        """
        计算六边形检测的置信度
        
        Args:
            hexagon: 六边形信息
            
        Returns:
            置信度分数 (0-1)
        """
        try:
            # 基础分数
            score = 0.5
            
            # 面积加分（较大的六边形更可信）
            area = hexagon['area']
            if area > 500:
                score += 0.2
            elif area > 200:
                score += 0.1
            
            # 顶点数加分（接近6个顶点的更可信）
            vertices = hexagon['vertices_count']
            if vertices == 6:
                score += 0.2
            elif vertices in [5, 7]:
                score += 0.1
            
            # 宽高比加分（接近1的更可信）
            aspect_ratio = hexagon['aspect_ratio']
            if 0.8 <= aspect_ratio <= 1.2:
                score += 0.15
            elif 0.6 <= aspect_ratio <= 1.4:
                score += 0.1
            
            # 凸包面积比加分
            solidity = hexagon['solidity']
            if solidity > 0.9:
                score += 0.15
            elif solidity > 0.8:
                score += 0.1
            
            # 圆度加分
            circularity = hexagon['circularity']
            if 0.7 <= circularity <= 0.9:
                score += 0.1
            elif 0.5 <= circularity <= 1.0:
                score += 0.05
            
            # 确保分数在0-1范围内
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"置信度计算异常: {e}")
            return 0.5
    
    def visualize_detection(self, image: np.ndarray, hexagons: List[Dict], 
                           save_path: Optional[str] = None) -> np.ndarray:
        """
        可视化六边形检测结果
        
        Args:
            image: 原始地图图像
            hexagons: 检测到的六边形列表
            save_path: 保存路径（可选）
            
        Returns:
            标注后的图像
        """
        try:
            # 复制图像用于标注
            annotated = image.copy()
            
            for i, hexagon in enumerate(hexagons):
                # 获取轮廓点
                contour = np.array(hexagon['contour'], dtype=np.int32)
                
                # 根据颜色类型选择标注颜色
                if hexagon['color_type'] == 'dark_orange':
                    color = (0, 0, 255)  # 红色
                else:
                    color = (0, 255, 255)  # 黄色
                
                # 绘制轮廓
                cv2.drawContours(annotated, [contour], -1, color, 2)
                
                # 绘制中心点
                center = hexagon['center']
                cv2.circle(annotated, center, 5, color, -1)
                
                # 添加标签
                label = f"{i+1}({hexagon['confidence']:.2f})"
                cv2.putText(annotated, label, 
                           (center[0] - 20, center[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # 保存标注图像
            if save_path:
                cv2.imwrite(save_path, annotated)
                logger.info(f"检测结果可视化已保存: {save_path}")
            
            return annotated
            
        except Exception as e:
            logger.error(f"可视化异常: {e}")
            return image
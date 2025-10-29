"""
地图拼接器
Map Stitcher for combining multiple screenshots into a complete map
"""

import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
from PIL import Image

from config.settings import Config

logger = logging.getLogger(__name__)


class MapStitcher:
    """地图拼接器"""
    
    def __init__(self):
        self.config = Config()
        
    def stitch_screenshots(self, screenshots: List[Dict]) -> Optional[np.ndarray]:
        """
        拼接多张截图为完整地图
        
        Args:
            screenshots: 截图信息列表
            
        Returns:
            拼接后的地图图像 (numpy数组) 或 None
        """
        try:
            if not screenshots:
                logger.error("没有截图可供拼接")
                return None
            
            logger.info(f"开始拼接 {len(screenshots)} 张截图")
            
            # 按行列排序截图
            sorted_screenshots = self._sort_screenshots_by_grid(screenshots)
            
            if not sorted_screenshots:
                logger.error("截图排序失败")
                return None
            
            # 提取地图区域（去除UI元素）
            cropped_images = self._extract_map_regions(sorted_screenshots)
            
            if not cropped_images:
                logger.error("地图区域提取失败")
                return None
            
            # 执行拼接
            stitched_map = self._perform_stitching(cropped_images)
            
            if stitched_map is not None:
                logger.info(f"拼接完成，地图尺寸: {stitched_map.shape[:2]}")
            else:
                logger.error("地图拼接失败")
            
            return stitched_map
            
        except Exception as e:
            logger.error(f"地图拼接异常: {e}")
            return None
    
    def _sort_screenshots_by_grid(self, screenshots: List[Dict]) -> Optional[List[List[Dict]]]:
        """
        按网格位置排序截图
        
        Args:
            screenshots: 截图信息列表
            
        Returns:
            按行列组织的截图网格 或 None
        """
        try:
            # 获取网格尺寸
            max_row = max(s['row'] for s in screenshots)
            max_col = max(s['col'] for s in screenshots)
            
            # 创建网格
            grid = [[None for _ in range(max_col + 1)] for _ in range(max_row + 1)]
            
            # 填充网格
            for screenshot in screenshots:
                row, col = screenshot['row'], screenshot['col']
                grid[row][col] = screenshot
            
            # 检查网格完整性
            missing_positions = []
            for row in range(max_row + 1):
                for col in range(max_col + 1):
                    if grid[row][col] is None:
                        missing_positions.append((row, col))
            
            if missing_positions:
                logger.warning(f"网格中缺失截图位置: {missing_positions}")
                # 可以考虑插值或跳过缺失位置
            
            return grid
            
        except Exception as e:
            logger.error(f"截图排序异常: {e}")
            return None
    
    def _extract_map_regions(self, grid: List[List[Dict]]) -> Optional[List[List[np.ndarray]]]:
        """
        从截图中提取纯地图区域（去除UI元素）
        
        Args:
            grid: 截图网格
            
        Returns:
            裁剪后的图像网格 或 None
        """
        try:
            cropped_grid = []
            
            for row_idx, row in enumerate(grid):
                cropped_row = []
                
                for col_idx, screenshot in enumerate(row):
                    if screenshot is None:
                        cropped_row.append(None)
                        continue
                    
                    # 读取图像
                    image = cv2.imread(screenshot['file_path'])
                    if image is None:
                        logger.error(f"无法读取截图: {screenshot['file_path']}")
                        cropped_row.append(None)
                        continue
                    
                    # 裁剪地图区域（去除UI元素）
                    cropped_image = self._crop_map_area(image)
                    
                    if cropped_image is not None:
                        cropped_row.append(cropped_image)
                    else:
                        logger.error(f"地图区域裁剪失败: {screenshot['file_path']}")
                        cropped_row.append(None)
                
                cropped_grid.append(cropped_row)
            
            return cropped_grid
            
        except Exception as e:
            logger.error(f"地图区域提取异常: {e}")
            return None
    
    def _crop_map_area(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        裁剪图像的地图区域，去除UI元素
        
        Args:
            image: 原始截图
            
        Returns:
            裁剪后的地图区域 或 None
        """
        try:
            height, width = image.shape[:2]
            
            # 根据配置裁剪
            top = self.config.MAP_UI_MARGINS['top']
            bottom = height - self.config.MAP_UI_MARGINS['bottom']
            left = self.config.MAP_UI_MARGINS['left']
            right = width - self.config.MAP_UI_MARGINS['right']
            
            # 验证裁剪区域有效性
            if top >= bottom or left >= right:
                logger.error("无效的裁剪区域")
                return None
            
            cropped = image[top:bottom, left:right]
            return cropped
            
        except Exception as e:
            logger.error(f"图像裁剪异常: {e}")
            return None
    
    def _perform_stitching(self, cropped_grid: List[List[np.ndarray]]) -> Optional[np.ndarray]:
        """
        执行图像拼接
        
        Args:
            cropped_grid: 裁剪后的图像网格
            
        Returns:
            拼接后的地图 或 None
        """
        try:
            # 首先按行拼接
            stitched_rows = []
            
            for row_idx, row in enumerate(cropped_grid):
                # 过滤掉None值
                valid_images = [img for img in row if img is not None]
                
                if not valid_images:
                    logger.warning(f"第{row_idx}行没有有效图像")
                    continue
                
                # 水平拼接这一行的图像
                if len(valid_images) == 1:
                    row_stitched = valid_images[0]
                else:
                    row_stitched = self._stitch_horizontally(valid_images)
                
                if row_stitched is not None:
                    stitched_rows.append(row_stitched)
                else:
                    logger.error(f"第{row_idx}行拼接失败")
            
            if not stitched_rows:
                logger.error("没有成功拼接的行")
                return None
            
            # 然后垂直拼接所有行
            if len(stitched_rows) == 1:
                final_stitched = stitched_rows[0]
            else:
                final_stitched = self._stitch_vertically(stitched_rows)
            
            return final_stitched
            
        except Exception as e:
            logger.error(f"图像拼接执行异常: {e}")
            return None
    
    def _stitch_horizontally(self, images: List[np.ndarray]) -> Optional[np.ndarray]:
        """
        水平拼接图像
        
        Args:
            images: 图像列表
            
        Returns:
            拼接后的图像 或 None
        """
        try:
            if not images:
                return None
            
            # 确保所有图像高度一致
            target_height = images[0].shape[0]
            resized_images = []
            
            for img in images:
                if img.shape[0] != target_height:
                    # 调整高度
                    aspect_ratio = img.shape[1] / img.shape[0]
                    new_width = int(target_height * aspect_ratio)
                    resized = cv2.resize(img, (new_width, target_height))
                    resized_images.append(resized)
                else:
                    resized_images.append(img)
            
            # 处理重叠区域
            processed_images = self._handle_horizontal_overlap(resized_images)
            
            # 水平拼接
            result = np.hstack(processed_images)
            return result
            
        except Exception as e:
            logger.error(f"水平拼接异常: {e}")
            return None
    
    def _stitch_vertically(self, images: List[np.ndarray]) -> Optional[np.ndarray]:
        """
        垂直拼接图像
        
        Args:
            images: 图像列表
            
        Returns:
            拼接后的图像 或 None
        """
        try:
            if not images:
                return None
            
            # 确保所有图像宽度一致
            target_width = images[0].shape[1]
            resized_images = []
            
            for img in images:
                if img.shape[1] != target_width:
                    # 调整宽度
                    aspect_ratio = img.shape[0] / img.shape[1]
                    new_height = int(target_width * aspect_ratio)
                    resized = cv2.resize(img, (target_width, new_height))
                    resized_images.append(resized)
                else:
                    resized_images.append(img)
            
            # 处理重叠区域
            processed_images = self._handle_vertical_overlap(resized_images)
            
            # 垂直拼接
            result = np.vstack(processed_images)
            return result
            
        except Exception as e:
            logger.error(f"垂直拼接异常: {e}")
            return None
    
    def _handle_horizontal_overlap(self, images: List[np.ndarray]) -> List[np.ndarray]:
        """
        处理水平拼接的重叠区域
        
        Args:
            images: 图像列表
            
        Returns:
            处理后的图像列表
        """
        try:
            if len(images) <= 1:
                return images
            
            # 计算重叠像素数
            overlap_pixels = int(self.config.MAP_DISPLAY_WIDTH * self.config.SWIPE_OVERLAP)
            
            processed = [images[0]]  # 第一张图完整保留
            
            for i in range(1, len(images)):
                current_img = images[i]
                
                # 去除左侧重叠部分
                if overlap_pixels < current_img.shape[1]:
                    cropped = current_img[:, overlap_pixels:]
                    processed.append(cropped)
                else:
                    # 重叠区域太大，保留部分图像
                    cropped = current_img[:, overlap_pixels//2:]
                    processed.append(cropped)
            
            return processed
            
        except Exception as e:
            logger.error(f"水平重叠处理异常: {e}")
            return images
    
    def _handle_vertical_overlap(self, images: List[np.ndarray]) -> List[np.ndarray]:
        """
        处理垂直拼接的重叠区域
        
        Args:
            images: 图像列表
            
        Returns:
            处理后的图像列表
        """
        try:
            if len(images) <= 1:
                return images
            
            # 计算重叠像素数
            overlap_pixels = int(self.config.MAP_DISPLAY_HEIGHT * self.config.SWIPE_OVERLAP)
            
            processed = [images[0]]  # 第一张图完整保留
            
            for i in range(1, len(images)):
                current_img = images[i]
                
                # 去除顶部重叠部分
                if overlap_pixels < current_img.shape[0]:
                    cropped = current_img[overlap_pixels:, :]
                    processed.append(cropped)
                else:
                    # 重叠区域太大，保留部分图像
                    cropped = current_img[overlap_pixels//2:, :]
                    processed.append(cropped)
            
            return processed
            
        except Exception as e:
            logger.error(f"垂直重叠处理异常: {e}")
            return images
    
    def save_stitched_map(self, stitched_map: np.ndarray, save_path: str) -> bool:
        """
        保存拼接后的地图
        
        Args:
            stitched_map: 拼接后的地图
            save_path: 保存路径
            
        Returns:
            保存成功标志
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 保存图像
            success = cv2.imwrite(save_path, stitched_map)
            
            if success:
                logger.info(f"拼接地图已保存: {save_path}")
                return True
            else:
                logger.error(f"拼接地图保存失败: {save_path}")
                return False
                
        except Exception as e:
            logger.error(f"拼接地图保存异常: {e}")
            return False
    
    def enhance_map_quality(self, stitched_map: np.ndarray) -> np.ndarray:
        """
        增强拼接地图的质量
        
        Args:
            stitched_map: 原始拼接地图
            
        Returns:
            增强后的地图
        """
        try:
            # 去除接缝
            enhanced = self._remove_seams(stitched_map)
            
            # 色彩校正
            enhanced = self._correct_colors(enhanced)
            
            # 锐化
            enhanced = self._sharpen_image(enhanced)
            
            return enhanced
            
        except Exception as e:
            logger.error(f"地图质量增强异常: {e}")
            return stitched_map
    
    def _remove_seams(self, image: np.ndarray) -> np.ndarray:
        """去除拼接接缝"""
        # 简单的高斯模糊处理接缝区域
        return cv2.GaussianBlur(image, (3, 3), 0)
    
    def _correct_colors(self, image: np.ndarray) -> np.ndarray:
        """色彩校正"""
        # 简单的对比度和亮度调整
        alpha = 1.1  # 对比度
        beta = 10    # 亮度
        return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    
    def _sharpen_image(self, image: np.ndarray) -> np.ndarray:
        """图像锐化"""
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        return cv2.filter2D(image, -1, kernel)
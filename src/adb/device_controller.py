"""
Android设备控制器
Android Device Controller for ADB operations
"""

import subprocess
import time
import logging
import os
from typing import Optional, List, Tuple, Dict
from config.settings import Config

logger = logging.getLogger(__name__)


class AndroidController:
    """Android设备ADB控制器"""
    
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id or Config.DEVICE_ID
        self.adb_path = Config.ADB_PATH
        self.connected = False
        
    def _run_adb_command(self, command: List[str]) -> Tuple[bool, str]:
        """
        执行ADB命令
        
        Args:
            command: ADB命令列表
            
        Returns:
            (成功标志, 输出结果)
        """
        try:
            # 构建完整命令
            full_command = [self.adb_path]
            
            if self.device_id:
                full_command.extend(['-s', self.device_id])
                
            full_command.extend(command)
            
            logger.debug(f"执行ADB命令: {' '.join(full_command)}")
            
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                logger.error(f"ADB命令失败: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            logger.error("ADB命令超时")
            return False, "命令超时"
        except Exception as e:
            logger.error(f"ADB命令执行异常: {e}")
            return False, str(e)
    
    def connect_device(self) -> bool:
        """
        连接Android设备
        
        Returns:
            连接成功标志
        """
        try:
            # 检查ADB是否可用
            if not os.path.exists(self.adb_path):
                logger.error(f"ADB工具未找到: {self.adb_path}")
                return False
            
            # 启动ADB服务器
            success, _ = self._run_adb_command(['start-server'])
            if not success:
                logger.error("无法启动ADB服务器")
                return False
            
            # 获取设备列表
            success, output = self._run_adb_command(['devices'])
            if not success:
                logger.error("无法获取设备列表")
                return False
            
            # 解析设备列表
            devices = []
            for line in output.split('\n')[1:]:  # 跳过标题行
                if line.strip() and 'device' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
            
            if not devices:
                logger.error("未找到连接的Android设备")
                return False
            
            # 如果没有指定设备ID，使用第一个设备
            if not self.device_id:
                self.device_id = devices[0]
                logger.info(f"自动选择设备: {self.device_id}")
            
            # 检查设备是否在线
            if self.device_id not in devices:
                logger.error(f"指定设备未连接: {self.device_id}")
                return False
            
            # 测试设备连接
            success, _ = self._run_adb_command(['shell', 'echo', 'test'])
            if not success:
                logger.error("设备连接测试失败")
                return False
            
            self.connected = True
            logger.info(f"成功连接到设备: {self.device_id}")
            return True
            
        except Exception as e:
            logger.error(f"设备连接异常: {e}")
            return False
    
    def capture_screenshot(self, save_path: str) -> bool:
        """
        截取屏幕截图
        
        Args:
            save_path: 保存路径
            
        Returns:
            截图成功标志
        """
        if not self.connected:
            logger.error("设备未连接")
            return False
        
        try:
            # 在设备上截图
            device_screenshot_path = '/sdcard/screenshot.png'
            success, _ = self._run_adb_command([
                'shell', 'screencap', '-p', device_screenshot_path
            ])
            
            if not success:
                logger.error("设备截图失败")
                return False
            
            # 将截图拉取到本地
            success, _ = self._run_adb_command([
                'pull', device_screenshot_path, save_path
            ])
            
            if not success:
                logger.error("截图文件拉取失败")
                return False
            
            # 清理设备上的临时文件
            self._run_adb_command([
                'shell', 'rm', device_screenshot_path
            ])
            
            logger.debug(f"截图保存至: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"截图异常: {e}")
            return False
    
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, 
              duration: int = 500) -> bool:
        """
        滑动屏幕
        
        Args:
            start_x: 起始X坐标
            start_y: 起始Y坐标
            end_x: 结束X坐标
            end_y: 结束Y坐标
            duration: 滑动持续时间（毫秒）
            
        Returns:
            滑动成功标志
        """
        if not self.connected:
            logger.error("设备未连接")
            return False
        
        try:
            success, _ = self._run_adb_command([
                'shell', 'input', 'swipe',
                str(start_x), str(start_y), str(end_x), str(end_y), str(duration)
            ])
            
            if success:
                logger.debug(f"滑动: ({start_x},{start_y}) -> ({end_x},{end_y})")
                # 滑动后稍等片刻，让动画完成
                time.sleep(duration / 1000 + 0.5)
                return True
            else:
                logger.error("滑动操作失败")
                return False
                
        except Exception as e:
            logger.error(f"滑动操作异常: {e}")
            return False
    
    def tap(self, x: int, y: int) -> bool:
        """
        点击屏幕
        
        Args:
            x: X坐标
            y: Y坐标
            
        Returns:
            点击成功标志
        """
        if not self.connected:
            logger.error("设备未连接")
            return False
        
        try:
            success, _ = self._run_adb_command([
                'shell', 'input', 'tap', str(x), str(y)
            ])
            
            if success:
                logger.debug(f"点击: ({x},{y})")
                time.sleep(0.2)  # 短暂等待
                return True
            else:
                logger.error("点击操作失败")
                return False
                
        except Exception as e:
            logger.error(f"点击操作异常: {e}")
            return False
    
    def get_gps_location(self) -> Optional[Dict[str, float]]:
        """
        获取设备GPS位置
        
        Returns:
            GPS坐标字典 {'latitude': float, 'longitude': float} 或 None
        """
        if not self.connected:
            logger.error("设备未连接")
            return None
        
        try:
            # 尝试通过dumpsys获取位置信息
            success, output = self._run_adb_command([
                'shell', 'dumpsys', 'location'
            ])
            
            if not success:
                logger.error("无法获取位置信息")
                return None
            
            # 解析位置信息
            # 这是一个简化的解析，实际可能需要根据具体输出格式调整
            import re
            
            # 寻找GPS坐标模式
            lat_match = re.search(r'latitude[:\s=]+([+-]?\d+\.?\d*)', output, re.IGNORECASE)
            lng_match = re.search(r'longitude[:\s=]+([+-]?\d+\.?\d*)', output, re.IGNORECASE)
            
            if lat_match and lng_match:
                latitude = float(lat_match.group(1))
                longitude = float(lng_match.group(1))
                
                # 验证坐标是否合理（拉萨范围内）
                if (Config.LHASA_BOUNDS['south'] <= latitude <= Config.LHASA_BOUNDS['north'] and
                    Config.LHASA_BOUNDS['west'] <= longitude <= Config.LHASA_BOUNDS['east']):
                    
                    logger.debug(f"GPS位置: {latitude}, {longitude}")
                    return {
                        'latitude': latitude,
                        'longitude': longitude
                    }
                else:
                    logger.warning(f"GPS坐标超出拉萨范围: {latitude}, {longitude}")
            
            # 如果无法通过dumpsys获取，尝试其他方法
            # 这里可以添加其他获取GPS的方法
            logger.warning("无法解析GPS位置信息")
            return None
            
        except Exception as e:
            logger.error(f"GPS位置获取异常: {e}")
            return None
    
    def get_screen_size(self) -> Optional[Tuple[int, int]]:
        """
        获取屏幕尺寸
        
        Returns:
            (宽度, 高度) 或 None
        """
        if not self.connected:
            logger.error("设备未连接")
            return None
        
        try:
            success, output = self._run_adb_command([
                'shell', 'wm', 'size'
            ])
            
            if success and 'Physical size:' in output:
                # 解析输出，例如："Physical size: 1080x2340"
                import re
                match = re.search(r'(\d+)x(\d+)', output)
                if match:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    logger.debug(f"屏幕尺寸: {width}x{height}")
                    return width, height
            
            logger.error("无法获取屏幕尺寸")
            return None
            
        except Exception as e:
            logger.error(f"屏幕尺寸获取异常: {e}")
            return None
    
    def wait_for_device(self, timeout: int = 30) -> bool:
        """
        等待设备连接
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            连接成功标志
        """
        try:
            success, _ = self._run_adb_command(['wait-for-device'])
            return success
            
        except Exception as e:
            logger.error(f"等待设备连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开设备连接"""
        self.connected = False
        logger.info("设备连接已断开")
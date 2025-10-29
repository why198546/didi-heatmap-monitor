"""
滴滴热力图监控和预测系统主入口
DiDi Heatmap Monitoring and Prediction System Main Entry
"""

import os
import sys
import time
import logging
from typing import Optional
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.adb.device_controller import AndroidController
from src.image.screenshot_manager import ScreenshotManager
from src.image.map_stitcher import MapStitcher
from src.image.hexagon_detector import HexagonDetector
from src.gps.location_manager import LocationManager
from src.database.data_manager import DataManager
from src.ml.predictor import HeatmapPredictor
from src.web.dashboard import WebDashboard
from config.settings import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/didi_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class DiDiHeatmapMonitor:
    """滴滴热力图监控主类"""
    
    def __init__(self):
        self.config = Config()
        self.android_controller = AndroidController()
        self.screenshot_manager = ScreenshotManager()
        self.map_stitcher = MapStitcher()
        self.hexagon_detector = HexagonDetector()
        self.location_manager = LocationManager()
        self.data_manager = DataManager()
        self.predictor = HeatmapPredictor()
        self.web_dashboard = WebDashboard()
        
    def initialize(self) -> bool:
        """初始化系统"""
        try:
            logger.info("初始化滴滴热力图监控系统...")
            
            # 检查ADB连接
            if not self.android_controller.connect_device():
                logger.error("无法连接到Android设备")
                return False
                
            # 初始化数据库
            self.data_manager.initialize_database()
            
            # 创建必要的目录
            os.makedirs('data/screenshots', exist_ok=True)
            os.makedirs('data/stitched_maps', exist_ok=True)
            os.makedirs('data/logs', exist_ok=True)
            
            logger.info("系统初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
            return False
    
    def capture_and_analyze(self) -> Optional[dict]:
        """捕获并分析热力图数据"""
        try:
            timestamp = datetime.now()
            logger.info(f"开始捕获热力图数据: {timestamp}")
            
            # 1. 获取当前GPS位置
            current_location = self.location_manager.get_current_location()
            if not current_location:
                logger.error("无法获取GPS位置")
                return None
            
            # 2. 截屏拉萨主城区
            screenshots = self.screenshot_manager.capture_lhasa_area(
                current_location, 
                self.android_controller
            )
            
            if not screenshots:
                logger.error("截屏失败")
                return None
            
            # 3. 拼接地图
            stitched_map = self.map_stitcher.stitch_screenshots(screenshots)
            if stitched_map is None:
                logger.error("地图拼接失败")
                return None
                
            # 4. 检测橙色六边形
            hexagons = self.hexagon_detector.detect_hexagons(stitched_map)
            
            # 5. 保存数据
            data_record = {
                'timestamp': timestamp,
                'location': current_location,
                'hexagons': hexagons,
                'map_image_path': f"data/stitched_maps/{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            }
            
            # 保存拼接的地图
            self.map_stitcher.save_stitched_map(stitched_map, data_record['map_image_path'])
            
            # 保存到数据库
            self.data_manager.save_heatmap_data(data_record)
            
            logger.info(f"数据捕获完成，检测到 {len(hexagons)} 个热点区域")
            return data_record
            
        except Exception as e:
            logger.error(f"数据捕获和分析失败: {e}")
            return None
    
    def run_continuous_monitoring(self, interval_minutes: int = 5):
        """持续监控模式"""
        logger.info(f"启动持续监控模式，间隔 {interval_minutes} 分钟")
        
        while True:
            try:
                # 捕获和分析数据
                result = self.capture_and_analyze()
                
                if result:
                    # 更新预测模型（如果有足够的历史数据）
                    self.predictor.update_model()
                    
                    # 更新Web仪表板数据
                    self.web_dashboard.update_data(result)
                
                # 等待下一次捕获
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("收到停止信号，退出监控")
                break
            except Exception as e:
                logger.error(f"监控过程中出现错误: {e}")
                time.sleep(60)  # 出错后等待1分钟再重试
    
    def start_web_dashboard(self):
        """启动Web仪表板"""
        logger.info("启动Web仪表板...")
        self.web_dashboard.run()


def main():
    """主函数"""
    monitor = DiDiHeatmapMonitor()
    
    if not monitor.initialize():
        logger.error("系统初始化失败，退出程序")
        sys.exit(1)
    
    import argparse
    parser = argparse.ArgumentParser(description='滴滴热力图监控系统')
    parser.add_argument('--mode', choices=['monitor', 'web', 'once'], 
                       default='monitor', help='运行模式')
    parser.add_argument('--interval', type=int, default=5, 
                       help='监控间隔(分钟)')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'once':
            # 单次运行
            result = monitor.capture_and_analyze()
            if result:
                print(f"捕获成功，检测到 {len(result['hexagons'])} 个热点区域")
            else:
                print("捕获失败")
                
        elif args.mode == 'web':
            # 仅启动Web仪表板
            monitor.start_web_dashboard()
            
        else:
            # 持续监控模式（默认）
            monitor.run_continuous_monitoring(args.interval)
            
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
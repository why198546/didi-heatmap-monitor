"""
Web仪表板
Web Dashboard for displaying heatmap data and predictions
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    from flask import Flask, render_template, jsonify, request, send_from_directory
    from flask_cors import CORS
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Flask not available, web dashboard will be disabled")
    Flask = None

from config.settings import Config
from src.database.data_manager import DataManager
from src.ml.predictor import HeatmapPredictor

logger = logging.getLogger(__name__)


class WebDashboard:
    """Web仪表板"""
    
    def __init__(self):
        self.config = Config()
        self.data_manager = DataManager()
        self.predictor = HeatmapPredictor()
        self.app = None
        self.latest_data = None
        
        if Flask:
            self._initialize_flask_app()
    
    def _initialize_flask_app(self):
        """初始化Flask应用"""
        try:
            self.app = Flask(__name__, 
                           template_folder='../../web/templates',
                           static_folder='../../web/static')
            
            # 启用CORS以支持跨域请求
            CORS(self.app)
            
            # 注册路由
            self._register_routes()
            
            logger.info("Flask应用初始化完成")
            
        except Exception as e:
            logger.error(f"Flask应用初始化异常: {e}")
    
    def _register_routes(self):
        """注册路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            return render_template('index.html')
        
        @self.app.route('/api/current-data')
        def get_current_data():
            """获取当前热力图数据"""
            try:
                # 获取最近1小时的数据
                recent_data = self.data_manager.get_recent_heatmap_data(hours=1)
                
                if recent_data:
                    latest = recent_data[0]
                    return jsonify({
                        'success': True,
                        'data': {
                            'timestamp': latest['timestamp'],
                            'location': {
                                'latitude': latest['latitude'],
                                'longitude': latest['longitude']
                            },
                            'hexagon_count': latest['hexagon_count'],
                            'hexagons': json.loads(latest['hexagons_data']) if latest['hexagons_data'] else []
                        }
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': '没有找到最新数据'
                    })
                    
            except Exception as e:
                logger.error(f"获取当前数据异常: {e}")
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/api/predictions')
        def get_predictions():
            """获取预测数据"""
            try:
                # 获取查询参数
                hours = request.args.get('hours', 2, type=int)
                
                if self.latest_data:
                    current_location = self.latest_data['location']
                else:
                    # 使用默认的拉萨中心位置
                    current_location = {
                        'latitude': 29.6516,
                        'longitude': 91.1175
                    }
                
                # 生成未来几个时间点的预测
                base_time = datetime.now()
                intervals = [30, 60, 90, 120]  # 30分钟、1小时、1.5小时、2小时
                
                predictions = self.predictor.predict_multiple_times(
                    base_time, intervals, current_location
                )
                
                return jsonify({
                    'success': True,
                    'predictions': predictions
                })
                
            except Exception as e:
                logger.error(f"获取预测数据异常: {e}")
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/api/statistics')
        def get_statistics():
            """获取统计数据"""
            try:
                # 获取查询参数
                days = request.args.get('days', 7, type=int)
                
                end_time = datetime.now()
                start_time = end_time - timedelta(days=days)
                
                stats = self.data_manager.get_hexagon_statistics(start_time, end_time)
                
                return jsonify({
                    'success': True,
                    'statistics': stats
                })
                
            except Exception as e:
                logger.error(f"获取统计数据异常: {e}")
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/api/historical-data')
        def get_historical_data():
            """获取历史数据"""
            try:
                # 获取查询参数
                hours = request.args.get('hours', 24, type=int)
                
                historical_data = self.data_manager.get_recent_heatmap_data(hours=hours)
                
                # 格式化数据
                formatted_data = []
                for record in historical_data:
                    formatted_data.append({
                        'timestamp': record['timestamp'],
                        'hexagon_count': record['hexagon_count'],
                        'location': {
                            'latitude': record['latitude'],
                            'longitude': record['longitude']
                        }
                    })
                
                return jsonify({
                    'success': True,
                    'data': formatted_data
                })
                
            except Exception as e:
                logger.error(f"获取历史数据异常: {e}")
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/api/heatmap-zones')
        def get_heatmap_zones():
            """获取热力图区域数据"""
            try:
                # 获取最新的热力图数据
                recent_data = self.data_manager.get_recent_heatmap_data(hours=1)
                
                if not recent_data:
                    return jsonify({
                        'success': False,
                        'message': '没有最新的热力图数据'
                    })
                
                latest = recent_data[0]
                hexagons = json.loads(latest['hexagons_data']) if latest['hexagons_data'] else []
                
                # 格式化为地图可用的数据
                zones = []
                for hexagon in hexagons:
                    geo_center = hexagon.get('geo_center', {})
                    geo_bounds = hexagon.get('geo_bounds', {})
                    
                    if geo_center:
                        zones.append({
                            'center': geo_center,
                            'bounds': geo_bounds,
                            'intensity': hexagon.get('confidence', 0.5),
                            'area': hexagon.get('geo_area_m2', 0),
                            'color_type': hexagon.get('color_type', 'unknown')
                        })
                
                return jsonify({
                    'success': True,
                    'zones': zones,
                    'timestamp': latest['timestamp']
                })
                
            except Exception as e:
                logger.error(f"获取热力图区域异常: {e}")
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/api/system-status')
        def get_system_status():
            """获取系统状态"""
            try:
                # 检查数据库连接
                recent_data = self.data_manager.get_recent_heatmap_data(hours=1)
                db_status = 'connected' if recent_data is not None else 'error'
                
                # 检查模型状态
                model_status = 'trained' if self.predictor.is_trained else 'not_trained'
                
                # 获取数据统计
                total_records = len(self.data_manager.get_recent_heatmap_data(hours=24 * 7))
                
                return jsonify({
                    'success': True,
                    'status': {
                        'database': db_status,
                        'model': model_status,
                        'total_records_week': total_records,
                        'last_update': recent_data[0]['timestamp'] if recent_data else None
                    }
                })
                
            except Exception as e:
                logger.error(f"获取系统状态异常: {e}")
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/static/<path:filename>')
        def serve_static(filename):
            """服务静态文件"""
            return send_from_directory('web/static', filename)
    
    def update_data(self, new_data: Dict):
        """更新最新数据"""
        self.latest_data = new_data
        logger.debug("仪表板数据已更新")
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None, 
            debug: Optional[bool] = None):
        """启动Web服务器"""
        try:
            if not self.app:
                logger.error("Flask应用未初始化")
                return
            
            config = self.config.WEB_CONFIG
            
            host = host or config['host']
            port = port or config['port']
            debug = debug if debug is not None else config['debug']
            
            logger.info(f"启动Web仪表板: http://{host}:{port}")
            
            self.app.run(
                host=host,
                port=port,
                debug=debug,
                threaded=True
            )
            
        except Exception as e:
            logger.error(f"Web服务器启动异常: {e}")
    
    def generate_dashboard_data(self) -> Dict:
        """生成仪表板数据"""
        try:
            # 获取最新数据
            current_data = self.data_manager.get_recent_heatmap_data(hours=1)
            
            # 获取历史趋势
            historical_data = self.data_manager.get_recent_heatmap_data(hours=24)
            
            # 获取统计信息
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            statistics = self.data_manager.get_hexagon_statistics(start_time, end_time)
            
            # 获取预测数据
            predictions = []
            if current_data:
                latest_location = {
                    'latitude': current_data[0]['latitude'],
                    'longitude': current_data[0]['longitude']
                }
                
                base_time = datetime.now()
                intervals = [30, 60]  # 30分钟和1小时预测
                
                predictions = self.predictor.predict_multiple_times(
                    base_time, intervals, latest_location
                )
            
            return {
                'current': current_data[0] if current_data else None,
                'historical': historical_data,
                'statistics': statistics,
                'predictions': predictions,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"仪表板数据生成异常: {e}")
            return {}
    
    def export_data(self, format_type: str = 'json') -> Optional[str]:
        """
        导出数据
        
        Args:
            format_type: 导出格式 ('json', 'csv')
            
        Returns:
            导出文件路径 或 None
        """
        try:
            dashboard_data = self.generate_dashboard_data()
            
            if not dashboard_data:
                logger.error("没有数据可导出")
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format_type == 'json':
                export_path = f"data/exports/dashboard_data_{timestamp}.json"
                
                import os
                os.makedirs(os.path.dirname(export_path), exist_ok=True)
                
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"数据已导出为JSON: {export_path}")
                return export_path
                
            elif format_type == 'csv':
                # 这里可以实现CSV导出逻辑
                logger.warning("CSV导出功能待实现")
                return None
            
            else:
                logger.error(f"不支持的导出格式: {format_type}")
                return None
                
        except Exception as e:
            logger.error(f"数据导出异常: {e}")
            return None
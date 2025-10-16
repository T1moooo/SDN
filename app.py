"""
SDN QoS 策略管理系统 - Flask Web 应用
Flask Web Application for SDN QoS Policy Management
"""

from flask import Flask, request, jsonify, send_from_directory, render_template_string
from werkzeug.utils import secure_filename
import os
from pathlib import Path
from datetime import datetime
import traceback

from config import Config
from core.engine import PolicyEngine
from core.deployer import NXAPIClient
from core.models import PolicyStatus
from utils.logger import setup_logger, get_operation_logger

# 初始化应用
app = Flask(__name__)
app.config.from_object(Config)

# 初始化目录
Config.init_directories()

# 初始化日志
logger = setup_logger(
    name='sdn_qos',
    level=app.config['LOG_LEVEL'],
    log_dir=Config.LOGS_DIR,
    console=True
)
op_logger = get_operation_logger()

# 内存存储策略（生产环境应使用数据库）
policies_storage = {}


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """主页 - 策略列表"""
    return send_from_directory(str(Config.FRONTEND_DIR), 'index.html')


@app.route('/upload')
def upload_page():
    """上传页面"""
    return send_from_directory(str(Config.FRONTEND_DIR), 'upload.html')


@app.route('/logs')
def logs_page():
    """日志页面"""
    return send_from_directory(str(Config.FRONTEND_DIR), 'logs.html')

# 静态文件不在标准的 根目录 static 目录下
# @app.route('/static/<path:path>')
# def send_static(path):
#     """静态文件服务"""
#     return send_from_directory(str(Config.STATIC_DIR), path)


@app.route('/frontend/static/<path:path>')
def send_frontend_static(path):
    """前端静态文件服务"""
    return send_from_directory(str(Config.STATIC_DIR), path)


# ============= REST API 端点 =============

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置信息（脱敏）"""
    return jsonify({
        'switch_ip': Config.SWITCH_IP,
        'switch_port': Config.SWITCH_PORT,
        'dry_run_mode': Config.DRY_RUN,
        'environment': Config.FLASK_ENV
    })


@app.route('/api/policies', methods=['GET'])
def get_policies():
    """获取策略列表"""
    try:
        policies_list = []
        
        for policy_id, policy in policies_storage.items():
            policies_list.append(policy.to_dict())
        
        # 按创建时间倒序
        policies_list.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'count': len(policies_list),
            'policies': policies_list
        })
    
    except Exception as e:
        logger.error(f"Error getting policies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/policies/<policy_id>', methods=['GET'])
def get_policy(policy_id):
    """获取单个策略详情"""
    try:
        if policy_id not in policies_storage:
            return jsonify({
                'success': False,
                'error': 'Policy not found'
            }), 404
        
        policy = policies_storage[policy_id]
        
        return jsonify({
            'success': True,
            'policy': policy.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error getting policy {policy_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/policies', methods=['POST'])
def upload_policy():
    """上传策略文件"""
    try:
        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Empty filename'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Allowed: {Config.ALLOWED_EXTENSIONS}'
            }), 400
        
        # 保存文件
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        saved_filename = f"{timestamp}_{filename}"
        filepath = Config.POLICIES_UPLOADED_DIR / saved_filename
        
        file.save(str(filepath))
        logger.info(f"Policy file uploaded: {saved_filename}")
        
        # 解析策略
        engine = PolicyEngine()
        try:
            policy = engine.parse_yaml(str(filepath))
            
            # 验证策略
            is_valid, errors = engine.validate(policy)
            
            if not is_valid:
                error_messages = [str(e) for e in errors if e.severity == "error"]
                op_logger.log_upload(policy.id, saved_filename, False, 
                                    error="; ".join(error_messages))
                return jsonify({
                    'success': False,
                    'error': 'Policy validation failed',
                    'validation_errors': error_messages
                }), 400
            
            # 存储策略
            policy.status = PolicyStatus.VALIDATED
            policies_storage[policy.id] = policy
            
            # 记录日志
            op_logger.log_upload(policy.id, saved_filename, True)
            op_logger.log_validation(policy.id, True, 0)
            
            return jsonify({
                'success': True,
                'message': 'Policy uploaded and validated successfully',
                'policy_id': policy.id,
                'policy': policy.to_dict()
            })
        
        except Exception as e:
            logger.error(f"Error parsing policy: {e}")
            op_logger.log_upload('unknown', saved_filename, False, error=str(e))
            return jsonify({
                'success': False,
                'error': f'Failed to parse policy: {str(e)}'
            }), 400
    
    except Exception as e:
        logger.error(f"Error uploading policy: {e}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/policies/<policy_id>/preview', methods=['GET'])
def preview_policy(policy_id):
    """预览策略生成的命令"""
    try:
        if policy_id not in policies_storage:
            return jsonify({
                'success': False,
                'error': 'Policy not found'
            }), 404
        
        policy = policies_storage[policy_id]
        engine = PolicyEngine()
        
        # 生成命令
        commands = engine.generate_commands(policy)
        preview = engine.preview_commands(policy)
        
        return jsonify({
            'success': True,
            'policy_id': policy_id,
            'commands': commands,
            'preview': preview,
            'commands_count': len([c for c in commands if c.strip()])
        })
    
    except Exception as e:
        logger.error(f"Error previewing policy {policy_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/policies/<policy_id>/apply', methods=['POST'])
def apply_policy(policy_id):
    """应用策略到设备"""
    try:
        if policy_id not in policies_storage:
            return jsonify({
                'success': False,
                'error': 'Policy not found'
            }), 404
        
        policy = policies_storage[policy_id]
        
        # 获取参数
        data = request.get_json() or {}
        dry_run = data.get('dry_run', Config.DRY_RUN)
        
        # 生成命令
        engine = PolicyEngine()
        commands = engine.generate_commands(policy)
        
        # 连接设备
        switch_config = Config.get_switch_config()
        client = NXAPIClient(**switch_config)
        
        # 测试连接
        if not client.test_connection():
            error_msg = f"Failed to connect to switch {Config.SWITCH_IP}"
            logger.error(error_msg)
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
        # 执行命令
        result = client.execute_commands(commands, dry_run=dry_run)
        result.policy_id = policy_id
        
        # 更新策略状态
        if result.success and not dry_run:
            policy.status = PolicyStatus.APPLIED
            policy.updated_at = datetime.now()
        elif not result.success:
            policy.status = PolicyStatus.FAILED
        
        # 记录日志
        op_logger.log_apply(
            policy_id=policy_id,
            dry_run=dry_run,
            success=result.success,
            duration_ms=result.duration_ms,
            commands_count=len(commands),
            error=result.message if not result.success else None
        )
        
        return jsonify({
            'success': result.success,
            'message': result.message,
            'result': result.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error applying policy {policy_id}: {e}\n{traceback.format_exc()}")
        op_logger.log_error('apply', str(e), policy_id)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/policies/<policy_id>', methods=['DELETE'])
def delete_policy(policy_id):
    """删除策略"""
    try:
        if policy_id not in policies_storage:
            return jsonify({
                'success': False,
                'error': 'Policy not found'
            }), 404
        
        del policies_storage[policy_id]
        logger.info(f"Policy deleted: {policy_id}")
        
        return jsonify({
            'success': True,
            'message': f'Policy {policy_id} deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"Error deleting policy {policy_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志"""
    try:
        # 获取参数
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        lines = int(request.args.get('lines', 100))
        
        # 读取日志文件
        log_file = Config.LOGS_DIR / 'operations' / f'{date}.log'
        
        if not log_file.exists():
            return jsonify({
                'success': True,
                'logs': [],
                'message': f'No logs found for {date}'
            })
        
        # 读取最后 N 行
        with open(log_file, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
        
        # 取最后 N 行
        recent_logs = log_lines[-lines:] if len(log_lines) > lines else log_lines
        
        # 解析 JSON 日志
        parsed_logs = []
        for line in recent_logs:
            try:
                import json
                log_entry = json.loads(line.strip())
                parsed_logs.append(log_entry)
            except:
                # 非 JSON 格式的日志
                parsed_logs.append({'message': line.strip()})
        
        return jsonify({
            'success': True,
            'date': date,
            'count': len(parsed_logs),
            'logs': parsed_logs
        })
    
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/switch/test', methods=['GET'])
def test_switch_connection():
    """测试交换机连接"""
    try:
        switch_config = Config.get_switch_config()
        client = NXAPIClient(**switch_config)
        
        is_connected = client.test_connection()
        
        if is_connected:
            # 获取设备信息
            result = client.show_command("show version")
            
            return jsonify({
                'success': True,
                'connected': True,
                'message': 'Successfully connected to switch',
                'switch_ip': Config.SWITCH_IP
            })
        else:
            return jsonify({
                'success': False,
                'connected': False,
                'message': 'Failed to connect to switch',
                'switch_ip': Config.SWITCH_IP
            })
    
    except Exception as e:
        logger.error(f"Error testing switch connection: {e}")
        return jsonify({
            'success': False,
            'connected': False,
            'error': str(e)
        }), 500


# ============= 错误处理 =============

@app.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return jsonify({
        'success': False,
        'error': 'Resource not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


# ============= 应用启动 =============

if __name__ == '__main__':
    # 显示配置
    print(Config.display_config())
    
    # 验证配置
    is_valid, errors = Config.validate_config()
    if not is_valid:
        logger.warning("Configuration warnings:")
        for error in errors:
            logger.warning(f"  - {error}")
    
    # 启动应用
    logger.info(f"Starting Flask application on {Config.FLASK_HOST}:{Config.FLASK_PORT}")
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.DEBUG
    )

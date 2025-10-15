"""
日志模块 - 统一的日志记录
Logger - Unified logging system
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import json


class JSONFormatter(logging.Formatter):
    """JSON 格式日志器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志为 JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加额外字段
        if hasattr(record, 'policy_id'):
            log_data['policy_id'] = record.policy_id
        
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """彩色控制台日志格式器"""
    
    # ANSI 颜色码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化带颜色的日志"""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str = 'sdn_qos',
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
    console: bool = True,
    json_format: bool = False
) -> logging.Logger:
    """
    设置日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_dir: 日志目录（None 则不写文件）
        console: 是否输出到控制台
        json_format: 是否使用 JSON 格式
        
    Returns:
        配置好的 Logger 对象
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 清除已有的 handlers
    logger.handlers.clear()
    
    # 日志格式
    if json_format:
        formatter = JSONFormatter()
    else:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter(log_format, date_format)
    
    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        if not json_format and sys.stdout.isatty():
            # 终端支持颜色
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                '%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
        else:
            console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    
    # 文件处理器
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 应用日志
        app_log_file = log_dir / 'app.log'
        file_handler = logging.FileHandler(app_log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 操作日志（按日期分割）
        operations_dir = log_dir / 'operations'
        operations_dir.mkdir(exist_ok=True)
        
        today = datetime.now().strftime('%Y-%m-%d')
        operation_log_file = operations_dir / f'{today}.log'
        operation_handler = logging.FileHandler(operation_log_file, encoding='utf-8')
        operation_handler.setLevel(logging.INFO)
        
        # 操作日志使用 JSON 格式
        operation_handler.setFormatter(JSONFormatter())
        logger.addHandler(operation_handler)
    
    return logger


def get_logger(name: str = 'sdn_qos') -> logging.Logger:
    """
    获取已配置的日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        Logger 对象
    """
    return logging.getLogger(name)


class OperationLogger:
    """操作日志记录器（用于记录用户操作）"""
    
    def __init__(self, logger: logging.Logger):
        """
        初始化操作日志记录器
        
        Args:
            logger: 日志器实例
        """
        self.logger = logger
    
    def log_upload(self, policy_id: str, filename: str, success: bool, error: Optional[str] = None):
        """记录策略上传"""
        self.logger.info(
            f"Policy upload: {policy_id}",
            extra={
                'policy_id': policy_id,
                'filename': filename,
                'operation': 'upload',
                'success': success,
                'error': error
            }
        )
    
    def log_apply(self, policy_id: str, dry_run: bool, success: bool, 
                  duration_ms: int, commands_count: int, error: Optional[str] = None):
        """记录策略应用"""
        self.logger.info(
            f"Policy apply: {policy_id} ({'dry-run' if dry_run else 'execute'})",
            extra={
                'policy_id': policy_id,
                'operation': 'apply',
                'dry_run': dry_run,
                'success': success,
                'duration_ms': duration_ms,
                'commands_count': commands_count,
                'error': error
            }
        )
    
    def log_validation(self, policy_id: str, success: bool, errors_count: int):
        """记录策略验证"""
        self.logger.info(
            f"Policy validation: {policy_id}",
            extra={
                'policy_id': policy_id,
                'operation': 'validation',
                'success': success,
                'errors_count': errors_count
            }
        )
    
    def log_error(self, operation: str, error: str, policy_id: Optional[str] = None):
        """记录错误"""
        self.logger.error(
            f"Error in {operation}: {error}",
            extra={
                'policy_id': policy_id,
                'operation': operation,
                'error': error
            }
        )


def get_operation_logger() -> OperationLogger:
    """
    获取操作日志记录器
    
    Returns:
        OperationLogger 实例
    """
    logger = get_logger()
    return OperationLogger(logger)

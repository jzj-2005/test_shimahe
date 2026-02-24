"""
日志管理模块
使用loguru库提供统一的日志功能
"""

import sys
from loguru import logger
from typing import Optional


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
    format_string: Optional[str] = None
):
    """
    设置日志系统
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，如果为None则不保存到文件
        rotation: 日志文件轮转规则
        retention: 日志保留时间
        format_string: 自定义日志格式
    """
    # 移除默认的处理器
    logger.remove()
    
    # 设置默认格式
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    # 添加控制台输出
    logger.add(
        sys.stderr,
        format=format_string,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 如果指定了日志文件，添加文件输出
    if log_file:
        logger.add(
            log_file,
            format=format_string,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
            encoding="utf-8"
        )
    
    logger.info(f"日志系统初始化完成 - 级别: {log_level}")
    if log_file:
        logger.info(f"日志文件: {log_file}")
    
    return logger


def get_logger():
    """获取全局日志实例"""
    return logger

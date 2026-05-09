"""日志工具模块

提供统一的日志配置和管理功能
"""
import logging
import os
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: str = "DEBUG"
) -> logging.Logger:
    """配置日志记录器

    参数:
        name: 日志记录器名称
        log_file: 日志文件路径（可选）
        level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）

    返回:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取已配置的日志记录器

    参数:
        name: 日志记录器名称

    返回:
        Logger 实例
    """
    return logging.getLogger(name)
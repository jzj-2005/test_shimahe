"""
配置文件加载器
支持YAML格式配置文件的加载和解析
"""

import os
import yaml
from typing import Dict, Any


class ConfigLoader:
    """配置加载器类"""
    
    def __init__(self, config_dir: str = "./config"):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置文件目录路径
        """
        self.config_dir = config_dir
        self._configs = {}
    
    def load(self, config_name: str) -> Dict[str, Any]:
        """
        加载指定的配置文件
        
        Args:
            config_name: 配置文件名 (不含.yaml后缀)
            
        Returns:
            配置字典
        """
        # 如果已经加载过，直接返回缓存的配置
        if config_name in self._configs:
            return self._configs[config_name]
        
        # 构建配置文件路径
        config_path = os.path.join(self.config_dir, f"{config_name}.yaml")
        
        # 检查文件是否存在
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        # 加载YAML文件
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 缓存配置
            self._configs[config_name] = config
            
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件解析失败: {config_path}\n错误: {e}")
        except Exception as e:
            raise RuntimeError(f"加载配置文件时发生错误: {e}")
    
    def load_all(self, *config_names: str) -> Dict[str, Dict[str, Any]]:
        """
        一次加载多个配置文件
        
        Args:
            *config_names: 配置文件名列表
            
        Returns:
            配置字典的字典 {config_name: config_dict}
        """
        configs = {}
        for name in config_names:
            configs[name] = self.load(name)
        return configs
    
    def get(self, config_name: str, key_path: str, default: Any = None) -> Any:
        """
        获取配置中的某个值 (支持嵌套路径)
        
        Args:
            config_name: 配置文件名
            key_path: 键路径，使用.分隔，例如 "input.video_path"
            default: 默认值
            
        Returns:
            配置值
            
        Example:
            >>> loader = ConfigLoader()
            >>> video_path = loader.get('offline_config', 'input.video_path')
        """
        config = self.load(config_name)
        
        # 按照路径逐层获取值
        keys = key_path.split('.')
        value = config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def reload(self, config_name: str) -> Dict[str, Any]:
        """
        重新加载配置文件 (清除缓存并重新读取)
        
        Args:
            config_name: 配置文件名
            
        Returns:
            配置字典
        """
        # 清除缓存
        if config_name in self._configs:
            del self._configs[config_name]
        
        # 重新加载
        return self.load(config_name)
    
    def clear_cache(self):
        """清除所有配置缓存"""
        self._configs.clear()


def load_config(config_path: str) -> Dict[str, Any]:
    """
    快捷函数：直接加载配置文件
    
    Args:
        config_path: 配置文件完整路径
        
    Returns:
        配置字典
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

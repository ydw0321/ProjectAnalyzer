"""
树生成器配置模块
"""
import os


def _get_int_env(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def extract_layer(file_path: str) -> str:
    """从文件路径提取所属层级（兼容 Windows/Unix 路径），供外部模块复用"""
    from src.tree.config import TreeConfig
    path_lower = file_path.lower().replace("\\", "/")
    for base_layer in TreeConfig.BASE_LAYERS:
        if (
            f"/{base_layer}/" in path_lower
            or path_lower.endswith(f"/{base_layer}")
            or path_lower.endswith(f"/{base_layer}.java")
        ):
            return base_layer
    return "other"


class TreeConfig:
    # 基础层级关键词
    BASE_LAYERS = {
        'controller', 'action', 'service', 'facade', 'biz', 'bl',
        'dal', 'dao', 'model', 'entity', 'vo', 'dto',
        'util', 'utils', 'helper', 'common'
    }
    
    # 子包配置
    SUB_PACKAGE_ENABLED = True      # 是否展开子包
    MAX_SUB_PACKAGE_DEPTH = _get_int_env('MAX_SUB_PACKAGE_DEPTH', 3)
    
    # 树节点配置
    MAX_TREE_DEPTH = _get_int_env('MAX_TREE_DEPTH', 10)
    MAX_NODE_COUNT = _get_int_env('MAX_NODE_COUNT', 1000)
    
    # 查询配置
    QUERY_TIMEOUT = _get_int_env('QUERY_TIMEOUT', 30)
    MAX_CALL_DEPTH = _get_int_env('MAX_CALL_DEPTH', 10)
    HARD_MAX_CALL_DEPTH = _get_int_env('HARD_MAX_CALL_DEPTH', 20)
    MAX_QUERY_RESULTS = _get_int_env('MAX_QUERY_RESULTS', 1000)
    MAX_METHOD_FANOUT = _get_int_env('MAX_METHOD_FANOUT', 100)
    
    # 导出配置
    DEFAULT_OUTPUT_FORMAT = 'json'  # 默认输出格式
    
    @classmethod
    def is_base_layer(cls, name: str) -> bool:
        """判断是否为基础层"""
        return name.lower() in cls.BASE_LAYERS
    
    @classmethod
    def get_layer_priority(cls, layer: str) -> int:
        """获取层级优先级（数字越小越上层）"""
        priority_map = {
            'controller': 1,
            'action': 1,
            'facade': 2,
            'service': 3,
            'biz': 4,
            'bl': 5,
            'dal': 6,
            'dao': 7,
            'model': 8,
            'entity': 9,
            'vo': 10,
            'dto': 11,
            'util': 12,
            'utils': 13,
            'helper': 14,
            'common': 15,
        }
        return priority_map.get(layer.lower(), 99)

"""
树生成器配置模块
"""

class TreeConfig:
    # 基础层级关键词
    BASE_LAYERS = {
        'controller', 'action', 'service', 'facade', 'biz', 'bl',
        'dal', 'dao', 'model', 'entity', 'vo', 'dto',
        'util', 'utils', 'helper', 'common'
    }
    
    # 子包配置
    SUB_PACKAGE_ENABLED = True      # 是否展开子包
    MAX_SUB_PACKAGE_DEPTH = 3       # 子包最大深度
    
    # 树节点配置
    MAX_TREE_DEPTH = 10             # 最大树深度
    MAX_NODE_COUNT = 1000          # 最大节点数
    
    # 查询配置
    QUERY_TIMEOUT = 30              # 查询超时时间(秒)
    MAX_CALL_DEPTH = 10             # 调用链最大深度
    
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

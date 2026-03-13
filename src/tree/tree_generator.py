"""
架构树生成器 - 基于图数据生成多层级应用架构树
"""
import os
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

from src.tree.config import TreeConfig
from src.tree.query_service import GraphQueryService


logger = logging.getLogger(__name__)


class ArchitectureTreeGenerator:
    """架构树生成器"""
    
    def __init__(self, query_service: GraphQueryService = None):
        self.query_service = query_service or GraphQueryService()
        self.expand_subpackages = TreeConfig.SUB_PACKAGE_ENABLED
        self._cache: Dict = {}  # 同一实例内缓存重复查询
        self._call_tree_node_budget = TreeConfig.MAX_NODE_COUNT
        self._call_tree_nodes = 0
    
    def close(self):
        if self.query_service:
            self.query_service.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def _get_all_methods(self) -> List[Dict]:
        """获取全部方法（带缓存，避免同一实例重复查询）"""
        if 'all_methods' not in self._cache:
            self._cache['all_methods'] = self.query_service.get_all_methods()
        return self._cache['all_methods']

    def _get_all_classes(self) -> List[Dict]:
        """获取全部类（带缓存）"""
        if 'all_classes' not in self._cache:
            self._cache['all_classes'] = self.query_service.get_all_classes()
        return self._cache['all_classes']

    # ==================== 树生成接口 ====================
    
    def generate_layer_tree(self, project_name: str = "Project") -> Dict:
        """生成按层级（Controller/Service/Facade/Biz/DAL）组织的树"""
        print("📊 生成层级架构树...")
        
        # 获取层级统计
        layer_stats = self.query_service.get_layer_statistics()
        
        # 获取所有方法（带缓存）
        all_methods = self._get_all_methods()
        
        # 构建树结构
        tree = {
            'project': project_name,
            'type': 'layer_tree',
            'layers': []
        }
        
        # 按优先级排序层级
        layer_stats.sort(key=lambda x: TreeConfig.get_layer_priority(x['layer']))
        
        for layer_info in layer_stats:
            layer = layer_info['layer']
            if layer == 'other':
                continue
            
            layer_node = {
                'name': layer,
                'type': 'layer',
                'classes': []
            }
            
            # 获取该层级下每个类的方法（从缓存的全量方法中过滤，不再额外查询 DB）
            for class_name in layer_info['classes']:
                methods = [m['method_name'] for m in all_methods
                          if m.get('class_name') == class_name]

                layer_node['classes'].append({
                    'name': class_name,
                    'type': 'class',
                    'method_count': len(methods),
                    'methods': methods
                })
            
            tree['layers'].append(layer_node)
        
        print(f"✅ 生成完成: {len(tree['layers'])} 个层级")
        return tree
    
    def generate_package_tree(self, project_name: str = "Project") -> Dict:
        """生成按包目录组织的树（支持子包展开）"""
        print("📊 生成包结构树...")
        
        all_classes = self._get_all_classes()
        all_methods = self._get_all_methods()
        
        # 构建路径到节点的映射
        tree = {
            'project': project_name,
            'type': 'package_tree',
            'root': self._build_tree_from_paths(all_classes, all_methods)
        }
        
        print("✅ 包结构树生成完成")
        return tree
    
    def _build_tree_from_paths(self, classes: List[Dict], methods: List[Dict]) -> Dict:
        """从类路径构建树结构"""
        root = {'name': 'root', 'type': 'root', 'children': {}}
        
        for cls in classes:
            class_name = cls['class_name']
            file_path = cls['file_path']
            
            # 解析路径
            path_parts = self._parse_file_path(file_path)
            
            # 插入到树中
            current = root
            for i, part in enumerate(path_parts):
                if part not in current['children']:
                    is_class = (i == len(path_parts) - 1)
                    current['children'][part] = {
                        'name': part,
                        'type': 'class' if is_class else 'package',
                        'children': {} if not is_class else None,
                        'file_path': file_path if is_class else None
                    }
                
                if i == len(path_parts) - 1:
                    # 叶子节点，添加方法
                    method_list = [m['method_name'] for m in methods 
                                   if m.get('class_name') == class_name]
                    current['children'][part]['methods'] = method_list
                    current['children'][part]['method_count'] = len(method_list)
                
                current = current['children'][part]
        
        return root
    
    def _parse_file_path(self, file_path: str) -> List[str]:
        """解析文件路径为层级列表"""
        # 移除文件扩展名
        if file_path.endswith('.java'):
            file_path = file_path[:-5]
        
        parts = file_path.replace('\\', '/').split('/')
        
        # 过滤并分类
        layers = []
        sub_packages = []
        
        for part in parts:
            if not part or part in ['src', 'main', 'java']:
                continue
            
            if TreeConfig.is_base_layer(part):
                layers.append(part)
                sub_packages.clear()  # 新的基础层，重置子包
            elif self.expand_subpackages:
                sub_packages.append(part)
            # else: 紧凑模式，跳过中间目录
        
        return layers + sub_packages
    
    def generate_call_chain_tree(self, entry_method: str = None, class_name: str = None,
                                  max_depth: int = None, max_entries: int = 1) -> Dict:
        """从入口方法向下游生成完整调用链树
        
        Args:
            entry_method: 指定入口方法名；为 None 时自动从 controller/action 层选取
            class_name: 指定入口方法所在类
            max_depth: 最大调用深度
            max_entries: 无指定入口时，最多生成几个入口的调用链（默认 1）
        """
        print(f"📊 生成调用链树 (入口: {entry_method})...")
        
        max_depth = max_depth or TreeConfig.MAX_CALL_DEPTH
        self._call_tree_nodes = 0
        
        # 如果没有指定入口方法，使用所有 Controller/Action 方法
        if not entry_method:
            entry_methods = self.query_service.get_entry_methods()
            if not entry_methods:
                print("⚠️ 未找到入口方法（Controller/Action层方法）")
                return {'error': 'No entry methods found'}
            
            # 支持多入口
            selected = entry_methods[:max_entries]
            if len(selected) == 1:
                entry_method = selected[0]['method_name']
                class_name = selected[0].get('class_name')
                print(f"🔗 使用入口方法: {class_name}.{entry_method}")
                chain_tree = {
                    'entry': f"{class_name}.{entry_method}" if class_name else entry_method,
                    'type': 'call_chain',
                    'max_depth': max_depth,
                    'tree': self._build_call_tree(entry_method, class_name, 0, max_depth, set())
                }
            else:
                # 多入口返回列表
                chains = []
                for em in selected:
                    em_name = em['method_name']
                    em_class = em.get('class_name')
                    print(f"🔗 使用入口方法: {em_class}.{em_name}")
                    chains.append({
                        'entry': f"{em_class}.{em_name}" if em_class else em_name,
                        'type': 'call_chain',
                        'max_depth': max_depth,
                        'tree': self._build_call_tree(em_name, em_class, 0, max_depth, set())
                    })
                print("✅ 调用链树生成完成")
                return {'type': 'multi_call_chain', 'chains': chains}
        else:
            chain_tree = {
                'entry': f"{class_name}.{entry_method}" if class_name else entry_method,
                'type': 'call_chain',
                'max_depth': max_depth,
                'tree': self._build_call_tree(entry_method, class_name, 0, max_depth, set())
            }
        
        print("✅ 调用链树生成完成")
        return chain_tree
    
    def _build_call_tree(self, method_name: str, class_name: str, depth: int,
                        max_depth: int, path_nodes: set) -> Dict:
        """递归构建调用树"""
        if depth >= max_depth:
            return {
                'name': method_name,
                'class': class_name,
                'type': 'method',
                'truncated': True,
                'truncate_reason': 'max_depth',
            }

        node_key = (class_name or '', method_name)
        if node_key in path_nodes:
            return {
                'name': method_name,
                'class': class_name,
                'type': 'method',
                'truncated': True,
                'truncate_reason': 'cycle',
            }

        if self._call_tree_nodes >= self._call_tree_node_budget:
            logger.warning("调用链树达到节点上限，提前截断: limit=%s", self._call_tree_node_budget)
            return {
                'name': method_name,
                'class': class_name,
                'type': 'method',
                'truncated': True,
                'truncate_reason': 'max_nodes',
            }

        self._call_tree_nodes += 1
        
        node = {
            'name': method_name,
            'class': class_name,
            'type': 'method',
            'depth': depth,
            'calls': []
        }
        
        # 获取下游调用
        downstream = self.query_service.get_method_calls(
            method_name,
            class_name,
            limit=TreeConfig.MAX_METHOD_FANOUT,
        )
        
        for call in downstream:
            child = self._build_call_tree(
                call['callee_name'], 
                call['callee_class'], 
                depth + 1, 
                max_depth,
                path_nodes | {node_key},
            )
            child['call_type'] = call['call_type']
            node['calls'].append(child)
        
        return node
    
    # ==================== 汇总信息 ====================
    
    def get_tree_summary(self, level: int = None) -> str:
        """获取指定层级的汇总信息"""
        layer_stats = self.query_service.get_layer_statistics()
        call_stats = self.query_service.get_call_statistics()
        
        if level is not None:
            # 特定层级汇总
            layer_info = next((l for l in layer_stats if l['layer'] == level), None)
            if not layer_info:
                return f"未找到层级: {level}"
            
            return f"""
层级 {level} 汇总:
- 类数量: {layer_info['class_count']}
- 类列表: {', '.join(layer_info['classes'][:10])}{'...' if len(layer_info['classes']) > 10 else ''}
"""
        
        # 全局汇总
        total_classes = sum(l['class_count'] for l in layer_stats)
        return f"""
项目架构汇总:
- 总类数: {total_classes}
- 层级数: {len(layer_stats)}
- 调用关系: {call_stats['total']} (内部: {call_stats['internal']}, 外部: {call_stats['external']})
"""
    
    # ==================== 导出接口 ====================
    
    def export_tree_json(self, tree: Dict, output_path: str):
        """导出树结构为 JSON 文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 已导出: {output_path}")
    
    def export_mermaid(self, tree: Dict, output_path: str = None) -> str:
        """导出为 Mermaid 格式"""
        lines = ["```mermaid", "graph TD"]
        
        if tree.get('type') == 'layer_tree':
            lines.extend(self._export_mermaid_layer_tree(tree))
        elif tree.get('type') == 'call_chain':
            lines.extend(self._export_mermaid_call_chain(tree))
        
        lines.append("```")
        
        mermaid_code = '\n'.join(lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(mermaid_code)
            print(f"✅ Mermaid 已导出: {output_path}")
        
        return mermaid_code
    
    def _export_mermaid_layer_tree(self, tree: Dict) -> List[str]:
        """导出层级树的 Mermaid 代码（每层一个 subgraph，类节点包含在对应 subgraph 内）"""
        lines = []

        # 先按 layer 分组收集所有类节点定义
        for layer in tree.get('layers', []):
            layer_name = layer['name']
            classes = layer.get('classes', [])
            if not classes:
                continue

            lines.append(f'    subgraph {layer_name}')
            for cls in classes:
                class_name = cls['name']
                method_count = cls.get('method_count', 0)
                methods_preview = ', '.join(cls.get('methods', [])[:3])
                if method_count > 3:
                    methods_preview += '...'
                lines.append(f'        {class_name}["{class_name}<br/>({method_count} methods)"]')
            lines.append('    end')
            lines.append('')

        # 跨层调用关系：相邻层之间第一个类做示例连线
        layers = tree.get('layers', [])
        for i in range(len(layers) - 1):
            curr_classes = layers[i].get('classes', [])
            next_classes = layers[i + 1].get('classes', [])
            if curr_classes and next_classes:
                lines.append(f'    {curr_classes[0]["name"]} -->|calls| {next_classes[0]["name"]}')

        return lines
    
    def _export_mermaid_call_chain(self, tree: Dict) -> List[str]:
        """导出调用链的 Mermaid 代码"""
        lines = []
        
        def add_nodes(node: Dict, parent_id: str = None):
            node_id = f"{node.get('class', '')}_{node['name']}".replace('.', '_')
            
            # 节点定义
            call_type = node.get('call_type', '')
            style = ""
            if call_type == 'external':
                style = ":::external"
            elif call_type == 'external_unknown':
                style = ":::unknown"
            
            lines.append(f'    {node_id}["{node["name"]}"] {style}')
            
            # 边定义
            if parent_id:
                lines.append(f'    {parent_id} --> {node_id}')
            
            # 递归子节点
            for child in node.get('calls', []):
                add_nodes(child, node_id)
        
        if 'tree' in tree:
            add_nodes(tree['tree'])
        
        # 添加样式
        lines.append("")
        lines.append("    classDef external fill:#f9f,stroke:#333")
        lines.append("    classDef unknown fill:#fcc,stroke:#f00")
        
        return lines
    
    def export_plantuml(self, tree: Dict, output_path: str = None) -> str:
        """导出为 PlantUML 格式"""
        lines = ["@startuml", ""]
        
        if tree.get('type') == 'layer_tree':
            lines.extend(self._export_plantuml_layer_tree(tree))
        elif tree.get('type') == 'call_chain':
            lines.extend(self._export_plantuml_call_chain(tree))
        elif tree.get('type') == 'package_tree':
            lines.extend(self._export_plantuml_package_tree(tree))
        
        lines.append("@enduml")
        
        plantuml_code = '\n'.join(lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(plantuml_code)
            print(f"✅ PlantUML 已导出: {output_path}")
        
        return plantuml_code
    
    def _export_plantuml_layer_tree(self, tree: Dict) -> List[str]:
        """导出层级树的 PlantUML 代码（同层所有类包含在同一个 package 内）"""
        lines = []
        lines.append("skinparam packageStyle rectangle")
        lines.append("")

        # 每个 layer 输出一个 package 块，其中包含该层所有类
        for layer in tree.get('layers', []):
            layer_name = layer['name']
            classes = layer.get('classes', [])
            if not classes:
                continue

            lines.append(f'package "{layer_name}" {{')
            for cls in classes:
                class_name = cls['name']
                method_count = cls.get('method_count', 0)
                lines.append(f'  class {class_name} {{')
                lines.append(f'    + {method_count} methods')
                lines.append(f'  }}')
            lines.append('}')
            lines.append('')

        # 添加跨层调用关系（使用合法的 class 节点 ID）
        layers = tree.get('layers', [])
        for i in range(len(layers) - 1):
            curr_classes = layers[i].get('classes', [])
            next_classes = layers[i + 1].get('classes', [])
            for src in curr_classes:
                for dst in next_classes:
                    lines.append(f'{src["name"]} --> {dst["name"]}')
            if curr_classes and next_classes:
                lines.append('')

        return lines
    
    def _export_plantuml_call_chain(self, tree: Dict) -> List[str]:
        """导出调用链的 PlantUML 代码"""
        lines = []
        
        def add_nodes(node: Dict):
            class_name = node.get('class', '')
            method_name = node['name']
            node_name = f"{class_name}_{method_name}" if class_name else method_name
            
            # 节点定义
            call_type = node.get('call_type', '')
            if call_type == 'external':
                lines.append(f'class "{method_name}" as {node_name} #pink')
            elif call_type == 'external_unknown':
                lines.append(f'class "{method_name}" as {node_name} #red')
            else:
                lines.append(f'class "{method_name}" as {node_name}')
            
            # 递归子节点
            for child in node.get('calls', []):
                child_name = f"{child.get('class', '')}_{child['name']}" if child.get('class') else child['name']
                lines.append(f'{node_name} --> {child_name}')
                add_nodes(child)
        
        if 'tree' in tree:
            add_nodes(tree['tree'])
        
        return lines
    
    def _export_plantuml_package_tree(self, tree: Dict) -> List[str]:
        """导出包结构树的 PlantUML 代码"""
        lines = ["skinparam packageStyle folder", ""]
        
        def traverse(node: Dict, indent: int = 0):
            prefix = "  " * indent
            node_type = node.get('type', 'package')
            
            if node_type == 'package':
                lines.append(f'{prefix}package "{node["name"]}" {{')
                for child in node.get('children', {}).values():
                    traverse(child, indent + 1)
                lines.append(f'{prefix}}}')
            elif node_type == 'class':
                method_count = node.get('method_count', 0)
                lines.append(f'{prefix}class {node["name"]} {{')
                lines.append(f'{prefix}  + {method_count} methods')
                lines.append(f'{prefix}}}')
        
        if 'root' in tree:
            for child in tree['root'].get('children', {}).values():
                traverse(child)
        
        return lines

# Code-GraphRAG 开发计划

> **最后更新**: 2026-03-12

## 一、项目概述

基于 `structure.md` 需求文档，开发一个**智能代码知识库构建工具**，将本地代码仓库（Java项目）转化为包含语义搜索（ChromaDB）和调用关系（Neo4j）的立体知识库。

---

## 二、技术架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Source Scanner │ -> │  Git Analyzer   │ -> │  AST Parser     │
│  (文件扫描)      │    │  (Git历史溯源)   │    │  (tree-sitter)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        v
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  ChromaDB       │ <- │  LLM Processor  │    │  Neo4j          │
│  (向量存储)      │    │  (大模型生成摘要) │    │  (图关系存储)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        v
                                               ┌─────────────────┐
                                               │  Tree Generator  │
                                               │  (架构树 & 调用链) │
                                               └─────────────────┘
```

**已确认技术选型：**
- 测试项目：`test_java/`（标准三层架构）+ `test_java_ssh/`（复杂多层 SSH 风格架构）
- 大模型：本地兼容 OpenAI 接口（Ollama）
- Neo4j：Community 5.26.0，本地安装
- 当前数据规模：88+ 类，148~355 方法，567 条调用关系

---

## 三、开发阶段规划

### 阶段一：项目初始化 ✅ 已完成

| 任务 | 描述 | 状态 |
|------|------|------|
| 1.1 | 创建 Python 虚拟环境 | ✅ |
| 1.2 | 配置 `requirements.txt` 依赖 | ✅ |
| 1.3 | 创建项目目录结构 | ✅ |
| 1.4 | 配置日志系统 | ✅ |

**实际目录结构：**
```
ProjectAnalyzer/
├── src/
│   ├── scanner/          # 文件扫描模块 ✅
│   ├── git_analyzer/     # Git历史分析模块 ✅
│   ├── parser/           # AST解析模块 (tree-sitter) ✅
│   ├── llm/              # 大模型交互模块 ✅
│   ├── storage/          # 存储引擎模块
│   │   ├── vector_store.py   # ChromaDB ✅
│   │   └── graph_store.py    # Neo4j ✅
│   └── tree/             # 架构树生成模块 ✅ (新增)
│       ├── config.py
│       ├── query_service.py
│       ├── tree_generator.py
│       └── graph_quality.py
├── test_java/            # 标准测试项目 ✅
├── test_java_ssh/        # 复杂测试项目 ✅
├── output/               # 生成产物目录 ✅
├── ui/                   # 可视化仪表板模块 ✅ (新增)
│   ├── layer_tree_panel.py   # 层级树面板（点击联动）
│   ├── call_graph_panel.py   # agraph 交互网络图
│   └── package_tree_panel.py # 包结构树面板
├── app.py                # Streamlit 主入口 ✅ (新增)
├── main.py               # 入口文件 ✅
└── requirements.txt      ✅
```

### 阶段二：核心模块开发 ✅ 已完成

| 任务 | 描述 | 状态 |
|------|------|------|
| 2.1 | 实现 GitAnalyzer 类 | ✅ |
| 2.2 | 实现 JavaParser (tree-sitter) | ✅ |
| 2.3 | 实现 LLMProcessor 类 | ✅ |
| 2.4 | 实现 ChromaDB 向量存储 | ✅ |
| 2.5 | 实现 Neo4j 图存储 | ✅ |

### 阶段三：主流水线集成 ✅ 已完成

| 任务 | 描述 | 状态 |
|------|------|------|
| 3.1 | 编排主处理流程（4阶段：解析→存图→分析→生成树） | ✅ |
| 3.2 | 添加进度条和日志（tqdm） | ✅ |
| 3.3 | 配置管理 (Config类) | ✅ |
| 3.4 | 错误处理和重试机制 | ✅ |

### 阶段四：测试与优化 ✅ 已完成

| 任务 | 描述 | 状态 |
|------|------|------|
| 4.1 | 单元/集成测试编写 | ✅ (15+ 测试文件) |
| 4.2 | 使用测试Java项目验证（test_java + test_java_ssh） | ✅ |
| 4.3 | 性能优化（BFS→Cypher变长路径，消除 O(n) DB轮次） | ✅ |
| 4.4 | 检索验证脚本（search.py） | ✅ |

### 阶段五：架构树生成 ✅ 已完成（计划外新增）

| 任务 | 描述 | 状态 |
|------|------|------|
| 5.1 | 实现 `layer_tree`（按 Controller/Action/Facade/Biz/DAL 分层） | ✅ |
| 5.2 | 实现 `package_tree`（按文件路径递归展开子包） | ✅ |
| 5.3 | 实现 `call_chain_tree`（从 Controller/Action 入口递归下游） | ✅ |
| 5.4 | 导出 JSON / Mermaid / PlantUML 格式 | ✅ |
| 5.5 | 图质量基准测试（6条关键链路命中率，业务断链率等） | ✅ |

### 阶段六：图与树优化 ✅ 已完成

| 任务 | 描述 | 状态 |
|------|------|------|
| 6.1 | 图数据优化（提升调用关系识别率） | ✅ |
| 6.2 | 修复 Windows 路径分隔符 Bug（`layer_tree` 输出为空的根因） | ✅ |
| 6.3 | 修复 `call_chain_tree` 入口方法查找失败（Cypher CONTAINS 正斜杠） | ✅ |
| 6.4 | 新增 `action` 层支持（覆盖 test_java_ssh 架构） | ✅ |
| 6.5 | 消除 `generate_layer_tree()` 死代码（N次多余 DB 查询） | ✅ |
| 6.6 | 修复 Mermaid subgraph 结构错误（每类单独空块→同层统一块） | ✅ |
| 6.7 | 修复 PlantUML 同层类分散输出问题 | ✅ |
| 6.8 | `get_downstream_calls` / `get_upstream_callers` 改 Cypher 变长路径 | ✅ |
| 6.9 | 修复 `get_data_flow_path` 的 `end_class` 逻辑错误 | ✅ |
| 6.10 | `get_call_statistics` 3条查询合并1条，去掉不安全 `.peek()` | ✅ |
| 6.11 | 新增方法查询结果缓存（避免 `layer_tree`/`package_tree` 重复查询） | ✅ |
| 6.12 | `generate_call_chain_tree` 支持 `max_entries` 多入口参数 | ✅ |

### 阶段七：可视化仪表板 ✅ 已完成

> **方案**：Streamlit + streamlit-agraph，实时查询 Neo4j，树与图双向联动

| 任务 | 描述 | 状态 |
|------|------|------|
| 7.1 | 方案选型（Streamlit + streamlit-agraph，支持 Python 点击回调） | ✅ |
| 7.2 | 安装依赖（`streamlit>=1.35.0`，`streamlit-agraph>=0.0.45`） | ✅ |
| 7.3 | 实现 `ui/layer_tree_panel.py`（层级树面板，点击联动） | ✅ |
| 7.4 | 实现 `ui/call_graph_panel.py`（agraph 交互网络图，实时 Neo4j 查询） | ✅ |
| 7.5 | 实现 `ui/package_tree_panel.py`（包结构树面板） | ✅ |
| 7.6 | 实现 `app.py`（主入口，工具栏 + 双栏布局 + 详情条） | ✅ |
| 7.7 | 修复重复类名导致的 `StreamlitDuplicateElementKey` 错误（`layer_tree_panel.py` 去重） | ✅ |
| 7.8 | 端到端启动验证（`python -m streamlit run app.py --server.port 8503`） | ✅ |

**关键设计：**
- 左面板：`st.tabs(["层级树", "包结构树"])` — 两种架构视图
- 右面板：`streamlit-agraph` 交互图，按层着色，边按 call_type 着色
- 联动机制：点击左树类名 → 更新 `session_state.selected_class` → 右图 reload；点击右图节点 → 写回 `session_state` → 左树高亮
- 节点颜色方案：action/controller=#E74C3C，facade=#E67E22，service=#27AE60，biz=#2980B9，dal/dao=#8E44AD，model=#16A085，util=#7F8C8D
- 启动命令：`python -m streamlit run app.py --server.port 8503`

---

## 四、核心类设计（实际实现）

### Config (`src/config.py`)
- `PROJECT_PATH`, `NEO4J_URI/USER/PASSWORD`, `LLM_API_URL/MODEL`, `CHROMA_DB_PATH`

### JavaParser (`src/parser/java_parser.py`)
```python
class JavaParser:
    def extract_methods(file_path) -> list[dict]   # tree-sitter 解析
    def extract_classes(file_path) -> list[dict]
    def extract_call_relationships(file_path) -> list[dict]
```

### GraphStore (`src/storage/graph_store.py`)
```python
class GraphStore:
    def add_method_node(method_info)
    def add_call_relationship(source, target, call_type)  # internal/external/external_unknown
    def get_method_neighbors(method_name) -> list
```

### ArchitectureTreeGenerator (`src/tree/tree_generator.py`)
```python
class ArchitectureTreeGenerator:
    def generate_layer_tree(project_name) -> dict       # 按层级组织
    def generate_package_tree(project_name) -> dict     # 按包路径组织
    def generate_call_chain_tree(entry, class_name, max_depth, max_entries) -> dict
    def export_tree_json(tree, output_path)
    def export_mermaid(tree, output_path) -> str
    def export_plantuml(tree, output_path) -> str
```

### GraphQueryService (`src/tree/query_service.py`)
```python
class GraphQueryService:
    def get_layer_statistics() -> list[dict]
    def get_entry_methods() -> list[dict]              # controller + action 层
    def get_downstream_calls(method, class, depth)     # 单条 Cypher 变长路径
    def get_upstream_callers(method, class, depth)     # 单条 Cypher 变长路径
    def get_data_flow_path(start, start_class, end, end_class) -> list
```

---

## 五、里程碑

| 里程碑 | 完成标准 | 状态 |
|--------|----------|------|
| M1 | 环境搭建完成，可运行 `python main.py` | ✅ |
| M2 | 核心模块开发完成，成功解析Java文件 | ✅ |
| M3 | 集成大模型，成功生成代码摘要 | ✅ |
| M4 | ChromaDB 存储完成，可执行语义检索 | ✅ |
| M5 | Neo4j 图关系存储完成 | ✅ |
| M6 | 完整流水线验证通过 | ✅ |
| M7 | 架构树生成完成（layer/package/call_chain，含 Mermaid/PlantUML 导出） | ✅ |
| M8 | 图质量基准系统完成（6条关键链 100% 命中，业务断链率 < 2%） | ✅ |
| M9 | 图与树全面优化完成（Bug 修复 + 性能优化） | ✅ |
| M10 | 可视化仪表板上线（Streamlit 树图双向联动） | ✅ |

---

## 六、当前输出产物

| 文件 | 内容 | 状态 |
|------|------|------|
| `output/layer_tree.json` | 9个层级（action/controller/facade/service/biz/dal/dao/model/util） | ✅ 正常 |
| `output/layer_tree.md` | Mermaid 格式，每层 subgraph 包含所有类 | ✅ 正常 |
| `output/package_tree.json` | 按文件路径展开的完整包树 | ✅ 正常 |
| `output/call_chain_tree.json` | 从 `OrderCreateAction.execute` 出发的调用链（深度10） | ✅ 正常 |
| `output/call_chain_tree.puml` | PlantUML 格式调用链 | ✅ 正常 |
| `output/graph_quality_benchmark.json` | 质量基准报告：断链率35%，业务断链14%，可达率56%，关键链100% | ✅ 正常 |

---

## 七、待确认/下一步方向

1. **ChromaDB 语义检索**：向量存储已实现，可进一步验证检索质量（相关性评估）
2. **图质量提升**：业务断链率 14.64%（83条），可通过扩展跨类调用识别规则继续优化
3. **可达率提升**：当前 56.34%（200/355），SSH 项目中部分孤立方法未被入口覆盖
4. **真实项目接入**：可接入实际 Java 业务仓库替换测试项目
5. **搜索接口增强**：`search.py` 现有语义搜索基础，可结合图关系做 GraphRAG 联合召回

---

## 八、风险与对策（已解决项）

| 风险 | 对策 | 结果 |
|------|------|------|
| tree-sitter Java 解析失败 | 降级到简单正则匹配 | ✅ tree-sitter 解析成功，无需降级 |
| 大模型 API 超时 | 添加重试机制和超时配置 | ✅ 已实现重试 |
| ChromaDB 版本兼容 | 锁定版本号 0.4.24 | ✅ 已锁定 |
| Neo4j 连接失败 | 跳过图存储，仅保留向量存储 | ✅ Neo4j 5.26.0 稳定运行 |
| Windows 路径分隔符不一致 | `_extract_layer()` 中 `replace('\\', '/')` 规范化 | ✅ 已修复 |
| 图遍历 O(n) DB 往返 | Cypher 变长路径 `[:CALLS*1..N]` 单条查询 | ✅ 已优化 |

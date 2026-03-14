# Code-GraphRAG 实施进展记录

> **目标**：将 ProjectAnalyzer 打造成面向大型历史老项目的 LLM 理解体系，涵盖全量索引、GraphRAG 引擎、多端问答界面、文档生成四大阶段。
>
> **启动时间**：2026-03-13

---

## 总体进展

| Phase | 内容 | 状态 | 完成时间 |
|-------|------|------|---------|
| Phase 1 | 全量 LLM 摘要索引 | ✅ 已实现 | 2026-03-13 |
| Phase 2 | GraphRAG 检索引擎 | ✅ 已实现 | 2026-03-13 |
| Phase 3 | 多端问答界面 | ✅ 已实现 | 2026-03-13 |
| Phase 4 | 文档生成（离线报告）| ✅ 已实现 | 2026-03-13 |
| Phase 5 | 调用图精度提升（4周计划）| ✅ 已实现 | 2026-03-14 |

---

## Phase 5 — 调用图精度提升（4周深度改造）

> **目标**：以不破坏关键链路命中（6/6 = 100%）为前提，降低 `unknown_calls` 和 `broken_chain_rate`，并补齐大项目可持续运行能力。
>
> **基线（ssh project）**：`unknown_calls=1363`（jdk=1093, business=270），`broken_chain_rate=77.2%`，`key_chain_hit=100%`

### Week 1 — 匹配与推断增强

| 任务 | 文件 | 说明 |
|------|------|------|
| 签名容差匹配 | `src/config.py`, `src/storage/graph_store.py` | 新增 `SIGNATURE_MATCH_TOLERANT`/`SIGNATURE_TOLERANT_MAX_DIFF` 配置；3层匹配：exact → fallback → tolerant；所有 CALLS 边携带 `match_mode` 属性 |
| External unknown 二次补链 | `src/storage/graph_store.py` | Pass 1: 唯一名称精确补链（`confidence=1.0`）；Pass 2: 文件路径邻近度启发式（`inferred_reason=path_proximity:N`）；`resolve_external_unknown_calls()` 返回总补链数 |
| 字段提取增强 | `src/parser/java_parser.py` | 正则扩展至 package-private 字段、`@注解` 前置字段 |
| 局部变量推断增强 | `src/parser/java_parser.py` | for-each 和 try-with-resources 变量提取 |
| 类型转换 receiver 推断 | `src/parser/java_parser.py` | `((TypeName) expr).method()` → 提取转换后类型 |

### Week 2 — 可解释性与复杂调用覆盖

| 任务 | 文件 | 说明 |
|------|------|------|
| 链式调用返回类型推断 | `src/parser/java_parser.py` | 新增 `method_return_types` 字典；`_infer_chain_receiver_type()` 支持 1跳链式推断（`obj.getX().method()`）；方法 dict 新增 `return_type` 字段 |
| 质量报告分层 | `src/tree/graph_quality.py` | 新增 `critical_chain_retention`、`critical_hop_dropout`、`util_unknown_ratio` 三维指标；分离关键路径与工具类噪声 |
| 阈值回归门禁扩展 | `tests/test_graph_quality_thresholds.py` | 3 个新 CLI 参数 + 3 个新阈值检查 |

### Week 3 — 规模化与框架调用补链

| 任务 | 文件 | 说明 |
|------|------|------|
| 增量解析模式 | `src/scanner/scanner.py`, `main.py`, `src/storage/graph_store.py` | SHA-256 文件哈希缓存（`.parse_cache.json`）；`compute_delta()` 返回变更/删除文件集；`--incremental` 标志；`delete_file_data()` 按文件清除旧图数据 |
| Spring/MyBatis 注解感知 | `src/parser/java_parser.py`, `src/storage/graph_store.py` | `_extract_spring_annotations()`：`@Autowired`/`@Resource`/`@Inject` 多行感知字段提取；`_get_class_annotations()`：`@Service`/`@Mapper` 类注解检测；Class 节点新增 `is_mapper`/`is_service` 属性；Pass 3 (Mapper) 补链至 `@Mapper` 接口方法（`confidence=0.80`） |
| 注解规则集配置化 | `config/reflection_patterns.yaml` | 可扩展 YAML 规则文件，无需改代码即可新增注解规则 |

### Week 4 — 稳定化与发布

| 任务 | 文件 | 说明 |
|------|------|------|
| 回归测试基础设施 | `scripts/run_regression.py` | 统一离线回归入口；区分 offline/online 套件；提供 Neo4j 手动验证清单 |
| .gitignore 补全 | `.gitignore` | `output/trees/`, `output/quality/`, `.parse_cache.json` |
| README 同步 | `README.md` | 增量模式、Spring 注解感知、规则集扩展说明 |

### 2026-03-14 增补 — 分析层可配置与可解释性增强

| 任务 | 文件 | 说明 |
|------|------|------|
| 关键链配置化 | `src/tree/graph_quality.py`, `config/critical_chains.json` | 关键链路支持 JSON 配置加载（`config/critical_chains.json`），无配置自动回退内置默认；支持 hop 多格式归一化 |
| 关键链解释性指标 | `src/tree/graph_quality.py`, `tests/test_graph_quality_thresholds.py` | 新增 `critical_definition_presence`（定义命中率）与 `critical_chain_coverage`（可达覆盖率），用于区分“配置不匹配”与“真实断链” |
| 入口识别优化 | `src/tree/query_service.py` | `get_entry_methods()` 从单一路径规则升级为多信号评分（层级、类名、方法名、出度），提升历史项目入口召回 |
| 候选关键链自动发现 | `src/tree/graph_quality.py`, `tests/test_graph_quality.py` | 新增 `suggest_critical_chains()`，可基于图结构自动生成候选关键链；CLI 支持 `--suggest-critical-chains-output` 导出 JSON 供人工筛选 |

#### 当前验证结论（reins 图）

- 关键链定义命中率 `critical_definition_presence=0%`，明确指向“默认链路配置与项目不匹配”而非图构建失败。
- 可达率在入口识别优化后从约 `10.54%` 提升到约 `13.31%`（同一图快照条件下）。

#### 2026-03-14 追加修复（候选链稳定性）

- 修复 `suggest_critical_chains()` 初版中 Neo4j 变长路径参数化语法不兼容问题（`[:CALLS*1..$max_hops]`）。
- 生成策略改为“逐跳扩展 + 贪心打分”：按当前节点调用关系逐层选择最优下一跳，避免大规模路径枚举。
- 复测通过：`tests/test_graph_quality.py` 已成功写出候选链文件 `output/quality/critical_chain_candidates.json`。
- 当前观察：候选链仍有同构路径集中，后续可增加前缀去重与分层多样性约束。

#### 2026-03-14 追加增强（候选链多样性约束）

- 在 `suggest_critical_chains()` 增加核心前缀分桶限流：
  - 参数：`max_per_core_prefix`（默认 2）
  - 参数：`core_prefix_len`（默认 3，从第 2 跳开始计）
- 在 `tests/test_graph_quality.py` 新增 CLI 参数：
  - `--suggest-max-per-core-prefix`
  - `--suggest-core-prefix-len`
- 目标：降低候选链同构聚集，提升人工筛选效率。

### 验收清单（Neo4j 启动后执行）

```bash
# 1. SSH 项目全量构建 + 质量门禁
python main.py --neo4j-only --reset-graph
python tests/test_graph_quality_thresholds.py \
  --max-unknown-ratio 0.80 \
  --min-reachability  0.55 \
  --min-critical-chain-retention 1.0

# 2. SSH unknown 分类报告
python tests/test_graph_quality_breakdown.py
# 目标: business_unknown < 180（基线270，目标降幅 ≥33%）

# 3. 增量一致性验证
python main.py --neo4j-only --reset-graph
python main.py --neo4j-only --incremental  # 无变更，CALLS 数量应不变

# 4. 离线套件（无需Neo4j）
python scripts/run_regression.py
# 预期：3+ PASS，0 FAIL
```

---

## Phase 1 — 全量 LLM 摘要索引

### 目标
把所有方法都索引进 ChromaDB，附带丰富元数据；增强 Prompt 质量；支持全量建库。

### 任务清单

- [x] **1.1** 创建 `src/llm/batch_indexer.py`：批量摘要生成，支持增量、并发、进度显示
- [x] **1.2** 增强 `src/llm/processor.py` Prompt：加入类名、所属层、字段依赖
- [x] **1.3** 增强 `src/storage/vector_store.py`：补充 `search()` 方法，写入层级元数据
- [x] **1.4** `main.py` 加 `--index-all` 模式：触发全量索引流水线

### 实施记录

#### 2026-03-13

**1.1 batch_indexer.py**
- 新建 `src/llm/batch_indexer.py`
- 实现 `BatchIndexer` 类，批量遍历方法索引，调用 LLM 生成摘要
- 支持增量更新：先查 ChromaDB 已有 chunk_id，跳过已索引项
- 支持 `max_workers` 并发（ThreadPoolExecutor）
- 集成 `tqdm` 进度条

**1.2 Prompt 增强**
- `LLMProcessor.generate_summary()` 补充参数：`class_name`、`layer`、`field_deps`
- Prompt 结构改为：上下文信息（层级/类/Git）+ 依赖字段 + 源代码 + 明确的输出格式要求

**1.3 vector_store 增强**
- 新增 `search(query, n_results, filter_layer)` 方法
- `add_code_chunk()` 写入 `layer`、`call_count`、`callers_count` 元数据

**1.4 main.py 加 --index-all**
- 新增 `phase3_index_all()` 函数，替换原先只索引 top-5 的逻辑
- `--index-all` 触发全量索引，`--graph-only` 跳过 LLM

---

## Phase 2 — GraphRAG 检索引擎

### 目标
向量找相关方法 → 图展开调用上下文 → 组装 LLM Context → 回答问题。

### 任务清单

- [x] **2.1** 新建 `src/llm/graphrag.py`：`GraphRAGEngine`，实现 `query()`、`trace_entry_to_db()`、`describe_module()`

### 实施记录

#### 2026-03-13

**2.1 GraphRAGEngine**
- 向量召回 → 图展开（下游+上游 depth=2）→ 上下文组装 → LLM 生成
- `trace_entry_to_db()`: 从入口自动追溯完整链路并自然语言描述
- `describe_module()`: 汇总层级所有类摘要，生成层级架构描述

---

## Phase 3 — 多端问答界面

### 目标
Streamlit Chat 面板 + CLI 命令行问答，多种方式理解项目。

### 任务清单

- [x] **3.1** 新建 `ui/chat_panel.py`：Streamlit Chat 面板，与图联动
- [x] **3.2** 更新 `app.py`：右侧加 Chat Tab
- [x] **3.3** 新建 `chat_cli.py`：CLI 交互问答，支持 `/trace`、`/describe` 命令

### 实施记录

#### 2026-03-13

**3.1 chat_panel.py**
- `st.chat_input` + `st.chat_message` 实现对话历史
- 联动 `selected_class/method`，自动带入上下文
- 动态展示来源方法（折叠块引用）

**3.2 app.py 改版**
- 右侧 Tab：`📊 调用图` | `💬 智能问答`
- 图点击节点 → chat 面板自动预填分析问题

**3.3 chat_cli.py**
- 交互式命令行，`/trace`、`/describe`、`/help`、`/exit` 命令
- 普通输入直接走 GraphRAG 问答

---

## Phase 4 — 文档生成（离线报告）

### 目标
为每个模块/层生成可读的 Markdown 文档，包含架构概览。

### 任务清单

- [x] **4.1** 新建 `scripts/generate_docs.py`：为每层生成 Markdown，生成全局架构概览

### 实施记录

#### 2026-03-13

**4.1 scripts/generate_docs.py**
- 遍历各层，聚合摘要，调用 LLM 生成层级说明
- 输出 `output/docs/{layer}_overview.md` + `output/architecture_overview.md`

---

## 验证记录

| 验证项 | 命令 | 预期结果 | 实际结果 |
|--------|------|---------|---------|
| 语法编译检查 | `python -m py_compile main.py chat_cli.py scripts/generate_docs.py src/llm/batch_indexer.py src/llm/graphrag.py ui/chat_panel.py src/storage/vector_store.py src/llm/processor.py src/tree/config.py app.py` | 全部通过 | ✅ 通过 |
| 图链路（graph-only） | `python main.py --graph-only` | 图写入+树导出完成 | ⚠️ Neo4j 未启动，解析与热点分析完成，图写入与树导出跳过 |
| 全量索引 | `python main.py --index-all` | vector_store.count() > 100 | ✅ 成功，148/148 新增，向量库文档数 148 |
| CLI 冒烟（help） | `printf '/help\n/exit\n' \| python chat_cli.py` | CLI 正常启动并处理命令 | ✅ 通过 |
| CLI 实际问答 | `printf '订单创建流程是怎样的？\n/exit\n' \| python chat_cli.py` | 返回含调用链答案 | ⚠️ Neo4j 连接失败导致中断 |
| Streamlit 启动 | `python -m streamlit run app.py --server.headless true --server.port 8503` | Chat Tab 正常问答 | ⚠️ 应用启动后访问图查询时报 Neo4j 连接失败 |
| 文档导出 | `python scripts/generate_docs.py` | output/docs/ 下生成各层 md | ✅ 通过，16 个分层文档 + architecture_overview.md |

---

## 已知问题与决策

- **GraphRAG 而非纯 RAG**：图展开是理解老项目调用链的核心差异化能力
- **全量摘要 + 增量更新**：一次性全量建库，后续增量只处理改动文件
- **复用已有存储**：不引入新的存储依赖（ChromaDB + Neo4j 复用）
- **暂不引入高质量 Embeddings**：ChromaDB 默认 embedding 先用，后续可替换 text2vec
- **当前阻塞（联调）**：本机 Neo4j 未启动（localhost:7687 Connection refused），导致调用图实时查询、CLI 真实问答（含图扩展）受阻
- **环境修复记录**：已安装缺失依赖 streamlit / streamlit-agraph，`python -m streamlit` 可执行

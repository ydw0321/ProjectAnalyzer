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

- [x] **4.1** 新建 `generate_docs.py`：为每层生成 Markdown，生成全局架构概览

### 实施记录

#### 2026-03-13

**4.1 generate_docs.py**
- 遍历各层，聚合摘要，调用 LLM 生成层级说明
- 输出 `output/docs/{layer}_overview.md` + `output/architecture_overview.md`

---

## 验证记录

| 验证项 | 命令 | 预期结果 | 实际结果 |
|--------|------|---------|---------|
| 语法编译检查 | `python -m py_compile main.py chat_cli.py generate_docs.py src/llm/batch_indexer.py src/llm/graphrag.py ui/chat_panel.py src/storage/vector_store.py src/llm/processor.py src/tree/config.py app.py` | 全部通过 | ✅ 通过 |
| 图链路（graph-only） | `python main.py --graph-only` | 图写入+树导出完成 | ⚠️ Neo4j 未启动，解析与热点分析完成，图写入与树导出跳过 |
| 全量索引 | `python main.py --index-all` | vector_store.count() > 100 | ✅ 成功，148/148 新增，向量库文档数 148 |
| CLI 冒烟（help） | `printf '/help\n/exit\n' \| python chat_cli.py` | CLI 正常启动并处理命令 | ✅ 通过 |
| CLI 实际问答 | `printf '订单创建流程是怎样的？\n/exit\n' \| python chat_cli.py` | 返回含调用链答案 | ⚠️ Neo4j 连接失败导致中断 |
| Streamlit 启动 | `python -m streamlit run app.py --server.headless true --server.port 8503` | Chat Tab 正常问答 | ⚠️ 应用启动后访问图查询时报 Neo4j 连接失败 |
| 文档导出 | `python generate_docs.py` | output/docs/ 下生成各层 md | ✅ 通过，16 个分层文档 + architecture_overview.md |

---

## 已知问题与决策

- **GraphRAG 而非纯 RAG**：图展开是理解老项目调用链的核心差异化能力
- **全量摘要 + 增量更新**：一次性全量建库，后续增量只处理改动文件
- **复用已有存储**：不引入新的存储依赖（ChromaDB + Neo4j 复用）
- **暂不引入高质量 Embeddings**：ChromaDB 默认 embedding 先用，后续可替换 text2vec
- **当前阻塞（联调）**：本机 Neo4j 未启动（localhost:7687 Connection refused），导致调用图实时查询、CLI 真实问答（含图扩展）受阻
- **环境修复记录**：已安装缺失依赖 streamlit / streamlit-agraph，`python -m streamlit` 可执行

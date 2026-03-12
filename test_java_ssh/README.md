# test_java_ssh

该目录是一套用于 ProjectAnalyzer 压测的老旧 SSH 风格 Java 样例工程。

## 目标
- 模拟 Struts1 + Spring + Hibernate3 时代遗留系统
- 保留明显技术债和混乱调用关系
- 让扫描、解析、图谱、树生成、热点分析都能产出可观察结果

## 特征
- 目录混合标准层和非标准层：action、service、biz、dao、model、util、interceptor、job、legacy
- 存在越级调用：Action -> Biz，Biz -> DAO，Job -> Biz
- 存在循环链路：OrderServiceImpl -> PaymentGatewayBiz -> RetryInterceptor -> OrderServiceImpl
- 存在接口多实现：PaymentService 的多个实现类
- 存在老式配置文件：struts-config.xml、applicationContext.xml、hibernate.cfg.xml、order.hbm.xml
- 存在脏代码特征：超长分支、魔法值、静态工具类滥用、同名方法污染
- 第二批加压：反射调用、God Class、Service Locator 和 external_unknown 断言

## 第二批加压点
- God Class: service/impl/order/LegacyOrderGodService.java
- 反射入口: legacy/integration/LegacyReflectionInvoker.java
- 同名方法污染: biz/order/LegacyDirtyRouter.java 与 dao/order/LegacyOrderHistoryDAO.java
- 调度扩散入口: action/order/LegacyDispatchAction.java
- external_unknown 测试脚本: ../test_ssh_external_unknown.py

## 第三批极限加压点
- 10+ 深链入口: action/order/LegacyStressAction.java
- 深链协调器: service/impl/order/DeepChainCoordinator.java
- 深链节点: DeepNode1Biz -> DeepNode11FinalService
- 超大类: service/impl/order/LegacyTicketMonsterService.java
- 深链阈值脚本: ../test_ssh_chain_depth.py

## 快速验证
- 仅扫和解析：`python test_ssh_scanner.py`
- 图谱流程（跳过 LLM）：`python test_ssh_graph.py`
- external_unknown 盲点断言：`python test_ssh_external_unknown.py`
- 深链与超大类阈值断言：`python test_ssh_chain_depth.py`

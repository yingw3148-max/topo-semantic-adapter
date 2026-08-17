# topo-semantic-adapter

`topo-semantic-adapter` 是拓扑理解流水线中的**领域适配层（Domain Adapter Layer）**。

它位于原始运维数据采集（CLI 巡检文件、配置库、告警日志等）与下游拓扑理解任务之间，负责把分散、异构、半结构化的拓扑要素（设备、接口、链路）及其业务语义，翻译成统一、可消费的图结构（节点-边-属性）。

## 1. 项目定位

| 项目 | 职责 |
|------|------|
| **network-topology-skills** | 提供拓扑领域知识/技能定义：设备类型、协议规范、实体关系等。 |
| **topograph-py** | 提供图结构的持久化、查询与操作能力。 |
| **topo-semantic-adapter（本项目）** | 负责从原始数据到标准图结构的**翻译**与**适配**：加载、解析、语义提取、意图过滤、图构建。 |

## 2. 架构（文字描述）

```text
┌──────────────────────────────────────────────────────────────────────┐
│                        topo-semantic-adapter                         │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │ CLI 文件加载器 │ → │ 语义解析引擎  │ → │       图构建器            │ │
│  │  (按站点/设备) │   │ (插件化 Parser)│   │ 输出 TopoGraph           │ │
│  └──────────────┘   └──────────────┘   └──────────────────────────┘ │
│           ↑                  ↑                      │                │
│    原始 CLI 文件      Adapter 注册表            对接 topograph-py     │
│           ↓                  ↓                                      │
│  ┌─────────────────────────────────────┐   ┌──────────────────┐    │
│  │         意图解析器 (IntentResolver)   │   │ 华为/华三/思科... │    │
│  │  根据下游任务意图选择挂载的属性集      │   │  多厂商适配器插件  │    │
│  └─────────────────────────────────────┘   └──────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

数据流：

1. **CLI 文件加载器**扫描 `{站点名}-配置/inspect/{设备IP}_{设备ID}/CommonCollectResult`，按 `=========######HUAWEI#####=========` 分隔符切分为命令-回显对。
2. **Adapter 注册表**根据命令命中对应的 `CommandParser`。
3. **语义解析引擎**提取拓扑实体（设备、接口、链路聚合组等）和语义属性（LLDP 邻居、OSPF 邻居状态、VRRP 主备状态、DHCP 绑定状态、LAG 成员状态等）。
4. **意图解析器**根据下游任务（如故障根因定位、影响范围分析）决定挂载哪些属性；`topology` 概念默认包含在所有意图中，确保 LLDP 基础拓扑始终重建。
5. **图构建器**把所有实体合并为统一的 `toposphere_core.TopoGraph`，供 `topograph-py`（TopoSphere Core）消费。

## 3. 目录结构

```text
topo-semantic-adapter/
├── pyproject.toml
├── README.md
├── docs/
│   └── design.md                     # 业务背景、规格、架构与流程设计
├── src/
│   └── topo_semantic_adapter/
│       ├── __init__.py
│       ├── models.py                 # 适配器内部中间模型 Node / Edge / Graph
│       ├── cli_loader.py             # CLI 文件加载与命令-回显分割
│       ├── intent_resolver.py        # 下游意图 → 属性集映射
│       ├── graph_builder.py          # 合并实体、输出 toposphere_core.TopoGraph
│       ├── toposphere_bridge.py      # 中间模型 → toposphere_core 类型桥接
│       ├── registry.py               # 插件化 Parser 注册表
│       └── adapters/
│           ├── __init__.py
│           ├── base.py               # CommandParser / SemanticAdapter 抽象
│           └── huawei/               # 华为 CLI 适配器插件集
│               ├── __init__.py       # HuaweiSemanticAdapter
│               ├── _helpers.py       # 设备 source、接口名规范化等工具
│               ├── lldp.py           # LLDP 拓扑重建
│               ├── link_aggregation.py  # 链路聚合成员状态
│               ├── ospf.py           # OSPF 邻居状态
│               ├── vrrp.py           # VRRP 主备状态
│               └── dhcp.py           # DHCP Snooping 绑定状态
├── tests/
│   ├── __init__.py
│   ├── test_cli_loader.py
│   ├── test_graph_builder.py
│   └── adapters/
│       ├── __init__.py
│       ├── test_link_aggregation.py
│       ├── test_lldp.py
│       ├── test_ospf.py
│       ├── test_vrrp.py
│       └── test_dhcp.py
```

## 4. 核心抽象

- `CLIFileLoader`：按站点文件夹结构读取 `CommonCollectResult`，产出 `CommandBlock`。
- `CommandParser`：命令级解析插件，声明自己能解析的命令、`semantic_concepts` 以及产出 `ParsedEntity`。
- `SemanticAdapter`：厂商级适配器，聚合一组 `CommandParser`。
- `IntentResolver`：根据意图返回 `IntentProfile`，决定需要挂载哪些属性。
- `GraphBuilder`：把解析后的实体合并成 `toposphere_core.TopoGraph`。

## 5. 快速开始

```python
from pathlib import Path
from topo_semantic_adapter import CLIFileLoader, GraphBuilder
from topo_semantic_adapter.registry import AdapterRegistry

# 1. 加载内置适配器（当前包含华为 LLDP/OSPF/VRRP/DHCP/LAG 解析器）
registry = AdapterRegistry()
registry.load_builtin()

# 2. 扫描站点 CLI 文件
loader = CLIFileLoader(site_name="site-a", base_path=Path("/data/sites"))
blocks = list(loader.iter_blocks())

# 3. 按意图构建图，直接得到 toposphere_core.TopoGraph
builder = GraphBuilder(registry=registry, intent="impact_analysis")
builder.consume_many(blocks)
graph = builder.build()

print(graph.get_node_count(), graph.get_edge_count())

# 4. 物化为 GraphView 进行下游分析
view = graph.to_graphview()
```

## 6. 扩展一个适配器

实现 `CommandParser` 并注册到 `AdapterRegistry` 即可：

```python
from topo_semantic_adapter.adapters.base import CommandParser, AdapterContext, ParsedEntity

class MyParser(CommandParser):
    def can_parse(self, command: str) -> bool:
        return "display ospf peer" in command.lower()

    def parse(self, command: str, output: str, context: AdapterContext) -> ParsedEntity:
        ...

registry.register(MyParser())
```

## 7. 设计文档

详细设计文档见 `docs/design.md`，包含：

- 业务背景与现状
- 输入/输出规格与 ID 规范
- 系统功能设计与模块划分
- 关键设计思路（语义驱动、插件化、确定性 ID、意图过滤）
- 关键流程时序图（CLI → Parser → TopoGraph）
- 扩展指南

## 8. 测试

```bash
# 建议先安装到可编辑模式
pip install -e ".[dev]"

# 运行测试
pytest
```

## 9. 与 network-topology-skills / topograph-py 的协作

- **network-topology-skills** 提供领域概念（如“链路聚合组”应有哪些属性、设备类型层级），`topo-semantic-adapter` 在提取时尽可能对齐这些概念，但两者保持松耦合。
- **topograph-py**（包名 `toposphere-core`）提供图存储与查询。`topo-semantic-adapter` 直接输出 `toposphere_core.TopoGraph`，并通过 `toposphere_bridge.py` 完成中间模型到 `toposphere_core.Node` / `toposphere_core.Edge` 的转换。

> 安装依赖前，请确保 `toposphere-core` 已在当前环境中可用（例如以可编辑模式安装 sibling 项目 `topograph-py`），因为 `pyproject.toml` 已将其声明为直接依赖。

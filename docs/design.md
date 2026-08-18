# topo-semantic-adapter 设计文档

## 1. 业务背景与现状

### 1.1 业务背景

在大型网络运维场景中，拓扑理解是故障定位、影响分析、变更评估等任务的共同基础。真实网络中的拓扑要素（设备、接口、链路）及其业务语义（DHCP 租约、OSPF 邻居、VRRP 主备、链路聚合成员状态等）分散在多种半结构化数据源中：

- CLI 巡检回显文件（华为、华三、思科等多厂商命令）
- 配置管理系统导出的配置片段
- 告警、日志、CMDB 等业务系统数据

这些原始数据通常具有以下特点：

- **格式异构**：同一语义在不同厂商、不同版本命令行中的表现形式不同。
- **信息互补**：物理链路关系往往由 LLDP/CDP 等协议回显给出，而业务状态由专门的 `display *` 命令给出。
- **体量分散**：一个站点可能包含数十台设备，每台设备包含数十条命令回显。

### 1.2 现状与痛点

当前运维团队通常采用以下方式处理上述数据：

1. **人工查看**：工程师逐台登录设备、逐条查看命令输出，效率低、易遗漏。
2. **硬编码脚本**：针对特定命令写一次性正则脚本，难以维护，厂商扩展成本高。
3. **数据孤岛**：拓扑数据、业务属性数据分别存储，难以在一张图上统一消费。

`topo-semantic-adapter` 的定位就是解决上述问题：作为**领域适配层**，把原始运维数据自动翻译成下游图存储/分析系统可直接消费的统一图结构，并在同一套节点/边上挂载多维度业务属性。

## 2. 业务规格

### 2.1 输入规格

| 输入项 | 说明 | 示例 |
|--------|------|------|
| 站点根目录 | 包含 `{site}-配置/inspect/` 的父目录 | `/data/sites` |
| 设备目录 | `{device_ip}_{device_id}` | `10.0.0.1_core-sw-01` |
| 采集结果文件 | `CommonCollectResult` | 明文命令-回显对 |
| 命令分隔符 | `=========######HUAWEI#####=========` | 分隔不同命令块 |
| 命令行 | 每块的第 1 行 | `display lldp neighbor brief` |
| 回显 | 每块第 1 行之后的内容 | 命令原始文本输出 |

### 2.2 输出规格

输出为 `toposphere_core.TopoGraph`，包含以下节点与边：

**节点（Node）**

| kind | 说明 | 关键属性 |
|------|------|----------|
| `device` | 网络设备 | `name`, `mgmt_ip`, `device_id` |
| `interface` | 物理/逻辑接口 | `name`, `device_ip`, `device_id` |
| `link_aggregation_group` | 链路聚合组 | `name`, `device_ip`, `device_id` |
| `ospf_router` | OSPF 邻居路由器（可选） | `router_id`, `state` |

**边（Edge）**

| kind | 说明 | 关键属性 |
|------|------|----------|
| `connects_to` | LLDP 发现的物理/逻辑连接 | `protocol`, `local_device`, `remote_device` |
| `member_of` | 接口加入链路聚合组 | `selected_status` |
| `peers_with` | OSPF 邻居关系（可选） | `ospf_state` |

**业务属性挂载**

业务属性统一挂载到对应 `interface` 节点的 `metadata` 中：

| 属性名 | 来源命令 | 说明 |
|--------|----------|------|
| `lldp_neighbors` | `display lldp neighbor brief` | 邻居列表（远端设备、端口） |
| `ospf_neighbor_state` | `display ospf peer` | OSPF 邻居状态，如 `Full`/`Init` |
| `ospf_neighbor_router_id` | `display ospf peer` | 对端 Router ID |
| `vrrp_role_state` | `display vrrp` | 当前接口 VRRP 角色：`Master`/`Backup` |
| `vrrp_vrid` / `vrrp_virtual_ip` | `display vrrp` | VRID 与虚拟 IP |
| `dhcp_lease_state` | `display dhcp snooping binding` | 是否绑定 DHCP 租约 |
| `dhcp_bound_ip` / `dhcp_bound_mac` | `display dhcp snooping binding` | 绑定的 IP/MAC |
| `lag_member_state` | `display link-aggregation verbose` | 聚合组成员选中状态 |

### 2.3 ID 规范

节点 ID 遵循 TopoSphere Core 的确定性约定：

```text
{source}:{kind}:{identifier}
```

- `source`：首选设备 hostname（`device_id`），缺失时使用设备管理 IP。
- `kind`：节点类型，如 `device`、`interface`、`link_aggregation_group`。
- `identifier`：局部标识符，如接口名、聚合组名、设备 hostname。

例如：

```text
core-sw-01:device:core-sw-01
core-sw-01:interface:GigabitEthernet0/0/1
core-sw-01:link_aggregation_group:Eth-Trunk1
```

## 3. 系统功能设计

### 3.1 模块划分

```text
topo-semantic-adapter/
├── src/topo_semantic_adapter/
│   ├── cli_loader.py              # 站点/设备/命令块加载
│   ├── models.py                  # 适配器内部中间模型
│   ├── toposphere_bridge.py       # 中间模型 → TopoGraph
│   ├── registry.py                # Parser 动态注册
│   ├── intent_resolver.py         # 意图 → 属性集/适配器过滤
│   ├── graph_builder.py           # 构建 TopoGraph
│   └── adapters/
│       ├── base.py                # CommandParser / SemanticAdapter 抽象
│       └── huawei/                # 华为 CLI 适配器插件集
│           ├── __init__.py
│           ├── _helpers.py        # 设备 source、接口名规范化等共享工具
│           ├── lldp.py            # LLDP 拓扑重建
│           ├── link_aggregation.py# 链路聚合成员状态
│           ├── ospf.py            # OSPF 邻居状态
│           ├── vrrp.py            # VRRP 主备状态
│           └── dhcp.py            # DHCP Snooping 绑定状态
```

### 3.2 核心接口

- `CLIFileLoader`：扫描站点目录，产出 `CommandBlock`（命令 + 回显 + 设备上下文）。
- `CommandParser`：
  - `can_parse(command: str) -> bool`
  - `semantic_concepts -> tuple[str, ...]`：声明自身贡献的语义概念。
  - `parse(command, output, context) -> ParsedEntity`
- `SemanticAdapter`：厂商级适配器，聚合一组 `CommandParser`。
- `AdapterRegistry`：运行时注册与查找 Parser。
- `IntentResolver`：根据下游任务意图返回需要挂载的属性集与适配器提示。
- `GraphBuilder`：消费命令块，调用 Parser，通过 `toposphere_bridge` 写入 `TopoGraph`。

### 3.3 LLDP 拓扑重建策略

1. 每台设备解析 `display lldp neighbor brief`，得到 `(local_intf, remote_device, remote_intf)` 三元组。
2. 以 `device_id`（或 `device_ip`）作为 source，创建本地 `device` 与 `interface` 节点。
3. 以远端 `System Name` 作为 source，创建远端 `device` 与 `interface` 节点。
4. 在本地接口与远端接口之间创建 `connects_to` 边。
5. 同一接口可能被多个 Parser 创建（如 LLDP + LAG + OSPF），由于 ID 确定，TopoGraph 会自动 upsert 并合并 `metadata`。

## 4. 关键设计思路

### 4.1 语义驱动而非模板硬编码

每个 Parser 关注“提取什么语义概念”（`semantic_concepts`）而不是单纯的正则模板。意图解析器按概念过滤，从而在不同运维场景下挂载不同属性集。

### 4.2 插件化与多厂商扩展

- `CommandParser` 是可插拔的最小单元。
- `SemanticAdapter` 按厂商组织 Parser（华为、华三、思科等）。
- 新增厂商只需新增目录并实现 `SemanticAdapter`；注册表通过 `load_builtin()` 自动加载。

### 4.3 输入无关性

当前优先支持华为 CLI，但 CLI 加载器、Parser 接口、图模型均与具体厂商命令解耦。未来接入配置库、SNMP、Telemetry 时，只需新增 Parser 或 Loader。

### 4.4 确定性 ID 与属性合并

- 节点 ID 由 `{source}:{kind}:{identifier}` 确定，保证同一实体跨命令、跨运行稳定。
- 多个 Parser 对同一节点贡献的属性会合并到 `metadata`，实现“一次建点、多源 enriching”。

### 4.5 意图过滤

`GraphBuilder` 根据 `IntentProfile.adapter_hints` 决定是否调用某个 Parser：

- `fault_root_cause`：挂载 DHCP、OSPF 等状态属性。
- `impact_analysis`：挂载 LAG、VRRP 等冗余/成员状态属性。
- `topology` 概念默认包含在所有意图中，确保 LLDP 基础拓扑始终重建。

## 5. 关键流程设计（时序图）

### 5.1 从 CLI 文件到 TopoGraph 的完整流程

```text
┌─────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  User   │     │  CLIFileLoader  │     │ AdapterRegistry  │     │ CommandParser   │
└────┬────┘     └────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
     │                   │                       │                        │
     │ load site         │                       │                        │
     │──────────────────>│                       │                        │
     │                   │ scan device dirs      │                        │
     │                   │──────────────────────>│                        │
     │                   │                       │                        │
     │                   │ split CommonCollectResult by delimiter          │
     │                   │───────────────────────────────────────────────>│
     │                   │                       │                        │
     │                   │ yield CommandBlock    │                        │
     │                   │──────────────────────>│                        │
     │                   │                       │                        │
     │                   │  registry.find_parser(command)                  │
     │                   │──────────────────────>│                        │
     │                   │                       │ return parser            │
     │                   │                       │<────────────────────────│
     │                   │                       │                        │
     │                   │ parser.parse(output, context)                   │
     │                   │───────────────────────────────────────────────>│
     │                   │                       │                        │
     │                   │ return ParsedEntity(nodes, edges)               │
     │                   │<───────────────────────────────────────────────│
     │                   │                       │                        │
     │                   │                       │                        │
     │     ┌─────────────────────────────────────────────────────────────────────────┐
     │     │                           GraphBuilder                                  │
     │     │  - filter by intent.adapter_hints                                         │
     │     │  - convert to toposphere_core.Node / Edge via toposphere_bridge           │
     │     │  - upsert into TopoGraph                                                    │
     │     └─────────────────────────────────────────────────────────────────────────┘
     │                   │                       │                        │
     │                   │ return TopoGraph      │                        │
     │<──────────────────│                       │                        │
     │                   │                       │                        │
```

### 5.2 LLDP 跨设备链路重建示意

```text
Device A (core-sw-01)
  display lldp neighbor brief
    GE0/0/1  --(lldp)-->  GE0/0/2 @ Device B (edge-sw-02)

Device B (edge-sw-02)
  display lldp neighbor brief
    GE0/0/2  --(lldp)-->  GE0/0/1 @ Device A (core-sw-01)

Result TopoGraph:
  Nodes:
    core-sw-01:device:core-sw-01
    core-sw-01:interface:GigabitEthernet0/0/1
    edge-sw-02:device:edge-sw-02
    edge-sw-02:interface:GigabitEthernet0/0/2
  Edges:
    core-sw-01:interface:GigabitEthernet0/0/1  connects_to  edge-sw-02:interface:GigabitEthernet0/0/2
    edge-sw-02:interface:GigabitEthernet0/0/2  connects_to  core-sw-01:interface:GigabitEthernet0/0/1
```

## 6. 扩展指南

新增一种业务解析器（如 BGP 邻居）：

1. 在 `adapters/huawei/` 下新建 `bgp.py`，实现 `CommandParser`。
2. 声明 `semantic_concepts = ("bgp", "bgp_peer_state")`。
3. 在 `HuaweiSemanticAdapter.supported_parsers()` 中注册。
4. 如需按意图过滤，在 `IntentResolver` 中对应意图里加入 `bgp`。
5. 新增 `tests/adapters/test_bgp.py` 覆盖解析逻辑。

新增厂商（如华三）：

1. 创建 `adapters/h3c/` 目录。
2. 实现 `H3CSemanticAdapter` 与对应 Parser。
3. 在 `AdapterRegistry.load_builtin()` 中注册。

## 7. 借鉴 graphify 的设计启示

[graphify](https://github.com/...) 是 2026 年“上下文工程”浪潮中极具代表性的代码知识图谱工具。它的核心主张不是用 LLM 端到端地“理解”代码，而是回到“代码本质是结构化图”的第一性原理：**确定性解析打底、LLM 语义补层、置信度标签兜底**，并以技能/插件形态进入开发者已有的工作流。这一思路对本项目有三条可直接迁移的启示。

### 7.1 确定性优先

网络运维数据（CLI 回显）本身就是高度结构化的命令-输出对。能用正则、AST 或状态机确定性抽取的关系，就不应交给生成式模型。因此：

- 所有 Parser 均基于确定性规则（正则、字符串分割、关键词匹配）实现，不依赖 LLM。
- 新增 `src/topo_semantic_adapter/validate.py` 校验层，对每个 Parser 产出的 `ParsedEntity` 做 schema 检查：节点 ID 唯一、边端点存在、类型/关系非空、`confidence` 合法。
- `GraphBuilder` 默认开启校验（`validate=True`），让不符合规范的数据在入图前即失败，而不是以噪声形式污染 `TopoGraph`。

### 7.2 可解释性内建

graphify 用 `EXTRACTED / INFERRED / AMBIGUOUS` 标签回答“这条关系是事实还是推断”。本项目把同样的思路内建到图里：

- `Edge.confidence` 默认为 `EXTRACTED`，未来对于跨源推断、拓扑补全等场景可标记为 `INFERRED` 或 `AMBIGUOUS`。
- `toposphere_bridge.py` 把 `confidence` 写入 `TopoEdge.metadata`，并在 `Provenance` 中记录来源文件、命令字符串和 Parser 类名。
- `analysis.py` 生成的报告新增“数据来源”章节，列出：
  - 边的置信度分布；
  - 每个 Parser 对图的贡献次数；
  - 单点故障、异常信号等分析结论都可以追溯到原始命令块。

这样，下游 Agent 或工程师不需要“信任黑盒”，而是可以直接验证每条边来自哪台设备的哪条命令、由哪个 Parser 产出、置信度如何。

### 7.3 去用户已经在的地方

graphify 不试图让用户换工具，而是以插件/技能形态寄生在 Claude Code、Cursor、VS Code 等已有环境里。对网络运维场景而言，工程师的日常环境是终端、CMDB、监控平台和 CI 流水线，而不是 Python REPL。因此：

- 新增 CLI 入口 `topo-semantic-adapter <site_dir>`（也支持 `python -m topo_semantic_adapter`）。
- CLI 直接输出 Markdown 报告、Mermaid 图、summary 或 skeleton，可嵌入到 shell 脚本、GitHub Actions、Jenkins 等现有流程。
- 意图过滤（`--intent`）让同一份原始数据在不改代码的情况下服务不同下游任务（故障根因定位、影响范围分析）。

### 7.4 带来的模块变化

| 新增/修改 | 作用 |
|-----------|------|
| `validate.py` | schema 校验，确定性守门 |
| `Edge.confidence` | 事实 / 推断 / 可疑 的可解释标签 |
| `toposphere_bridge.py` | 把 confidence 与 Provenance 写入 `toposphere_core` |
| `analysis.py` | 社区、中心性、单点故障、异常信号 + 可解释报告 |
| `__main__.py` + `pyproject.toml` scripts | 终端原生入口 |

综上，graphify 的启示让本项目从“一个能把 CLI 转成图形的库”进一步变成“**可验证、可解释、可嵌入现有工作流**”的拓扑适配基础设施。

## 8. 推断拓扑重建

CLI 巡检数据往往是局部的：你可能只采集到部分设备，或者某些关系只在一侧被显式报告。为此，本项目在确定性抽取之后增加了一层**推断拓扑重建**，其规则与 graphify 的“INFERRED”置信度一致：

- 所有推断产出的节点/边都标记 `confidence="INFERRED"`；
- 推断逻辑在 `src/topo_semantic_adapter/inference.py` 中实现，作为 `GraphBuilder` 可选的第二趟（`infer=True` 或在 CLI 中加 `--infer`）；
- 推断结果与原图共享同一套 ID 与合并语义，因此可以与抽取结果自然叠加。

### 8.1 当前推断规则

1. **OSPF 邻居拓扑推断**

   `display ospf peer` 只给出了本地接口与对端 Router ID。推断层会为每个对端 Router ID 创建一个 `ospf_router` 节点，并从本地设备创建一条 `peers_with` 边。这样 OSPF 不再只是接口上的元数据，而是真正参与拓扑构图。

2. **LLDP 反向边推断**

   LLDP 在数据层面是单向的：设备 A 报告“我能看到 B”，但 B 的回显里未必包含 A（例如 B 未采集或命令缺失）。如果图中存在 `A -> B` 的 `connects_to` 边而缺少 `B -> A`，推断层会自动补齐反向边，使下游算法看到闭合的物理链路。

### 8.2 与抽取结果的关系

```text
CLI 文件
  -> Parser（EXTRACTED）
    -> validate.py（schema 校验）
      -> TopoGraph（抽取事实）
        -> inference.py（INFERRED）
          -> TopoGraph（完整拓扑）
            -> analysis.py / CLI / export
```

推断层不会修改已抽取的节点/边，只会追加新的 INFERRED 事实。下游分析报告的“数据来源”章节会把 EXTRACTED 与 INFERRED 的数量分别列出，方便用户区分“机器亲口说的”和“系统合理猜的”。

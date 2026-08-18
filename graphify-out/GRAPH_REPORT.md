# Graph Report - 湖北大学配置

## 概要
- 节点数: 9
- 边数: 4
- 密度: 0.1111
- 平均度: 0.8889
- 社区数: 5
- 节点类型分布:
  - device: 2
  - interface: 5
  - link_aggregation_group: 2
- 边类型分布:
  - connects_to: 1
  - member_of: 3

## 数据来源（可解释性）
- 边置信度分布:
  - EXTRACTED: 5
- Parser 贡献次数:
  - LldpNeighborParser: 10
  - OspfNeighborParser: 1
  - VrrpParser: 2
  - DhcpSnoopingParser: 2
  - LinkAggregationParser: 8

## 关键节点（度中心性 Top）
- `Eth-Trunk1`: degree 2
- `GigabitEthernet0/0/1`: degree 1
- `GigabitEthernet0/0/1`: degree 1
- `GigabitEthernet0/0/2`: degree 1
- `GigabitEthernet0/0/2`: degree 1
- `GigabitEthernet0/0/3`: degree 1
- `Eth-Trunk1`: degree 1
- `core-sw-01`: degree 0
- `edge-sw-02`: degree 0

## 社区划分
- Eth-Trunk1: 3 个节点
- GigabitEthernet0/0/1: 2 个节点
- GigabitEthernet0/0/2: 2 个节点
- core-sw-01: 1 个节点
- edge-sw-02: 1 个节点

## 单点故障风险
- 桥接边: 3
  - `core-sw-01:interface:GigabitEthernet0/0/3--member-of--core-sw-01:link_aggregation_group:Eth-Trunk1`
  - `core-sw-01:interface:GigabitEthernet0/0/2--member-of--core-sw-01:link_aggregation_group:Eth-Trunk1`
  - `edge-sw-02:interface:GigabitEthernet0/0/2--member-of--edge-sw-02:link_aggregation_group:Eth-Trunk1`
- 割点: 1
  - `core-sw-01:link_aggregation_group:Eth-Trunk1`

## 异常信号
发现以下异常信号：
- LAG 成员 `core-sw-01:interface:GigabitEthernet0/0/3` 未选中（状态：Unselected）

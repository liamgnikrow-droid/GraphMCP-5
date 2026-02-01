---
uid: "REQUIREMENT-PRINCIPLE__TOPOLOGY_INTEGRITY__NO_ISLAND"
title: "Principle: Topology Integrity (No Islands)"
type: "Requirement"
spec_ref: "['4.2', '4.2.1', '4.2.2']"
project_id: "graphmcp"
status: "Draft"
tags: [graph/requirement, state/draft]
cssclasses: [juggl-node, type-requirement, premium-card]
---
# Principle: Topology Integrity (No Islands)

> [!abstract] Requirement Context
> **ID:** `REQUIREMENT-PRINCIPLE__TOPOLOGY_INTEGRITY__NO_ISLAND` | **Status:** `Draft`

## Description
**Spec Ref:** `[4.2]`

Обеспечение структурной связности графа:
- **Запрет самоудаления:** Агент не может удалить узел, в котором находится.
- **Запрет островов:** При удалении связи проверяется наличие альтернативных путей к узлу.
- Гарантия того, что у каждого узла (кроме Idea) есть хотя бы одна входящая структурная связь.

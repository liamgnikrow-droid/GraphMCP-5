---
uid: "REQUIREMENT-TOOL__LOOK_AROUND__DASHBOARD"
title: "Tool: Look Around (Dashboard)"
type: "Requirement"
spec_ref: "['3.1.1', '7.1']"
project_id: "graphmcp"
status: "Draft"
tags: [graph/requirement, state/draft]
cssclasses: [juggl-node, type-requirement, premium-card]
---
# Tool: Look Around (Dashboard)

> [!abstract] Requirement Context
> **ID:** `REQUIREMENT-TOOL__LOOK_AROUND__DASHBOARD` | **Status:** `Draft`

## Description
Инструмент для получения контекста текущей локации агента (Dashboard).
Должен возвращать:
- Текущий UID и описание локации.
- Список соседей с типами связей.
- Доступные контекстные действия.
- Системные ограничения (Constraints).
- Связанные требования в радиусе 2-х шагов.
- Статистику проекта.

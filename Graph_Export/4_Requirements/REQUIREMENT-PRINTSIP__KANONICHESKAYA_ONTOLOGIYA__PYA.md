---
uid: "REQUIREMENT-PRINTSIP__KANONICHESKAYA_ONTOLOGIYA__PYA"
title: "Принцип: Каноническая Онтология (Пять Типов)"
type: "Requirement"
spec_ref: "['\\\"3.4\\']"
project_id: "graphmcp"
status: "Implemented"
tags: [graph/requirement, state/implemented]
cssclasses: [juggl-node, type-requirement, premium-card]
---
# Принцип: Каноническая Онтология (Пять Типов)

> [!abstract] Requirement Context
> **ID:** `REQUIREMENT-PRINTSIP__KANONICHESKAYA_ONTOLOGIYA__PYA` | **Status:** `Implemented`

## Description
Соблюдение Канонической Пятерки типов связей для обеспечения чистоты семантики графа.
Разрешенные типы: DECOMPOSES, DEPENDS_ON, IMPLEMENTS, RELATES_TO, CONFLICT.
Все устаревшие типы (CONTAINS, IMPORTS, CALLS, SATISFIES, PART_OF) должны быть заменены.

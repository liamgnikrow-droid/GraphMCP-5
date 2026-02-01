---
uid: "REQUIREMENT-PRINCIPLE__CARDINALITY_INTEGRITY__UNIQUE"
title: "Principle: Cardinality Integrity (Unique Core Nodes)"
type: "Requirement"
spec_ref: "['4.3', '4.3.1', '4.3.2']"
project_id: "graphmcp"
status: "Draft"
tags: [graph/requirement, state/draft]
cssclasses: [juggl-node, type-requirement, premium-card]
---
# Principle: Cardinality Integrity (Unique Core Nodes)

> [!abstract] Requirement Context
> **ID:** `REQUIREMENT-PRINCIPLE__CARDINALITY_INTEGRITY__UNIQUE` | **Status:** `Draft`

## Description
**Spec Ref:** `[4.3]`

Контроль количества уникальных узлов:
- Запрет на создание второй Idea в рамках одного проекта.
- Запрет на создание второй Spec.
- Middleware должен отклонять любые попытки `create_concept`, нарушающие эти лимиты.

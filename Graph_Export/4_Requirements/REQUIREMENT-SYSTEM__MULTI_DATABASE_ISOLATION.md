---
uid: "REQUIREMENT-SYSTEM__MULTI_DATABASE_ISOLATION"
title: "System: Multi-Database Isolation"
type: "Requirement"
spec_ref: "['1.1.1']"
project_id: "graphmcp"
status: "Draft"
tags: [graph/requirement, state/draft]
cssclasses: [juggl-node, type-requirement, premium-card]
---
# System: Multi-Database Isolation

> [!abstract] Requirement Context
> **ID:** `REQUIREMENT-SYSTEM__MULTI_DATABASE_ISOLATION` | **Status:** `Draft`

## Description
**Spec Ref:** `[1.1.1]`

Физическое и логическое разделение данных на уровне СУБД:
- **Core БД:** Хранение Мета-Графа (NodeType, Action, Constraint). Доступна только для чтения в Runtime.
- **Project БД:** Хранение данных конкретного проекта. Переключается через `switch_project`.
- Обеспечение невозможности случайной модификации правил из контекста проекта.

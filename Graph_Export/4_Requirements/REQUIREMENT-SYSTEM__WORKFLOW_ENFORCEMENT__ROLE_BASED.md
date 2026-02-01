---
uid: "REQUIREMENT-SYSTEM__WORKFLOW_ENFORCEMENT__ROLE_BASED"
title: "System: Workflow Enforcement (Role-Based Access)"
type: "Requirement"
spec_ref: "['1.5']"
project_id: "graphmcp"
status: "Draft"
tags: [graph/requirement, state/draft]
cssclasses: [juggl-node, type-requirement, premium-card]
---
# System: Workflow Enforcement (Role-Based Access)

> [!abstract] Requirement Context
> **ID:** `REQUIREMENT-SYSTEM__WORKFLOW_ENFORCEMENT__ROLE_BASED` | **Status:** `Draft`

## Description
**Spec Ref:** `[1.5]`

Механизм контроля разрешений на основе роли:
- **Architect:** Блокировка записи в файлы и системных команд.
- **Builder:** Блокировка создания новых Spec/Requirement (только расширение через Task).
- **Auditor:** Режим "только чтение" для всех модифицирующих инструментов.
- Валидация каждого вызова на соответствие активному режиму.

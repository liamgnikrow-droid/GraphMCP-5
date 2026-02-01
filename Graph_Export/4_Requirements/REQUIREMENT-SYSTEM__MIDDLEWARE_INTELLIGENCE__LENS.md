---
uid: "REQUIREMENT-SYSTEM__MIDDLEWARE_INTELLIGENCE__LENS"
title: "System: Middleware Intelligence (Lens)"
type: "Requirement"
spec_ref: "['1.6', '4.5.3']"
project_id: "graphmcp"
status: "Draft"
tags: [graph/requirement, state/draft]
cssclasses: [juggl-node, type-requirement, premium-card]
---
# System: Middleware Intelligence (Lens)

> [!abstract] Requirement Context
> **ID:** `REQUIREMENT-SYSTEM__MIDDLEWARE_INTELLIGENCE__LENS` | **Status:** `Draft`

## Description
**Spec Ref:** `[1.6, 4.5.3]`

Реализация логики Middleware как интеллектуального фильтра:
- Динамическое формирование списка инструментов (`list_tools`) на основе текущей локации и прав Агента.
- Выполнение проверок (Validators) перед каждым действием.
- Интеграция декларативных правил Мета-Графа с процедурными примитивами Python.

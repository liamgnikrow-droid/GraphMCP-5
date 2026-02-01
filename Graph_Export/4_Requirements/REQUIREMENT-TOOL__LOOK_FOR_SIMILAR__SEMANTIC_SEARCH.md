---
uid: "REQUIREMENT-TOOL__LOOK_FOR_SIMILAR__SEMANTIC_SEARCH"
title: "Tool: Look For Similar (Semantic Search)"
type: "Requirement"
spec_ref: "[\"3.1.3\", \"1.3\"]"
project_id: "graphmcp"
status: "Implemented"
tags: [graph/requirement, state/implemented]
cssclasses: [juggl-node, type-requirement, premium-card]
---
# Tool: Look For Similar (Semantic Search)

> [!abstract] Requirement Context
> **ID:** `REQUIREMENT-TOOL__LOOK_FOR_SIMILAR__SEMANTIC_SEARCH` | **Status:** `Implemented`

## Description
Семантический поиск по графу (Semantic Search).
Функциональные требования:
- Поиск на основе эмбеддингов (all-MiniLM-L6-v2).
- Возврат списка узлов с оценкой схожести (Score).
- Переиндексация при изменениях.

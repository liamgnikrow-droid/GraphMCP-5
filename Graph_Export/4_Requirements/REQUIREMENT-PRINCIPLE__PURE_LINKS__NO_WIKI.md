---
uid: "REQUIREMENT-PRINCIPLE__PURE_LINKS__NO_WIKI"
title: "Principle: Pure Links (No Wiki)"
type: "Requirement"
spec_ref: "['4.1']"
project_id: "graphmcp"
status: "Draft"
tags: [graph/requirement, state/draft]
cssclasses: [juggl-node, type-requirement, premium-card]
---
# Principle: Pure Links (No Wiki)

> [!abstract] Requirement Context
> **ID:** `REQUIREMENT-PRINCIPLE__PURE_LINKS__NO_WIKI` | **Status:** `Draft`

## Description
Принципиальный запрет на использование текстовых Wiki-ссылок в двойных квадратных скобках.
Функциональные требования:
- Валидация контента на отсутствие зарезервированных символов ссылок.
- Все связи между узлами в базе знаний должны быть структурными (через link_nodes).
- Это обеспечивает целостность графа и возможность автоматического анализа.

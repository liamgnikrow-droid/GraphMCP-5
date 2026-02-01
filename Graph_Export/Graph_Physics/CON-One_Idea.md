---
uid: "CON-One_Idea"
title: "CON-One_Idea"
type: "Constraint"
error_message: "В проекте может быть только одна Idea. Idea уже существует."
rule_name: "Закон Кардинальности Idea"
function: "node_count"
threshold: 1
operator: ">="
target_label: "Idea"
tags: [graph/constraint, state/draft]
cssclasses: [juggl-node, type-constraint, premium-card]
---
# CON-One_Idea

> [!abstract] Constraint Context
> **ID:** `CON-One_Idea` | **Status:** `Draft`

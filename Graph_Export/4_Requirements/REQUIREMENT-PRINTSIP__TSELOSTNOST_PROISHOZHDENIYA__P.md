---
uid: "REQUIREMENT-PRINTSIP__TSELOSTNOST_PROISHOZHDENIYA__P"
title: "Принцип: Целостность Происхождения (Provenance)"
type: "Requirement"
spec_ref: "['\\\"3.5\\']"
project_id: "graphmcp"
status: "Implemented"
tags: [graph/requirement, state/implemented]
cssclasses: [juggl-node, type-requirement, premium-card]
---
# Принцип: Целостность Происхождения (Provenance)

> [!abstract] Requirement Context
> **ID:** `REQUIREMENT-PRINTSIP__TSELOSTNOST_PROISHOZHDENIYA__P` | **Status:** `Implemented`

## Description
Соблюдение правил происхождения связей. Каждая связь должна создаваться только разрешенным инструментом или ролью.
Это гарантирует, что структура кода (File->Class->Func) управляется инструментом map_codebase, а логические связи требований — инструментом link_nodes или Архитектором.

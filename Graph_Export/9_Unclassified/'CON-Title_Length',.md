---
uid: "'CON-Title_Length',"
title: "PROPOSAL-ADD_CONSTRAINT-20260128_202820"
type: "Unknown"
CREATE (c)-[: "RESTRICTS]->(a);"
error_message: "'Заголовок не должен превышать 100 символов'"
MATCH (c: "Constraint {uid: 'CON-Title_Length'}), (a:Action {uid: 'ACT-create_req'})"
CREATE (: "Constraint {"
rule_name: "'Закон Длины Заголовка',"
change_type: "add_constraint"
rationale: "Нужно ограничить длину заголовков до 100 символов"
created_by: "agent"
cypher_script: ""
function: "'string_length',"
// Add new Constraint: "CON-Title_Length"
details: "{\\"uid\\": \\"CON-Title_Length\\", \\"rule_name\\": \\"Закон Длины Заголовка\\", \\"function\\": \\"string_length\\", \\"error_message\\": \\"Заголовок не должен превышать 100 символов\\", \\"restricts\\": [\\"ACT-create_spec\\", \\"ACT-create_req\\"]}"
status: "pending"
tags: [graph/unknown, state/pending]
cssclasses: [juggl-node, type-unknown, premium-card]
---
# PROPOSAL-ADD_CONSTRAINT-20260128_202820

> [!abstract] Unknown Context
> **ID:** `'CON-Title_Length',` | **Status:** `pending`

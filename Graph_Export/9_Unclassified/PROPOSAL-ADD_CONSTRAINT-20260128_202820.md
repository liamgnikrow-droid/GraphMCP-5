---
uid: "PROPOSAL-ADD_CONSTRAINT-20260128_202820"
title: "PROPOSAL-ADD_CONSTRAINT-20260128_202820"
type: "Unknown"
change_type: "add_constraint"
details: "{\"uid\": \"CON-Title_Length\", \"rule_name\": \"Закон Длины Заголовка\", \"function\": \"string_length\", \"error_message\": \"Заголовок не должен превышать 100 символов\", \"restricts\": [\"ACT-create_spec\", \"ACT-create_req\"]}"
cypher_script: "
// Add new Constraint: CON-Title_Length
CREATE (:Constraint {
    uid: 'CON-Title_Length',
    rule_name: 'Закон Длины Заголовка',
    function: 'string_length',
    error_message: 'Заголовок не должен превышать 100 символов'
});

// Link to Actions (specify in details.restricts)

MATCH (c:Constraint {uid: 'CON-Title_Length'}), (a:Action {uid: 'ACT-create_spec'})
CREATE (c)-[:RESTRICTS]->(a);

MATCH (c:Constraint {uid: 'CON-Title_Length'}), (a:Action {uid: 'ACT-create_req'})
CREATE (c)-[:RESTRICTS]->(a);
"
rationale: "Нужно ограничить длину заголовков до 100 символов"
created_by: "agent"
status: "pending"
tags: [graph/unknown, state/pending]
cssclasses: [juggl-node, type-unknown, premium-card]
---
# PROPOSAL-ADD_CONSTRAINT-20260128_202820

> [!abstract] Unknown Context
> **ID:** `PROPOSAL-ADD_CONSTRAINT-20260128_202820` | **Status:** `pending`

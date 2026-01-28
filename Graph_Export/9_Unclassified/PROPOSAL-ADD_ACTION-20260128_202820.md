---
uid: "PROPOSAL-ADD_ACTION-20260128_202820"
title: "PROPOSAL-ADD_ACTION-20260128_202820"
type: "Unknown"
change_type: "add_action"
details: "{\"uid\": \"ACT-create_epic\", \"tool_name\": \"create_concept\", \"target_type\": \"Epic\", \"scope\": \"contextual\", \"allowed_from\": [\"Spec\"]}"
cypher_script: "
// Add new Action: ACT-create_epic
CREATE (:Action {
    uid: 'ACT-create_epic',
    tool_name: 'create_concept',
    scope: 'contextual', target_type: 'Epic'
});

// Link to NodeType (specify in details.allowed_from)

MATCH (nt:NodeType {name: 'Spec'}), (a:Action {uid: 'ACT-create_epic'})
CREATE (nt)-[:CAN_PERFORM]->(a);
"
rationale: "Нужна возможность создавать Epic из Spec"
created_by: "agent"
status: "pending"
tags: [graph/unknown, state/pending]
cssclasses: [juggl-node, type-unknown, premium-card]
---
# PROPOSAL-ADD_ACTION-20260128_202820

> [!abstract] Unknown Context
> **ID:** `PROPOSAL-ADD_ACTION-20260128_202820` | **Status:** `pending`

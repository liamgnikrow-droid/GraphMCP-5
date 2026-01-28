---
uid: "PROPOSAL-ADD_NODE_TYPE-20260128_202819"
title: "PROPOSAL-ADD_NODE_TYPE-20260128_202819"
type: "Unknown"
change_type: "add_node_type"
details: "{\"name\": \"Epic\", \"description\": \"Крупная функциональная единица, объединяющая несколько Requirement\", \"max_count\": null}"
cypher_script: "
// Add new NodeType: Epic
CREATE (:NodeType {
    name: 'Epic',
    description: 'Крупная функциональная единица, объединяющая несколько Requirement',
    max_count: None
});
"
rationale: "Нужен узел Epic для группировки больших фич проекта"
created_by: "agent"
status: "pending"
tags: [graph/unknown, state/pending]
cssclasses: [juggl-node, type-unknown, premium-card]
---
# PROPOSAL-ADD_NODE_TYPE-20260128_202819

> [!abstract] Unknown Context
> **ID:** `PROPOSAL-ADD_NODE_TYPE-20260128_202819` | **Status:** `pending`

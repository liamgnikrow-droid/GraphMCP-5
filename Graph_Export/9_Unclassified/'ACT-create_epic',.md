---
uid: "'ACT-create_epic',"
title: "PROPOSAL-ADD_ACTION-20260128_202820"
type: "Unknown"
tool_name: "'create_concept',"
CREATE (nt)-[: "CAN_PERFORM]->(a);"
// Add new Action: "ACT-create_epic"
CREATE (: "Action {"
change_type: "add_action"
rationale: "Нужна возможность создавать Epic из Spec"
created_by: "agent"
cypher_script: ""
MATCH (nt: "NodeType {name: 'Spec'}), (a:Action {uid: 'ACT-create_epic'})"
scope: "'contextual', target_type: 'Epic'"
details: "{\\"uid\\": \\"ACT-create_epic\\", \\"tool_name\\": \\"create_concept\\", \\"target_type\\": \\"Epic\\", \\"scope\\": \\"contextual\\", \\"allowed_from\\": [\\"Spec\\"]}"
status: "pending"
tags: [graph/unknown, state/pending]
cssclasses: [juggl-node, type-unknown, premium-card]
---
# PROPOSAL-ADD_ACTION-20260128_202820

> [!abstract] Unknown Context
> **ID:** `'ACT-create_epic',` | **Status:** `pending`

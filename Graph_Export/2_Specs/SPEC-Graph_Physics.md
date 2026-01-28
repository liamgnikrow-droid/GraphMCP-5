---
uid: "SPEC-Graph_Physics"
title: "SPEC-Graph_Physics"
type: "Spec"
status: "unknown"
tags: [graph/spec, state/unknown]
cssclasses: [juggl-node, type-spec, premium-card]
decomposes:
  - "[[REQ-YAML_LINKS_ONLY]]"
  - "[[REQUIREMENT-TRE_OVANIE__EZOPASNOSTI_API]]"
---
# SPEC-Graph_Physics

> [!abstract] Spec Context
> **ID:** `SPEC-Graph_Physics` | **Status:** `unknown`

## Description
> This node defines the Allowed Transitions and Tool Availability based on the Agent's Location.

## Content
# Graph Physics Definition (The Laws)

> This node defines the Allowed Transitions and Tool Availability based on the Agent's Location.

## Transitions (The "Doors")

| Source Type | Target Type | Action Name | Required Tool |
| :--- | :--- | :--- | :--- |
| **Idea** | **Spec** | `decompose` | `create_concept(type='Spec')` |
| **Idea** | **Task** | `assign` | `create_concept(type='Task')` |
| **Spec** | **Requirement** | `refine` | `create_concept(type='Requirement')` |
| **Spec** | **Task** | `assign` | `create_concept(type='Task')` |
| **Requirement** | **File** | `implement` | `create_concept(type='File')` |
| **Requirement** | **Task** | `assign` | `create_concept(type='Task')` |
| **Task** | **Idea** | `brainstorm` | `create_concept(type='Idea')` |

## Constraints (The "Walls")

### Global Tools
*   `look_around`
*   `move_to`
*   `read_graph`

### Contextual Tools

#### Context: `(:Idea)`
**Allowed:**
*   `create_concept` (Only for `Spec`)
*   `link_nodes` (Only `DEPENDS_ON` between Ideas)

#### Context: `(:Spec)`
**Allowed:**
*   `create_concept` (Only for `Requirement`)
*   `link_nodes` (Only `DECOMPOSES` to Req)

#### Context: `(:Requirement)`
**Allowed:**
*   `create_concept` (Only for `File` stub)

#### Context: `(:File)`
**Allowed:**
*   `read_content`
*   `edit_content` (The "Holy Grail" - write access)
*   `grep_search`

#### Context: `(:Task)`
**Allowed:**
*   `submit_plan`
*   `finish_task`

---

## Evolution Protocol
To modify these rules, the Agent must be in **Genesis Mode** or use the `propose_amendment` tool (Future).

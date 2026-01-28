# Architecture: Graph-Native Agent (Law of the Node)

> "Agent is not in Docker. Agent is in the Graph."

**User Vision:** The Graph is the Environment ("Physics"). The Agent "swims" inside it. If the structure (Requirement) doesn't exist, the "space" for action (Code) does not exist.

**Core Concept: Locality & Contextual Constraints**
Instead of a global "God Mode" agent verified by a Gatekeeper, we restrict the agent to a **Single Point of Presence (Focus)**.

## 1. The "Agent Focus" Pointer
*   The system maintains a standard pointer: `(:Agent {uid: "ANTIGRAVITY"})-[:LOCATED_AT]->(:Node)`
*   The Agent **cannot** see the whole project.
*   The Agent **can only** see:
    1.  The Node it is currently located at.
    2.  The direct neighbors of that Node.

## 2. Dynamic Tooling (Contextual Physics)
The list of available tools is no longer static (`tools.py`). It is generated dynamically based on the `[:LOCATED_AT]` node type.

| Current Location | Available Actions ("Physics") | Impossible Actions |
| :--- | :--- | :--- |
| **(:Idea)** | `decompose_to_spec()` | Write code, Run tests, Edit files |
| **(:Spec)** | `define_requirement()` | Write code, Edit files |
| **(:Requirement)** | `create_implementation_stub()` (Creates File Node) | Edit file content directly |
| **(:File)** | `read_content()`, `edit_content()` | Create requirements, Define specs |
| **(:Task)** | `move_to(target)`, `read_context()` | Edit code (unless moved to File) |

**Result:** To write code for "Login", the agent **MUST**:
1.  Navigate to `Idea`.
2.  Decompose to `Spec`.
3.  Move to `Spec`.
4.  Define `REQ-Login`.
5.  Move to `REQ-Login`.
6.  Create `File:login.py`.
7.  Move to `File:login.py`.
8.  *Only now* `edit_content` becomes available.

**Why this solves the problem:**
The agent literally **cannot** write "half a code" without "all the spec", because it cannot reach the File-layer "room" without building the Spec-layer "corridor".

## 3. The "Graph Shell" (Interaction Protocol)

The User doesn't just chat. The User manipulates the Graph, and the Agent inhabits it.

**New Toolset (The Only Tools):**
1.  **`look_around()`**: Returns content of current Node + list of output links (Doors).
2.  **`move_to(link_id)`**: Traverses a link. Updates `[:LOCATED_AT]`.
3.  **`act_on_node(action, params)`**: Executes a context-specific action (e.g., "edit" if at File, "decompose" if at Spec).

## 4. Implementation Strategy (The Pivot)

### Phase 1: The Locality Manager (`graph_nav.py`)
*   Create `ensure_agent_node()`: Spawn the Agent node.
*   Implement `move_to(uid)`: Verifies link exists, updates pointer.
*   Implement `get_context()`: Returns the local "Room" description.

### Phase 2: Dynamic Tool Dispatcher
*   Rewrite `tools.py` to be a facade.
*   `list_tools()` now queries the Graph: "Where is Agent? At `(:File)`. Return `['edit_content']`."

### Phase 3: The "Void" (Null Space)
*   Delete `write_to_file` global tool.
*   Delete `read_file` global tool.
*   Global tools remaining: `look_around`, `move_to`.

## User Review Required
This converts the Agent from a "Wizard" (can do anything) to a "Robot in a Maze" (can only interact with what's in front of it).

*   **Risk:** Navigation overhead. The agent might get "lost" or annoyed by needing 5 hops to fix a typo.
*   **Mitigation:** `teleport()` capability for "Task" nodes, but strictly blocked for "Creative" nodes.

## Next Steps
1.  Define the **Node-Tool Matrix** (Which node type grants which tool).
2.  Implement `graph_nav.py`.
3.  Lock down the `tools.py` list.

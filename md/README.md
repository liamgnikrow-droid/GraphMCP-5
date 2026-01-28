# GraphMCP-5: Graph-Native Agent (Genesis)

Welcome to the new era.
This project implements the **Graph-Physics Architecture**.

## Connection
- **Workspace:** `/Users/yuri/Documents/PROJECTS/AI-Infrastructure/GraphMCP-5`
- **Neo4j:** `bolt://localhost:7687` (User: neo4j, Pass: password)
- **MCP Server:** Running in Docker (`graphmcp-core`), exposes SSE on port 8000.

## The Law
The agent's capabilities are defined in:
`Graph_Physics/SPEC-Graph_Physics.md`

## Current State
- **Genesis Mode:** The agent works in a limited "Bootstrapping" capability set.
- **Available Tools:** `look_around`, `move_to`, `read_graph`.
- **Goal:** Create the Semantic Hierarchy (`Idea -> Spec -> Requirement`).

## How to Start
1. Open this folder in VS Code.
2. Connect your MCP Client (Claude/Inspector) to `http://localhost:8000/sse`.
3. Ask the Agent: "Where are you?"

from mcp.server import Server
import mcp.types as types
from db_config import get_driver, WORKSPACE_ROOT
from graph_sync import GraphSync
import os
import re
import sys

# Initialize MCP Server
mcp = Server("graph-native-core")
sync_tool = GraphSync()

# --- EMBEDDING MANAGER (LIGHTWEIGHT) ---
class EmbeddingManager:
    _instance = None
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print("🧠 Loading Embedding Model (all-MiniLM-L6-v2)...", file=sys.stderr)
                cls._model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"❌ Error loading model: {e}", file=sys.stderr)
                return None
        return cls._model

    @classmethod
    def get_embedding(cls, text):
        model = cls.get_model()
        if not model: return None
        return model.encode(text).tolist()

emb_manager = EmbeddingManager()

# --- MIDDLEWARE: THE LENS (META-GRAPH IMPLEMENTATION) ---
def get_allowed_tool_names(context_node_type):
    """
    Reads allowed tools from Meta-Graph in Neo4j.
    Returns tools that are either:
    1. Global (scope='global')
    2. Contextual and linked via (:NodeType {name: context_node_type})-[:CAN_PERFORM]->(:Action)
    """
    driver = get_driver()
    if not driver: 
        return ["look_around"]  # Emergency Mode
    
    # 1. Get Global Tools (always available)
    global_query = """
    MATCH (a:Action {scope: 'global'})
    RETURN a.tool_name as tool_name
    """
    global_tools = set()
    try:
        records, _, _ = driver.execute_query(global_query, database_="neo4j")
        global_tools = {r["tool_name"] for r in records}
    except Exception as e:
        print(f"⚠️  Failed to fetch global tools: {e}")
        global_tools = {"look_around"}  # Absolute minimum
    
    # 2. Get Contextual Tools (specific to current NodeType)
    contextual_query = """
    MATCH (nt:NodeType {name: $node_type})-[:CAN_PERFORM]->(a:Action {scope: 'contextual'})
    RETURN a.tool_name as tool_name
    """
    contextual_tools = set()
    try:
        records, _, _ = driver.execute_query(
            contextual_query, 
            {"node_type": context_node_type}, 
            database_="neo4j"
        )
        contextual_tools = {r["tool_name"] for r in records}
    except Exception as e:
        print(f"⚠️  Failed to fetch contextual tools for {context_node_type}: {e}")
    
    # 3. Combine
    allowed_tools = global_tools | contextual_tools
    
    return list(allowed_tools)

def get_node_type(uid):
    """Refactored helper to get node type by UID"""
    driver = get_driver()
    if not driver: return "Idea"
    
    query = "MATCH (n {uid: $uid}) RETURN labels(n) as labels"
    records, _, _ = driver.execute_query(query, {"uid": uid}, database_="neo4j")
    
    if records and records[0]['labels']:
         return records[0]['labels'][0]
    return "Idea"

def get_agent_location():
    """
    Returns the UID of the node where the Agent is currently located.
    Checks for persisted (:Agent)-[:LOCATED_AT]->(node) relationship.
    Defaults to 'IDEA-Genesis' if no location is found.
    """
    driver = get_driver()
    if not driver: return "IDEA-Genesis" # Emergency fallback

    # 1. Try to find LOCATED_AT relationship for yuri_agent
    query = "MATCH (:Agent {id: 'yuri_agent'})-[:LOCATED_AT]->(n) RETURN n.uid as uid"
    records, _, _ = driver.execute_query(query, database_="neo4j")
    
    if records:
        return records[0]['uid']
        
    # 2. Fallback: Agent might be lost or newborn. Default to Genesis.
    return "IDEA-Genesis"

# --- TOOL IMPLEMENTATIONS ---
async def tool_look_around(arguments: dict) -> list[types.TextContent]:
    driver = get_driver()
    if not driver:
         return [types.TextContent(type="text", text="Error: No Backend Connection")]
         
    loc_uid = get_agent_location()
    
    query = """
    MATCH (n {uid: $uid})
    OPTIONAL MATCH (n)-[r]->(target)
    RETURN n, collect({type: type(r), uid: target.uid, title: target.title}) as neighbors
    """
    records, _, _ = driver.execute_query(query, {"uid": loc_uid}, database_="neo4j")
    
    if not records:
         if loc_uid == "IDEA-Genesis":
             driver.execute_query("MERGE (:Idea {uid: 'IDEA-Genesis', title: 'Genesis Point'})", database_="neo4j")
             return [types.TextContent(type="text", text="Genesis Node Created. You are at (:Idea {uid: 'IDEA-Genesis'}). Neighbors: []")]
         return [types.TextContent(type="text", text=f"Error: You are lost. Location {loc_uid} not found.")]
    
    node = records[0]['n']
    neighbors = records[0]['neighbors']
    
    return [types.TextContent(
        type="text",
        text=f"You are at (:{list(node.labels)[0]} {{uid: '{node['uid']}', title: '{node.get('title')}'}})\nNeighbors: {neighbors}"
    )]

async def tool_move_to(arguments: dict) -> list[types.TextContent]:
    target_uid = arguments.get("target_uid")
    driver = get_driver()
    if not driver: return [types.TextContent(type="text", text="Error: No Backend Connection")]
    
    # 1. Check if target exists
    check_query = "MATCH (n {uid: $uid}) RETURN n.title as title, labels(n) as labels"
    records, _, _ = driver.execute_query(check_query, {"uid": target_uid}, database_="neo4j")
    
    if not records:
         return [types.TextContent(type="text", text=f"Error: Target node {target_uid} does not exist.")]
         
    target_title = records[0]['title']
    target_type = records[0]['labels'][0]

    # 2. Move Agent (Atomic Transaction)
    move_query = """
    MERGE (a:Agent {id: 'yuri_agent'})
    WITH a
    MATCH (target {uid: $uid})
    OPTIONAL MATCH (a)-[r:LOCATED_AT]->(old)
    DELETE r
    CREATE (a)-[:LOCATED_AT]->(target)
    """
    try:
        driver.execute_query(move_query, {"uid": target_uid}, database_="neo4j")
        return [types.TextContent(
            type="text",
            text=f"Agent moved to {target_uid} ({target_type}: {target_title})"
        )]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error moving agent: {e}")]

def validate_physics_constraints(text: str):
    """
    Enforces 'Hard Physics' rules on content.
    For example: REQ-YAML_LINKS_ONLY forbids wiki-links in description/title.
    """
    if not text:
        return
    
    # Check for forbidden wiki-links [[...]]
    if "[[" in text or "]]" in text:
        raise ValueError("PHYSICS ERROR: Wiki-links [[target]] are FORBIDDEN in content. Links must be established ONLY via YAML properties and link_nodes tool.")

    # Check for Language Constraints (REQ-Russian_Language)
    # Heuristic: At least 25% of characters (excluding spaces) must be Cyrillic.
    # This allows for English technical terms but enforces Russian as the primary language.
    clean_text = re.sub(r'\s+', '', text)
    if not clean_text: return
    
    cyrillic_count = len(re.findall(r'[а-яА-ЯёЁ]', clean_text))
    if cyrillic_count / len(clean_text) < 0.25:
        raise ValueError("PHYSICS ERROR: Language Violation. Content must be primarily in Russian (REQ-Russian_Language).")

async def tool_create_concept(arguments: dict) -> list[types.TextContent]:
    """
    Creates a new high-level node (Spec, Req, etc.) and syncs to Markdown.
    Used by Agent to build the graph.
    """
    c_type = arguments.get("type")
    title = arguments.get("title")
    desc = arguments.get("description", "")
    
    # 1. ENFORCE HARD PHYSICS
    try:
        validate_physics_constraints(title)
        validate_physics_constraints(desc)
    except ValueError as e:
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]
    
    # Transliteration for Safe UIDs
    def transliterate(text):
        mapping = {
            'а': 'a', 'b': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
            'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'YO',
            'Ж': 'ZH', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'TS', 'Ч': 'CH', 'Ш': 'SH', 'Щ': 'SCH', 'Ъ': '',
            'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'YU', 'Я': 'YA',
        }
        return "".join([mapping.get(char, char) for char in text])

    transliterated_title = transliterate(title)
    safe_title = re.sub(r'[^a-zA-Z0-9]', '_', transliterated_title).strip('_').upper()
    uid = f"{c_type.upper()}-{safe_title[:40]}"
    
    # 2. Check Allowed Types (Hardcoded Enum + Logic)
    # The middleware checked if 'create_concept' is allowed generally.
    # Ideally we should check specific Transition here too, but for now we rely on Physics.
    if c_type not in ["Spec", "Requirement", "Task", "Idea", "Domain"]:
         return [types.TextContent(type="text", text=f"Error: Invalid concept type '{c_type}'. Epic is DEAD.")]

    driver = get_driver()
    parent_uid = get_agent_location() # "IDEA-Genesis"
    
    query_create = f"""
    MATCH (parent {{uid: $parent_uid}})
    MERGE (n:{c_type} {{uid: $uid}})
    SET n.title = $title,
        n.description = $desc,
        n.status = 'Draft',
        n.created_at = datetime()
    MERGE (parent)-[:DECOMPOSES]->(n)
    RETURN n.uid as uid
    """
    try:
        # Generate Semantic Embedding
        semantic_text = f"{title} {desc}"
        embedding = emb_manager.get_embedding(semantic_text)

        driver.execute_query(query_create, {
            "parent_uid": parent_uid,
            "uid": uid,
            "title": title,
            "desc": desc
        }, database_="neo4j")
        
        # Save Embedding if successful
        if embedding:
            driver.execute_query(
                "MATCH (n {uid: $uid}) SET n.embedding = $emb",
                {"uid": uid, "emb": embedding},
                database_="neo4j"
            )

        # Sync new node AND parent (because parent now has a new connection)
        file_path = sync_tool.sync_node(uid, sync_connected=True)
        
        return [types.TextContent(
            type="text",
            text=f"✅ Created {c_type} {uid} and linked to {parent_uid}.\nSynced to Obsidian: {file_path}"
        )]
        
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error creating concept: {e}")]

@mcp.list_tools()
async def list_tools() -> list[types.Tool]:
    """Returns all available tools. Enforcement happens in call_tool."""
    return [
        types.Tool(
            name="look_around", 
            description="Returns the current Agent Location and neighbors.",
            inputSchema={"type": "object"}
        ),
        types.Tool(
            name="move_to",
            description="Moves the Agent to a neighbor node.",
            inputSchema={"type": "object", "properties": {"target_uid": {"type": "string"}}, "required": ["target_uid"]}
        ),
        types.Tool(
            name="create_concept",
            description="Creates a new child node (Spec, Requirement, etc). ALL CONTENT (title, description) MUST BE IN RUSSIAN.",
            inputSchema={
                "type": "object", 
                "properties": {
                    "type": {"type": "string", "enum": ["Spec", "Requirement", "Task", "Idea", "Domain"]}, 
                    "title": {"type": "string", "description": "Title in Russian"},
                    "description": {"type": "string", "description": "Description in Russian"}
                },
                "required": ["type", "title"]
            }
        ),
        types.Tool(
            name="look_for_similar",
            description="Finds semantically similar nodes across the entire graph.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query in Russian or English"}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="sync_graph",
            description="Forces a full synchronization of the Neo4j graph into Obsidian Markdown files.",
            inputSchema={"type": "object"}
        ),
        types.Tool(
            name="link_nodes",
            description="Creates a relationship between two existing nodes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_uid": {"type": "string"},
                    "target_uid": {"type": "string"},
                    "rel_type": {"type": "string", "enum": ["IMPLEMENTS", "DECOMPOSES", "DEPENDS_ON", "CONFLICT", "IMPORTS"]}
                },
                "required": ["source_uid", "target_uid", "rel_type"]
            }
        ),
        types.Tool(
            name="delete_node",
            description="Permanently deletes a node from the graph and its file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "uid": {"type": "string", "description": "UID of the node to delete"}
                },
                "required": ["uid"]
            }
        ),
        types.Tool(
            name="delete_link",
            description="Removes a specific relationship between two nodes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_uid": {"type": "string"},
                    "target_uid": {"type": "string"},
                    "rel_type": {"type": "string"}
                },
                "required": ["source_uid", "target_uid", "rel_type"]
            }
        ),
        types.Tool(
            name="register_task",
            description="Registers a new Task from Human's chat message. ALL CONTENT MUST BE IN RUSSIAN.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title in Russian"},
                    "description": {"type": "string", "description": "Task description in Russian"}
                },
                "required": ["title"]
            }
        )
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    # --- MIDDLEWARE CHECK ---
    loc_uid = get_agent_location()
    current_node_type = get_node_type(loc_uid)
    allowed = get_allowed_tool_names(current_node_type)
    
    if name not in allowed:
         return [types.TextContent(
             type="text", 
             text=f"❌ PHYSICS ERROR: Tool '{name}' is FORBIDDEN when you are at a node of type '{current_node_type}'.\nLocation: {loc_uid}"
         )]

    # --- DISPATCH ---
    if name == "look_around": return await tool_look_around(arguments)
    elif name == "move_to": return await tool_move_to(arguments)
    elif name == "create_concept": return await tool_create_concept(arguments)
    elif name == "look_for_similar": return await tool_look_for_similar(arguments)
    elif name == "sync_graph": return await tool_sync_graph(arguments)
    elif name == "link_nodes": return await tool_link_nodes(arguments)
    elif name == "delete_node": return await tool_delete_node(arguments)
    elif name == "delete_link": return await tool_delete_link(arguments)
    elif name == "register_task": return await tool_register_task(arguments)
    else: return [types.TextContent(type="text", text=f"Error: Unknown tool {name}")]

async def tool_delete_node(arguments: dict) -> list[types.TextContent]:
    uid = arguments.get("uid")
    if not uid: return [types.TextContent(type="text", text="Error: UID is required")]
    
    # Check if this is the Agent's current location
    if uid == get_agent_location():
        return [types.TextContent(type="text", text="❌ PHYSICS error: You cannot delete the node you are currently standing on.")]

    driver = get_driver()
    
    # 1. Structural Integrity Check: Does this node have children (outgoing dependencies)?
    # We only care about semantic links like DECOMPOSES, IMPLEMENTS, DEPENDS_ON.
    # If it is a leaf (no children), it is safe to delete.
    check_children_query = """
    MATCH (n {uid: $uid})-[r]->(child)
    RETURN count(r) as child_count
    """
    check_recs, _, _ = driver.execute_query(check_children_query, {"uid": uid}, database_="neo4j")
    if check_recs and check_recs[0]['child_count'] > 0:
        return [types.TextContent(type="text", text=f"❌ PHYSICS ERROR (STRUCTURAL INTEGRITY): Node {uid} acts as a parent for {check_recs[0]['child_count']} other nodes. You must re-link or delete the children first.")]

    # DETACH DELETE removes all relationships as well
    query = "MATCH (n {uid: $uid}) DETACH DELETE n RETURN count(n) as count"
    try:
        records, _, _ = driver.execute_query(query, {"uid": uid}, database_="neo4j")
        if records[0]['count'] == 0:
            return [types.TextContent(type="text", text=f"⚠️ Node {uid} not found in database.")]
        
        # Sync: remove file
        sync_tool.delete_node(uid)
        
        return [types.TextContent(type="text", text=f"✅ Node {uid} has been PERMANENTLY DELETED.")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error deleting node: {e}")]

async def tool_delete_link(arguments: dict) -> list[types.TextContent]:
    source = arguments.get("source_uid")
    target = arguments.get("target_uid")
    rel_type = arguments.get("rel_type")
    
    driver = get_driver()
    
    # 1. Structural Integrity Check: Is this the ONLY incoming link for the target?
    # If we cut this, does the target become an island?
    check_island_query = """
    MATCH (t {uid: $target})<-[r]-(any_parent)
    RETURN count(r) as incoming_count
    """
    check_recs, _, _ = driver.execute_query(check_island_query, {"target": target}, database_="neo4j")
    
    if check_recs and check_recs[0]['incoming_count'] <= 1:
         return [types.TextContent(type="text", text=f"❌ PHYSICS ERROR (STRUCTURAL INTEGRITY): This link is the ONLY incoming connection for node '{target}'. Deleting it would create an Island. Create a new link to '{target}' first.")]

    query = f"MATCH (s {{uid: $source}})-[r:{rel_type}]->(t {{uid: $target}}) DELETE r RETURN count(r) as count"
    try:
        records, _, _ = driver.execute_query(query, {"source": source, "target": target}, database_="neo4j")
        if records[0]['count'] == 0:
            return [types.TextContent(type="text", text="⚠️ Relationship not found.")]
        
        # Sync both nodes to update frontmatter
        sync_tool.sync_node(source)
        sync_tool.sync_node(target)
        
        return [types.TextContent(type="text", text=f"✅ Link {source} -[:{rel_type}]-> {target} deleted.")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error deleting link: {e}")]

async def tool_sync_graph(arguments: dict) -> list[types.TextContent]:
    try:
        result = sync_tool.sync_all()
        return [types.TextContent(type="text", text=f"✅ Graph Synchronization Complete. {result}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Sync Error: {e}")]

async def tool_link_nodes(arguments: dict) -> list[types.TextContent]:
    source = arguments.get("source_uid")
    target = arguments.get("target_uid")
    rel_type = arguments.get("rel_type")
    
    driver = get_driver()
    query = f"""
    MATCH (s {{uid: $source}}), (t {{uid: $target}})
    MERGE (s)-[:{rel_type}]->(t)
    RETURN s.uid, t.uid
    """
    try:
        records, _, _ = driver.execute_query(query, {"source": source, "target": target}, database_="neo4j")
        if not records:
            return [types.TextContent(type="text", text=f"❌ Error: One or both nodes ({source}, {target}) not found.")]
            
        # Sync both nodes
        sync_tool.sync_node(source)
        sync_tool.sync_node(target)
        
        return [types.TextContent(type="text", text=f"✅ Linked {source} -[:{rel_type}]-> {target}.\nMarkdown files updated.")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error linking nodes: {e}")]

async def tool_register_task(arguments: dict) -> list[types.TextContent]:
    """
    Registers a new Task node from Human's chat message.
    Task nodes are NOT linked automatically — the agent decides where to connect them.
    """
    title = arguments.get("title")
    desc = arguments.get("description", "")
    
    # 1. ENFORCE HARD PHYSICS (Russian Language + No WikiLinks)
    try:
        validate_physics_constraints(title)
        if desc:
            validate_physics_constraints(desc)
    except ValueError as e:
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]
    
    # 2. Transliteration for Safe UIDs
    def transliterate(text):
        mapping = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
            'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'YO',
            'Ж': 'ZH', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'TS', 'Ч': 'CH', 'Ш': 'SH', 'Щ': 'SCH', 'Ъ': '',
            'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'YU', 'Я': 'YA',
        }
        return "".join([mapping.get(char, char) for char in text])

    transliterated_title = transliterate(title)
    safe_title = re.sub(r'[^a-zA-Z0-9]', '_', transliterated_title).strip('_').upper()
    uid = f"TASK-{safe_title[:40]}"
    
    driver = get_driver()
    
    # 3. Create Task node (without automatic linking)
    query_create = """
    MERGE (n:Task {uid: $uid})
    SET n.title = $title,
        n.description = $desc,
        n.status = 'Registered',
        n.created_at = datetime()
    RETURN n.uid as uid
    """
    
    try:
        # Generate Semantic Embedding
        semantic_text = f"{title} {desc}"
        embedding = emb_manager.get_embedding(semantic_text)

        driver.execute_query(query_create, {
            "uid": uid,
            "title": title,
            "desc": desc
        }, database_="neo4j")
        
        # Save Embedding if successful
        if embedding:
            driver.execute_query(
                "MATCH (n {uid: $uid}) SET n.embedding = $emb",
                {"uid": uid, "emb": embedding},
                database_="neo4j"
            )

        # Sync new node to Markdown
        file_path = sync_tool.sync_node(uid, sync_connected=False)
        
        return [types.TextContent(
            type="text",
            text=f"✅ Registered Task {uid}.\nSynced to Obsidian: {file_path}\n\n💡 Tip: Use link_nodes to connect this Task to a Spec or Requirement."
        )]
        
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error registering task: {e}")]


async def tool_look_for_similar(arguments: dict) -> list[types.TextContent]:
    query_text = arguments.get("query")
    embedding = emb_manager.get_embedding(query_text)
    
    if not embedding:
        return [types.TextContent(type="text", text="Error: Semantic search is not available (model failed to load).")]

    driver = get_driver()
    # Simple cosine similarity via Cypher (Vector index would be faster, but this works for lightweight)
    # n.embedding is a list of floats
    cypher = """
    MATCH (n)
    WHERE n.embedding IS NOT NULL
    WITH n, gds.similarity.cosine(n.embedding, $query_emb) as score
    WHERE score > 0.7
    RETURN n.uid as uid, n.title as title, labels(n)[0] as type, score
    ORDER BY score DESC LIMIT 5
    """
    
    # Wait, GDS similarity might not be there. Let's use internal vector index if possible or manual calculation.
    # Since we don't have GDS, we use dot product as approximation or a manual formula.
    # Actually, Neo4j 5.15 has built-in vector functions in Cypher even without GDS.
    
    # Manual Dot Product calculation in Cypher (since we lack vector functions/GDS)
    # Sentence-transformers usually return normalized vectors, so dot product = cosine similarity.
    vector_search_cypher = """
    MATCH (n)
    WHERE n.embedding IS NOT NULL AND (n:Idea OR n:Spec OR n:Requirement OR n:Task)
    WITH n, REDUCE(s = 0.0, i IN RANGE(0, size(n.embedding)-1) | s + n.embedding[i] * $query_emb[i]) as score
    WHERE score > 0.3
    RETURN n.uid as uid, n.title as title, labels(n)[0] as type, score
    ORDER BY score DESC LIMIT 10
    """
    
    try:
        driver = get_driver()
        records, _, _ = driver.execute_query(vector_search_cypher, {"query_emb": embedding}, database_="neo4j")
        
        if not records:
             return [types.TextContent(type="text", text="No similar nodes found (threshold > 0.3).")]
             
        results = [f"- [{r['type']}] {r['uid']}: {r['title']} (Score: {r['score']:.4f})" for r in records]
        return [types.TextContent(type="text", text="Semantically similar nodes:\n" + "\n".join(results))]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error during semantic search: {e}")]

# --- SERVER ENTRYPOINT ---
if __name__ == "__main__":
    import sys
    
    # Check if we should use stdio (explicitly asked)
    if "--stdio" in sys.argv:
        from mcp.server.stdio import stdio_server
        
        async def run_stdio():
            async with stdio_server() as (read_stream, write_stream):
                await mcp.run(
                    read_stream,
                    write_stream,
                    mcp.create_initialization_options()
                )
        
        import asyncio
        print("🚀 Starting Graph-Native Core (stdio)...", file=sys.stderr)
        asyncio.run(run_stdio())
    else:
        # Fallback to SSE/ASGI for containerized network access
        from mcp.server.sse import SseServerTransport
        from starlette.responses import Response
        import uvicorn

        sse = SseServerTransport("/messages")

        async def app(scope, receive, send):
            """Pure ASGI entrypoint for SSE support."""
            if scope["type"] == "lifespan":
                while True:
                    message = await receive()
                    if message["type"] == "lifespan.startup":
                        await send({"type": "lifespan.startup.complete"})
                    elif message["type"] == "lifespan.shutdown":
                        await send({"type": "lifespan.shutdown.complete"})
                        return

            if scope["type"] == "http":
                path = scope["path"]
                if path == "/sse":
                    async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                        await mcp.run(read_stream, write_stream, mcp.create_initialization_options())
                    return
                if path.startswith("/messages"):
                    await sse.handle_post_message(scope, receive, send)
                    return
                response = Response("Not Found", status_code=404)
                await response(scope, receive, send)
                return

        print("🚀 Starting Graph-Native Core (SSE/ASGI) on port 8000...", file=sys.stderr)
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

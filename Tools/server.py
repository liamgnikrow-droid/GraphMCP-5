from mcp.server import Server
import mcp.types as types
from db_config import get_driver, WORKSPACE_ROOT
from graph_sync import GraphSync
import constraint_primitives as primitives
import os
import re
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from codebase_mapper import CodebaseMapper
except ImportError:
    # Fallback to prevent crash if file not found immediately
    CodebaseMapper = None
    print("⚠️ Warning: CodebaseMapper module not found (codebase_mapper.py).", file=sys.stderr)

# Initialize MCP Server
mcp = Server("graph-native-core")
sync_tool = GraphSync()

# --- PHASE 8: MULTI-PROJECT STATE ---
STATE_FILE = os.path.join(os.path.dirname(__file__), ".active_project_state")

def load_project_state():
    """Loads active project state from file persistence."""
    default_state = {"id": "graphmcp", "root": WORKSPACE_ROOT, "workflow": "Architect"}
    try:
        import json
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                # Ensure all keys exist (migration support)
                if "workflow" not in state: state["workflow"] = "Architect"
                return state
    except Exception as e:
        print(f"⚠️ Failed to load project state: {e}", file=sys.stderr)
    return default_state

def save_project_state(project_id, project_root, workflow):
    """Persists active project state."""
    try:
        import json
        with open(STATE_FILE, 'w') as f:
            json.dump({"id": project_id, "root": project_root, "workflow": workflow}, f)
    except Exception as e:
        print(f"⚠️ Failed to save project state: {e}", file=sys.stderr)

# Initialize State
_initial_state = load_project_state()
ACTIVE_PROJECT_ID = _initial_state["id"]
ACTIVE_PROJECT_ROOT = _initial_state["root"]
ACTIVE_WORKFLOW = _initial_state["workflow"]
print(f"🚀 ACTIVE PROJECT: {ACTIVE_PROJECT_ID} (Root: {ACTIVE_PROJECT_ROOT}) | Workflow: {ACTIVE_WORKFLOW}", file=sys.stderr)

def get_current_project_id():
    return ACTIVE_PROJECT_ID

def get_current_project_root():
    return ACTIVE_PROJECT_ROOT

def get_current_workflow():
    return ACTIVE_WORKFLOW

def set_current_project(project_id: str, project_root: str):
    global ACTIVE_PROJECT_ID, ACTIVE_PROJECT_ROOT, ACTIVE_WORKFLOW
    ACTIVE_PROJECT_ID = project_id
    ACTIVE_PROJECT_ROOT = project_root
    # Preserve current workflow when switching project
    save_project_state(project_id, project_root, ACTIVE_WORKFLOW)
    
    print(f"🔄 Switched to project: {ACTIVE_PROJECT_ID} at {ACTIVE_PROJECT_ROOT}", file=sys.stderr)

def set_workflow_state(mode: str):
    global ACTIVE_PROJECT_ID, ACTIVE_PROJECT_ROOT, ACTIVE_WORKFLOW
    if mode not in ["Architect", "Builder", "Auditor"]:
        raise ValueError(f"Invalid workflow mode: {mode}")
    
    ACTIVE_WORKFLOW = mode
    save_project_state(ACTIVE_PROJECT_ID, ACTIVE_PROJECT_ROOT, mode)
    print(f"🔄 Switched Workflow to: {ACTIVE_WORKFLOW}", file=sys.stderr)
    
    print(f"🔄 Switched to project: {ACTIVE_PROJECT_ID} at {ACTIVE_PROJECT_ROOT}", file=sys.stderr)

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
    """
    ENHANCED DASHBOARD: Returns comprehensive context for Agent decision-making.
    
    Shows:
    1. Current location with description
    2. Neighbors with relationship types and descriptions
    3. Available actions from Meta-Graph
    4. Active system constraints
    5. Related Requirements within 2 hops
    6. Graph statistics
    """
    driver = get_driver()
    if not driver:
         return [types.TextContent(type="text", text="Error: No Backend Connection")]
         
    loc_uid = get_agent_location()
    loc_uid = get_agent_location()
    output_parts = []
    
    # === 0. SYSTEM STATE ===
    active_project = get_current_project_id()
    active_workflow = get_current_workflow()
    
    output_parts.append(f"🏴 **PROJECT:** `{active_project}` | **MODE:** `{active_workflow}`")
    
    if active_workflow == "Architect":
        output_parts.append("   ⚠️ **RESTRICTION:** You are in DESIGN mode. DO NOT write code. Focus on Nodes.")
    elif active_workflow == "Auditor":
        output_parts.append("   ⛔ **READ ONLY:** You are in AUDIT mode. Graph mutations are BLOCKED.")
    elif active_workflow == "Builder":
         output_parts.append("   ✅ **BUILDER:** Code actions allowed.")
         
    output_parts.append("")
    
    # === 1. CURRENT LOCATION ===
    loc_query = """
    MATCH (n {uid: $uid})
    RETURN labels(n)[0] as type, n.title as title, n.description as description
    """
    records, _, _ = driver.execute_query(loc_query, {"uid": loc_uid}, database_="neo4j")
    
    if not records:
        if loc_uid == "IDEA-Genesis":
            driver.execute_query("MERGE (:Idea {uid: 'IDEA-Genesis', title: 'Genesis Point'})", database_="neo4j")
            return [types.TextContent(type="text", text="Genesis Node Created. You are at (:Idea {uid: 'IDEA-Genesis'}). Use look_around again.")]
        return [types.TextContent(type="text", text=f"Error: Location {loc_uid} not found.")]
    
    loc_type = records[0]['type']
    loc_title = records[0]['title'] or loc_uid
    loc_desc = records[0]['description'] or "(no description)"
    
    # Truncate description
    if len(loc_desc) > 150:
        loc_desc = loc_desc[:150] + "..."
    
    output_parts.append("📍 **CURRENT LOCATION**")
    output_parts.append(f"   **{loc_uid}** ({loc_type})")
    output_parts.append(f"   {loc_desc}")
    output_parts.append("")
    
    # === 2. NEIGHBORS WITH RELATIONSHIP TYPES ===
    neighbors_query = """
    MATCH (n {uid: $uid})-[r]-(other)
    WHERE NOT other:Agent
    RETURN 
        CASE WHEN startNode(r) = n THEN '→' ELSE '←' END as direction,
        type(r) as rel_type,
        other.uid as uid,
        labels(other)[0] as type,
        other.title as title,
        SUBSTRING(COALESCE(other.description, ''), 0, 80) as desc
    ORDER BY direction, rel_type
    """
    neighbors_rec, _, _ = driver.execute_query(neighbors_query, {"uid": loc_uid}, database_="neo4j")
    
    output_parts.append(f"👥 **NEIGHBORS** ({len(neighbors_rec)})")
    if neighbors_rec:
        for n in neighbors_rec:
            arrow = n['direction']
            rel = n['rel_type']
            uid = n['uid']
            ntype = n['type']
            title = n['title'] or uid
            desc = n['desc']
            
            if desc:
                output_parts.append(f"   {arrow} {rel} {arrow} **{uid}** ({ntype})")
                output_parts.append(f"      \"{title}\": {desc}...")
            else:
                output_parts.append(f"   {arrow} {rel} {arrow} **{uid}** ({ntype}): {title}")
    else:
        output_parts.append("   (no neighbors)")
    output_parts.append("")
    
    # === 3. AVAILABLE ACTIONS (from Meta-Graph) ===
    actions_query = """
    MATCH (nt:NodeType {name: $node_type})-[:CAN_PERFORM]->(a:Action {scope: 'contextual'})
    RETURN a.tool_name as tool, a.target_type as target
    """
    actions_rec, _, _ = driver.execute_query(actions_query, {"node_type": loc_type}, database_="neo4j")
    
    output_parts.append("🔧 **AVAILABLE ACTIONS** (contextual)")
    if actions_rec:
        for a in actions_rec:
            tool = a['tool']
            target = a['target']
            if target:
                output_parts.append(f"   • {tool}(type='{target}')")
            else:
                output_parts.append(f"   • {tool}")
    else:
        output_parts.append("   (none specific to this node type)")
    output_parts.append("   + Global: look_around, move_to, read_node, get_full_context, look_for_similar")
    output_parts.append("")
    
    # === 4. ACTIVE SYSTEM CONSTRAINTS ===
    constraints_query = """
    MATCH (c:Constraint)
    RETURN c.uid as uid, c.rule_name as name, c.error_message as msg
    """
    constraints_rec, _, _ = driver.execute_query(constraints_query, database_="neo4j")
    
    output_parts.append("⚠️ **SYSTEM CONSTRAINTS** (enforced automatically)")
    for c in constraints_rec:
        output_parts.append(f"   • {c['name']}: {c['msg'][:60]}...")
    output_parts.append("")
    
    # === 5. RELATED REQUIREMENTS (2 hops) with description ===
    current_project = get_current_project_id()
    
    req_query = """
    MATCH (n {uid: $uid})-[*1..2]-(r:Requirement)
    WHERE (r.project_id = $project_id OR r.project_id IS NULL)
    RETURN DISTINCT r.uid as uid, r.title as title, 
           SUBSTRING(COALESCE(r.description, ''), 0, 100) as desc
    LIMIT 5
    """
    req_rec, _, _ = driver.execute_query(req_query, {"uid": loc_uid, "project_id": current_project}, database_="neo4j")
    
    if req_rec:
        output_parts.append("📋 **RELATED REQUIREMENTS** (within 2 hops)")
        for r in req_rec:
            title = r['title'] or r['uid']
            desc = r['desc']
            if desc:
                output_parts.append(f"   • **{r['uid']}**: \"{title}\"")
                output_parts.append(f"     ↳ {desc}...")
            else:
                output_parts.append(f"   • **{r['uid']}**: {title}")
        output_parts.append("")
    
    # === 6. GRAPH STATS (Filtered by Project) ===
    stats_query = """
    MATCH (n)
    WHERE (n:Idea OR n:Spec OR n:Requirement OR n:Task OR n:Domain)
      AND (n.project_id = $project_id OR n.project_id IS NULL)
    RETURN labels(n)[0] as type, count(n) as count
    """
    stats_rec, _, _ = driver.execute_query(stats_query, {"project_id": current_project}, database_="neo4j")
    
    stats_str = " • ".join([f"{s['type']}: {s['count']}" for s in stats_rec])
    output_parts.append(f"📊 **PROJECT STATS ({current_project}):** {stats_str}")
    
    return [types.TextContent(type="text", text="\n".join(output_parts))]

async def tool_move_to(arguments: dict) -> list[types.TextContent]:
    """
    Moves Agent to a neighbor node.
    After successful move, automatically returns look_around context.
    """
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
        
        # 3. AUTO-REFRESH: Return look_around context for new location
        # This is like a camera following the player in a game
        look_result = await tool_look_around({})
        
        move_confirmation = f"✅ **MOVED TO:** {target_uid} ({target_type}: {target_title})\n"
        move_confirmation += "=" * 50 + "\n\n"
        
        # Combine move confirmation with fresh context
        return [types.TextContent(
            type="text",
            text=move_confirmation + look_result[0].text
        )]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error moving agent: {e}")]



def check_constraints(action_uid: str, context: dict) -> tuple[bool, list[str]]:
    """
    PHASE 3: Centralized Constraint Middleware
    
    Checks all Constraints from Meta-Graph that RESTRICT the given action.
    
    Args:
        action_uid: UID of the Action being performed (e.g. 'ACT-create_spec')
        context: Dictionary with contextual data:
            - 'text': content being validated (for cyrillic_ratio, regex_match)
            - 'target_type': type of node being created (for node_count cardinality checks)
            - 'uid': UID of current node (for not_equals self-deletion check)
            
    Returns:
        (passed: bool, violations: list[str])
        - passed: True if all constraints pass
        - violations: List of error messages for failed constraints
    """
    driver = get_driver()
    violations = []
    
    # Fetch all Constraints that RESTRICT this action
    query = """
    MATCH (c:Constraint)-[:RESTRICTS]->(a:Action)
    WHERE a.uid = $action_uid OR a.tool_name IN $tool_names
    RETURN DISTINCT c.uid as uid, 
           c.rule_name as rule_name, 
           c.error_message as error_message,
           c.function as function,
           c.operator as operator,
           c.threshold as threshold,
           c.pattern as pattern,
           c.target_label as target_label
    """
    
    # Also match by tool_name for flexibility
    tool_name = context.get('tool_name')
    tool_names = [tool_name] if tool_name else []
    
    try:
        records, _, _ = driver.execute_query(
            query, 
            {"action_uid": action_uid, "tool_names": tool_names}, 
            database_="neo4j"
        )
    except Exception as e:
        # If constraint loading fails, we FAIL SAFE (block action)
        return False, [f"Failed to load constraints: {e}"]
    
    # Deduplicate by constraint UID (to avoid checking same constraint multiple times)
    seen_constraints = set()
    
    for record in records:
        constraint_uid = record['uid']
        
        # Skip if already checked
        if constraint_uid in seen_constraints:
            continue
        seen_constraints.add(constraint_uid)
        
        rule_name = record['rule_name']
        error_message = record['error_message']
        function = record.get('function')
        operator = record.get('operator')
        threshold = record.get('threshold')
        pattern = record.get('pattern')
        target_label = record.get('target_label')
        
        # Apply the appropriate primitive
        try:
            if function == 'cyrillic_ratio':
                text = context.get('text', '')
                ratio = primitives.cyrillic_ratio(text)
                # threshold = 0.25, operator = '>='
                if threshold is not None:
                    if operator == '<' and ratio < threshold:
                        violations.append(error_message or f"{rule_name}: Cyrillic ratio {ratio:.2f} < {threshold}")
                    elif operator == '>=' and ratio < threshold:
                        violations.append(error_message or f"{rule_name}: Cyrillic ratio {ratio:.2f} < {threshold}")
                        
            elif function == 'regex_match':
                text = context.get('text', '')
                if pattern and primitives.regex_match(text, pattern):
                    violations.append(error_message or f"{rule_name}: Pattern '{pattern}' found in text")
                    
            elif function == 'node_count':
                # IMPORTANT: Use target_label from Constraint, not from context
                # Example: CON-One_Spec has target_label='Spec'
                # We only check this if context['target_type'] matches target_label
                if target_label:
                    context_target = context.get('target_type')
                    
                    # Only apply this constraint if we're creating a node of this type
                    if context_target == target_label:
                        count = primitives.node_count(driver, target_label)
                        # threshold = 1, operator = '>='
                        if threshold is not None and operator:
                            if primitives.compare(count, operator, threshold):
                                violations.append(error_message or f"{rule_name}: {target_label} count {count} {operator} {threshold}")
                            
            elif function == 'not_equals':
                # For preventing self-deletion
                current_uid = context.get('current_uid')
                target_uid = context.get('target_uid')
                if current_uid and target_uid:
                    if not primitives.not_equals(current_uid, target_uid):
                        violations.append(error_message or f"{rule_name}: Cannot operate on self")
                        
        except Exception as e:
            violations.append(f"{rule_name}: Error applying constraint - {e}")
    
    passed = len(violations) == 0
    return passed, violations



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
    
    # 1. ENFORCE HARD PHYSICS via Centralized Constraint Middleware
    combined_text = f"{title} {desc}"
    context = {
        "text": combined_text,
        "target_type": c_type,
        "tool_name": "create_concept"
    }
    
    passed, violations = check_constraints(action_uid=None, context=context)
    
    if not passed:
        violation_msg = "\n".join(f"  • {v}" for v in violations)
        return [types.TextContent(
            type="text", 
            text=f"❌ **CONSTRAINT VIOLATION**\n\n{violation_msg}"
        )]
    
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
    if c_type not in ["Spec", "Requirement", "Task", "Idea", "Domain"]:
         return [types.TextContent(type="text", text=f"Error: Invalid concept type '{c_type}'. Epic is DEAD.")]

    # 2.1 META-GRAPH VALIDATION (Critical Fix)
    # Middleware only checks if 'create_concept' tool is allowed.
    # We must also check if the SPECIFIC target_type is allowed from the current parent node.
    parent_uid = get_agent_location()
    parent_type = get_node_type(parent_uid)
    
    # Exception for Genesis: Can always create allowed roots if logic permits, but let's stick to graph rules if possible.
    # Assuming 'Idea' creation is handled properly by constraints. 
    # Let's validate strictly.
    
    driver = get_driver()
    
    meta_validation_query = """
    MATCH (nt:NodeType {name: $parent_type})-[:CAN_PERFORM]->(a:Action {tool_name: 'create_concept'})
    WHERE a.target_type = $target_type
    RETURN count(a) as allowed
    """
    
    val_recs, _, _ = driver.execute_query(
        meta_validation_query, 
        {"parent_type": parent_type, "target_type": c_type}, 
        database_="neo4j"
    )
    
    is_target_allowed = val_recs and val_recs[0]['allowed'] > 0
    
    if not is_target_allowed:
        # Find what IS allowed to help the user
        hint_query = """
        MATCH (nt:NodeType {name: $parent_type})-[:CAN_PERFORM]->(a:Action {tool_name: 'create_concept'})
        RETURN a.target_type as allowed_type
        """
        hint_recs, _, _ = driver.execute_query(hint_query, {"parent_type": parent_type}, database_="neo4j")
        allowed_types = [h["allowed_type"] for h in hint_recs if h["allowed_type"]]
        
        return [types.TextContent(
             type="text", 
             text=f"❌ PHYSICS ERROR: Hierarchy Violation.\n\n"
                  f"Location: (:{parent_type} {{uid: '{parent_uid}'}})\n"
                  f"Action: Create (:{c_type})\n\n"
                  f"⛔ The Meta-Graph forbids creating a '{c_type}' directly from a '{parent_type}'.\n"
                  f"✅ Allowed children types from here: {allowed_types}"
        )]

    driver = get_driver()
    current_project = get_current_project_id()
    
    # --- STRICT UNIQUENESS CHECK (Iron Dome) ---
    if c_type == "Idea":
        check_query = "MATCH (n:Idea {project_id: $pid}) RETURN count(n) as count"
        check_recs, _, _ = driver.execute_query(check_query, {"pid": current_project}, database_="neo4j")
        if check_recs and check_recs[0]["count"] >= 1:
             return [types.TextContent(
                 type="text",
                 text=f"❌ **CREATION REJECTED**\n\nA Project can have only ONE Root Idea (One Truth Policy).\nExisting Idea count: {check_recs[0]['count']}.\n\n💡 Use `read_graph` or `look_around` to find the existing root."
             )]
    parent_uid = get_agent_location() # "IDEA-Genesis"
    
    query_create = f"""
    MATCH (parent {{uid: $parent_uid}})
    MERGE (n:{c_type} {{uid: $uid}})
    SET n.title = $title,
        n.description = $desc,
        n.status = 'Draft',
        n.created_at = datetime(),
        n.project_id = $project_id
    MERGE (parent)-[:DECOMPOSES]->(n)
    RETURN n.uid as uid
    """
    try:
        # Generate Semantic Embedding
        semantic_text = f"{title} {desc}"
        embedding = emb_manager.get_embedding(semantic_text)

        _, _, _ = driver.execute_query(
            query_create, 
            {"parent_uid": parent_uid, "uid": uid, "title": title, "desc": desc, "project_id": current_project}, 
            database_="neo4j"
        )
        
        # Save Embedding if successful
        if embedding:
            driver.execute_query(
                "MATCH (n {uid: $uid}) SET n.embedding = $emb",
                {"uid": uid, "emb": embedding},
                database_="neo4j"
            )

        # Sync new node AND parent (because parent now has a new connection)
        file_path = sync_tool.sync_node(uid, sync_connected=True)
        
        # === IMPACT ANALYSIS ===
        impact_report = []
        impact_report.append(f"✅ **СОЗДАНО:** (:{c_type} {{uid: '{uid}'}})")
        impact_report.append(f"   Project: {current_project}")
        impact_report.append(f"   Title: {title}")
        impact_report.append(f"   Synced to: {file_path}\n")
        
        # 1. Check for semantically similar nodes (possible duplicates)
        if embedding:
            impact_report.append("🔍 **СЕМАНТИЧЕСКИ БЛИЗКИЕ НОДЫ** (возможные дубликаты)")
            
            similar_query = """
            MATCH (n)
            WHERE n.embedding IS NOT NULL AND n.uid <> $new_uid
                AND (n:Idea OR n:Spec OR n:Requirement OR n:Task OR n:Domain)
                AND (n.project_id = $project_id OR n.project_id IS NULL)
            WITH n, REDUCE(s = 0.0, i IN RANGE(0, size(n.embedding)-1) | s + n.embedding[i] * $emb[i]) as score
            WHERE score > 0.6
            RETURN n.uid as uid, n.title as title, labels(n)[0] as type, score
            ORDER BY score DESC LIMIT 3
            """
            
            similar_rec, _, _ = driver.execute_query(
                similar_query, 
                {"new_uid": uid, "emb": embedding, "project_id": current_project}, 
                database_="neo4j"
            )
            
            if similar_rec:
                for s in similar_rec:
                    stype = s["type"]
                    suid = s["uid"]
                    stitle = s.get("title", "N/A")
                    score = s["score"]
                    impact_report.append(f"   ⚠️  [{stype}] {suid}: {stitle} (Similarity: {score:.3f})")
                impact_report.append("   💡 Проверьте, не дубликат ли это\n")
            else:
                impact_report.append("   (Нет похожих нод)\n")
        
        # 2. Show applied Constraints
        impact_report.append("⚠️ **ПРИМЕНЁННЫЕ CONSTRAINTS**")
        constraints_query = """
        MATCH (c:Constraint)
        RETURN c.uid as uid, c.rule_name as rule_name
        """
        constraints_rec, _, _ = driver.execute_query(constraints_query, database_="neo4j")
        
        if constraints_rec:
            for c in constraints_rec:
                cuid = c["uid"]
                crule = c.get("rule_name", "N/A")
                impact_report.append(f"   ✓ {cuid}: {crule}")
        impact_report.append("")
        
        # 3. Show parent link
        impact_report.append("🔗 **АВТОМАТИЧЕСКИЕ СВЯЗИ**")
        parent_query = "MATCH (p {uid: $parent_uid}) RETURN p.title as title, labels(p)[0] as type"
        parent_rec, _, _ = driver.execute_query(parent_query, {"parent_uid": parent_uid}, database_="neo4j")
        
        if parent_rec:
            ptype = parent_rec[0]["type"]
            ptitle = parent_rec[0].get("title", "N/A")
            impact_report.append(f"   (:{ptype} {{uid: '{parent_uid}'}}) -[:DECOMPOSES]-> (:{c_type} {{uid: '{uid}'}})")
            impact_report.append(f"   Parent: {ptitle}\n")
        
        # 4. Show related Specs/Requirements in vicinity
        impact_report.append("📋 **ЗАТРОНУТЫЕ ОБЛАСТИ ГРАФА**")
        related_query = """
        MATCH path = (new {uid: $uid})-[:DECOMPOSES*1..2]-(related)
        WHERE related:Spec OR related:Requirement
        RETURN DISTINCT related.uid as uid, related.title as title, labels(related)[0] as type
        LIMIT 5
        """
        related_rec, _, _ = driver.execute_query(related_query, {"uid": uid}, database_="neo4j")
        
        if related_rec:
            for r in related_rec:
                rtype = r["type"]
                ruid = r["uid"]
                rtitle = r.get("title", "N/A")
                impact_report.append(f"   • [{rtype}] {ruid}: {rtitle}")
        else:
            impact_report.append("   (Нет связанных Specs/Requirements)")
        
        impact_text = "\n".join(impact_report)
        
        return [types.TextContent(
            type="text",
            text=impact_text
        )]
        
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error creating concept: {e}")]

async def tool_refresh_knowledge(arguments: dict) -> list[types.TextContent]:
    """
    Refreshes semantic embeddings for all nodes in the graph.
    Useful after bulk imports or manual edits.
    """
    driver = get_driver()
    if not driver: return [types.TextContent(type="text", text="Error: No Backend Connection")]
    
    # 1. Fetch all semantic nodes
    query = """
    MATCH (n)
    WHERE (n:Idea OR n:Spec OR n:Requirement OR n:Task OR n:Domain)
    RETURN n.uid as uid, n.title as title, n.description as description
    """
    try:
        records, _, _ = driver.execute_query(query, database_="neo4j")
        updated_count = 0
        
        print(f"🧠 Refreshing embeddings for {len(records)} nodes...", file=sys.stderr)
        
        with driver.session(database="neo4j") as session:
            for rec in records:
                uid = rec['uid']
                title = rec.get('title', '') or ''
                desc = rec.get('description', '') or ''
                
                # Re-calculate embedding
                semantic_text = f"{title} {desc}"
                embedding = emb_manager.get_embedding(semantic_text)
                
                if embedding:
                    session.run(
                        "MATCH (n {uid: $uid}) SET n.embedding = $emb",
                        {"uid": uid, "emb": embedding}
                    )
                    updated_count += 1
                    
        return [types.TextContent(
            type="text", 
            text=f"✅ Knowledge Refreshed. Updated embeddings for {updated_count} nodes."
        )]
        
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error refreshing knowledge: {e}")]


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
            name="update_node",
            description="Adds or updates metadata properties (like status, priority, spec_ref) to a node.",
            inputSchema={
                "type": "object",
                "properties": {
                    "uid": {"type": "string"},
                    "properties": {
                        "type": "object",
                        "description": "Dictionary of key-value pairs to set. E.g. {'spec_ref': '1.2.3', 'status': 'Done'}"
                    }
                },
                "required": ["uid", "properties"]
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
            name="explain_physics",
            description="Explains why a tool is blocked or available at your current location. Provides path to unlock if blocked.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "Name of the tool to check (e.g., 'create_concept')"}
                },
                "required": ["tool_name"]
            }
        ),
        types.Tool(
            name="get_full_context",
            description="Gets FULL context for a task/query: similar nodes, related specs, constraints, current location. Use at start of ANY task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Task description or query (e.g., 'добавить авторизацию', 'implement OAuth')"}
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
                    "rel_type": {"type": "string", "enum": ["IMPLEMENTS", "DECOMPOSES", "DEPENDS_ON", "CONFLICT", "IMPORTS", "SATISFIES", "PART_OF"]}
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
            name="format_cypher",
            description="Formats Cypher scripts for Meta-Graph changes. ONLY AT HUMAN REQUEST. Agent = secretary, Human = architect.",
            inputSchema={
                "type": "object",
                "properties": {
                    "change_type": {
                        "type": "string", 
                        "enum": ["add_node_type", "add_action", "add_constraint", "modify_rule"],
                        "description": "Type of Meta-Graph change"
                    },
                    "details": {
                        "type": "object",
                        "description": "JSON object with change-specific details (e.g., {name, description, ...})"
                    }
                },
                "required": ["change_type", "details"]
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
        ),
        types.Tool(
            name="switch_project",
            description="Switches the active project context (Multi-Project Architecture). Filters all subsequent queries by this project_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID (e.g., 'tgappparking')"}
                },
                "required": ["project_id"]
            }
        ),
        types.Tool(
            name="set_workflow",
            description="Sets the agent's active workflow mode (Architect, Builder, Auditor). Controls available tools.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["Architect", "Builder", "Auditor"], "description": "Workflow Mode"}
                },
                "required": ["mode"]
            }
        ),
        types.Tool(
            name="map_codebase",
            description="Scans the active project codebase to create Graph nodes (File, Class, Function). Use this to keep the Graph in sync with Reality.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="read_node",
            description="Reads the FULL content of a node by UID. Returns title, description, and body text. Use to understand what a node contains before making decisions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "uid": {"type": "string", "description": "UID of the node to read (e.g., 'SPEC-Graph_Physics')"}
                },
                "required": ["uid"]
            }
        ),
        types.Tool(
            name="illuminate_path",
            description="🔦 ILLUMINATE THE PATH: Given a task/query, finds the relevant path through the graph (Idea→Spec→Req→Task) and returns FULL CONTENT of all nodes on that path. Use at START of any task to get complete context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Task or question (e.g., 'добавить 2FA авторизацию', 'security requirements')"}
                },
                "required": ["query"]
            }

        ),
        types.Tool(
            name="refresh_knowledge",
            description="Recalculates semantic embeddings for ALL nodes. Use this if you suspect the graph is out of sync with manual file edits.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="find_orphans",
            description="Finds isolated nodes (orphans) that have NO relationships. Read-only diagnostics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max number of orphans to return (default: 50)"}
                },
                "required": []
            }
        )
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    print(f"DEBUG_TOOL_CALL: name='{name}' arguments={arguments} type={type(arguments)}", file=sys.stderr)
    # --- MIDDLEWARE CHECK ---
    loc_uid = get_agent_location()
    current_node_type = get_node_type(loc_uid)
    allowed = get_allowed_tool_names(current_node_type)
    
    if name not in allowed:
         return [types.TextContent(
             type="text", 
             text=f"❌ PHYSICS ERROR: Tool '{name}' is FORBIDDEN when you are at a node of type '{current_node_type}'.\nLocation: {loc_uid}"
         )]
         
    # --- WORKFLOW CHECK ---
    current_workflow = get_current_workflow()
    MUTATION_TOOLS = ["create_concept", "link_nodes", "delete_node", "delete_link", "register_task", "sync_graph"]
    
    if current_workflow == "Auditor" and name in MUTATION_TOOLS:
        return [types.TextContent(
             type="text",
             text=f"⛔ WORKFLOW RESTRICTION: Tool '{name}' is BLOCKED in 'Auditor' mode.\nTip: Use set_workflow('Builder') or set_workflow('Architect') to enable modifications."
        )]

    # --- DISPATCH ---
    if name == "look_around": return await tool_look_around(arguments)
    elif name == "move_to": return await tool_move_to(arguments)
    elif name == "create_concept": return await tool_create_concept(arguments)
    elif name == "look_for_similar": return await tool_look_for_similar(arguments)
    elif name == "explain_physics": return await tool_explain_physics(arguments)
    elif name == "get_full_context": return await tool_get_full_context(arguments)
    elif name == "sync_graph": return await tool_sync_graph(arguments)
    elif name == "link_nodes": return await tool_link_nodes(arguments)
    elif name == "delete_node": return await tool_delete_node(arguments)
    elif name == "delete_link": return await tool_delete_link(arguments)
    elif name == "update_node": return await tool_update_node(arguments)
    elif name == "format_cypher": return await tool_format_cypher(arguments)
    elif name == "register_task": return await tool_register_task(arguments)
    elif name == "read_node": return await tool_read_node(arguments)
    elif name == "switch_project": return await tool_switch_project(arguments)
    elif name == "set_workflow": return await tool_set_workflow(arguments)
    elif name == "map_codebase": return await tool_map_codebase(arguments)
    elif name == "illuminate_path": return await tool_illuminate_path(arguments)
    elif name == "refresh_knowledge": return await tool_refresh_knowledge(arguments)
    elif name == "find_orphans": return await tool_find_orphans(arguments)
    else: return [types.TextContent(type="text", text=f"Error: Unknown tool {name}")]

async def tool_delete_node(arguments: dict) -> list[types.TextContent]:
    uid = arguments.get("uid")
    if not uid: return [types.TextContent(type="text", text="Error: UID is required")]
    
    # 0. IRON DOME SECURITY: System Types Protection
    driver = get_driver()
    type_check_query = "MATCH (n {uid: $uid}) RETURN labels(n) as labels"
    type_recs, _, _ = driver.execute_query(type_check_query, {"uid": uid}, database_="neo4j")
    
    if type_recs and type_recs[0]['labels']:
        labels = type_recs[0]['labels']
        if any(lbl in ['Action', 'Constraint', 'NodeType'] for lbl in labels):
            return [types.TextContent(type="text", text=f"⛔ IRON DOME SECURITY: Permission Denied. You cannot delete system node {uid} (Type: {labels}). These define the laws of physics.")]

    # Check if this is the Agent's current location
    if uid == get_agent_location():
        return [types.TextContent(type="text", text="❌ PHYSICS error: You cannot delete the node you are currently standing on.")]
    
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
        db_deleted = records[0]['count'] > 0
        
        # Always attempt to delete file (Clean up ghosts)
        file_deleted = sync_tool.delete_node(uid)
        
        if db_deleted and file_deleted:
            return [types.TextContent(type="text", text=f"✅ Node {uid} and its file have been PERMANENTLY DELETED.")]
        elif db_deleted:
            return [types.TextContent(type="text", text=f"✅ Node {uid} deleted from DB (File was not found).")]
        elif file_deleted:
            return [types.TextContent(type="text", text=f"🧹 Ghost File for {uid} deleted (Node was not in DB).")]
        else:
             return [types.TextContent(type="text", text=f"⚠️ Node {uid} not found in database AND no file found on disk.")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error deleting node: {e}")]

def _propagate_implementation_links(driver, source_uid, target_uid):
    """
    Implementation Echo:
    If a Child (Class/Function) implements a Requirement, 
    its Parent (File) must also implement it.
    """
    query = """
    MATCH (child {uid: $source_uid})
    MATCH (child)-[:IMPLEMENTS]->(req {uid: $target_uid})
    
    // Find parent container (File or Class)
    MATCH (parent)-[:DECOMPOSES]->(child)
    
    // Echo the link up
    MERGE (parent)-[:IMPLEMENTS]->(req)
    RETURN parent.uid, labels(parent)[0] as type
    """
    try:
        records, _, _ = driver.execute_query(query, 
            {"source_uid": source_uid, "target_uid": target_uid}, 
            database_="neo4j")
            
        for r in records:
            parent_uid = r['parent.uid']
            # Sync parent to update frontmatter
            sync_tool.sync_node(parent_uid)
            
            # Recursive propagation (if Class inside File)
            _propagate_implementation_links(driver, parent_uid, target_uid)
            
    except Exception as e:
        print(f"⚠️ Echo propagation failed: {e}", file=sys.stderr)



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
    
    # 1. Fetch Types of Source and Target
    type_query = """
    MATCH (s {uid: $source})
    OPTIONAL MATCH (t {uid: $target})
    RETURN labels(s) as s_labels, labels(t) as t_labels
    """
    try:
        type_recs, _, _ = driver.execute_query(type_query, {"source": source, "target": target}, database_="neo4j")
        
        if not type_recs:
             return [types.TextContent(type="text", text=f"❌ Error: Source node {source} not found.")]
        
        s_labels = type_recs[0]['s_labels']
        t_labels = type_recs[0]['t_labels']
        
        if not s_labels: return [types.TextContent(type="text", text=f"❌ Error: Source node {source} not found.")]
        if not t_labels: return [types.TextContent(type="text", text=f"❌ Error: Target node {target} not found.")]
        
        s_type = s_labels[0]
        t_type = t_labels[0]
        
        # 2. SCHEMA VALIDATION (Query Meta-Graph)
        # We query the Core DB ('neo4j') for implicit permission:
        # (:NodeType {name: Source}) -[:ALLOWS_CONNECTION {type: RelType}]-> (:NodeType {name: Target})
        
        schema_query = """
        MATCH (s:NodeType {name: $s_type})-[r:ALLOWS_CONNECTION {type: $rel_type}]->(t:NodeType {name: $t_type})
        RETURN count(r) as is_allowed
        """
        
        schema_recs, _, _ = driver.execute_query(
            schema_query, 
            {"s_type": s_type, "rel_type": rel_type, "t_type": t_type}, 
            database_="neo4j"
        )
        
        is_allowed = schema_recs[0]['is_allowed'] > 0
        
        if not is_allowed:
            # Construct helpful hint by querying what IS allowed
            hint_query = """
            MATCH (s:NodeType {name: $s_type})-[r:ALLOWS_CONNECTION]->(t:NodeType)
            RETURN r.type as rel, t.name as target
            """
            hint_recs, _, _ = driver.execute_query(hint_query, {"s_type": s_type}, database_="neo4j")
            
            hints = [f"{h['rel']} -> {h['target']}" for h in hint_recs]
            hint_msg = "\n".join([f"   • {h}" for h in hints[:5]]) or "   (No allowed connections found)"
            
            return [types.TextContent(
                type="text", 
                text=f"❌ PHYSICS ERROR: Connection Forbidden (Meta-Graph Schema).\n\n"
                     f"Attempted: (:{s_type}) -[:{rel_type}]-> (:{t_type})\n"
                     f"The Meta-Graph does not have an [:ALLOWS_CONNECTION] rule for this.\n\n"
                     f"Allowed connections from {s_type}:\n{hint_msg}"
            )]

        
        # 3. Execution
        query = f"""
        MATCH (s {{uid: $source}}), (t {{uid: $target}})
        MERGE (s)-[:{rel_type}]->(t)
        RETURN s.uid, t.uid
        """
        records, _, _ = driver.execute_query(query, {"source": source, "target": target}, database_="neo4j")
        
        # 3. Post-Hook: Implementation Echo
        if rel_type == "IMPLEMENTS":
            _propagate_implementation_links(driver, source, target)
        
        # Sync both nodes
        sync_tool.sync_node(source)
        sync_tool.sync_node(target)
        
        return [types.TextContent(type="text", text=f"✅ Linked {source} -[:{rel_type}]-> {target}.\nMarkdown files updated.")]
        
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error linking nodes: {e}")]

async def tool_update_node(arguments: dict) -> list[types.TextContent]:
    """
    Updates properties of an existing node.
    Useful for detailed metadata like 'spec_ref', 'priority', 'status', etc.
    """
    uid = arguments.get("uid")
    properties = arguments.get("properties")
    
    if not uid or not properties:
        return [types.TextContent(type="text", text="Error: 'uid' and 'properties' (dict) are required.")]
        
    # Security: Prevent overwriting critical system fields
    driver = get_driver()
    type_check_query = "MATCH (n {uid: $uid}) RETURN labels(n) as labels"
    type_recs, _, _ = driver.execute_query(type_check_query, {"uid": uid}, database_="neo4j")
    
    if type_recs and type_recs[0]['labels']:
        labels = type_recs[0]['labels']
        if any(lbl in ['Action', 'Constraint', 'NodeType'] for lbl in labels):
            return [types.TextContent(type="text", text=f"⛔ IRON DOME SECURITY: Permission Denied. You cannot modify system node {uid} (Type: {labels}). These define the laws of physics.")]

    forbidden_keys = ['uid', 'type', 'created_at', 'embedding', 'project_id']
    clean_props = {k: v for k, v in properties.items() if k not in forbidden_keys}
    
    if not clean_props:
        return [types.TextContent(type="text", text=f"Error: No valid properties to update. Forbidden keys: {forbidden_keys}")]

    driver = get_driver()
    query = f"""
    MATCH (n {{uid: $uid}})
    SET n += $props
    RETURN n.uid, n.title
    """
    
    try:
        records, _, _ = driver.execute_query(query, {"uid": uid, "props": clean_props}, database_="neo4j")
        
        if not records:
            return [types.TextContent(type="text", text=f"⚠️ Node {uid} not found.")]
            
        # Sync to Markdown
        file_path = sync_tool.sync_node(uid)
        
        return [types.TextContent(type="text", text=f"✅ Updated node {uid}.\nProperties set: {list(clean_props.keys())}\nSynced to: {file_path}")]
        
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error updating node: {e}")]

async def tool_register_task(arguments: dict) -> list[types.TextContent]:

    """
    Registers a new Task node from Human's chat message.
    Task nodes are NOT linked automatically — the agent decides where to connect them.
    """
    title = arguments.get("title")
    desc = arguments.get("description", "")
    
    # 1. ENFORCE HARD PHYSICS via Centralized Constraint Middleware
    combined_text = f"{title} {desc}"
    context = {
        "text": combined_text,
        "target_type": "Task",
        "tool_name": "register_task"
    }
    
    passed, violations = check_constraints(action_uid="ACT-register_task", context=context)
    
    if not passed:
        violation_msg = "\n".join(f"  • {v}" for v in violations)
        return [types.TextContent(
            type="text", 
            text=f"❌ **CONSTRAINT VIOLATION**\n\n{violation_msg}"
        )]
    
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


async def tool_format_cypher(arguments: dict) -> list[types.TextContent]:
    """
    Formats Cypher scripts for Meta-Graph changes.
    ONLY AT HUMAN REQUEST - Agent helps format, Human decides and executes.
    """
    change_type = arguments.get("change_type")
    details = arguments.get("details", {})
    
    # Generate Cypher script based on change_type
    cypher_script = ""
    
    if change_type == "add_node_type":
        node_name = details.get("name", "Unknown")
        description = details.get("description", "")
        max_count = details.get("max_count", "null")
        
        cypher_script = f"""
// Add new NodeType: {node_name}
CREATE (:NodeType {{
    name: '{node_name}',
    description: '{description}',
    max_count: {max_count}
}});
"""
    
    elif change_type == "add_action":
        action_uid = details.get("uid", "ACT-UNKNOWN")
        tool_name = details.get("tool_name", "unknown")
        scope = details.get("scope", "contextual")
        target_type = details.get("target_type")
        
        cypher_script = f"""
// Add new Action: {action_uid}
CREATE (:Action {{
    uid: '{action_uid}',
    tool_name: '{tool_name}',
    scope: '{scope}'{f", target_type: '{target_type}'" if target_type else ""}
}});

// Link to NodeType (specify in details.allowed_from)
"""
        if "allowed_from" in details:
            for node_type in details["allowed_from"]:
                cypher_script += f"""
MATCH (nt:NodeType {{name: '{node_type}'}}), (a:Action {{uid: '{action_uid}'}})
CREATE (nt)-[:CAN_PERFORM]->(a);
"""
    
    elif change_type == "add_constraint":
        constraint_uid = details.get("uid", "CON-UNKNOWN")
        rule_name = details.get("rule_name", "Unknown Rule")
        function = details.get("function", "")
        error_message = details.get("error_message", "")
        
        cypher_script = f"""
// Add new Constraint: {constraint_uid}
CREATE (:Constraint {{
    uid: '{constraint_uid}',
    rule_name: '{rule_name}',
    function: '{function}',
    error_message: '{error_message}'
}});

// Link to Actions (specify in details.restricts)
"""
        if "restricts" in details:
            for action_uid in details["restricts"]:
                cypher_script += f"""
MATCH (c:Constraint {{uid: '{constraint_uid}'}}), (a:Action {{uid: '{action_uid}'}})
CREATE (c)-[:RESTRICTS]->(a);
"""
    
    elif change_type == "modify_rule":
        cypher_script = details.get("cypher", "// Custom Cypher provided by Human")
    
    # Return formatted script WITHOUT executing or saving
    return [types.TextContent(
        type="text",
        text=f"📝 **FORMATTED CYPHER SCRIPT**\n"
             f"Type: {change_type}\n\n"
             f"```cypher\n{cypher_script}\n```\n\n"
             f"⚠️  **HUMAN REVIEW REQUIRED**\n"
             f"This script was NOT executed.\n"
             f"1. Review the Cypher above\n"
             f"2. Test in Neo4j Browser if needed\n"
             f"3. Execute manually when ready\n"
             f"4. Update bootstrap script if permanent"
    )]


async def tool_look_for_similar(arguments: dict) -> list[types.TextContent]:
    query_text = arguments.get("query")
    embedding = emb_manager.get_embedding(query_text)
    
    if not embedding:
        return [types.TextContent(type="text", text="Error: Semantic search is not available (model failed to load).")]

    driver = get_driver()
    current_project = get_current_project_id()
    
    # Manual Dot Product calculation in Cypher (since we lack vector functions/GDS)
    # Sentence-transformers usually return normalized vectors, so dot product = cosine similarity.
    vector_search_cypher = """
    MATCH (n)
    WHERE n.embedding IS NOT NULL 
        AND (n:Idea OR n:Spec OR n:Requirement OR n:Task)
        AND (n.project_id = $project_id OR n.project_id IS NULL)
    WITH n, REDUCE(s = 0.0, i IN RANGE(0, size(n.embedding)-1) | s + n.embedding[i] * $query_emb[i]) as score
    WHERE score > 0.3
    RETURN n.uid as uid, n.title as title, labels(n)[0] as type, score
    ORDER BY score DESC LIMIT 10
    """
    
    try:
        driver = get_driver()
        records, _, _ = driver.execute_query(
            vector_search_cypher, 
            {"query_emb": embedding, "project_id": current_project}, 
            database_="neo4j"
        )
        
        if not records:
             return [types.TextContent(type="text", text="No similar nodes found (threshold > 0.3).")]
             
        results = [f"- [{r['type']}] {r['uid']}: {r['title']} (Score: {r['score']:.4f})" for r in records]
        return [types.TextContent(type="text", text="Semantically similar nodes:\n" + "\n".join(results))]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error during semantic search: {e}")]

async def tool_explain_physics(arguments: dict) -> list[types.TextContent]:
    """
    Explains why a tool is available or blocked at the current location.
    Introspects the Meta-Graph to provide reasoning and unlock paths.
    """
    tool_name = arguments.get("tool_name")
    
    # Get current context
    loc_uid = get_agent_location()
    current_node_type = get_node_type(loc_uid)
    allowed_tools = get_allowed_tool_names(current_node_type)
    
    driver = get_driver()
    
    # Check if tool is allowed
    is_allowed = tool_name in allowed_tools
    
    if is_allowed:
        # Tool is AVAILABLE — explain why
        
        # Check if it's a global tool
        global_query = """
        MATCH (a:Action {tool_name: $tool_name, scope: 'global'})
        RETURN a.uid as uid
        """
        global_records, _, _ = driver.execute_query(global_query, {"tool_name": tool_name}, database_="neo4j")
        
        if global_records:
            return [types.TextContent(
                type="text",
                text=f"✅ Действие ДОСТУПНО.\n\n"
                     f"📍 Ваша локация: (:{current_node_type} {{uid: '{loc_uid}'}})\n\n"
                     f"⚙️ Причина доступности:\n"
                     f"   Инструмент '{tool_name}' является ГЛОБАЛЬНЫМ (scope='global').\n"
                     f"   Он доступен из любой локации в графе."
            )]
        
        # Otherwise it's contextual
        contextual_query = """
        MATCH (nt:NodeType {name: $node_type})-[:CAN_PERFORM]->(a:Action {tool_name: $tool_name, scope: 'contextual'})
        RETURN a.uid as action_uid, a.target_type as target_type
        """
        contextual_records, _, _ = driver.execute_query(
            contextual_query, 
            {"node_type": current_node_type, "tool_name": tool_name}, 
            database_="neo4j"
        )
        
        if contextual_records:
            action_info = contextual_records[0]
            target_type = action_info.get("target_type", "N/A")
            
            return [types.TextContent(
                type="text",
                text=f"✅ Действие ДОСТУПНО.\n\n"
                     f"📍 Ваша локация: (:{current_node_type} {{uid: '{loc_uid}'}})\n\n"
                     f"⚙️ Причина доступности:\n"
                     f"   Мета-Граф содержит связь:\n"
                     f"   (:NodeType {{name: '{current_node_type}'}})-[:CAN_PERFORM]->(:Action {{tool_name: '{tool_name}'}})\n\n"
                     f"💡 Детали:\n"
                     f"   Target Type: {target_type if target_type != 'N/A' else 'любой'}"
            )]
    
    else:
        # Tool is BLOCKED — explain why and suggest path
        
        # Find which NodeTypes CAN use this tool
        unlock_query = """
        MATCH (nt:NodeType)-[:CAN_PERFORM]->(a:Action {tool_name: $tool_name})
        RETURN nt.name as node_type, a.target_type as target_type
        ORDER BY nt.name
        """
        unlock_records, _, _ = driver.execute_query(unlock_query, {"tool_name": tool_name}, database_="neo4j")
        
        if not unlock_records:
            return [types.TextContent(
                type="text",
                text=f"❌ Действие НЕДОСТУПНО.\n\n"
                     f"📍 Ваша локация: (:{current_node_type} {{uid: '{loc_uid}'}})\n\n"
                     f"⚙️ Причина блокировки:\n"
                     f"   Инструмент '{tool_name}' не существует в Мета-Графе или не привязан ни к одному NodeType.\n\n"
                     f"💡 Возможные причины:\n"
                     f"   1. Опечатка в названии инструмента\n"
                     f"   2. Инструмент ещё не реализован\n"
                     f"   3. Мета-Граф не содержит правил для этого инструмента"
            )]
        
        # Build unlock path suggestions
        unlock_paths = []
        for record in unlock_records:
            node_type = record["node_type"]
            target_type = record.get("target_type")
            
            if target_type:
                unlock_paths.append(f"   • Находясь в (:{node_type}), можно создать :{target_type}")
            else:
                unlock_paths.append(f"   • Находясь в (:{node_type}), можно использовать '{tool_name}'")
        
        # Suggest concrete steps
        first_unlock_type = unlock_records[0]["node_type"]
        
        return [types.TextContent(
            type="text",
            text=f"❌ Действие НЕДОСТУПНО.\n\n"
                 f"📍 Ваша локация: (:{current_node_type} {{uid: '{loc_uid}'}})\n\n"
                 f"⚙️ Причина блокировки:\n"
                 f"   Мета-Граф не содержит связи:\n"
                 f"   (:NodeType {{name: '{current_node_type}'}})-[:CAN_PERFORM]->(:Action {{tool_name: '{tool_name}'}})\n\n"
                 f"🚪 Где этот инструмент ДОСТУПЕН:\n" + "\n".join(unlock_paths) + "\n\n"
                 f"💡 Путь к действию:\n"
                 f"   1. Переместитесь в узел типа :{first_unlock_type}\n"
                 f"      → Используйте look_around для поиска соседей\n"
                 f"      → Используйте move_to(target_uid) для перемещения\n"
                 f"   2. Теперь '{tool_name}' будет доступен"
        )]



async def tool_get_full_context(arguments: dict) -> list[types.TextContent]:
    """
    Gets FULL context for a task:
    - Semantically similar nodes (embeddings)
    - Related Specs/Requirements (graph structure) 
    - Active Constraints (Meta-Graph)
    - Current location and neighbors
    - Graph statistics
    """
    query = arguments.get("query")
    
    driver = get_driver()
    loc_uid = get_agent_location()
    current_node_type = get_node_type(loc_uid)
    
    context_parts = []
    
    # === 1. CURRENT LOCATION ===
    context_parts.append("📍 **ТЕКУЩАЯ ЛОКАЦИЯ**")
    
    loc_query = "MATCH (n {uid: $uid}) RETURN n.title as title, labels(n)[0] as type"
    loc_rec, _, _ = driver.execute_query(loc_query, {"uid": loc_uid}, database_="neo4j")
    
    
    loc_title = ""
    loc_type = ""
    
    if loc_rec:
        loc_title = loc_rec[0].get("title", "N/A")
        loc_type = loc_rec[0].get("type", current_node_type)
        context_parts.append(f"   (:{loc_type} {{uid: '{loc_uid}'}})")
        context_parts.append(f"   Title: {loc_title}\n")
    else:
        # STRICT MODE: Fail if node doesn't exist to prevent working with phantom data
        return [types.TextContent(
            type="text",
            text=f"❌ PHYSICS ERROR (DATA CORRUPTION):\nCurrent location node '{loc_uid}' was NOT found in the Graph Database.\n\nACTION REQUIRED:\n1. Use 'sync_graph' to restore database from files.\n2. Or use 'move_to' to go to a known node (e.g. IDEA-Genesis)."
        )]
    
    # === 2. NEIGHBORS ===
    neighbors_query = """
    MATCH (current {uid: $uid})-[r]-(neighbor)
    RETURN neighbor.uid as uid, neighbor.title as title, 
           labels(neighbor)[0] as type, type(r) as rel_type
    LIMIT 5
    """
    neighbors_rec, _, _ = driver.execute_query(neighbors_query, {"uid": loc_uid}, database_="neo4j")
    
    if neighbors_rec:
        context_parts.append("🔗 **СОСЕДИ** (первые 5)")
        for n in neighbors_rec:
            rel = n["rel_type"]
            ntype = n["type"]
            nuid = n["uid"]
            ntitle = n.get("title", n.get("name", "N/A"))
            context_parts.append(f"   [{rel}] → (:{ntype} {{uid: '{nuid}'}}) — {ntitle}")
        context_parts.append("")
    
    # === 3. SEMANTICALLY SIMILAR NODES ===
    embedding = emb_manager.get_embedding(f"{loc_type} {loc_title}") # Changed to use loc_type and loc_title
    current_project = get_current_project_id() # Added
    
    if embedding:
        context_parts.append("🧠 **СЕМАНТИЧЕСКИ БЛИЗКИЕ НОДЫ** (top-5)")
        
        vector_search_cypher = """
        MATCH (n)
        WHERE n.embedding IS NOT NULL AND (n:Idea OR n:Spec OR n:Requirement OR n:Task OR n:Domain)
            AND (n.project_id = $project_id OR n.project_id IS NULL)
        WITH n, REDUCE(s = 0.0, i IN RANGE(0, size(n.embedding)-1) | s + n.embedding[i] * $query_emb[i]) as score
        WHERE score > 0.4
        RETURN n.uid as uid, n.title as title, labels(n)[0] as type, score
        ORDER BY score DESC LIMIT 5
        """
        
        sim_rec, _, _ = driver.execute_query(vector_search_cypher, {"query_emb": embedding, "project_id": current_project}, database_="neo4j")
        
        if sim_rec:
            for s in sim_rec:
                stype = s["type"]
                suid = s["uid"]
                stitle = s.get("title", "N/A")
                score = s["score"]
                context_parts.append(f"   [{stype}] {suid}: {stitle} (Score: {score:.3f})")
        else:
            context_parts.append("   (Не найдено похожих нод)")
        context_parts.append("")
    
    # === 4. RELATED SPECS & REQUIREMENTS ===
    context_parts.append("📋 **СВЯЗАННЫЕ SPECS & REQUIREMENTS**")
    
    related_query = """
    MATCH path = (current {uid: $uid})-[:DECOMPOSES*1..2]-(related)
    WHERE (related:Spec OR related:Requirement)
      AND (related.project_id = $project_id OR related.project_id IS NULL)
    RETURN DISTINCT related.uid as uid, related.title as title, labels(related)[0] as type
    LIMIT 10
    """
    related_rec, _, _ = driver.execute_query(related_query, {"uid": loc_uid, "project_id": current_project}, database_="neo4j")
    
    if related_rec:
        for r in related_rec:
            rtype = r["type"]
            ruid = r["uid"]
            rtitle = r.get("title", "N/A")
            context_parts.append(f"   [{rtype}] {ruid}: {rtitle}")
    else:
        context_parts.append("   (Нет связанных Specs/Requirements)")
    context_parts.append("")
    
    # === 5. ACTIVE CONSTRAINTS ===
    context_parts.append("⚠️ **АКТИВНЫЕ CONSTRAINTS** (применяются ко всем actions)")
    
    constraints_query = """
    MATCH (c:Constraint)
    RETURN c.uid as uid, c.rule_name as rule_name, c.error_message as error_message
    """
    constraints_rec, _, _ = driver.execute_query(constraints_query, database_="neo4j")
    
    if constraints_rec:
        for c in constraints_rec:
            cuid = c["uid"]
            crule = c.get("rule_name", "N/A")
            cerr = c.get("error_message", "")
            context_parts.append(f"   {cuid}: {crule}")
            if cerr:
                context_parts.append(f"      → {cerr}")
    else:
        context_parts.append("   (Нет активных constraints)")
    context_parts.append("")
    
    # === 6. GRAPH STATISTICS ===
    context_parts.append("📊 **СТАТИСТИКА ГРАФА**")
    
    stats_query = """
    MATCH (n)
    WHERE (n:Idea OR n:Spec OR n:Requirement OR n:Task OR n:Domain)
      AND (n.project_id = $project_id OR n.project_id IS NULL)
    RETURN labels(n)[0] as type, count(n) as count
    ORDER BY count DESC
    """
    stats_rec, _, _ = driver.execute_query(stats_query, {"project_id": current_project}, database_="neo4j")
    
    if stats_rec:
        for s in stats_rec:
            stype = s["type"]
            scount = s["count"]
            context_parts.append(f"   {stype}: {scount} узлов")
    context_parts.append("")
    
    # === 7. RECOMMENDATIONS ===
    context_parts.append("💡 **РЕКОМЕНДАЦИИ**")
    context_parts.append("   • Используйте create_concept для создания новых узлов")
    context_parts.append("   • Используйте link_nodes для связывания с найденными узлами")
    context_parts.append("   • Проверьте Constraints перед созданием контента")
    
    full_text = "\n".join(context_parts)
    
    return [types.TextContent(type="text", text=full_text)]


async def tool_switch_project(arguments: dict) -> list[types.TextContent]:
    """
    Switches the active project context.
    Updates global state (ACTIVE_PROJECT_ID, ACTIVE_PROJECT_ROOT).
    """
    project_id = arguments.get("project_id")
    # For now, we assume root is managed externally or stays same for simple test
    # In full version, this would check if project exists in DB.
    
    if not project_id:
        return [types.TextContent(type="text", text="Error: project_id is required")]
        
    # Switch Global State
    # Note: project_root argument can be added later
    set_current_project(project_id, WORKSPACE_ROOT)
    
    return [types.TextContent(type="text", text=f"✅ **SWITCHED PROJECT**\n\nActive Project: `{project_id}`\nRoot: `{WORKSPACE_ROOT}`\n\nAll subsequent queries will be filtered by this project_id.")]


async def tool_set_workflow(arguments: dict) -> list[types.TextContent]:
    """
    Sets the agent's active workflow mode.
    Modes: Architect, Builder, Auditor.
    """
    mode = arguments.get("mode")
    if not mode:
        return [types.TextContent(type="text", text="Error: mode is required")]
    
    try:
        set_workflow_state(mode)
        
        # Explain what changed
        explanation = ""
        if mode == "Architect":
            explanation = "🏗️ **ARCHITECT MODE**: You can design graph (Idea/Spec/Req). Coding tools are LOCKED."
        elif mode == "Builder":
            explanation = "👷 **BUILDER MODE**: You can write code and create Tasks. Graph design tools are RESTRICTED."
        elif mode == "Auditor":
            explanation = "🕵️ **AUDITOR MODE**: Read-only access to Code and Graph. Modification tools are LOCKED."
            
        return [types.TextContent(type="text", text=f"✅ **WORKFLOW SET**\n\n{explanation}")]
    except ValueError as e:
        return [types.TextContent(type="text", text=f"Error: {e}")]


async def tool_map_codebase(arguments: dict) -> list[types.TextContent]:
    """
    Scans codebase and maps it to Neo4j.
    """
    if not CodebaseMapper:
         return [types.TextContent(type="text", text="Error: CodebaseMapper not loaded. Please ensure Tools/codebase_mapper.py exists.")]
         
    mapper = CodebaseMapper()
    try:
        count = mapper.scan_and_map()
        return [types.TextContent(type="text", text=f"✅ Data Mapped Successfully.\nProcessed {count} nodes (Files, Classes, Functions).\nGraph is now aware of the codebase structure.")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error mapping codebase: {e}")]


async def tool_read_node(arguments: dict) -> list[types.TextContent]:
    """
    Reads the FULL content of a node by UID.
    Returns title, description, and body text.
    
    If content is not stored in Neo4j, attempts to read from Markdown file.
    """
    uid = arguments.get("uid")
    if not uid:
        return [types.TextContent(type="text", text="Error: uid is required")]
    
    driver = get_driver()
    current_project = get_current_project_id()
    
    # 1. Fetch node properties from Neo4j (Filtered by Project)
    query = """
    MATCH (n {uid: $uid})
    RETURN labels(n)[0] as type,
           n.title as title,
           n.description as description,
           n.content as content,
           n.status as status,
           n.project_id as project_id
    """
    
    try:
        records, _, _ = driver.execute_query(query, {"uid": uid}, database_="neo4j")
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error querying node: {e}")]
    
    if not records:
        return [types.TextContent(type="text", text=f"❌ Node '{uid}' not found in graph")]
    
    record = records[0]
    # CHECK ACCESS
    node_project = record.get("project_id")
    if node_project and node_project != current_project:
        return [types.TextContent(type="text", text=f"⛔ ACCESS DENIED: Node '{uid}' belongs to project '{node_project}', but you are in '{current_project}'.")]

    node_type = record.get("type", "Unknown")
    title = record.get("title", "N/A")
    description = record.get("description", "")
    content = record.get("content", "")
    status = record.get("status", "N/A")
    created_at = record.get("created_at", "N/A")
    
    # 2. If content is empty, try to read from Markdown file
    if not content:
        # Use Centralized Logic
        file_path = sync_tool.get_file_path(uid, node_type)
        
        if os.path.exists(file_path):
            try:
                # Use centralized parser
                _, body = sync_tool.parse_markdown_file(file_path)
                content = body or "(No content body in file)"
            except Exception as e:
                content = f"(Error reading file: {e})"
        else:
            content = "(No content stored in database or file)"
    
    # 3. Format output
    output_parts = []
    output_parts.append(f"📖 **NODE: {uid}**")
    output_parts.append(f"")
    output_parts.append(f"**Type:** {node_type}")
    output_parts.append(f"**Title:** {title}")
    output_parts.append(f"**Status:** {status}")
    output_parts.append(f"")
    
    if description:
        output_parts.append(f"**Description:**")
        output_parts.append(description)
        output_parts.append(f"")
    
    if content:
        # Limit content to prevent token explosion
        MAX_CONTENT_LENGTH = 8000
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH] + f"\n\n... [TRUNCATED - {len(content)} chars total]"
        
        output_parts.append(f"**Content:**")
        output_parts.append("```")
        output_parts.append(content)
        output_parts.append("```")
    
    return [types.TextContent(type="text", text="\n".join(output_parts))]



async def tool_find_orphans(arguments: dict) -> list[types.TextContent]:
    """
    Finds isolated nodes (orphans) that have NO effective connection to the main graph hierarchy.
    The "Main Graph" is defined as the set of nodes reachable from the 'IDEA-Genesis' root.
    
    This finds:
    1. Absolute orphans (0 connections)
    2. "Micro-islands" (Nodes connected to each other but isolated from the main tree)
    """
    limit = arguments.get("limit", 50)
    driver = get_driver()
    current_project = get_current_project_id()
    
    output_lines = []
    
    try:
        # 1. ABSOLUTE ORPHANS (Degree 0)
        query_absolute = """
        MATCH (n)
        WHERE (n.project_id = $project_id OR n.project_id IS NULL)
          AND NOT (n:NodeType)
          AND NOT (n)--()
        RETURN n.uid as uid, labels(n)[0] as type, n.title as title
        LIMIT $limit
        """
        
        abs_records, _, _ = driver.execute_query(query_absolute, 
            {"project_id": current_project, "limit": limit}, 
            database_="neo4j")
            
        if abs_records:
             output_lines.append(f"Found {len(abs_records)} absolute orphans (0 links):")
             for r in abs_records:
                 output_lines.append(f"- [{r['type']}] {r['uid']}: {r.get('title', 'N/A')}")
        
        # Determine how many more we need
        remaining_limit = limit - len(abs_records)
        
        if remaining_limit > 0:
            # 2. ISLAND DETECTION (Connectivity check to IDEA-Genesis)
            # Find nodes that have relationships but are NOT connected to IDEA-Genesis
            
            island_query = """
            MATCH (root:Idea {uid: 'IDEA-Genesis'})
            // Get all nodes in the Main Component via VERTICAL relationships only
            // DECOMPOSES: Hierarchy (Idea->Spec->Req... File->Class->Func)
            // IMPLEMENTS: Realization (File->Req...)
            CALL apoc.path.subgraphNodes(root, {relationshipFilter: 'DECOMPOSES|IMPLEMENTS'}) YIELD node as connected_node
            WITH collect(connected_node) as main_component_nodes
            
            MATCH (n)
            WHERE (n.project_id = $project_id OR n.project_id IS NULL)
              AND NOT (n:NodeType)
              AND NOT n IN main_component_nodes
              AND (n)--() // Only consider nodes that HAVE links (absolute orphans already found)
              
            RETURN n.uid as uid, labels(n)[0] as type, n.title as title
            LIMIT $limit
            """
            
            try:
                island_records, _, _ = driver.execute_query(island_query, 
                    {"project_id": current_project, "limit": remaining_limit}, 
                    database_="neo4j")
                    
                if island_records:
                    if output_lines: output_lines.append("") # Spacer
                    output_lines.append(f"Found {len(island_records)} island nodes (isolated groups):")
                    for r in island_records:
                        output_lines.append(f"- [{r['type']}] {r['uid']}: {r.get('title', 'N/A')}")
            except Exception as e:
                output_lines.append(f"\n⚠️ Warning: Island detection failed (possibly APOC missing): {e}")

        if not output_lines:
             return [types.TextContent(type="text", text="✅ No orphans or islands found! The graph is fully connected (to 'IDEA-Genesis').")]
             
        return [types.TextContent(type="text", text="\n".join(output_lines))]
        
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error finding orphans: {e}")]


async def tool_illuminate_path(arguments: dict) -> list[types.TextContent]:
    """
    🔦 ILLUMINATE THE PATH
    
    Given a task/query, finds the relevant path through the graph and returns
    FULL CONTENT of all nodes on that path.
    
    Algorithm:
    1. Semantic search to find entry point (most relevant node)
    2. Traverse UP to root (Idea)
    3. Traverse DOWN to leaves (Tasks/Files)
    4. Find lateral connections (DEPENDS_ON, CONFLICT)
    5. Return content of all nodes on the path
    """
    query = arguments.get("query")
    if not query:
        return [types.TextContent(type="text", text="Error: query is required")]
    
    driver = get_driver()
    output_parts = []
    
    output_parts.append("🔦 **PATH ILLUMINATION**")
    output_parts.append(f"   Query: \"{query}\"")
    output_parts.append("=" * 60)
    output_parts.append("")
    
    # 1. SEMANTIC SEARCH - Find entry point
    query_embedding = emb_manager.get_embedding(query)
    current_project = get_current_project_id()
    
    if not query_embedding:
        return [types.TextContent(type="text", text="Error: Could not generate embedding for query")]
    
    # Find most relevant node as entry point (Filtered by Project)
    search_query = """
    MATCH (n)
    WHERE n.embedding IS NOT NULL 
        AND (n:Idea OR n:Spec OR n:Requirement OR n:Task OR n:Domain)
        AND (n.project_id = $project_id OR n.project_id IS NULL)
    WITH n, REDUCE(s = 0.0, i IN RANGE(0, size(n.embedding)-1) | s + n.embedding[i] * $emb[i]) as score
    WHERE score > 0.5
    RETURN n.uid as uid, n.title as title, labels(n)[0] as type, score
    ORDER BY score DESC
    LIMIT 1
    """
    
    entry_rec, _, _ = driver.execute_query(
        search_query, 
        {"emb": query_embedding, "project_id": current_project}, 
        database_="neo4j"
    )
    
    if not entry_rec:
        output_parts.append("❌ No relevant nodes found for this query.")
        output_parts.append("   Try a different search term or check if graph has embeddings.")
        return [types.TextContent(type="text", text="\n".join(output_parts))]
    
    entry_uid = entry_rec[0]['uid']
    entry_title = entry_rec[0]['title']
    entry_type = entry_rec[0]['type']
    entry_score = entry_rec[0]['score']
    
    output_parts.append(f"📍 **ENTRY POINT** (similarity: {entry_score:.2f})")
    output_parts.append(f"   {entry_uid} ({entry_type}): {entry_title}")
    output_parts.append("")
    
    # 2. COLLECT PATH NODES
    # Get all nodes on the vertical path (up and down) + lateral connections
    path_query = """
    // Find entry node
    MATCH (entry {uid: $entry_uid})
    
    // Collect path UP (to ancestors)
    OPTIONAL MATCH pathUp = (entry)<-[:DECOMPOSES*1..5]-(ancestor)
    
    // Collect path DOWN (to descendants)
    OPTIONAL MATCH pathDown = (entry)-[:DECOMPOSES*1..5]->(descendant)
    
    // Collect lateral connections
    OPTIONAL MATCH (entry)-[lateral:DEPENDS_ON|CONFLICT|IMPLEMENTS]-(related)
    
    // Return all unique nodes
    WITH entry,
         COLLECT(DISTINCT ancestor) as ancestors,
         COLLECT(DISTINCT descendant) as descendants,
         COLLECT(DISTINCT related) as laterals
    
    RETURN entry, ancestors, descendants, laterals
    """
    
    path_rec, _, _ = driver.execute_query(
        path_query,
        {"entry_uid": entry_uid},
        database_="neo4j"
    )
    
    if not path_rec:
        output_parts.append("❌ Could not trace path from entry point.")
        return [types.TextContent(type="text", text="\n".join(output_parts))]
    
    record = path_rec[0]
    entry_node = record['entry']
    ancestors = record['ancestors'] or []
    descendants = record['descendants'] or []
    laterals = record['laterals'] or []
    
    # Collect all UIDs to fetch content
    all_uids = set()
    all_uids.add(entry_uid)
    for node in ancestors:
        if node and node.get('uid'):
            all_uids.add(node['uid'])
    for node in descendants:
        if node and node.get('uid'):
            all_uids.add(node['uid'])
    
    lateral_uids = set()
    for node in laterals:
        if node and node.get('uid'):
            lateral_uids.add(node['uid'])
    
    output_parts.append(f"📊 **PATH STATISTICS**")
    output_parts.append(f"   • Vertical path: {len(all_uids)} nodes")
    output_parts.append(f"   • Lateral connections: {len(lateral_uids)} nodes")
    output_parts.append("")
    
    # 3. FETCH CONTENT OF ALL PATH NODES
    content_query = """
    MATCH (n)
    WHERE n.uid IN $uids
    RETURN n.uid as uid, 
           labels(n)[0] as type,
           n.title as title,
           SUBSTRING(COALESCE(n.description, ''), 0, 500) as description,
           SUBSTRING(COALESCE(n.content, ''), 0, 500) as content
    ORDER BY 
        CASE labels(n)[0]
            WHEN 'Idea' THEN 1
            WHEN 'Spec' THEN 2
            WHEN 'Domain' THEN 3
            WHEN 'Requirement' THEN 4
            WHEN 'Task' THEN 5
            ELSE 6
        END
    """
    
    # Vertical path content
    output_parts.append("🛤️ **VERTICAL PATH** (Idea → Spec → Req → Task)")
    output_parts.append("-" * 50)
    
    content_rec, _, _ = driver.execute_query(
        content_query,
        {"uids": list(all_uids)},
        database_="neo4j"
    )
    
    for node in content_rec:
        uid = node['uid']
        ntype = node['type']
        title = node['title'] or uid
        desc = node['description'] or ""
        content = node['content'] or ""
        
        # Marker for entry point
        marker = " ← ENTRY" if uid == entry_uid else ""
        
        output_parts.append(f"\n**[{ntype}] {uid}**{marker}")
        output_parts.append(f"Title: {title}")
        
        if desc:
            output_parts.append(f"Description: {desc[:300]}...")
        
        if content:
            output_parts.append(f"Content: {content[:300]}...")
    
    # 4. LATERAL CONNECTIONS
    if lateral_uids:
        output_parts.append("")
        output_parts.append("↔️ **LATERAL CONNECTIONS** (DEPENDS_ON, CONFLICT, IMPLEMENTS)")
        output_parts.append("-" * 50)
        
        lateral_rec, _, _ = driver.execute_query(
            content_query,
            {"uids": list(lateral_uids)},
            database_="neo4j"
        )
        
        for node in lateral_rec:
            uid = node['uid']
            ntype = node['type']
            title = node['title'] or uid
            desc = node['description'] or ""
            
            output_parts.append(f"\n**[{ntype}] {uid}**")
            output_parts.append(f"Title: {title}")
            if desc:
                output_parts.append(f"Description: {desc[:200]}...")
    
    # 5. ACTIVE CONSTRAINTS reminder
    output_parts.append("")
    output_parts.append("⚠️ **REMEMBER CONSTRAINTS:**")
    output_parts.append("   • Russian language required (min 25% Cyrillic)")
    output_parts.append("   • No [[WikiLinks]] - use link_nodes tool")
    output_parts.append("   • Check available actions with look_around")
    
    return [types.TextContent(type="text", text="\n".join(output_parts))]


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
        import secrets

        # --- IRON DOME: TOKEN AUTHENTICATION ---
        # Generate or load auth token
        MCP_AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN")
        if not MCP_AUTH_TOKEN:
            # Generate a new token if not provided
            MCP_AUTH_TOKEN = secrets.token_hex(32)
            print(f"⚠️  WARNING: MCP_AUTH_TOKEN not set. Generated temporary token.", file=sys.stderr)
            print(f"🔑 Token (share with mcp_client_adapter): {MCP_AUTH_TOKEN}", file=sys.stderr)
        else:
            print(f"🔒 Iron Dome: Token authentication ENABLED", file=sys.stderr)

        def get_header(scope, name):
            """Extract header value from ASGI scope."""
            name_lower = name.lower().encode()
            for header_name, header_value in scope.get("headers", []):
                if header_name == name_lower:
                    return header_value.decode()
            return None

        sse = SseServerTransport("/messages")

        async def app(scope, receive, send):
            """Pure ASGI entrypoint for SSE support with Iron Dome authentication."""
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
                
                # --- IRON DOME: AUTHENTICATE ALL REQUESTS ---
                auth_token = get_header(scope, "X-MCP-Auth-Token")
                
                # Allow /health endpoint without auth (for Docker healthchecks)
                if path == "/health":
                    response = Response("OK", status_code=200)
                    await response(scope, receive, send)
                    return
                
                # Validate token for all other endpoints
                if auth_token != MCP_AUTH_TOKEN:
                    print(f"🚫 Iron Dome: BLOCKED unauthorized request to {path}", file=sys.stderr)
                    print(f"   Received token: {auth_token[:8] if auth_token else 'None'}...", file=sys.stderr)
                    response = Response(
                        "🚫 IRON DOME: Unauthorized. Valid X-MCP-Auth-Token header required.",
                        status_code=403
                    )
                    await response(scope, receive, send)
                    return
                
                # Authenticated - proceed normally
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
        print("🛡️  Iron Dome: Token authentication ACTIVE", file=sys.stderr)
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


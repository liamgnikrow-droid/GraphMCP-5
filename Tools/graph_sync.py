import os
import json
import glob
from neo4j import GraphDatabase
import time
import yaml
import re

import sys
# Add parent directory to path if running as script
if __name__ == "__main__" and __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    from db_config import get_driver, close_driver, WORKSPACE_ROOT

# Folder Mapping
TYPE_TO_FOLDER = {
    "Epic": "0_Epics",
    "Idea": "1_Ideas",
    "Spec": "2_Specs",
    "Task": "3_Tasks",
    "Bug": "3_Tasks",
    "Requirement": "4_Requirements",
    "Domain": "5_Domain",
    "Roadmap": "2_Specs",
    "SpecItem": "2_Specs/Items",
    "File": "6_Code/Files",
    "Class": "6_Code/Classes",
    "Function": "6_Code/Functions",
    "Module": "6_Code/Modules",
    # Architecture Nodes
    "Constraint": "Graph_Physics",
    "Action": "Graph_Physics",
    "NodeType": "Graph_Physics"
}

class GraphSync:
    def __init__(self):
        self.driver = None

    def get_driver(self):
        return get_driver()

    def close(self):
        if self.driver:
            self.driver.close()

    def fetch_node(self, uid: str):
        """
        Fetches full node state from Neo4j:
        - Properties
        - Labels (Type)
        - Incoming/Outgoing Relationships
        """
        drv = self.get_driver()

        # 1. Fetch Node Properties
        query_node = """
        MATCH (n)
        WHERE n.uid = $uid
        RETURN n, labels(n) as labels
        """
        records, _, _ = drv.execute_query(query_node, {"uid": uid}, database_="neo4j")

        if not records:
            return None

        node_props = dict(records[0]['n'])
        labels = records[0]['labels']

        # Determine Primary Type
        node_type = "Unknown"
        # Prioritize known types
        for label in labels:
            if label in TYPE_TO_FOLDER:
                node_type = label
                break

        # 2. Fetch Relationships
        # STRICT CANONICAL: We only care about IMPLEMENTS, DECOMPOSES, DEPENDS_ON, CONFLICT, IMPORTS
        # RELATED_TO is forbidden and ignored.
        query_rels = """
        MATCH (n {uid: $uid})-[r]-(other)
        WHERE type(r) IN ['IMPLEMENTS', 'DECOMPOSES', 'DEPENDS_ON', 'CONFLICT', 'RELATES_TO', 'IMPORTS']
        RETURN
            startNode(r).uid as source,
            endNode(r).uid as target,
            type(r) as type,
            r.justification as justification,
            r.auto as auto,
            other.title as title,
            other.name as name,
            other.uid as other_uid
        """
        rel_records, _, _ = drv.execute_query(query_rels, {"uid": uid}, database_="neo4j")

        relationships = []
        for rel in rel_records:
            is_outgoing = (rel['source'] == uid)
            other_uid = rel['other_uid']
            other_title = rel['title'] or rel['name'] or other_uid

            relationships.append({
                "type": rel['type'],
                "target": other_uid if is_outgoing else uid,
                "other_uid": other_uid,
                "other_title": other_title,
                "direction": "OUT" if is_outgoing else "IN",
                "justification": rel.get('justification'),
                "auto": rel.get('auto', False)
            })

        return {
            "props": node_props,
            "type": node_type,
            "labels": labels,
            "relationships": relationships
        }

    def render_markdown(self, node_data: dict) -> str:
        """
        Generates premium Markdown content for Obsidian + Juggl.
        """
        props = node_data['props']
        node_type = node_data['type']
        uid = props.get('uid')
        title = props.get('title') or props.get('name') or uid
        description = props.get('description') or ""
        status = props.get('status', 'Draft')

        # CSS Classes for Juggl and Modern Look
        css_classes = ["juggl-node", f"type-{node_type.lower()}", "premium-card"]
        if node_type in ["Task", "Bug"]:
            css_classes.append("kanban-card")
        if node_type == "Epic":
            css_classes.append("epic-node")
        
        # Frontmatter
        fm_lines = ["---"]
        fm_lines.append(f'uid: "{uid}"')
        fm_lines.append(f'title: "{title}"')
        fm_lines.append(f'type: "{node_type}"')

        # Add all metadata properties
        # EXCLUDE properties that will be rendered as relationships to avoid YAML key duplication
        excluded_keys = [
            'uid', 'type', 'title', 'description', 'created_at', 'updated_at', 'content', 'embedding',
            # Relationship properties (rendered separately as YAML lists below)
            'decomposes', 'implements', 'depends_on', 'relates_to', 'restricts', 'can_perform'
        ]
        
        for key, val in props.items():
            if key not in excluded_keys:
                if val is not None:
                    if isinstance(val, bool):
                        fm_lines.append(f'{key}: {str(val).lower()}')
                    elif isinstance(val, (int, float)):
                        fm_lines.append(f'{key}: {val}')
                    else:
                        # Escape quotes
                        safe_val = str(val).replace('"', '\\"')
                        fm_lines.append(f'{key}: "{safe_val}"')

        fm_lines.append(f'tags: [graph/{node_type.lower()}, state/{status.lower().replace(" ", "_")}]')
        fm_lines.append(f'cssclasses: [{", ".join(css_classes)}]')

        # --- RELATIONSHIPS (YAML ONLY) ---
        rels = sorted(node_data['relationships'], key=lambda x: (x['type'], x['other_uid']))
        
        # We store relationships in a structured way that Juggl can exploit
        # and as flat properties for Obsidian's native 'Properties' view.
        typed_rels = {}
        for rel in rels:
            # We treat OUTGOING as primary semantic links
            if rel['direction'] == 'OUT':
                rel_type = rel['type'].lower().replace('_', '-')
                target = rel['other_uid']
                
                if rel_type not in typed_rels:
                    typed_rels[rel_type] = []
                typed_rels[rel_type].append(f"[[{target}]]")

        # Add to frontmatter
        for key, links in typed_rels.items():
            if links:
                # Obsidian standard for multiple links in properties
                fm_lines.append(f"{key}:")
                for link in links:
                    fm_lines.append(f"  - \"{link}\"")

        fm_lines.append("---")

        # Body
        body = []
        body.append(f"# {title}")
        body.append("")
        
        # Status Bar / Breadcrumbs (Optional but premium)
        body.append(f"> [!abstract] {node_type} Context")
        body.append(f"> **ID:** `{uid}` | **Status:** `{status}`")
        body.append("")

        # Content / Description Handling
        # PRIORITY: Content (Full Body) > Description (Metadata)
        # If Content exists, it usually subsumes the Description (as per import logic).
        # We render Content under the "## Description" header.
        
        content = props.get('content')
        
        if content:
            body.append("## Description")
            # normalization check for legacy title
            check_content = content.strip()
            if check_content.startswith(f"# {title}"):
                 lines = check_content.split('\n')
                 content = "\n".join(lines[1:]).strip()
            
            body.append(content)
            body.append("")
        elif description:
            # Fallback if no content but description exists
            body.append("## Description")
            body.append(description)
            body.append("")
         
        return "\n".join(fm_lines + body)

    def parse_markdown_file(self, file_path: str):
        """
        Robustly parses a Markdown file into Frontmatter (dict) and Body (str).
        Returns: (frontmatter_dict, body_string)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            fm_lines = []
            body_start_idx = 0
            
            # 1. Extract Frontmatter
            if lines and lines[0].strip() == "---":
                for i in range(1, len(lines)):
                    if lines[i].strip() == "---":
                        body_start_idx = i + 1
                        break
                    fm_lines.append(lines[i])
            
            frontmatter = {}
            if fm_lines:
                try:
                    frontmatter = yaml.safe_load("\n".join(fm_lines)) or {}
                except yaml.YAMLError as e:
                    print(f"⚠️ YAML Error in {file_path}: {e}")
            
            # DEBUG
            print(f"DEBUG: Parsed FM for {file_path}: {frontmatter.keys()}")
            print(f"DEBUG: Props: {frontmatter}")
            
            # 2. Extract Body
            raw_body = "\n".join(lines[body_start_idx:]).strip()
            
            # DUPLICATION FIX: Strip conflict markers
            conflict_marker = "## 🔄 SYNC CONFLICT: Database Version"
            if conflict_marker in raw_body:
                raw_body = raw_body.split(conflict_marker)[0].strip()
            
            # 3. Clean Body (Skip System Headers)
            body_lines = raw_body.split('\n')
            clean_lines = []
            skipping_metadata = True
            
            for line in body_lines:
                sline = line.strip()
                if skipping_metadata:
                    if not sline: continue
                    if sline.startswith("# "): continue # Skip H1
                    if sline.startswith("> "): continue # Skip Context
                    if sline.startswith("**ID:**") or sline.startswith("**Type:**") or sline.startswith("**Status:**"): continue
                    if sline == "## Description" or sline == "## Content": continue
                    skipping_metadata = False
                    clean_lines.append(line)
                else:
                    if sline == "## Description" or sline == "## Content": continue
                    clean_lines.append(line)
            
            return frontmatter, "\n".join(clean_lines).strip()

        except Exception as e:
            print(f"⚠️ Error parsing markdown {file_path}: {e}")
            return {}, ""

    def extract_body_from_markdown(self, file_path: str) -> str:
        """
        Wrapper for backward compatibility. Returns only body.
        """
        _, body = self.parse_markdown_file(file_path)
        return body

    def push_file_to_db(self, file_path: str):
        """
        Reads a local Markdown file and updates the Neo4j Node.
        """
        print(f"🔄 GraphSync: Pushing {file_path} to Neo4j...")
        
        # 1. Parse File
        frontmatter, body = self.parse_markdown_file(file_path)
        
        uid = frontmatter.get('uid')
        if not uid:
            print(f"⚠️  Skipping {file_path}: No UID in frontmatter.")
            return

        # 2. Prepare Properties
        props = {}
        # Map Standard YAML keys to DB properties
        keys_to_sync = ['title', 'description', 'status', 'project_id']
        for k in keys_to_sync:
            if k in frontmatter:
                props[k] = frontmatter[k]
        
        # Sync Content
        if body:
            props['content'] = body
            
        # 3. DB Update
        drv = self.get_driver()
        
        
        # Determine Label for MERGE/CREATE
        node_type = frontmatter.get('type')
        if not node_type:
            # Fallback: Try to fetch existing to update, or fail
            print(f"⚠️  No 'type' in frontmatter for {uid}. Assuming update only.")
            query_check = "MATCH (n {uid: $uid}) RETURN count(n) as c"
            recs, _, _ = drv.execute_query(query_check, {"uid": uid}, database_="neo4j")
            if recs[0]['c'] == 0:
                print(f"❌ Node {uid} does not exist and no type provided. Cannot create.")
                return

        # A. Update Properties (and Create if needed)
        set_clauses = []
        for k, v in props.items():
            set_clauses.append(f"n.{k} = ${k}")
        
        if set_clauses:
            # If we know the type, use it in MERGE
            if node_type:
                # Sanitize type (simple alpha check)
                safe_type = "".join(x for x in node_type if x.isalnum())
                # Cypher doesn't allow dynamic labels in MERGE easily without APOC or string formatting
                query = f"""
                MERGE (n:{safe_type} {{uid: $uid}})
                SET {", ".join(set_clauses)}, n.updated_at = datetime()
                RETURN n
                """
            else:
                # Update existing only
                query = f"""
                MATCH (n {{uid: $uid}})
                SET {", ".join(set_clauses)}, n.updated_at = datetime()
                RETURN n
                """
            
            props['uid'] = uid
            try:
                drv.execute_query(query, props, database_="neo4j")
                print(f"✅ Synced {uid} ({node_type or 'Existing'}) to DB")
            except Exception as e:
                print(f"❌ DB Sync Error for {uid}: {e}")

        # B. Update Relationships (Optional Step: Sync Links from Frontmatter?)
        # For now, we focusing on CONTENT sync. Link sync is riskier without full schema checks.
        # But user asked for bi-directional. Let's do partial link sync (safe ones).
        # We look for keys in YAML that match known relationships (implements, decomposes, etc)
        # Note: Frontmatter usually has `implements: \n - "[[UID]]"`
        
        # (Link sync implementation deferred to avoid complexity in this step)



    def get_file_path(self, uid: str, node_type: str) -> str:
        """
        Determines the absolute file path for a node.
        """
        subfolder = TYPE_TO_FOLDER.get(node_type, "9_Unclassified")
        filename = f"{uid}.md"
        safe_filename = filename.replace("/", "_").replace("\\", "_")
        dir_path = os.path.join(WORKSPACE_ROOT, "Graph_Export", subfolder)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, safe_filename)

    def sync_node(self, uid: str, sync_connected: bool = False):
        """
        Full Sync: Fetch -> Render -> Write.
        If sync_connected is True, also syncs nodes directly connected to this one.
        
        SAFE MODE: If file exists and Neo4j 'content' is empty, preserve existing file body.
        """
        node_data = self.fetch_node(uid)
        if not node_data:
            print(f"⚠️ GraphSync: Node {uid} not found in Neo4j.")
            return None

        node_type = node_data['type']
        
        # SKIP SYSTEM NODES (Clean Slate Architecture)
        # Note: We now ALLOW Action and Constraint to sync because they are part of architectural documentation.
        # But we still skip purely internal schema nodes (NodeType).
        if node_type in ['NodeType']:
            # print(f"ℹ️ GraphSync: Skipping system node {uid} (Type: {node_type})")
            return None

        file_path = self.get_file_path(uid, node_type)
        
        
        # === CONTENT MERGE STRATEGY ===
        # Priority 1: Content from Neo4j (if exists)
        # Priority 2: Existing Body from File (if Neo4j content is empty)
        
        db_content = node_data['props'].get('content', "").strip()
        existing_body = ""
        conflict_detected = False
        
        if os.path.exists(file_path):
             existing_body = self.extract_body_from_markdown(file_path).strip()
        
        # === CONTENT PRIORITY LOGIC ===
        # For Idea and Spec, we TRUST THE DISK more than the DB for content.
        # This prevents accidental overwrites when tools rebuild links but haven't synced content yet.
        
        if node_type in ['Idea', 'Spec'] and existing_body:
             # Always use disk content.
             # If DB differs, we silently update our internal state to match disk 
             # before rendering, effectively "adopting" the disk content.
             if db_content != existing_body:
                 print(f"🔄 GraphSync: Adopting LOCAL content for {node_type} {uid} (Disk Priority).")
                 node_data['props']['content'] = existing_body
                 # Optional: Schedule a DB update? For now, we just don't overwrite the file with old DB data.
        
        else:
            # Standard Logic for other types / conflict detection
            def normalize(text):
                return "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    
            db_norm = normalize(db_content)
            file_norm = normalize(existing_body)
    
            if db_content and existing_body and db_norm != file_norm:
                # CONFLICT DETECTED
                print(f"⚠️ Conflict details for {uid}:")
                conflict_detected = True
                node_data['props']['content'] = existing_body # Safe Default: Keep local
                
            elif existing_body and not db_content:
                # DB is empty, preserve file
                node_data['props']['content'] = existing_body
        
        # Render
        content = self.render_markdown(node_data)
        
        # Handle Conflict Append
        if conflict_detected:
            content += "\n\n"
            content += "## 🔄 SYNC CONFLICT: Database Version\n"
            content += "> [!warning] Database content differs from local file.\n"
            content += "> Below is the version from Neo4j Graph:\n\n"
            content += db_content
            
            # Create BUG node in Graph
            bug_uid = f"BUG-Conflict-{uid}"
            print(f"⚠️  CONFLICT detected for {uid}. Creating {bug_uid}...")
            
            bug_query = """
            MATCH (n {uid: $uid})
            MERGE (b:Bug {uid: $bug_uid})
            SET b.title = 'Sync Conflict: ' + $uid,
                b.description = 'Content mismatch between Obsidian (Local) and Neo4j (DB). Please resolve in file.',
                b.status = 'Open',
                b.created_at = datetime()
            MERGE (b)-[:RELATES_TO]->(n)
            """
            try:
                drv = self.get_driver()
                drv.execute_query(bug_query, {"uid": uid, "bug_uid": bug_uid}, database_="neo4j")
                print(f"🐛 Created Bug: {bug_uid}")
            except Exception as e:
                print(f"❌ Failed to create conflict bug: {e}")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ GraphSync: Synced {uid} to {file_path}")

        if sync_connected:
            print(f"🔄 GraphSync: Syncing neighbors of {uid}...")
            for rel in node_data['relationships']:
                neighbor_uid = rel['other_uid']
                self.sync_node(neighbor_uid, sync_connected=False) # Avoid recursion loop

        return file_path

    def delete_node(self, uid: str):
        """
        Removes the markdown file associated with a UID.
        Neo4j deletion must be handled separately.
        """
        # We don't know the type easily without fetching, so we search all folders
        export_root = os.path.join(WORKSPACE_ROOT, "Graph_Export")
        filename = f"{uid}.md"
        safe_filename = filename.replace("/", "_").replace("\\", "_")
        
        found = False
        for root, dirs, files in os.walk(export_root):
            if safe_filename in files:
                file_path = os.path.join(root, safe_filename)
                os.remove(file_path)
                print(f"🗑️ GraphSync: Removed file {file_path}")
                found = True
        
        if not found:
            print(f"ℹ️ GraphSync: No file found for {uid} to delete.")
        return found

    def sync_all(self):
        """
        Regenerate ALL markdown files from Neo4j.
        """
        drv = self.get_driver()

        query = "MATCH (n) RETURN n.uid as uid"
        records, _, _ = drv.execute_query(query, database_="neo4j")

        count = 0
        for r in records:
            uid = r['uid']
            if uid:
                self.sync_node(uid)
                count += 1

        return f"Synced {count} nodes."

if __name__ == "__main__":
    # Test run
    syncer = GraphSync()
    syncer.sync_all()

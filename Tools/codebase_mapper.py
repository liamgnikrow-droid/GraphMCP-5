
import os
import ast
import hashlib
import re
from typing import List, Dict, Set

# Try importing local modules, handling both script and package execution
try:
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    try:
        from db_config import get_driver, close_driver, WORKSPACE_ROOT
    except ImportError:
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT

class CodebaseMapper:
    def __init__(self, project_root: str = WORKSPACE_ROOT):
        self.project_root = project_root
        self.driver = get_driver()
        self.ignore_dirs = {'.git', 'node_modules', '__pycache__', 'venv', 'env', '.vscode', '.idea', 'dist', 'build', 'Graph_Export'}
        self.ignore_exts = {'.pyc', '.git', '.DS_Store', '.zip', '.tar', '.gz'}

    def generate_uid(self, type_prefix: str, relative_path: str, name: str = "") -> str:
        """
        Generates a deterministic UID.
        FILE: FILE-{sanitized_path}
        CLASS: CLS-{sanitized_path}-{name}
        FUNC: FUNC-{sanitized_path}-{name}
        """
        sanitized_path = relative_path.replace('/', '_').replace('\\', '_').replace('.', '_')
        if name:
            return f"{type_prefix}-{sanitized_path}-{name}"
        return f"{type_prefix}-{sanitized_path}"

    def parse_python_file(self, file_path: str, relative_path: str) -> List[Dict]:
        nodes = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # File Node
            file_uid = self.generate_uid("FILE", relative_path)
            nodes.append({
                "uid": file_uid,
                "name": os.path.basename(file_path),
                "type": "File",
                "path": relative_path,
                "content": content, # Optional: might be too heavy?
                "parent": None
            })

            # Classes and Functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    cls_name = node.name
                    cls_uid = self.generate_uid("CLASS", relative_path, cls_name)
                    nodes.append({
                        "uid": cls_uid,
                        "name": cls_name,
                        "type": "Class",
                        "path": relative_path,
                        "parent": file_uid
                    })
                    
                    # Methods inside Class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                            method_name = item.name
                            if method_name.startswith("__"): continue # Skip magic methods for less noise
                            
                            method_uid = self.generate_uid("FUNC", relative_path, f"{cls_name}_{method_name}")
                            nodes.append({
                                "uid": method_uid,
                                "name": method_name,
                                "type": "Function",
                                "path": relative_path,
                                "parent": cls_uid
                            })

                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    # Top level functions (check if it's already processed as method)
                    # ast.walk visits everything, so we need to be careful.
                    # Actually, simple walk flattens the tree. 
                    # We can check strict parentage or just use the fact they are visited.
                    # For simplicity in this v1: We might double count methods if not careful.
                    # Better approach: Recursive visitor.
                    pass
            
            # Re-implementing with Visitor for better hierarchy control
            visitor = CodeVisitor(file_uid, relative_path, self)
            visitor.visit(tree)
            nodes.extend(visitor.collected_nodes)

        except Exception as e:
            print(f"Error parsing {relative_path}: {e}")
            
        return nodes

    def parse_js_file(self, file_path: str, relative_path: str) -> List[Dict]:
        nodes = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            file_uid = self.generate_uid("FILE", relative_path)
            nodes.append({
                "uid": file_uid,
                "name": os.path.basename(file_path),
                "type": "File",
                "path": relative_path,
                "parent": None
            })
            
            # Simple Regex for Classes
            class_matches = re.finditer(r'class\s+(\w+)', content)
            for match in class_matches:
                cls_name = match.group(1)
                cls_uid = self.generate_uid("CLASS", relative_path, cls_name)
                nodes.append({
                    "uid": cls_uid,
                    "name": cls_name,
                    "type": "Class",
                    "path": relative_path,
                    "parent": file_uid
                })

            # Simple Regex for Functions (function foo() or const foo = () =>)
            func_matches = re.finditer(r'function\s+(\w+)', content)
            for match in func_matches:
                func_name = match.group(1)
                func_uid = self.generate_uid("FUNC", relative_path, func_name)
                nodes.append({
                    "uid": func_uid,
                    "name": func_name,
                    "type": "Function",
                    "path": relative_path,
                    "parent": file_uid
                })

        except Exception as e:
            print(f"Error parsing JS {relative_path}: {e}")
            
        return nodes

    def _should_ignore(self, rel_path: str, filename: str) -> bool:
        """
        Determines if a file should be ignored based on project rules.
        Filters out:
        - Auxiliary tools (maintenance scripts)
        - Tests (test_*.py)
        - Documentation/Exports (md/, Graph_Export/)
        - System logs
        """
        # 1. Check extensions
        if any(filename.endswith(ext) for ext in self.ignore_exts):
            return True
            
        # 2. Check directory patterns
        path_parts = rel_path.split(os.sep)
        if 'maintenance' in path_parts: return True
        if 'archive' in path_parts: return True
        if 'Graph_Export' in path_parts: return True
        if 'md' in path_parts: return True
        if 'examples' in path_parts: return True
        
        # 3. Check filename patterns
        if filename.startswith('test_') or filename.endswith('_test.py'):
            return True
        if filename.startswith('mock_'):
            return True
            
        # 4. Specific files
        if filename in ['sync_watcher.log', '.DS_Store']:
            return True
            
        return False

    def scan_and_map(self):
        all_nodes = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Ignore dirs
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.project_root)
                
                if self._should_ignore(rel_path, file):
                    continue
                
                if file.endswith('.py'):
                    # Use AST
                    # Note: parse_python_file implementation below calls visitor, 
                    # let's refine existing one.
                    all_nodes.extend(self.parse_python_file(full_path, rel_path))
                elif file.endswith(('.js', '.ts', '.jsx', '.tsx')):
                   all_nodes.extend(self.parse_js_file(full_path, rel_path))
                else:
                    # just file node
                    file_uid = self.generate_uid("FILE", rel_path)
                    all_nodes.append({
                        "uid": file_uid,
                        "name": file,
                        "type": "File",
                        "path": rel_path,
                        "parent": None
                    })

        # Sync to Neo4j
        self.batch_create_nodes(all_nodes)
        return len(all_nodes)

    def batch_create_nodes(self, nodes: List[Dict]):
        if not nodes: return
        
        # Cypher query with UNWIND
        query = """
        UNWIND $batch AS item
        MERGE (n {uid: item.uid})
        SET n.name = item.name,
            n.path = item.path,
            n.project_id = 'graphmcp'
        
        // Set dynamic labels
        WITH n, item
        CALL apoc.create.addLabels(n, [item.type]) YIELD node
        
        // Create hierarchy link
        WITH n, item
        MATCH (p {uid: item.parent})
        WHERE item.parent IS NOT NULL
        MERGE (p)-[:DECOMPOSES]->(n)
        """
        
        # Simplified version without APOC (if not available)
        # We'll stick to running separate queries if types differ, 
        # but to keep it simple and clean, let's group by type.
        
        files = [n for n in nodes if n['type'] == 'File']
        classes = [n for n in nodes if n['type'] == 'Class']
        functions = [n for n in nodes if n['type'] == 'Function']
        
        self._write_batch("File", files)
        self._write_batch("Class", classes)
        self._write_batch("Function", functions)
        
    def _write_batch(self, label: str, nodes: List[Dict]):
        if not nodes: return
        
        query = f"""
        UNWIND $batch AS item
        MERGE (n:{label} {{uid: item.uid}})
        SET n.name = item.name,
            n.path = item.path,
            n.project_id = 'graphmcp', // Hardcoded for now
            n.title = item.name
        
        WITH n, item
        MATCH (p {{uid: item.parent}})
        WHERE item.parent IS NOT NULL
        MERGE (p)-[:DECOMPOSES]->(n)
        """
        
        # Clean dicts for transport
        cleaned_nodes = []
        for n in nodes:
            cleaned_nodes.append({
                "uid": n['uid'],
                "name": n['name'],
                "path": n['path'],
                "parent": n['parent']
            })
            
        self.driver.execute_query(query, {"batch": cleaned_nodes}, database_="neo4j")
        print(f"Saved {len(cleaned_nodes)} {label} nodes.")


class CodeVisitor(ast.NodeVisitor):
    def __init__(self, file_uid, rel_path, mapper):
        self.file_uid = file_uid
        self.rel_path = rel_path
        self.mapper = mapper
        self.collected_nodes = []
        # No initial file node here, assumed created by caller

    def visit_ClassDef(self, node):
        cls_name = node.name
        cls_uid = self.mapper.generate_uid("CLASS", self.rel_path, cls_name)
        
        self.collected_nodes.append({
            "uid": cls_uid,
            "name": cls_name,
            "type": "Class",
            "path": self.rel_path,
            "parent": self.file_uid
        })
        
        # Visit methods specifically
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.visit_Method(item, cls_uid, cls_name)
        
        # Do not continue visiting children via generic visit to avoid double counting
    
    def visit_Method(self, node, parent_uid, class_name):
        method_name = node.name
        if method_name.startswith("__") and method_name != "__init__": return 
        
        method_uid = self.mapper.generate_uid("FUNC", self.rel_path, f"{class_name}_{method_name}")
        self.collected_nodes.append({
            "uid": method_uid,
            "name": method_name,
            "type": "Function",
            "path": self.rel_path,
            "parent": parent_uid
        })

    def visit_FunctionDef(self, node):
        # Top level functions only (methods are handled in visit_ClassDef)
        # But AST visitor visits everything. 
        # If we are inside a class, we shouldn't trigger this if we handle it manually.
        # But simple NodeVisitor is depth-first.
        
        # To avoid complexity:
        # We only catch top-level functions here.
        # How do we know if it's top level?
        pass # Disabling generic FunctionDef visit to rely on manual walk in parse logic is safer,
             # OR we change logic to track context.
             
        # Let's simplify: 
        # We will NOT use this visitor for FunctionDef if it creates duplicates.
        # Actually, let's just use the `visit` method carefully.
        
        func_name = node.name
        func_uid = self.mapper.generate_uid("FUNC", self.rel_path, func_name)
        
        self.collected_nodes.append({
            "uid": func_uid,
            "name": func_name,
            "type": "Function",
            "path": self.rel_path,
            "parent": self.file_uid
        })

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

# Monkey patch/Better Logic for Parsing
# The visitor above has a flaw: it treats methods as top-level functions too if we just `generic_visit` or standard visit flow.
# Let's fix parse_python_file to be robust.

def parse_python_enhanced(self, file_path: str, relative_path: str) -> List[Dict]:
    nodes = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        file_uid = self.generate_uid("FILE", relative_path)
        
        # ADD FILE NODE (Only once)
        if not any(n['uid'] == file_uid for n in nodes):
             nodes.append({
                "uid": file_uid,
                "name": os.path.basename(file_path),
                "type": "File",
                "path": relative_path,
                "parent": None
            })

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                cls_name = node.name
                cls_uid = self.generate_uid("CLASS", relative_path, cls_name)
                nodes.append({
                    "uid": cls_uid,
                    "name": cls_name,
                    "type": "Class",
                    "path": relative_path,
                    "parent": file_uid
                })
                
                for item in node.body:
                     if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_name = item.name
                        if method_name.startswith("__") and method_name != "__init__": continue
                        method_uid = self.generate_uid("FUNC", relative_path, f"{cls_name}_{method_name}")
                        nodes.append({
                            "uid": method_uid,
                            "name": method_name,
                            "type": "Function",
                            "path": relative_path,
                            "parent": cls_uid
                        })
                        
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                func_uid = self.generate_uid("FUNC", relative_path, func_name)
                nodes.append({
                    "uid": func_uid,
                    "name": func_name,
                    "type": "Function",
                    "path": relative_path,
                    "parent": file_uid
                })
                
    except Exception as e:
        print(f"Error parsing {relative_path}: {e}")
    return nodes

CodebaseMapper.parse_python_file = parse_python_enhanced

if __name__ == "__main__":
    mapper = CodebaseMapper()
    print("Mapping codebase...")
    count = mapper.scan_and_map()
    print(f"Mapped {count} nodes.")

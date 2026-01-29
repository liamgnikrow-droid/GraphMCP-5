import os
import ast
import uuid
import hashlib

class CodeMapper:
    def __init__(self, project_root, project_id):
        self.project_root = project_root
        self.project_id = project_id
        self.nodes = [] # List of dicts to insert
        self.rels = []  # List of relationships

    def generate_uid(self, type_prefix, name):
        """Generates deterministic UID based on project and name."""
        raw = f"{self.project_id}:{type_prefix}:{name}"
        # hash = hashlib.md5(raw.encode()).hexdigest()[:8]
        # Better to keep it readable if possible, but safe
        sanitized = "".join([c if c.isalnum() else "_" for c in name])
        return f"{type_prefix}-{sanitized}"

    def scan(self):
        for root, dirs, files in os.walk(self.project_root):
            if "node_modules" in dirs: dirs.remove("node_modules")
            if ".git" in dirs: dirs.remove(".git")
            if "__pycache__" in dirs: dirs.remove("__pycache__")
            if "venv" in dirs: dirs.remove("venv")

            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.project_root)
                    self.process_python_file(full_path, rel_path)
                    
        return self.nodes, self.rels

    def process_python_file(self, full_path, rel_path):
        file_uid = self.generate_uid("FILE", rel_path)
        
        # File Node
        self.nodes.append({
            "uid": file_uid,
            "type": "File",
            "title": rel_path,
            "path": rel_path,
            "project_id": self.project_id
        })

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content)
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    class_uid = self.generate_uid("CLS", f"{rel_path}:{class_name}")
                    
                    self.nodes.append({
                        "uid": class_uid,
                        "type": "Class",
                        "title": class_name,
                        "project_id": self.project_id
                    })
                    
                    self.rels.append((file_uid, "CONTAINS", class_uid))
                    
                    # Methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_name = item.name
                            method_uid = self.generate_uid("FUNC", f"{rel_path}:{class_name}:{method_name}")
                            
                            self.nodes.append({
                                "uid": method_uid,
                                "type": "Function",
                                "title": f"{class_name}.{method_name}",
                                "project_id": self.project_id
                            })
                            
                            self.rels.append((class_uid, "CONTAINS", method_uid))

                elif isinstance(node, ast.FunctionDef):
                    # Top-level function
                    if isinstance(node.parent, ast.Module) if hasattr(node, 'parent') else True: 
                        # AST walk doesn't give parent by default easily without specific visitor
                        # Simplified: logic above covers methods inside ClassDef loop. 
                        # Here we catch ALL FunctionDefs. We need to distinguish top-level.
                        pass

            # Improved AST Visitor
            visitor = CodeVisitor(file_uid, rel_path, self.project_id, self.nodes, self.rels, self)
            visitor.visit(tree)
            
        except Exception as e:
            print(f"Error parsing {rel_path}: {e}")

class CodeVisitor(ast.NodeVisitor):
    def __init__(self, file_uid, rel_path, project_id, nodes, rels, mapper):
        self.file_uid = file_uid
        self.rel_path = rel_path
        self.project_id = project_id
        self.nodes = nodes
        self.rels = rels
        self.mapper = mapper
        self.current_class_uid = None

    def visit_ClassDef(self, node):
        class_name = node.name
        class_uid = self.mapper.generate_uid("CLS", f"{self.rel_path}::{class_name}")
        
        self.nodes.append({
            "uid": class_uid,
            "type": "Class",
            "title": class_name,
            "project_id": self.project_id
        })
        
        # Link File -> Class
        self.rels.append((self.file_uid, "CONTAINS", class_uid))
        
        prev_class = self.current_class_uid
        self.current_class_uid = class_uid
        self.generic_visit(node)
        self.current_class_uid = prev_class

    def visit_FunctionDef(self, node):
        func_name = node.name
        
        if self.current_class_uid:
            # Method
            func_uid = self.mapper.generate_uid("FUNC", f"{self.current_class_uid.split('CLS-')[1]}::{func_name}")
            parent_uid = self.current_class_uid
            title = f"{func_name} (method)"
        else:
            # Top-level function
            func_uid = self.mapper.generate_uid("FUNC", f"{self.rel_path}::{func_name}")
            parent_uid = self.file_uid
            title = func_name

        self.nodes.append({
            "uid": func_uid,
            "type": "Function",
            "title": title,
            "project_id": self.project_id
        })
        
        self.rels.append((parent_uid, "CONTAINS", func_uid))
        self.generic_visit(node)

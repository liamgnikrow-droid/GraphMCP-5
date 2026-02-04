#!/usr/bin/env python3
"""
Автоматическая очистка устаревших test и maintenance файлов.
Также удаляет соответствующие узлы из Neo4j графа.
"""
import os
import sys
sys.path.append("/opt/tools")
from db_config import get_driver, close_driver

# Файлы для удаления
FILES_TO_DELETE = {
    "test": [
        "test_explain_physics.py",
        "test_get_full_context.py",
        "test_impact_analysis.py",
        "test_map_codebase_live.py",
        "test_register_task.py",
        "test_server_logic.py",
        "test_sync_push.py",
    ],
    "maintenance": [
        "aggressive_clean.py",
        "apply_semantic_links.py",
        "audit_file_links.py",
        "check_db_node.py",
        "check_islands.py",
        "check_orphaned_files.py",
        "check_stats.py",
        "clean_duplicates.py",
        "consolidate_graph.py",
        "debug_ideas.py",
        "deduplicate_genesis.py",
        "enforce_physics.py",
        "export_mapping_inventory.py",
        "final_fix_spec.py",
        "final_link_tools.py",
        "finalize_cleanup.py",
        "fix_duplication.py",
        "force_full_sync.py",
        "force_link_files.py",
        "intelligent_link_files.py",
        "manual_link_final.py",
        "migrate_implements_links.py",
        "migrate_rels.py",
        "purge_junk_nodes.py",
        "purge_specitems.py",
        "sanitize_and_link.py",
        "surgical_fix_spec.py",
    ],
}

# Файлы для архивирования (перемещение в archive/ subdirectory)
FILES_TO_ARCHIVE = {
    "test": ["test_create_concept_with_middleware.py"],
    "maintenance": ["register_find_orphans.py"],
}

def delete_nodes_from_graph(file_list, base_path):
    """Удаляет узлы File, Class, Function из графа для указанных файлов"""
    driver = get_driver()
    
    total_deleted = 0
    for filename in file_list:
        # Construct File UID pattern
        if base_path == "Tools/maintenance":
            file_uid_pattern = f"FILE-Tools_maintenance_{filename.replace('.py', '_py')}"
        else:
            file_uid_pattern = f"FILE-{filename.replace('.py', '_py')}"
        
        # Delete File node and all related Code nodes
        q = """
        MATCH (f:File)
        WHERE f.uid STARTS WITH $file_uid_pattern
        OPTIONAL MATCH (f)-[:DECOMPOSES]->(child)
        WHERE child:Class OR child:Function
        DETACH DELETE f, child
        RETURN count(f) + count(child) as deleted_count
        """
        
        try:
            recs, _, _ = driver.execute_query(q, {'file_uid_pattern': file_uid_pattern}, database_='neo4j')
            deleted = recs[0]['deleted_count']
            if deleted > 0:
                print(f"  🗑️ Neo4j: Удалено {deleted} узлов для {filename}")
                total_deleted += deleted
        except Exception as e:
            print(f"  ⚠️ Ошибка при удалении узлов для {filename}: {e}")
    
    close_driver()
    return total_deleted

def delete_markdown_files(file_list, category):
    """Удаляет соответствующие .md файлы из Graph_Export"""
    total_deleted = 0
    
    # Search in Graph_Export/6_Code for File/Class/Function nodes
    code_dirs = [
        "/workspace/Graph_Export/6_Code/Files",
        "/workspace/Graph_Export/6_Code/Classes",
        "/workspace/Graph_Export/6_Code/Functions",
    ]
    
    for filename in file_list:
        base_name = filename.replace('.py', '_py')
        patterns = [
            f"FILE-{base_name}.md",
            f"FILE-Tools_maintenance_{base_name}.md",
            f"CLASS-*{base_name}*.md",
            f"FUNC-*{base_name}*.md",
        ]
        
        for code_dir in code_dirs:
            if not os.path.exists(code_dir):
                continue
            
            for pattern in patterns:
                import glob
                matches = glob.glob(os.path.join(code_dir, pattern))
                for match in matches:
                    try:
                        os.remove(match)
                        print(f"  🗑️ Удалён: {os.path.basename(match)}")
                        total_deleted += 1
                    except Exception as e:
                        print(f"  ⚠️ Не удалось удалить {match}: {e}")
    
    return total_deleted

def delete_physical_files(file_list, base_path):
    """Удаляет физические .py файлы"""
    total_deleted = 0
    for filename in file_list:
        file_path = os.path.join(base_path, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"  ✅ Удалён: {filename}")
                total_deleted += 1
            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
        else:
            print(f"  ⚠️ Файл не найден: {filename}")
    
    return total_deleted

def archive_file(filename, base_path):
    """Перемещает файл в archive/ subdirectory"""
    archive_dir = os.path.join(base_path, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    
    src = os.path.join(base_path, filename)
    dst = os.path.join(archive_dir, filename)
    
    if os.path.exists(src):
        try:
            import shutil
            shutil.move(src, dst)
            print(f"  📦 Архивирован: {filename}")
            return True
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            return False
    else:
        print(f"  ⚠️ Файл не найден: {filename}")
        return False

def main():
    print("=" * 70)
    print("АВТОМАТИЧЕСКАЯ ОЧИСТКА УСТАРЕВШИХ ФАЙЛОВ")
    print("=" * 70)
    
    total_files_deleted = 0
    total_nodes_deleted = 0
    total_md_deleted = 0
    
    # 1. Delete test files
    print("\n📝 УДАЛЕНИЕ ТЕСТОВЫХ ФАЙЛОВ")
    print("-" * 70)
    test_path = "/workspace/Tools"
    
    print("Удаление узлов из Neo4j...")
    total_nodes_deleted += delete_nodes_from_graph(FILES_TO_DELETE["test"], "Tools")
    
    print("\nУдаление .md файлов...")
    total_md_deleted += delete_markdown_files(FILES_TO_DELETE["test"], "test")
    
    print("\nУдаление физических файлов...")
    total_files_deleted += delete_physical_files(FILES_TO_DELETE["test"], test_path)
    
    # 2. Delete maintenance files
    print("\n🔧 УДАЛЕНИЕ MAINTENANCE СКРИПТОВ")
    print("-" * 70)
    maintenance_path = "/workspace/Tools/maintenance"
    
    print("Удаление узлов из Neo4j...")
    total_nodes_deleted += delete_nodes_from_graph(FILES_TO_DELETE["maintenance"], "Tools/maintenance")
    
    print("\nУдаление .md файлов...")
    total_md_deleted += delete_markdown_files(FILES_TO_DELETE["maintenance"], "maintenance")
    
    print("\nУдаление физических файлов...")
    total_files_deleted += delete_physical_files(FILES_TO_DELETE["maintenance"], maintenance_path)
    
    # 3. Archive files
    print("\n📦 АРХИВИРОВАНИЕ ФАЙЛОВ")
    print("-" * 70)
    
    archived_count = 0
    for filename in FILES_TO_ARCHIVE["test"]:
        if archive_file(filename, test_path):
            archived_count += 1
    
    for filename in FILES_TO_ARCHIVE["maintenance"]:
        if archive_file(filename, maintenance_path):
            archived_count += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("ИТОГИ ОЧИСТКИ:")
    print(f"  ✅ Удалено физических файлов: {total_files_deleted}")
    print(f"  🗑️ Удалено узлов Neo4j: {total_nodes_deleted}")
    print(f"  📄 Удалено .md файлов: {total_md_deleted}")
    print(f"  📦 Архивировано файлов: {archived_count}")
    print("=" * 70)

if __name__ == "__main__":
    main()

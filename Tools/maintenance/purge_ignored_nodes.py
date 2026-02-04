#!/usr/bin/env python3
"""
Скрипт для удаления "мусорных" узлов из графа (тесты, maintenance),
которые были ошибочно замаппированы ранее.
Использует ту же логику фильтрации, что и обновленный codebase_mapper.py.
"""
import os
import sys
sys.path.append("/opt/tools")
from db_config import get_driver, close_driver, WORKSPACE_ROOT
from codebase_mapper import CodebaseMapper

def main():
    print("=" * 70)
    print("ОЧИСТКА ГРАФА ОТ ИГНОРИРУЕМЫХ ФАЙЛОВ")
    print("=" * 70)
    
    mapper = CodebaseMapper()
    driver = get_driver()
    
    # 1. Получаем ВСЕ File узлы из графа
    q = """
    MATCH (f:File)
    RETURN f.uid as uid, f.path as path
    ORDER BY f.path
    """
    recs, _, _ = driver.execute_query(q, database_='neo4j')
    
    print(f"Всего File узлов в графе: {len(recs)}")
    
    nodes_to_delete = []
    
    for r in recs:
        path = r['path']
        filename = os.path.basename(path)
        
        # Используем логику маппера
        if mapper._should_ignore(path, filename):
            nodes_to_delete.append(r)
            print(f"  🔍 Будет удален: {path}")

    # Дополнительно: явно проверим на test_codebase_map.js и другие
    # которые могли пролезть по какой-то причине
    
    if not nodes_to_delete:
        print("\n✅ Мусорных узлов не найдено.")
    else:
        print(f"\nНайдено {len(nodes_to_delete)} узлов для удаления.")
        
        # Удаляем
        for node in nodes_to_delete:
            uid = node['uid']
            
            # Удаляем File и все его дочерние Class/Function
            dq = """
            MATCH (f:File {uid: $uid})
            OPTIONAL MATCH (f)-[:DECOMPOSES*]->(child)
            DETACH DELETE f, child
            RETURN count(child) as children_deleted
            """
            
            try:
                res, _, _ = driver.execute_query(dq, {'uid': uid}, database_='neo4j')
                children = res[0]['children_deleted']
                print(f"  🗑️ Удален: {uid} (+ {children} детей)")
            except Exception as e:
                print(f"  ❌ Ошибка при удалении {uid}: {e}")
                
        # Удаляем также соответствующие .md файлы
        print("\nУдаление Markdown файлов...")
        md_base = "/workspace/Graph_Export/6_Code"
        import glob
        
        count_md = 0
        for node in nodes_to_delete:
            # File md
            file_md = os.path.join(md_base, "Files", f"{node['uid']}.md")
            if os.path.exists(file_md):
                os.remove(file_md)
                count_md += 1
                
            # Children md (wildcard search)
            # FUNC-path-name.md
            # CLASS-path-name.md
            # path part in UID is sanitized: Tools_test...
            
            path_sanitized = node['path'].replace('/', '_').replace('.', '_')
            
            for type_dir, prefix in [("Functions", "FUNC"), ("Classes", "CLASS")]:
                 pattern = os.path.join(md_base, type_dir, f"{prefix}-{path_sanitized}-*.md")
                 for f in glob.glob(pattern):
                     os.remove(f)
                     count_md += 1

        print(f"  📄 Удалено .md файлов: {count_md}")

    print("=" * 70)
    close_driver()

if __name__ == "__main__":
    main()

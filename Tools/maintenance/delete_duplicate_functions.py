#!/usr/bin/env python3
"""
Удаление дубликатов Functions с двойным подчеркиванием.
Стратегия: Удалять узлы с '__ClassName__' (старый формат),
оставлять узлы с '_ClassName_' (новый формат).
"""
import sys
sys.path.append("/opt/tools")
from db_config import get_driver, close_driver

def delete_duplicate_functions():
    """Удаление дубликатов с '__' в имени"""
    driver = get_driver()
    
    print("🔍 Поиск дубликатов Functions...")
    
    # Find all functions with '__GraphSync__' pattern (old format)
    q = """
    MATCH (f:Function)
    WHERE f.uid CONTAINS '__GraphSync__'
    RETURN f.uid as uid, f.name as name
    ORDER BY f.uid
    """
    recs, _, _ = driver.execute_query(q, database_="neo4j")
    
    if not recs:
        print("✅ Дубликатов с '__' не найдено")
        return
    
    print(f"Найдено {len(recs)} Functions с двойным подчеркиванием:")
    for r in recs:
        print(f"  - {r['uid']}")
    
    print("\n⚙️ Удаляю дубликаты...")
    
    # Delete duplicates (and their markdown files)
    deleted_count = 0
    for r in recs:
        uid = r['uid']
        
        # Check if corresponding single-underscore version exists
        normalized = uid.replace('__GraphSync__', '_GraphSync_')
        check_q = """
        MATCH (f:Function {uid: $normalized})
        RETURN f.uid as uid
        """
        check_recs, _, _ = driver.execute_query(check_q, {'normalized': normalized}, database_="neo4j")
        
        if check_recs:
            # Normalized version exists, safe to delete old version
            delete_q = """
            MATCH (f:Function {uid: $uid})
            DETACH DELETE f
            RETURN count(*) as deleted
            """
            result, _, _ = driver.execute_query(delete_q, {'uid': uid}, database_="neo4j")
            
            print(f"  ✅ Удалён: {uid} (есть нормализованная версия: {normalized})")
            deleted_count += result[0]['deleted']
            
            # Also delete markdown file
            import os
            file_path = f"/workspace/Graph_Export/6_Code/Functions/{uid}.md"
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"     🗑️ Удалён файл: {file_path}")
        else:
            print(f"  ⚠️ Пропущен: {uid} (нет нормализованной версии, возможно единственная копия)")
    
    print(f"\n✅ Удалено {deleted_count} дубликатов Functions")
    close_driver()

if __name__ == "__main__":
    delete_duplicate_functions()

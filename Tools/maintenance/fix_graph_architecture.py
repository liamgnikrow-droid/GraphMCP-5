#!/usr/bin/env python3
"""
Массовое исправление архитектурных проблем графа:
1. Миграция CONTAINS -> DECOMPOSES
2. Удаление неканоничных связей (ALLOWS_CONNECTION, CAN_PERFORM)  
3. Проверка и удаление дубликатов Functions
4. Очистка свойства depends_on из узлов (оставляя только связи)
"""
import sys
sys.path.append("/opt/tools")
from db_config import get_driver, close_driver

def migrate_contains_to_decomposes():
    """Миграция CONTAINS -> DECOMPOSES"""
    print("=" * 60)
    print("ЗАДАЧА 1: Миграция CONTAINS -> DECOMPOSES")
    print("=" * 60)
    
    driver = get_driver()
    
    # Check existing CONTAINS relationships
    check_q = """
    MATCH (parent)-[r:CONTAINS]->(child)
    RETURN count(r) as count, labels(parent)[0] as parent_type, labels(child)[0] as child_type
    """
    recs, _, _ = driver.execute_query(check_q, database_="neo4j")
    
    if recs:
        print(f"Найдено связей CONTAINS: {recs[0]['count']}")
        for r in recs:
            print(f"  {r['parent_type']} -[:CONTAINS]-> {r['child_type']}: {r['count']}")
    else:
        print("✅ Связей CONTAINS не найдено")
        return
    
    # Migration
    migrate_q = """
    MATCH (parent)-[old:CONTAINS]->(child)
    MERGE (parent)-[:DECOMPOSES]->(child)
    DELETE old
    RETURN count(*) as migrated
    """
    
    print("\n⚙️ Выполняю миграцию...")
    result, _, _ = driver.execute_query(migrate_q, database_="neo4j")
    print(f"✅ Мигрировано: {result[0]['migrated']} связей CONTAINS -> DECOMPOSES")

def remove_noncanonical_relationships():
    """Удаление неканоничных связей"""
    print("\n" + "=" * 60)
    print("ЗАДАЧА 2: Удаление неканоничных связей")
    print("=" * 60)
    
    driver = get_driver()
    
    # Check for non-canonical relationships
    for rel_type in ['ALLOWS_CONNECTION', 'CAN_PERFORM']:
        check_q = f"""
        MATCH ()-[r:{rel_type}]->()
        RETURN count(r) as count
        """
        recs, _, _ = driver.execute_query(check_q, database_="neo4j")
        count = recs[0]['count']
        
        if count > 0:
            print(f"\n⚠️ Найдено связей {rel_type}: {count}")
            
            # Show examples
            example_q = f"""
            MATCH (s)-[r:{rel_type}]->(t)
            RETURN s.uid as source, t.uid as target, labels(s)[0] as s_type, labels(t)[0] as t_type
            LIMIT 5
            """
            examples, _, _ = driver.execute_query(example_q, database_="neo4j")
            print(f"  Примеры:")
            for ex in examples:
                print(f"    {ex['s_type']}:{ex['source']} -> {ex['t_type']}:{ex['target']}")
            
            # Delete
            delete_q = f"""
            MATCH ()-[r:{rel_type}]->()
            DELETE r
            RETURN count(*) as deleted
            """
            result, _, _ = driver.execute_query(delete_q, database_="neo4j")
            print(f"  ✅ Удалено: {result[0]['deleted']} связей {rel_type}")
        else:
            print(f"✅ Связей {rel_type} не найдено")

def find_duplicate_functions():
    """Поиск дубликатов Functions"""
    print("\n" + "=" * 60)
    print("ЗАДАЧА 3: Поиск дубликатов Functions")
    print("=" * 60)
    
    driver = get_driver()
    
    # Find functions with similar names (different underscore patterns)
    q = """
    MATCH (f:Function)
    WHERE f.uid CONTAINS 'graph_sync_py'
    RETURN f.uid as uid, coalesce(f.name, f.uid) as name
    ORDER BY f.uid
    """
    recs, _, _ = driver.execute_query(q, database_="neo4j")
    
    print(f"Найдено Functions с 'graph_sync_py': {len(recs)}")
    
    # Group by normalized name (replace __ with _)
    groups = {}
    for r in recs:
        uid = r['uid']
        
        # Normalize: replace __ClassName__ with _ClassName_
        normalized = uid.replace('__GraphSync__', '_GraphSync_')
        
        if normalized not in groups:
            groups[normalized] = []
        groups[normalized].append(uid)
    
    duplicates_found = False
    for norm, uids in groups.items():
        if len(uids) > 1:
            duplicates_found = True
            print(f"\n⚠️ Дубликаты для {norm}:")
            for uid in uids:
                # Check relationships
                rel_q = """
                MATCH (f {uid: $uid})-[r]-()
                RETURN count(r) as rel_count
                """
                rel_recs, _, _ = driver.execute_query(rel_q, {'uid': uid}, database_="neo4j")
                rel_count = rel_recs[0]['rel_count']
                print(f"    {uid} (связей: {rel_count})")
    
    if not duplicates_found:
        print("✅ Дубликатов не найдено")
    
    return groups

def clean_depends_on_property():
    """Очистка свойства depends_on из File узлов"""
    print("\n" + "=" * 60)
    print("ЗАДАЧА 4: Очистка свойства depends_on")
    print("=" * 60)
    
    driver = get_driver()
    
    # Check for nodes with depends_on property
    check_q = """
    MATCH (n:File)
    WHERE n.depends_on IS NOT NULL
    RETURN count(n) as count
    """
    recs, _, _ = driver.execute_query(check_q, database_="neo4j")
    count = recs[0]['count']
    
    if count > 0:
        print(f"⚠️ Найдено File узлов с свойством depends_on: {count}")
        
        # Remove property
        remove_q = """
        MATCH (n:File)
        WHERE n.depends_on IS NOT NULL
        REMOVE n.depends_on
        RETURN count(n) as cleaned
        """
        result, _, _ = driver.execute_query(remove_q, database_="neo4j")
        print(f"✅ Очищено узлов: {result[0]['cleaned']}")
    else:
        print("✅ Свойства depends_on не найдено")

def main():
    print("🔧 МАССОВОЕ ИСПРАВЛЕНИЕ ГРАФА")
    print("=" * 60)
    
    try:
        # 1. Migrate CONTAINS
        migrate_contains_to_decomposes()
        
        # 2. Remove non-canonical rels
        remove_noncanonical_relationships()
        
        # 3. Find duplicates (reporting only)
        duplicate_groups = find_duplicate_functions()
        
        # 4. Clean depends_on property
        clean_depends_on_property()
        
        print("\n" + "=" * 60)
        print("✅ ИСПРАВЛЕНИЯ ЗАВЕРШЕНЫ")
        print("=" * 60)
        print("\n💡 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Запустить полную синхронизацию: sync_all()")
        print("2. Удалить дубликаты Functions вручную (если найдены)")
        print("3. Проверить find_orphans снова")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
    finally:
        close_driver()

if __name__ == "__main__":
    main()

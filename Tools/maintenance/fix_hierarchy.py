
import os
import sys

# Добавляем путь к Tools чтобы импортировать модули
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # Tools/
sys.path.append(parent_dir)

from db_config import get_driver, close_driver
from graph_sync import GraphSync

def diagnose_and_fix(dry_run=True):
    driver = get_driver()
    sync_tool = GraphSync()
    
    print(f"🔍 Запуск диагностики иерархии (DRY_RUN={dry_run})...")
    print("   Ищем запрещенные связи: (Idea) -> (Requirement)")
    
    # 1. Поиск нарушений
    # Мы ищем Requirement, которые напрямую подключены к Idea
    query_violations = """
    MATCH (i:Idea)-[r:DECOMPOSES]->(req:Requirement)
    RETURN i.uid as idea_uid, i.project_id as project_id, req.uid as req_uid, req.title as req_title, elementId(r) as rel_id
    """
    
    violations, _, _ = driver.execute_query(query_violations, database_="neo4j")
    
    if not violations:
        print("✅ Нарушений не найдено. Иерархия чиста.")
        close_driver()
        return

    print(f"\n⚠️  Найдено {len(violations)} нарушений:")
    for v in violations:
        print(f"   • {v['idea_uid']} -> {v['req_uid']} ({v['req_title']})")

    if dry_run:
        print("\n💡 Для исправления запустите скрипт с флагом --fix")
        print("   Будет выполнено: Перенос этих Requirement под соответствующую Spec.")
        close_driver()
        return

    # 2. Исправление
    print("\n🛠️  Начинаем исправление...")
    
    fixed_count = 0
    
    for v in violations:
        idea_uid = v['idea_uid']
        req_uid = v['req_uid']
        project_id = v.get('project_id')
        
        # Находим подходящую Spec
        # Ищем Spec в том же проекте (или любую Spec, если проектов нет/один)
        # Предполагаем "Закон одной Spec" (CON-One_Spec)
        
        query_spec = """
        MATCH (s:Spec)
        WHERE ($project_id IS NULL OR s.project_id = $project_id)
        RETURN s.uid as spec_uid
        LIMIT 1
        """
        
        spec_recs, _, _ = driver.execute_query(query_spec, {"project_id": project_id}, database_="neo4j")
        
        if not spec_recs:
            print(f"❌ Пропуск {req_uid}: Не найдена Spec для привязки (Project: {project_id})")
            continue
            
        spec_uid = spec_recs[0]['spec_uid']
        
        try:
            # Транзакция переноса:
            # 1. Создать Spec -> Req
            # 2. Удалить Idea -> Req
            
            # Атомарно в Cypher
            query_fix = """
            MATCH (i:Idea)-[old_r:DECOMPOSES]->(req:Requirement {uid: $req_uid})
            MATCH (s:Spec {uid: $spec_uid})
            MERGE (s)-[new_r:DECOMPOSES]->(req)
            DELETE old_r
            RETURN count(new_r) as created
            """
            
            driver.execute_query(query_fix, {"req_uid": req_uid, "spec_uid": spec_uid}, database_="neo4j")
            
            print(f"   ✅ {req_uid}: Перенесен из {idea_uid} в {spec_uid}")
            
            # 3. Синхронизация Markdown
            sync_tool.sync_node(req_uid)  # 1. Обновляем ребенка (смена родителей)
            sync_tool.sync_node(idea_uid) # 2. Обновляем СТАРОГО родителя (удаление ссылки)
            sync_tool.sync_node(spec_uid) # 3. Обновляем НОВОГО родителя (добавление ссылки)
            print(f"      Files synced (Req, Old Parent, New Parent).")
            
            fixed_count += 1
            
        except Exception as e:
            print(f"   ❌ Ошибка при переносе {req_uid}: {e}")

    print(f"\n✨ Готово. Исправлено {fixed_count} из {len(violations)}.")
    close_driver()

if __name__ == "__main__":
    is_fix = "--fix" in sys.argv
    diagnose_and_fix(dry_run=not is_fix)

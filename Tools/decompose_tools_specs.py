
from neo4j import GraphDatabase
import os
import datetime

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j-db:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
PROJECT_ID = "graphmcp"

# Requirements to create
TOOLS_REQS = [
    {
        "title": "Tool: Look Around (Dashboard)",
        "uid": "REQ-Tool_Look_Around",
        "description": "Инструмент для получения контекста текущей локации агента. Должен возвращать: UID, тип, соседей, доступные действия и ограничения."
    },
    {
        "title": "Tool: Move To (Navigation)",
        "uid": "REQ-Tool_Move_To",
        "description": "Инструмент перемещения агента по графу. Должен проверять наличие ребра к целевому узлу перед перемещением."
    },
    {
        "title": "Tool: Look For Similar (Semantic Search)",
        "uid": "REQ-Tool_Look_For_Similar",
        "description": "Поиск узлов по семантической близости (векторный поиск). Использует эмбеддинги заголовков и описаний."
    },
    {
        "title": "Tool: Explain Physics (Introspection)",
        "uid": "REQ-Tool_Explain_Physics",
        "description": "Объясняет архитектурные причины доступности или блокировки инструментов в данной локации (Meta-Graph introspection)."
    },
    {
        "title": "Tool: Register Task",
        "uid": "REQ-Tool_Register_Task",
        "description": "Регистрация задач от пользователя. Создает узел Task. Служит входной точкой для работы агента (Builder mode)."
    },
    {
        "title": "Tool: Read Node",
        "uid": "REQ-Tool_Read_Node",
        "description": "Чтение полного контента узла (Body). Необходимо для глубокого понимания контекста перед изменением."
    },
    {
        "title": "Tool: Get Full Context",
        "uid": "REQ-Tool_Get_Full_Context",
        "description": "Агрегатор контекста: возвращает соседей, связанные требования, ограничения и Spec для текущей задачи."
    },
    {
        "title": "Tool: Illuminate Path",
        "uid": "REQ-Tool_Illuminate_Path",
        "description": "Подсветка пути от Idea до Task. Показывает вертикальный срез графа для понимания 'откуда растет' задача."
    },
    {
        "title": "Tool: Switch Project",
        "uid": "REQ-Tool_Switch_Project",
        "description": "Переключение глобального контекста сервера (ACTIVE_PROJECT). Обеспечивает изоляцию данных между проектами."
    },
    {
        "title": "Tool: Set Workflow",
        "uid": "REQ-Tool_Set_Workflow",
        "description": "Управление режимом работы агента (Architect, Builder, Auditor). Ограничивает набор доступных инструментов."
    },
    {
        "title": "Tool: Map Codebase",
        "uid": "REQ-Tool_Map_Codebase",
        "description": "Сканирование файловой системы проекта. Создает узлы File, Class, Function и связывает их с графом (Code Integration)."
    }
]

def decompose():
    print("🚀 Starting Decomposition of SPEC-Graph_Physics...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # 1. Find Parent Spec
            parent_uid = "SPEC-Graph_Physics"
            res = session.run("MATCH (n:Spec {uid: $uid}) RETURN n", uid=parent_uid)
            if not res.single():
                print(f"❌ Error: Parent Spec '{parent_uid}' not found!")
                return

            print(f"✅ Found Parent: {parent_uid}")

            # 2. Create Requirements and Link
            for req in TOOLS_REQS:
                query = """
                MERGE (r:Requirement {uid: $uid})
                ON CREATE SET 
                    r.title = $title,
                    r.description = $desc,
                    r.project_id = $pid,
                    r.created_at = datetime(),
                    r.status = 'Approved'
                ON MATCH SET
                    r.title = $title,
                    r.description = $desc
                
                WITH r
                MATCH (s:Spec {uid: $parent_uid})
                MERGE (s)-[:DECOMPOSES]->(r)
                RETURN r.uid
                """
                session.run(query, {
                    "uid": req["uid"],
                    "title": req["title"],
                    "desc": req["description"],
                    "pid": PROJECT_ID,
                    "parent_uid": parent_uid
                })
                print(f"   Created/Updated: {req['uid']}")
                
                # Sync needs to be called externally or we rely on 'sync_graph' tool later
                # But for now, DB is enough. Files will be created on next sync.

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.close()
        print("✅ Decomposition Complete.")

if __name__ == "__main__":
    decompose()

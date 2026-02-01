#!/usr/bin/env python3
"""
Bootstrap Meta-Graph Script
============================

Этот скрипт создаёт начальный Мета-Граф (Kernel Space) в Neo4j,
определяющий законы физики для Graph-Native Agent.

Выполняет Cypher-скрипт из SPEC-Graph_Physics.md (Часть 8).

Использование:
    python bootstrap_metagraph.py [--force]

Флаги:
    --force : Удалить существующий Мета-Граф перед загрузкой (ОПАСНО!)
"""

import sys
import os
from neo4j import GraphDatabase

# --- CONFIG ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j-db:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# --- CYPHER SCRIPT ---
BOOTSTRAP_SCRIPT = """
// ===== ТИПЫ УЗЛОВ =====
CREATE (:NodeType {name: 'Idea', description: 'Главная концепция проекта', max_count: 1});
CREATE (:NodeType {name: 'Spec', description: 'Техническая спецификация', max_count: 1});
CREATE (:NodeType {name: 'Requirement', description: 'Функциональное требование', max_count: null});
CREATE (:NodeType {name: 'Task', description: 'Задача от Human через чат', max_count: null});
CREATE (:NodeType {name: 'Domain', description: 'Доменная модель, справочник терминов', max_count: null});

// ===== ГЛОБАЛЬНЫЕ ДЕЙСТВИЯ =====
CREATE (:Action {uid: 'ACT-look_around', tool_name: 'look_around', scope: 'global'});
CREATE (:Action {uid: 'ACT-move_to', tool_name: 'move_to', scope: 'global'});
CREATE (:Action {uid: 'ACT-look_for_similar', tool_name: 'look_for_similar', scope: 'global'});
CREATE (:Action {uid: 'ACT-explain_physics', tool_name: 'explain_physics', scope: 'global'});
CREATE (:Action {uid: 'ACT-register_task', tool_name: 'register_task', scope: 'global'});
CREATE (:Action {uid: 'ACT-read_node', tool_name: 'read_node', scope: 'global'});
CREATE (:Action {uid: 'ACT-get_full_context', tool_name: 'get_full_context', scope: 'global'});
CREATE (:Action {uid: 'ACT-sync_graph', tool_name: 'sync_graph', scope: 'global'});
CREATE (:Action {uid: 'ACT-refresh_knowledge', tool_name: 'refresh_knowledge', scope: 'global', description: 'Recalculates semantic embeddings for ALL nodes. Useful after manual edits or imports.'});

// ===== КОНТЕКСТНЫЕ ДЕЙСТВИЯ =====
// Idea может создавать только Spec
CREATE (:Action {uid: 'ACT-create_spec', tool_name: 'create_concept', target_type: 'Spec', link_type: 'DECOMPOSES', scope: 'contextual'});

// Spec может создавать Requirement и Domain
CREATE (:Action {uid: 'ACT-create_req', tool_name: 'create_concept', target_type: 'Requirement', link_type: 'DECOMPOSES', scope: 'contextual'});
CREATE (:Action {uid: 'ACT-create_domain_from_spec', tool_name: 'create_concept', target_type: 'Domain', link_type: 'RELATES_TO', scope: 'contextual'});

// Requirement может создавать Domain
CREATE (:Action {uid: 'ACT-create_domain_from_req', tool_name: 'create_concept', target_type: 'Domain', link_type: 'RELATES_TO', scope: 'contextual'});

// Общие контекстные действия
CREATE (:Action {uid: 'ACT-link_nodes', tool_name: 'link_nodes', scope: 'contextual'});
CREATE (:Action {uid: 'ACT-delete_node', tool_name: 'delete_node', scope: 'contextual'});
CREATE (:Action {uid: 'ACT-delete_link', tool_name: 'delete_link', scope: 'contextual'});
CREATE (:Action {uid: 'ACT-sync_graph', tool_name: 'sync_graph', scope: 'contextual'});
CREATE (:Action {uid: 'ACT-propose_change', tool_name: 'propose_change', scope: 'contextual'});
CREATE (:Action {uid: 'ACT-update_node', tool_name: 'update_node', scope: 'contextual'});

// ===== СВЯЗИ CAN_PERFORM =====
// Idea может создавать Spec (если Spec ещё нет)
MATCH (nt:NodeType {name: 'Idea'}), (a:Action {uid: 'ACT-create_spec'})
CREATE (nt)-[:CAN_PERFORM]->(a);

// Spec может создавать Requirement и Domain
MATCH (nt:NodeType {name: 'Spec'}), (a:Action {uid: 'ACT-create_req'})
CREATE (nt)-[:CAN_PERFORM]->(a);
MATCH (nt:NodeType {name: 'Spec'}), (a:Action {uid: 'ACT-create_domain_from_spec'})
CREATE (nt)-[:CAN_PERFORM]->(a);

// Requirement может создавать Domain
MATCH (nt:NodeType {name: 'Requirement'}), (a:Action {uid: 'ACT-create_domain_from_req'})
CREATE (nt)-[:CAN_PERFORM]->(a);

// Все типы (кроме Domain) могут использовать общие действия
MATCH (nt:NodeType) WHERE nt.name IN ['Idea', 'Spec', 'Requirement', 'Task']
WITH nt
MATCH (a:Action) WHERE a.uid IN ['ACT-link_nodes', 'ACT-delete_node', 'ACT-delete_link', 'ACT-sync_graph', 'ACT-propose_change', 'ACT-update_node']
CREATE (nt)-[:CAN_PERFORM]->(a);

// ===== ОГРАНИЧЕНИЯ =====
CREATE (:Constraint {
  uid: 'CON-Russian_Language',
  rule_name: 'Закон Языка',
  function: 'cyrillic_ratio',
  operator: '>=',
  threshold: 0.25,
  error_message: 'Контент должен быть преимущественно на русском языке (мин. 25% кириллицы)'
});

CREATE (:Constraint {
  uid: 'CON-No_WikiLinks',
  rule_name: 'Закон Чистых Ссылок',
  function: 'regex_match',
  pattern: '\\\\[\\\\[.*?\\\\]\\\\]',
  error_message: 'Запрещено использовать [[WikiLinks]] в контенте. Связи создаются только через link_nodes.'
});

CREATE (:Constraint {
  uid: 'CON-One_Idea',
  rule_name: 'Закон Кардинальности Idea',
  function: 'node_count',
  operator: '>=',
  threshold: 1,
  target_label: 'Idea',
  error_message: 'В проекте может быть только одна Idea. Idea уже существует.'
});

CREATE (:Constraint {
  uid: 'CON-One_Spec',
  rule_name: 'Закон Кардинальности Spec',
  function: 'node_count',
  operator: '>=',
  threshold: 1,
  target_label: 'Spec',
  error_message: 'В проекте может быть только одна Spec. Spec уже существует.'
});

// Привязка ограничений к действиям
MATCH (c:Constraint {uid: 'CON-Russian_Language'})
WITH c
MATCH (a:Action) WHERE a.tool_name = 'create_concept'
CREATE (c)-[:RESTRICTS]->(a);

MATCH (c:Constraint {uid: 'CON-No_WikiLinks'})
WITH c
MATCH (a:Action) WHERE a.tool_name = 'create_concept'
CREATE (c)-[:RESTRICTS]->(a);

MATCH (c:Constraint {uid: 'CON-One_Spec'}), (a:Action {uid: 'ACT-create_spec'})
CREATE (c)-[:RESTRICTS]->(a);
"""

CLEANUP_SCRIPT = """
// ВНИМАНИЕ: Удаляет весь Мета-Граф!
MATCH (n:NodeType) DETACH DELETE n;
MATCH (n:Action) DETACH DELETE n;
MATCH (n:Constraint) DETACH DELETE n;
"""


def check_metagraph_exists(driver):
    """Проверяет существует ли Мета-Граф"""
    query = "MATCH (n:NodeType) RETURN count(n) as count"
    records, _, _ = driver.execute_query(query, database_="neo4j")
    count = records[0]["count"] if records else 0
    return count > 0


def cleanup_metagraph(driver):
    """Удаляет существующий Мета-Граф"""
    print("🧹 Очистка существующего Мета-Графа...")
    
    # Выполняем по одному statement
    statements = [
        "MATCH (n:NodeType) DETACH DELETE n",
        "MATCH (n:Action) DETACH DELETE n",
        "MATCH (n:Constraint) DETACH DELETE n"
    ]
    
    for stmt in statements:
        driver.execute_query(stmt, database_="neo4j")
    
    print("✅ Мета-Граф очищен")


def bootstrap_metagraph(driver):
    """Создаёт Мета-Граф из Cypher-скрипта"""
    print("🚀 Загрузка Мета-Графа...")
    
    # Разбиваем скрипт на отдельные команды (по ;)
    commands = [cmd.strip() for cmd in BOOTSTRAP_SCRIPT.split(';') if cmd.strip()]
    
    total = len(commands)
    for i, command in enumerate(commands, 1):
        try:
            driver.execute_query(command, database_="neo4j")
            print(f"  [{i}/{total}] ✓", end='\r')
        except Exception as e:
            print(f"\n❌ Ошибка при выполнении команды {i}/{total}:")
            print(f"   {command[:100]}...")
            print(f"   Ошибка: {e}")
            return False
    
    print(f"\n✅ Мета-Граф загружен ({total} команд выполнено)")
    return True


def verify_metagraph(driver):
    """Проверяет корректность загруженного Мета-Графа"""
    print("\n🔍 Проверка Мета-Графа...")
    
    checks = [
        ("NodeType узлов", "MATCH (n:NodeType) RETURN count(n) as count", 5),
        ("Action узлов", "MATCH (n:Action) RETURN count(n) as count", 17),  # +3: read_node, get_full_context, sync_graph
        ("Constraint узлов", "MATCH (n:Constraint) RETURN count(n) as count", 4),
        ("CAN_PERFORM связей", "MATCH ()-[r:CAN_PERFORM]->() RETURN count(r) as count", 24),  # 4 специфичных + 4 типа * 5 общих
        ("RESTRICTS связей", "MATCH ()-[r:RESTRICTS]->() RETURN count(r) as count", 9),  # 2 constraints * 4 create_concept + 1 CON-One_Spec
    ]
    
    all_ok = True
    for name, query, expected in checks:
        records, _, _ = driver.execute_query(query, database_="neo4j")
        actual = records[0]["count"] if records else 0
        status = "✅" if actual == expected else "⚠️"
        print(f"  {status} {name}: {actual} (ожидалось {expected})")
        if actual != expected:
            all_ok = False
    
    return all_ok


def main():
    force = "--force" in sys.argv
    
    print("=" * 70)
    print("BOOTSTRAP META-GRAPH")
    print("=" * 70)
    print()
    
    # Подключение к Neo4j
    print(f"🔌 Подключение к Neo4j ({NEO4J_URI})...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("✅ Подключено к Neo4j")
    except Exception as e:
        print(f"❌ Не удалось подключиться к Neo4j: {e}")
        return 1
    
    # Проверка существующего Мета-Графа
    if check_metagraph_exists(driver):
        if force:
            cleanup_metagraph(driver)
        else:
            print()
            print("⚠️  Мета-Граф уже существует!")
            print("   Используйте флаг --force для пересоздания (УДАЛИТ ВСЕ ПРАВИЛА)")
            driver.close()
            return 1
    
    # Загрузка Мета-Графа
    if not bootstrap_metagraph(driver):
        driver.close()
        return 1
    
    # Проверка
    if not verify_metagraph(driver):
        print("\n⚠️  Обнаружены расхождения. Проверьте вручную.")
    else:
        print("\n🎉 Мета-Граф успешно загружен и проверен!")
    
    driver.close()
    
    print()
    print("=" * 70)
    print("ГОТОВО!")
    print("=" * 70)
    print()
    print("Следующие шаги:")
    print("  1. Проверьте Мета-Граф в Neo4j Browser:")
    print("     MATCH (n:NodeType)-[:CAN_PERFORM]->(a:Action) RETURN n, a")
    print("  2. Перезапустите MCP сервер для применения новых правил")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

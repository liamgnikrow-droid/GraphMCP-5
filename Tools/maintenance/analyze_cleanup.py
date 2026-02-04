#!/usr/bin/env python3
"""
Анализ актуальности test и maintenance файлов для очистки
"""

# ТЕСТОВЫЕ ФАЙЛЫ (12 штук)

test_files = {
    # АКТУАЛЬНЫЕ (используются для проверки core функций)
    "test_middleware.py": {
        "date": "2026-01-28",
        "purpose": "Тестирование Middleware (core функция)",
        "status": "KEEP - тестирует критическую функциональность",
    },
    "test_constraint_middleware.py": {
        "date": "2026-01-29",
        "purpose": "Тестирование Constraints (Pure Links, Russian)",
        "status": "KEEP - проверяет Iron Dome правила",
    },
    "test_find_orphans.py": {
        "date": "2026-02-01",
        "purpose": "Тестирование find_orphans (мы его только что чинили!)",
        "status": "KEEP - актуальный тест недавно исправленного инструмента",
    },
    
    # УСТАРЕВШИЕ / ОДНОРАЗОВЫЕ
    "test_create_concept_with_middleware.py": {
        "date": "2026-01-29",
        "purpose": "Тест create_concept с constraints",
        "status": "ARCHIVE - функциональность покрыта test_constraint_middleware.py",
    },
    "test_explain_physics.py": {
        "date": "2026-01-28",
        "purpose": "Тест explain_physics инструмента",
        "status": "DELETE - одноразовый тест, функция работает",
    },
    "test_format_cypher.py": {
        "date": "2026-01-28",
        "purpose": "Тест format_cypher (propose_change)",
        "status": "KEEP - документирует переименование propose_change",
    },
    "test_get_full_context.py": {
        "date": "2026-01-28",
        "purpose": "Тест get_full_context",
        "status": "DELETE - одноразовый тест",
    },
    "test_impact_analysis.py": {
        "date": "2026-01-28",
        "purpose": "Тест create_concept с impact analysis",
        "status": "DELETE - одноразовый тест",
    },
    "test_map_codebase_live.py": {
        "date": "2026-01-29",
        "purpose": "Живой тест map_codebase",
        "status": "DELETE - одноразовый тест",
    },
    "test_register_task.py": {
        "date": "2026-01-28",
        "purpose": "Тест register_task с constraints",
        "status": "DELETE - одноразовый тест",
    },
    "test_server_logic.py": {
        "date": "2026-01-27",
        "purpose": "Базовый тест server.py",
        "status": "DELETE - устарел",
    },
    "test_sync_push.py": {
        "date": "2026-02-01",
        "purpose": "Тест двунаправленной синхронизации",
        "status": "DELETE - функциональность не реализована",
    },
}

# MAINTENANCE СКРИПТЫ (33 штуки)

maintenance_files = {
    # АКТУАЛЬНЫЕ (используются регулярно)
    "spec_coverage.py": {
        "purpose": "Проверка покрытия спецификации Requirements",
        "status": "KEEP - полезный диагностический инструмент",
    },
    "sync_watcher.py": {
        "date": "2026-02-01",
        "purpose": "Отслеживание изменений файлов для auto-sync",
        "status": "KEEP - может быть полезен в будущем",
    },
    "delete_duplicate_functions.py": {
        "date": "2026-02-04",
        "purpose": "Удаление дубликатов Functions (использовался сегодня!)",
        "status": "KEEP - недавно использовался",
    },
    "fix_graph_architecture.py": {
        "date": "2026-02-04",
        "purpose": "Массовое исправление архитектуры (использовался сегодня!)",
        "status": "KEEP - недавно использовался",
    },
    "find_orphan_files.py": {
        "date": "2026-02-04",
        "purpose": "Диагностика файлов-призраков (использовался сегодня!)",
        "status": "KEEP - недавно использовался",
    },
    "link_physics_implementation.py": {
        "date": "2026-02-01",
        "purpose": "Линковка Functions к Actions/Constraints",
        "status": "KEEP - может быть актуален",
    },
    "register_find_orphans.py": {
        "date": "2026-02-01",
        "purpose": "Регистрация find_orphans в мета-графе",
        "status": "ARCHIVE - одноразовый скрипт, уже выполнен",
    },
    
    # УСТАРЕВШИЕ / ОДНОРАЗОВЫЕ (выполнили задачу и больше не нужны)
    "aggressive_clean.py": {"status": "DELETE - одноразовая очистка"},
    "apply_semantic_links.py": {"status": "DELETE - одноразовая миграция"},
    "audit_file_links.py": {"status": "DELETE - одноразовый аудит"},
    "check_db_node.py": {"status": "DELETE - одноразовая проверка"},
    "check_islands.py": {"status": "DELETE - функциональность в find_orphans"},
    "check_orphaned_files.py": {"status": "DELETE - функциональность в find_orphan_files"},
    "check_stats.py": {"status": "DELETE - одноразовая статистика"},
    "clean_duplicates.py": {"status": "DELETE - одноразовая очистка"},
    "consolidate_graph.py": {"status": "DELETE - одноразовая операция"},
    "debug_ideas.py": {"status": "DELETE - одноразовая отладка"},
    "deduplicate_genesis.py": {"status": "DELETE - одноразовая операция"},
    "enforce_physics.py": {"status": "DELETE - одноразовая операция"},
    "export_mapping_inventory.py": {"status": "DELETE - одноразовый экспорт"},
    "final_fix_spec.py": {"status": "DELETE - одноразовое исправление"},
    "final_link_tools.py": {"status": "DELETE - одноразовая линковка"},
    "finalize_cleanup.py": {"status": "DELETE - одноразовая очистка"},
    "fix_duplication.py": {"status": "DELETE - одноразовое исправление"},
    "force_full_sync.py": {"status": "DELETE - одноразовая синхронизация"},
    "force_link_files.py": {"status": "DELETE - одноразовая линковка"},
    "intelligent_link_files.py": {"status": "DELETE - одноразовая линковка"},
    "manual_link_final.py": {"status": "DELETE - одноразовая линковка"},
    "migrate_implements_links.py": {"status": "DELETE - одноразовая миграция"},
    "migrate_rels.py": {"status": "DELETE - одноразовая миграция"},
    "purge_junk_nodes.py": {"status": "DELETE - одноразовая очистка"},
    "purge_specitems.py": {"status": "DELETE - одноразовая очистка"},
    "sanitize_and_link.py": {"status": "DELETE - одноразовая операция"},
    "surgical_fix_spec.py": {"status": "DELETE - одноразовое исправление"},
}

# SUMMARY

print("=" * 70)
print("АНАЛИЗ АКТУАЛЬНОСТИ ФАЙЛОВ")
print("=" * 70)

print("\n📝 ТЕСТОВЫЕ ФАЙЛЫ (test_*.py)")
print("-" * 70)
keep = [f for f, d in test_files.items() if "KEEP" in d["status"]]
delete = [f for f, d in test_files.items() if "DELETE" in d["status"]]
archive = [f for f, d in test_files.items() if "ARCHIVE" in d["status"]]

print(f"\n✅ ОСТАВИТЬ ({len(keep)}):")
for f in keep:
    print(f"  • {f}")
    print(f"    {test_files[f]['status']}")

print(f"\n🗑️  УДАЛИТЬ ({len(delete)}):")
for f in delete:
    print(f"  • {f}")

print(f"\n📦 АРХИВИРОВАТЬ ({len(archive)}):")
for f in archive:
    print(f"  • {f}")

print("\n🔧 MAINTENANCE СКРИПТЫ (maintenance/*.py)")
print("-" * 70)
m_keep = [f for f, d in maintenance_files.items() if "KEEP" in d["status"]]
m_delete = [f for f, d in maintenance_files.items() if "DELETE" in d["status"]]
m_archive = [f for f, d in maintenance_files.items() if "ARCHIVE" in d["status"]]

print(f"\n✅ ОСТАВИТЬ ({len(m_keep)}):")
for f in m_keep:
    print(f"  • {f}")
    print(f"    {maintenance_files[f]['status']}")

print(f"\n🗑️  УДАЛИТЬ ({len(m_delete)}):")
for f in m_delete:
    print(f"  • {f}")

print(f"\n📦 АРХИВИРОВАТЬ ({len(m_archive)}):")
for f in m_archive:
    print(f"  • {f}")

print("\n" + "=" * 70)
print("ИТОГО:")
print(f"  Тестовые: {len(keep)} оставить, {len(delete)} удалить, {len(archive)} архивировать")
print(f"  Maintenance: {len(m_keep)} оставить, {len(m_delete)} удалить, {len(m_archive)} архивировать")
print(f"  TOTAL: {len(m_delete) + len(delete) + len(archive) + len(m_archive)} файлов для очистки")
print("=" * 70)

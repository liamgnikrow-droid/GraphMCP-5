# Отчёт: Очистка устаревших файлов

**Дата:** 2026-02-04  
**Задача:** Удаление ненужных test и maintenance файлов

## Выполненная работа

### 1. Анализ файлов

Проанализировано **45 файлов**:
- 12 тестовых файлов (`test_*.py`)
- 33 maintenance скрипта

**Результат анализа:**
- ✅ Оставить: 10 файлов (4 test + 6 maintenance)
- 🗑️ Удалить: 34 файла (7 test + 27 maintenance)
- 📦 Архивировать: 2 файла (1 test + 1 maintenance)

### 2. Автоматическая очистка

**Статистика:**
- ✅ Удалено физических файлов: **34**
- 🗑️ Удалено узлов Neo4j: **63**
- 📄 Удалено .md файлов: **54**
- 📦 Архивировано файлов: **2**

**Итого удалено:** 151 объект (34 .py + 63 Neo4j nodes + 54 .md)

### 3. Оставшиеся файлы

#### Тестовые (4 файла):
1. `test_middleware.py` - тестирует критическую Middleware функциональность
2. `test_constraint_middleware.py` - проверяет Iron Dome правила (Pure Links, Russian)
3. `test_find_orphans.py` - актуальный тест недавно исправленного инструмента
4. `test_format_cypher.py` - документирует переименование propose_change

#### Maintenance (6 файлов):
1. `spec_coverage.py` - проверка покрытия спецификации Requirements
2. `sync_watcher.py` - отслеживание изменений для auto-sync
3. `delete_duplicate_functions.py` - использовался сегодня
4. `fix_graph_architecture.py` - использовался сегодня
5. `find_orphan_files.py` - использовался сегодня
6. `link_physics_implementation.py` - может быть актуален

#### Архив (2 файла):
- `archive/test_create_concept_with_middleware.py`
- `archive/register_find_orphans.py`

## Статус островов

### До очистки:
- 76 островов (test files + maintenance scripts)

### После очистки:
- 74 островов

**Состав оставшихся островов:**
- 19 File nodes
- 54 Function nodes
- 1 Class node

**Почему они острова:**
Эти узлы - вспомогательные инструменты (тесты, maintenance), которые **не линкованы к Requirements**. Это ожидаемо и правильно.

**Решение:** Оставить как есть. Эти "острова" не мешают основному графу.

### Альтернативные варианты:

**Вариант A:** Создать `REQUIREMENT-Testing_Infrastructure` и слинковать все test-файлы  
**Вариант B:** Создать `REQUIREMENT-Maintenance_Tools` и слинковать maintenance скрипты  
**Вариант C:** Полностью исключить их из графа (не маппить в `codebase_mapper.py`)

Рекомендую **Вариант C** - добавить в `codebase_mapper.py` фильтр:
```python
if filename.startswith('test_') or dirname.endswith('/maintenance'):
    continue  # Skip auxiliary files
```

## Ответ на вопрос об Obsidian

### Почему не видно связей?

**Проблема:** В `ACT-find_orphans.md` нет явных связей в frontmatter.

**Причина:** Связь `IMPLEMENTS` идёт **от Function К Action** (входящая для Action), а `graph_sync.py` добавляет в frontmatter только **исходящие** связи.

**Решение:** Использовать **Backlinks** в Obsidian:
1. Откройте `ACT-find_orphans.md`
2. В правой панели найдите **"Backlinks"**
3. Там будет `FUNC-Tools_server_py-tool_find_orphans`

**Альтернатива:** Модифицировать `graph_sync.py` чтобы добавлять поле `implemented_by:` для Action/Constraint узлов.

См. подробности в: `HOWTO_View_Action_Links_in_Obsidian.md`

## Удалённые файлы

### Тестовые (7):
- `test_explain_physics.py`
- `test_get_full_context.py`
- `test_impact_analysis.py`
- `test_map_codebase_live.py`
- `test_register_task.py`
- `test_server_logic.py`
- `test_sync_push.py`

### Maintenance (27):
- `aggressive_clean.py`
- `apply_semantic_links.py`
- `audit_file_links.py`
- `check_db_node.py`
- `check_islands.py`
- `check_orphaned_files.py`
- `check_stats.py`
- `clean_duplicates.py`
- `consolidate_graph.py`
- `debug_ideas.py`
- `deduplicate_genesis.py`
- `enforce_physics.py`
- `export_mapping_inventory.py`
- `final_fix_spec.py`
- `final_link_tools.py`
- `finalize_cleanup.py`
- `fix_duplication.py`
- `force_full_sync.py`
- `force_link_files.py`
- `intelligent_link_files.py`
- `manual_link_final.py`
- `migrate_implements_links.py`
- `migrate_rels.py`
- `purge_junk_nodes.py`
- `purge_specitems.py`
- `sanitize_and_link.py`
- `surgical_fix_spec.py`

## Рекомендации

1. **Периодическая очистка:** Запускать `cleanup_obsolete_files.py` раз в месяц
2. **Фильтрация маппинга:** Не маппировать test/maintenance файлы в граф (Вариант C)
3. **Obsidian backlinks:** Использовать встроенные backlinks вместо явных полей в frontmatter

## Файлы созданы

- `analyze_cleanup.py` - анализ актуальности файлов
- `cleanup_obsolete_files.py` - автоматическая очистка
- `HOWTO_View_Action_Links_in_Obsidian.md` - инструкция по просмотру связей

# Анализ "Чистых Островов" (28 узлов)

## Исполнительное резюме
Все 28 "островов" **СУЩЕСТВУЮТ в Neo4j** и **ИМЕЮТ связи**, но они **изолированы от IDEA-Genesis** при использовании строгого фильтра (`DECOMPOSES|IMPLEMENTS`).

## Категории островов

### 1. Functions с устаревшей связью `CONTAINS` (24 узла)

**Проблема:** 
Функции из `graph_sync.py` связаны с родительским `Class` через связь `CONTAINS` вместо канонической `DECOMPOSES`.

**Примеры:**
- `FUNC-Tools_graph_sync_py__GraphSync__extract_body_from_markdown`
- `FUNC-Tools_graph_sync_py__GraphSync__sync_node`
- `FUNC-Tools_graph_sync_py__GraphSync__fetch_node`
- И ещё ~21 функция с двойным подчеркиванием `__`

**Диагностика:**
```cypher
MATCH (func:Function {uid: 'FUNC-Tools_graph_sync_py__GraphSync__extract_body_from_markdown'})
OPTIONAL MATCH (parent)-[r]->(func)
RETURN type(r), labels(parent)[0]
// Result: CONTAINS, Class
```

**Причина:**
Старая версия `codebase_mapper.py` использовала `CONTAINS` для методов классов. Новая версия использует `DECOMPOSES`.

**Последствия:**
- Функции не достижимы из IDEA-Genesis через `DECOMPOSES|IMPLEMENTS` фильтр
- Считаются "островами" при строгой проверке связности
- Markdown-файлы НЕ синхронизированы с графом (нет frontmatter `implements:`)

**Дополнительная проблема - дубликаты:**
Для одних и тех же методов класса существуют 2 версии:
- С двойным подчеркиванием: `FUNC-Tools_graph_sync_py__GraphSync__sync_node` (CONTAINS)
- С одинарным подчеркиванием: `FUNC-Tools_graph_sync_py_GraphSync_sync_node` (возможно DECOMPOSES?)

### 2. System Actions без бизнес-связей (2 узла)

**Узлы:**
- `ACT-find_orphans`
- `ACT-propose_change`

**Проблема:**
Эти Action-узлы являются частью **мета-графа** (системная онтология), но не имеют прямых связей с бизнес-требованиями через `IMPLEMENTS`.

**Текущие связи:**
```
ACT-find_orphans:
  - ALLOWS_CONNECTION -> NodeType (метаграф-правило)
  - CAN_PERFORM -> NodeType (множественные, для разных типов узлов)
```

**Диагностика:**
Эти узлы НЕ являются "островами" в смысле изоляции от графа, но они **изолированы от бизнес-дерева** (IDEA-Genesis).

**Причина:**
System Actions живут в отдельном namespace `/Graph_Physics/` и представляют **мета-модель**, а не **бизнес-логику**. Они не должны иметь путь к IDEA-Genesis.

**Вопрос:** 
Должны ли системные узлы (`Action`, `Constraint`, `NodeType`) вообще проверяться инструментом `find_orphans`? 
Предыдущая версия исключала их (`AND NOT (n:NodeType)`), но не исключала `Action` и `Constraint`.

### 3. File-узлы с "повреждённым" YAML (2 узла, НО НЕ ОСТРОВА!)

**Узлы:**
- `FILE-Tools_server_py`
- `FILE-Tools_code_mapper_py`

**Статус:** 
✓ НЕ острова! Они ПОДКЛЮЧЕНЫ к IDEA-Genesis.

**Диагностика:**
```
FILE-Tools_server_py:
  - 26 IMPLEMENTS -> Requirement
  - 34 DECOMPOSES -> Function
  - Путь к IDEA-Genesis существует
```

**Проблема:**
Вы указали "видно что сломан YAML", но анализ файла показывает **корректный frontmatter**:
- `implements:` содержит 26 ссылок на Requirements
- `decomposes:` содержит 34 ссылки на Functions
- Синтаксис валиден

**Возможная причина упоминания:**
- Frontmatter содержит WikiLinks (`[[...]]`), которые нарушают принцип "Pure Links"
- Но это **ожидаемое поведение** для синхронизированных файлов (`graph_sync.py` генерирует WikiLinks)

## Корневая причина: Миграция `CONTAINS` → `DECOMPOSES`

### Timeline проблемы:

1. **2026-01-29 13:21:33** - `codebase_mapper.py` запущен с логикой `CONTAINS`
2. **Позже** - `codebase_mapper.py` обновлён для использования `DECOMPOSES`
3. **2026-02-02** - Строгая фильтрация `find_orphans` введена
4. **Сегодня** - Старые узлы с `CONTAINS` стали видны как "острова"

### Proof:
```python
# Старый код codebase_mapper.py (предположительно):
rel_type = "CONTAINS"  # Для методов класса

# Новый код:
rel_type = "DECOMPOSES"  # Для всех дочерних элементов
```

## Рекомендации (БЕЗ ДЕЙСТВИЙ, ТОЛЬКО АНАЛИЗ)

### Вариант 1: Миграция связей CONTAINS → DECOMPOSES
**Плюсы:**
- Унифицирует граф
- Устранит "острова"
- Приведёт к канонической онтологии

**Минусы:**
- Риск повреждения существующих связей
- Требует тестирования

**Скрипт (концепт):**
```cypher
MATCH (parent:Class)-[old:CONTAINS]->(child:Function)
MERGE (parent)-[:DECOMPOSES]->(child)
DELETE old
```

### Вариант 2: Удаление дубликатов
**Проблема:** 
Есть ли дубликаты вида:
- `FUNC-...__ GraphSync__sync_node` (CONTAINS)
- `FUNC-..._GraphSync_sync_node` (DECOMPOSES)?

**Требуется проверка:**
Сколько функций с паттерном `graph_sync_py` существует и какие из них дубликаты?

### Вариант 3: Исключение System Nodes из find_orphans
**Логика:**
Action/Constraint живут в мета-графе и не должны проверяться на связность с IDEA-Genesis.

**Изменение фильтра:**
```python
WHERE NOT (n:NodeType) 
  AND NOT (n:Action)
  AND NOT (n:Constraint)
```

## Статистика

| Категория | Количество | Статус |
|-----------|-----------|---------|
| Functions (CONTAINS) | ~24 | ✗ Острова |
| System Actions | 2 | ✗ Острова (но это нормально?) |
| Files с "повреждённым" YAML | 2 | ✓ НЕ острова (ложное упоминание) |
| **Итого реальных островов** | **24-26** | |

## Вопросы для принятия решений

1. **Должны ли System Actions (ACT-*, CON-*) проверяться find_orphans?**
   - Если нет, исключить их из фильтра
   - Если да, нужно ли их линковать к Requirements?

2. **Существуют ли дубликаты Functions?**
   - Проверить наличие паттерна `__ClassName__method` vs `_ClassName_method`

3. **Безопасна ли миграция CONTAINS → DECOMPOSES?**
   - Проверить, не сломает ли это existing logic

4. **Что означает "сломан YAML" для FILE-узлов?**
   - Нужны конкретные примеры повреждений

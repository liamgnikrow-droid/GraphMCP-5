# Отчёт: Устранение островов Action-узлов

**Дата:** 2026-02-04  
**Задача:** Подключение `ACT-find_orphans` и `ACT-propose_change` к графу IDEA-Genesis

## Проблема

Два Action-узла были изолированы от графа:
- `ACT-find_orphans` 
- `ACT-propose_change`

**Причина:** Отсутствовали связи `IMPLEMENTS` между Functions и Actions, как требует спецификация (SPEC-Graph_Physics, раздел 1.6).

## Корневая причина

### Архитектура мета-графа (из SPEC-Graph_Physics):

```
(:Function)-[:IMPLEMENTS]->(:Action)
```

Эта связь создаёт **"Мост в Реальность"** между:
- **Kernel Space** (Action — абстрактный инструмент)
- **Reality** (Function — конкретная реализация в `server.py`)

### Что пошло не так:

1. **`tool_find_orphans`**: Функция существовала в коде, но НЕ была в графе (не замаппирована `codebase_mapper.py`)
2. **`tool_propose_change`**: Action был создан, но функция была **переименована** в `tool_format_cypher`

## Решение

### 1. Пересканирование кода ✅

```bash
docker exec graphmcp-core python -c "
from server import tool_map_codebase
import asyncio
asyncio.run(tool_map_codebase({}))
"
```

**Результат:** 
- 91 File
- 7 Class
- 184 Function  
В том числе `FUNC-Tools_server_py-tool_find_orphans`

### 2. Создание связей IMPLEMENTS ✅

```cypher
// Связь 1: tool_find_orphans реализует ACT-find_orphans
MATCH (f:Function {uid: 'FUNC-Tools_server_py-tool_find_orphans'})
MATCH (a:Action {uid: 'ACT-find_orphans'})
MERGE (f)-[:IMPLEMENTS]->(a)

// Связь 2: tool_format_cypher реализует ACT-propose_change (renamed)
MATCH (f:Function {uid: 'FUNC-Tools_server_py-tool_format_cypher'})
MATCH (a:Action {uid: 'ACT-propose_change'})
MERGE (f)-[:IMPLEMENTS]->(a)
```

### 3. Верификация пути к IDEA-Genesis ✅

```
IDEA-Genesis (root)
  -> ... (через DECOMPOSES)
    -> SPEC-Graph_Physics
      -> REQUIREMENT-TOOL__MAP_CODEBASE__CODE_INTEGRATION
        <- FILE-Tools_server_py (IMPLEMENTS)
          -> FUNC-Tools_server_py-tool_find_orphans (DECOMPOSES)
            -> ACT-find_orphans (IMPLEMENTS)
```

## Результат

| Метрика | До | После |
|---------|-----|-------|
| Острова Action | 2 | 0 ✅ |
| ACT-find_orphans | Изолирован | Подключен ✅ |
| ACT-propose_change | Изолирован | Подключен ✅ |

### Оставшиеся "острова" (76 узлов):

Все оставшиеся острова — это **тестовые файлы** и **maintenance скрипты**:
- `test_*.py` (13 файлов + их Functions)
- `Tools/maintenance/*.py` (7 скриптов + их Functions)

**Статус:** Это ожидаемо, т.к. они не являются частью основной бизнес-логики и не должны линковаться к Requirements.

## Почему Actions не показывают IMPLEMENTS в frontmatter?

**Вопрос:** Почему в `ACT-find_orphans.md` нет поля `implements:`?

**Ответ:** 
`graph_sync.py` добавляет только **OUTGOING** связи в frontmatter (строка 178):
```python
if rel['direction'] == 'OUT':
    typed_rels[rel_type].append(f"[[{target}]]")
```

Для Action-узлов связь `IMPLEMENTS` является **INCOMING** (Function -> Action), поэтому она не появляется в YAML.

**Это правильное поведение** согласно семантике:
- Function линкует **к** Action (реализует абстракцию)
- Action **не линкует к** Function (не знает о конкретной реализации)

В Obsidian эта связь видна через **Backlinks**.

## Рекомендации

### 1. Автоматическая линковка новых tools

При добавлении нового tool в `server.py`:

1. Создать Action в `bootstrap_metagraph.py`
2. Запустить `map_codebase` для сканирования
3. Создать связь `IMPLEMENTS` автоматически или через maintenance скрипт

### 2. Тестовые файлы

Варианты обработки test-файлов:

**Вариант A:** Создать `REQUIREMENT-Testing_Infrastructure` и слинковать все test-файлы к нему  
**Вариант B:** Исключить test-файлы из графа (добавить в .gitignore для `codebase_mapper`)  
**Вариант C:** Оставить как есть (они не мешают основному графу)

Рекомендую **Вариант C** — острова test-файлов не критичны.

## Файлы изменены

- Граф Neo4j: +2 связи IMPLEMENTS
- Markdown: синхронизированы `ACT-find_orphans.md`, `ACT-propose_change.md`

## Заключение

✅ Оба Action-узла успешно подключены к графу через архитектурные связи `IMPLEMENTS`  
✅ Путь к IDEA-Genesis установлен  
✅ Философия "всё есть граф" реализована для мета-узлов

Острова устранены!

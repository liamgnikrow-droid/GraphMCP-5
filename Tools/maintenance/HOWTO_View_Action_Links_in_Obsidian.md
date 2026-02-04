# Как увидеть связи Action-узлов в Obsidian

## Проблема
В файлах `ACT-find_orphans.md` и `ACT-propose_change.md` нет явных связей в frontmatter.

## Почему так?

### Направление связей:
```
Function -[:IMPLEMENTS]-> Action
```

Для Action-узлов это **входящие связи** (IN), а `graph_sync.py` добавляет в frontmatter только **исходящие** (OUT).

## Как увидеть связи в Obsidian?

### Способ 1: Backlinks (рекомендуется) ✅

1. Откройте файл `ACT-find_orphans.md` в Obsidian
2. В правой панели найдите раздел **"Backlinks"** (Обратные ссылки)
3. Там должна быть ссылка от `FUNC-Tools_server_py-tool_find_orphans`

### Способ 2: Graph View

1. Откройте Graph View в Obsidian (Ctrl+G или Cmd+G)
2. Найдите узел `ACT-find_orphans`
3. Вы увидите связь с `FUNC-Tools_server_py-tool_find_orphans`

### Способ 3: Проверка в Neo4j напрямую

```cypher
MATCH (func:Function)-[:IMPLEMENTS]->(action:Action {uid: 'ACT-find_orphans'})
RETURN func.uid, func.name, action.uid
```

**Результат:**
```
func.uid: FUNC-Tools_server_py-tool_find_orphans
func.name: tool_find_orphans
action.uid: ACT-find_orphans
```

## Хотите видеть связи в frontmatter?

Если нужно, чтобы в frontmatter Action-узлов было поле `implemented_by:`, можно модифицировать `graph_sync.py`:

### Вариант A: Добавить входящие связи в отдельное поле

```python
# В graph_sync.py, после блока OUTGOING связей:

# Add INCOMING relationships for specific types
if node_type in ['Action', 'Constraint']:
    incoming_rels = {}
    for rel in rels:
        if rel['direction'] == 'IN':
            rel_type = f"{rel['type'].lower().replace('_', '-')}-from"
            source = rel['other_uid']
            
            if rel_type not in incoming_rels:
                incoming_rels[rel_type] = []
            incoming_rels[rel_type].append(f"[[{source}]]")
    
    for key, links in incoming_rels.items():
        if links:
            fm_lines.append(f"{key}:")
            for link in links:
                fm_lines.append(f"  - \"{link}\"")
```

Это добавит в frontmatter:
```yaml
implements-from:
  - "[[FUNC-Tools_server_py-tool_find_orphans]]"
```

### Вариант B: Использовать семантическое имя

```python
# Специально для Action -> Function mapping
if node_type == 'Action':
    implementers = [rel['other_uid'] for rel in rels if rel['type'] == 'IMPLEMENTS' and rel['direction'] == 'IN']
    if implementers:
        fm_lines.append("implemented_by:")
        for impl in implementers:
            fm_lines.append(f"  - \"[[{impl}]]\"")
```

Это добавит:
```yaml
implemented_by:
  - "[[FUNC-Tools_server_py-tool_find_orphans]]"
```

## Рекомендация

**Текущая ситуация:** Связи есть, они работают, они видны через Backlinks.

**Если нужно:** Можно добавить явное поле `implemented_by:` для Action/Constraint узлов, но это не обязательно, т.к. Obsidian и так показывает эти связи.

Хотите, чтобы я добавил явное поле `implemented_by:` в frontmatter?

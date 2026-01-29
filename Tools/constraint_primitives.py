"""
Constraint Primitives for Meta-Graph Validation

These are atomic operations referenced by :Constraint nodes in Meta-Graph.
They are immutable - changes to rules happen in Meta-Graph, not here.
"""

import re


def cyrillic_ratio(text: str) -> float:
    """
    Calculates the ratio of Cyrillic characters in text.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Float between 0.0 and 1.0 representing Cyrillic character ratio
    """
    if not text:
        return 0.0
    
    cyrillic_count = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
    total_count = len(text)
    
    return cyrillic_count / total_count if total_count > 0 else 0.0


def regex_match(text: str, pattern: str) -> bool:
    """
    Checks if text matches a regex pattern.
    
    Args:
        text: Input text to check
        pattern: Regex pattern
        
    Returns:
        True if pattern found in text, False otherwise
    """
    if not text or not pattern:
        return False
    
    return bool(re.search(pattern, text))


def node_count(driver, label: str) -> int:
    """
    Counts nodes with a specific label in Neo4j.
    
    Args:
        driver: Neo4j Driver instance
        label: Node label to count (e.g., 'Spec', 'Idea')
        
    Returns:
        Integer count of nodes with that label
    """
    query = f"MATCH (n:{label}) RETURN count(n) as count"
    records, _, _ = driver.execute_query(query, database_="neo4j")
    
    if records:
        return records[0]["count"]
    return 0


def incoming_count(driver, uid: str) -> int:
    """
    Counts incoming relationships to a node.
    
    Args:
        driver: Neo4j Driver instance
        uid: Node UID
        
    Returns:
        Integer count of incoming relationships
    """
    query = "MATCH (n {uid: $uid})<-[r]-() RETURN count(r) as count"
    records, _, _ = driver.execute_query(query, {"uid": uid}, database_="neo4j")
    
    if records:
        return records[0]["count"]
    return 0


def not_equals(a, b) -> bool:
    """
    Checks inequality.
    
    Args:
        a: First value
        b: Second value
        
    Returns:
        True if a != b
    """
    return a != b


def compare(a, operator: str, b) -> bool:
    """
    Universal comparison operator.
    
    Args:
        a: Left operand
        operator: Comparison operator (>=, <=, ==, !=, >, <)
        b: Right operand
        
    Returns:
        Boolean result of comparison
    """
    ops = {
        ">=": lambda x, y: x >= y,
        "<=": lambda x, y: x <= y,
        "==": lambda x, y: x == y,
        "!=": lambda x, y: x != y,
        ">": lambda x, y: x > y,
        "<": lambda x, y: x < y,
    }
    
    if operator not in ops:
        raise ValueError(f"Unknown operator: {operator}")
    
    return ops[operator](a, b)


# Registry of available primitives
PRIMITIVES = {
    "cyrillic_ratio": cyrillic_ratio,
    "regex_match": regex_match,
    "node_count": node_count,
    "incoming_count": incoming_count,
    "not_equals": not_equals,
    "compare": compare,
}

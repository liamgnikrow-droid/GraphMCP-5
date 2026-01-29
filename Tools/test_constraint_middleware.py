#!/usr/bin/env python3
"""
Test script for Constraint Middleware (Phase 3)

Tests that check_constraints() correctly:
1. Loads constraints from Meta-Graph
2. Applies primitives (cyrillic_ratio, regex_match, node_count)
3. Returns violations when rules are broken
"""

import sys
sys.path.insert(0, '/opt/tools')

from server import check_constraints
import asyncio


def test_cyrillic_ratio():
    """Test Russian Language constraint"""
    print("=" * 70)
    print("TEST 1: Russian Language Constraint (cyrillic_ratio)")
    print("=" * 70)
    
    # Test with English text (should FAIL)
    context = {
        "text": "Hello World",
        "target_type": "Requirement",
        "tool_name": "create_concept"
    }
    
    passed, violations = check_constraints(action_uid=None, context=context)
    
    print(f"Input: 'Hello World'")
    print(f"Passed: {passed}")
    if violations:
        print(f"Violations:")
        for v in violations:
            print(f"  • {v}")
    else:
        print("  (No violations)")
    print()
    
    # Test with Russian text (should PASS)
    context = {
        "text": "Привет мир",
        "target_type": "Requirement",
        "tool_name": "create_concept"
    }
    
    passed, violations = check_constraints(action_uid=None, context=context)
    
    print(f"Input: 'Привет мир'")
    print(f"Passed: {passed}")
    if violations:
        print(f"Violations:")
        for v in violations:
            print(f"  • {v}")
    else:
        print("  (No violations)")
    print()


def test_wikilinks():
    """Test No WikiLinks constraint"""
    print("=" * 70)
    print("TEST 2: No WikiLinks Constraint (regex_match)")
    print("=" * 70)
    
    # Test with wikilink (should FAIL)
    context = {
        "text": "Связано с [[REQ-Auth]]",
        "target_type": "Task",
        "tool_name": "create_concept"
    }
    
    passed, violations = check_constraints(action_uid=None, context=context)
    
    print(f"Input: 'Связано с [[REQ-Auth]]'")
    print(f"Passed: {passed}")
    if violations:
        print(f"Violations:")
        for v in violations:
            print(f"  • {v}")
    else:
        print("  (No violations)")
    print()
    
    # Test without wikilink (should PASS)
    context = {
        "text": "Связано с требованием авторизации",
        "target_type": "Task",
        "tool_name": "create_concept"
    }
    
    passed, violations = check_constraints(action_uid=None, context=context)
    
    print(f"Input: 'Связано с требованием авторизации'")
    print(f"Passed: {passed}")
    if violations:
        print(f"Violations:")
        for v in violations:
            print(f"  • {v}")
    else:
        print("  (No violations)")
    print()


def test_combined_constraints():
    """Test multiple constraints at once"""
    print("=" * 70)
    print("TEST 3: Combined Constraints (Russian + No WikiLinks)")
    print("=" * 70)
    
    # Test with English + wikilink (should FAIL BOTH)
    context = {
        "text": "Check [[REQ-Security]] for details",
        "target_type": "Requirement",
        "tool_name": "create_concept"
    }
    
    passed, violations = check_constraints(action_uid=None, context=context)
    
    print(f"Input: 'Check [[REQ-Security]] for details'")
    print(f"Passed: {passed}")
    if violations:
        print(f"Violations ({len(violations)}):")
        for v in violations:
            print(f"  • {v}")
    else:
        print("  (No violations)")
    print()


def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "CONSTRAINT MIDDLEWARE TEST" + " " * 27 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    test_cyrillic_ratio()
    test_wikilinks()
    test_combined_constraints()
    
    print("=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print()
    print("💡 Middleware loads constraints from Neo4j Meta-Graph dynamically!")
    print()


if __name__ == "__main__":
    main()

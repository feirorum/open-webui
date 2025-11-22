"""
title: Requirements Management Toolkit v2.0
author: Open WebUI Requirements Agent
author_url: https://github.com/open-webui/open-webui
version: 2.0.0
requirements: pyyaml, python-slugify
license: MIT
description: Enterprise-grade requirements engineering toolkit with hierarchical requirements, conflict detection, quality scoring (SMART/INVEST), approval workflows, and stakeholder management.
"""

import os
import json
import yaml
import re
import math
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Set
from pathlib import Path
from pydantic import BaseModel, Field
from collections import defaultdict

try:
    from slugify import slugify
except ImportError:
    def slugify(text):
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        return text.strip('-')


# =============================================================================
# CONSTANTS
# =============================================================================

REQUIREMENT_TYPES = {
    "epic": {"prefix": "EPIC", "level": 1, "can_have_children": True},
    "feature": {"prefix": "FEAT", "level": 2, "can_have_children": True},
    "user-story": {"prefix": "REQ", "level": 3, "can_have_children": True},
    "task": {"prefix": "TASK", "level": 4, "can_have_children": False},
    "constraint": {"prefix": "CONS", "level": 0, "can_have_children": False},
    "nfr": {"prefix": "NFR", "level": 0, "can_have_children": False},
    "bug": {"prefix": "BUG", "level": 0, "can_have_children": False},
}

HIERARCHY_RULES = {
    "epic": {"can_have_parent": [], "must_have_parent": False},
    "feature": {"can_have_parent": ["epic"], "must_have_parent": True},
    "user-story": {"can_have_parent": ["feature", "epic"], "must_have_parent": False},
    "task": {"can_have_parent": ["user-story", "feature"], "must_have_parent": True},
    "constraint": {"can_have_parent": ["epic", "feature", "user-story"], "must_have_parent": False},
    "nfr": {"can_have_parent": ["epic", "feature"], "must_have_parent": False},
    "bug": {"can_have_parent": ["feature", "user-story"], "must_have_parent": False},
}

WORKFLOW_STAGES = ["draft", "proposed", "in-review", "accepted", "in-progress", "implemented", "deprecated"]

VAGUE_TERMS = [
    'good', 'bad', 'better', 'worse', 'fast', 'slow', 'easy', 'hard',
    'user-friendly', 'intuitive', 'nice', 'clean', 'modern', 'simple',
    'efficient', 'powerful', 'robust', 'scalable', 'flexible', 'seamless',
    'optimal', 'best', 'worst', 'quick', 'adequate', 'reasonable', 'appropriate'
]

CONTRADICTION_PAIRS = [
    ("mandatory", "optional"), ("required", "optional"), ("always", "never"),
    ("must", "must not"), ("public", "private"), ("enabled", "disabled"),
    ("allow", "deny"), ("permit", "prohibit"), ("can", "cannot"),
    ("synchronous", "asynchronous"), ("encrypted", "unencrypted"),
]


# =============================================================================
# HELPER CLASSES
# =============================================================================

class HierarchyManager:
    """Manages hierarchical relationships between requirements."""

    def __init__(self, get_requirement_func, save_requirement_func):
        self.get_requirement = get_requirement_func
        self.save_requirement = save_requirement_func

    def validate_parent_child(self, child_type: str, parent_type: str) -> Tuple[bool, str]:
        """Validate if parent-child relationship is allowed."""
        rules = HIERARCHY_RULES.get(child_type, {})
        allowed_parents = rules.get("can_have_parent", [])

        if not allowed_parents:
            return True, "No parent restrictions"

        if parent_type not in allowed_parents:
            return False, f"{child_type} cannot have {parent_type} as parent. Allowed: {allowed_parents}"

        return True, "Valid relationship"

    def calculate_path(self, req_id: str, requirements_map: Dict) -> str:
        """Calculate the full hierarchy path for a requirement."""
        path_parts = []
        current_id = req_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            req = requirements_map.get(current_id)
            if not req:
                break
            path_parts.insert(0, current_id)
            parent_id = req.get('hierarchy', {}).get('parent_id')
            current_id = parent_id

        return " > ".join(path_parts)

    def get_root_epic(self, req_id: str, requirements_map: Dict) -> Optional[str]:
        """Find the root epic for a requirement."""
        current_id = req_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            req = requirements_map.get(current_id)
            if not req:
                break
            if req.get('type') == 'epic':
                return current_id
            parent_id = req.get('hierarchy', {}).get('parent_id')
            if not parent_id:
                break
            current_id = parent_id

        return None

    def calculate_rollup(self, req_id: str, requirements_map: Dict) -> Dict:
        """Calculate rollup metrics for a requirement."""
        req = requirements_map.get(req_id)
        if not req:
            return {}

        children_ids = req.get('hierarchy', {}).get('children_ids', [])

        metrics = {
            'total_children': len(children_ids),
            'total_descendants': 0,
            'completed_descendants': 0,
            'completion_percentage': 0.0,
            'total_effort': 0,
            'completed_effort': 0,
        }

        def count_descendants(rid: str):
            r = requirements_map.get(rid)
            if not r:
                return

            metrics['total_descendants'] += 1

            effort = r.get('planning', {}).get('estimated_effort', 0) or 0
            metrics['total_effort'] += effort

            status = r.get('status', '').lower()
            if status in ['implemented', 'done', 'completed']:
                metrics['completed_descendants'] += 1
                metrics['completed_effort'] += effort

            for cid in r.get('hierarchy', {}).get('children_ids', []):
                count_descendants(cid)

        for child_id in children_ids:
            count_descendants(child_id)

        if metrics['total_descendants'] > 0:
            metrics['completion_percentage'] = round(
                (metrics['completed_descendants'] / metrics['total_descendants']) * 100, 2
            )

        return metrics


class ConflictDetector:
    """Detects various types of conflicts between requirements."""

    def __init__(self):
        self.vague_terms = set(VAGUE_TERMS)
        self.contradiction_pairs = CONTRADICTION_PAIRS

    def detect_all_conflicts(self, req: Dict, all_requirements: List[Dict]) -> List[Dict]:
        """Run all conflict detection algorithms."""
        conflicts = []

        # Semantic conflicts
        for other_req in all_requirements:
            if other_req.get('id') == req.get('id'):
                continue

            semantic_conflicts = self.detect_semantic_conflicts(req, other_req)
            conflicts.extend(semantic_conflicts)

        # Logical conflicts (circular dependencies, missing refs)
        logical_conflicts = self.detect_logical_conflicts(req, all_requirements)
        conflicts.extend(logical_conflicts)

        # Constraint violations
        constraint_violations = self.detect_constraint_violations(req)
        conflicts.extend(constraint_violations)

        return conflicts

    def detect_semantic_conflicts(self, req1: Dict, req2: Dict) -> List[Dict]:
        """Detect semantic contradictions between two requirements."""
        conflicts = []

        text1 = self._get_text(req1).lower()
        text2 = self._get_text(req2).lower()

        # Check for contradiction pairs
        for word1, word2 in self.contradiction_pairs:
            # Check if opposite words appear in related context
            if self._has_contradiction_in_context(text1, text2, word1, word2):
                conflicts.append({
                    'type': 'semantic_contradiction',
                    'severity': 'high',
                    'req1_id': req1.get('id'),
                    'req2_id': req2.get('id'),
                    'details': f"Potential contradiction: '{word1}' vs '{word2}'",
                    'suggestion': f"Review {req1.get('id')} and {req2.get('id')} for conflicting statements"
                })
                break

        # Check for numeric constraint conflicts
        numeric_conflict = self._detect_numeric_conflict(text1, text2, req1, req2)
        if numeric_conflict:
            conflicts.append(numeric_conflict)

        return conflicts

    def _has_contradiction_in_context(self, text1: str, text2: str, word1: str, word2: str) -> bool:
        """Check if contradiction words appear in similar context."""
        # Simple check: both texts discuss similar topics and have opposite stances
        if word1 in text1 and word2 in text2:
            # Check for overlapping context words
            words1 = set(re.findall(r'\b\w+\b', text1))
            words2 = set(re.findall(r'\b\w+\b', text2))
            common_words = words1 & words2
            # Filter out common stop words
            stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'to', 'of', 'and', 'or', 'in', 'on', 'for', 'with'}
            meaningful_common = common_words - stop_words - {word1, word2}
            # If they share meaningful words, likely discussing same topic
            if len(meaningful_common) >= 3:
                return True
        return False

    def _detect_numeric_conflict(self, text1: str, text2: str, req1: Dict, req2: Dict) -> Optional[Dict]:
        """Detect conflicting numeric constraints."""
        pattern = r'([<>=]+)\s*(\d+(?:\.\d+)?)\s*(seconds?|ms|milliseconds?|minutes?|hours?|%|percent|users?|requests?)'

        constraints1 = re.findall(pattern, text1)
        constraints2 = re.findall(pattern, text2)

        for op1, val1, unit1 in constraints1:
            for op2, val2, unit2 in constraints2:
                # Normalize units
                unit1_norm = self._normalize_unit(unit1)
                unit2_norm = self._normalize_unit(unit2)

                if unit1_norm == unit2_norm:
                    val1_f, val2_f = float(val1), float(val2)

                    # Check for conflicts
                    if self._numeric_constraints_conflict(op1, val1_f, op2, val2_f):
                        return {
                            'type': 'numeric_conflict',
                            'severity': 'medium',
                            'req1_id': req1.get('id'),
                            'req2_id': req2.get('id'),
                            'details': f"Conflicting constraints: {op1}{val1}{unit1} vs {op2}{val2}{unit2}",
                            'suggestion': "Reconcile the numeric constraints or clarify which takes precedence"
                        }

        return None

    def _normalize_unit(self, unit: str) -> str:
        """Normalize time/metric units."""
        unit = unit.lower()
        if unit in ['second', 'seconds', 's']:
            return 'seconds'
        elif unit in ['millisecond', 'milliseconds', 'ms']:
            return 'milliseconds'
        elif unit in ['minute', 'minutes', 'm', 'min']:
            return 'minutes'
        elif unit in ['hour', 'hours', 'h', 'hr']:
            return 'hours'
        elif unit in ['%', 'percent']:
            return 'percent'
        return unit

    def _numeric_constraints_conflict(self, op1: str, val1: float, op2: str, val2: float) -> bool:
        """Check if two numeric constraints conflict."""
        # = vs = with different values
        if '=' in op1 and '=' in op2 and '<' not in op1 and '>' not in op1 and '<' not in op2 and '>' not in op2:
            return val1 != val2

        # < vs > creating impossible range
        if '<' in op1 and '>' in op2 and val1 <= val2:
            return True
        if '>' in op1 and '<' in op2 and val1 >= val2:
            return True

        return False

    def detect_logical_conflicts(self, req: Dict, all_requirements: List[Dict]) -> List[Dict]:
        """Detect logical conflicts like circular dependencies."""
        conflicts = []
        req_map = {r.get('id'): r for r in all_requirements}
        req_id = req.get('id')

        # Check for circular dependencies
        blocked_by = req.get('dependencies', {}).get('blocked_by', [])
        for dep_id in blocked_by:
            if self._has_circular_dependency(req_id, dep_id, req_map, set()):
                conflicts.append({
                    'type': 'circular_dependency',
                    'severity': 'critical',
                    'req_id': req_id,
                    'details': f"Circular dependency detected involving {dep_id}",
                    'suggestion': f"Break the cycle by removing dependency between {req_id} and {dep_id}"
                })

        # Check for missing dependencies
        for dep_id in blocked_by:
            if dep_id not in req_map:
                conflicts.append({
                    'type': 'missing_dependency',
                    'severity': 'high',
                    'req_id': req_id,
                    'details': f"References non-existent requirement: {dep_id}",
                    'suggestion': f"Create {dep_id} or remove the dependency"
                })

        # Check for missing parent
        parent_id = req.get('hierarchy', {}).get('parent_id')
        if parent_id and parent_id not in req_map:
            conflicts.append({
                'type': 'missing_parent',
                'severity': 'high',
                'req_id': req_id,
                'details': f"Parent requirement {parent_id} not found",
                'suggestion': f"Create {parent_id} or update parent reference"
            })

        return conflicts

    def _has_circular_dependency(self, start_id: str, current_id: str, req_map: Dict, visited: Set) -> bool:
        """Check for circular dependency using DFS."""
        if current_id == start_id:
            return True
        if current_id in visited:
            return False
        if current_id not in req_map:
            return False

        visited.add(current_id)
        current_req = req_map[current_id]

        for dep_id in current_req.get('dependencies', {}).get('blocked_by', []):
            if self._has_circular_dependency(start_id, dep_id, req_map, visited):
                return True

        return False

    def detect_constraint_violations(self, req: Dict) -> List[Dict]:
        """Check requirement against business rules."""
        violations = []

        # Rule: Security requirements must be high/critical priority
        area = req.get('area', '').lower()
        priority = req.get('priority', 'medium').lower()
        title = req.get('title', '').lower()

        security_keywords = ['security', 'authentication', 'authorization', 'encryption', 'auth', 'password', 'credential']
        is_security = any(kw in area or kw in title for kw in security_keywords)

        if is_security and priority not in ['high', 'critical']:
            violations.append({
                'type': 'constraint_violation',
                'severity': 'medium',
                'req_id': req.get('id'),
                'rule': 'Security requirements should be high/critical priority',
                'details': f"Security requirement has priority '{priority}'",
                'suggestion': "Raise priority to 'high' or 'critical'"
            })

        # Rule: Implemented requirements should have examples/tests
        status = req.get('status', '').lower()
        examples = req.get('examples', [])

        if status in ['implemented', 'done', 'completed'] and not examples:
            violations.append({
                'type': 'constraint_violation',
                'severity': 'low',
                'req_id': req.get('id'),
                'rule': 'Implemented requirements should have test scenarios',
                'details': 'No examples/scenarios defined for implemented requirement',
                'suggestion': 'Add Gherkin scenarios for test coverage'
            })

        return violations

    def _get_text(self, req: Dict) -> str:
        """Get searchable text from requirement."""
        parts = [
            req.get('title', ''),
            req.get('summary', ''),
            req.get('details', ''),
        ]
        return ' '.join(filter(None, parts))


class QualityScorer:
    """Scores requirements using SMART and INVEST frameworks."""

    def __init__(self):
        self.vague_terms = set(VAGUE_TERMS)

    def score_smart(self, req: Dict) -> Dict:
        """Score requirement using SMART criteria."""
        scores = {
            'specific': self._score_specific(req),
            'measurable': self._score_measurable(req),
            'achievable': self._score_achievable(req),
            'relevant': self._score_relevant(req),
            'time_bound': self._score_time_bound(req),
        }

        overall = sum(scores.values()) / len(scores)
        scores['overall'] = round(overall, 2)
        scores['grade'] = self._calculate_grade(overall)
        scores['issues'] = self._identify_smart_issues(req, scores)
        scores['suggestions'] = self._generate_smart_suggestions(scores)

        return scores

    def score_invest(self, req: Dict) -> Dict:
        """Score user story using INVEST criteria."""
        if req.get('type') not in ['user-story', 'story', 'functional']:
            return {'error': 'INVEST only applies to user stories', 'overall': 0}

        scores = {
            'independent': self._score_independent(req),
            'negotiable': self._score_negotiable(req),
            'valuable': self._score_valuable(req),
            'estimable': self._score_estimable(req),
            'small': self._score_small(req),
            'testable': self._score_testable(req),
        }

        overall = sum(scores.values()) / len(scores)
        scores['overall'] = round(overall, 2)
        scores['grade'] = self._calculate_grade(overall)
        scores['sprint_ready'] = overall >= 0.7 and scores['small'] >= 0.6 and scores['testable'] >= 0.6

        return scores

    def _score_specific(self, req: Dict) -> float:
        """Score how specific the requirement is."""
        text = self._get_text(req).lower()

        # Check for vague terms
        vague_count = sum(1 for term in self.vague_terms if term in text)
        vague_penalty = min(vague_count * 0.1, 0.5)

        # Check for concrete indicators
        concrete_patterns = [
            r'\d+',  # Numbers
            r'\b(user|admin|customer|manager|system)\b',  # Roles
            r'\b(click|submit|enter|select|view|create|update|delete)\b',  # Actions
            r'\b(email|password|username|id|token)\b',  # Specific fields
        ]
        concrete_count = sum(1 for p in concrete_patterns if re.search(p, text))
        concrete_bonus = min(concrete_count * 0.1, 0.3)

        score = 0.6 - vague_penalty + concrete_bonus
        return max(0.0, min(1.0, score))

    def _score_measurable(self, req: Dict) -> float:
        """Score if requirement has measurable criteria."""
        score = 0.0
        text = self._get_text(req)

        # Numeric criteria
        if re.search(r'[<>=]+\s*\d+', text):
            score += 0.4

        # Percentage or metrics
        if re.search(r'\d+\s*%|\d+\s*percent', text.lower()):
            score += 0.2

        # Examples/scenarios
        examples = req.get('examples', [])
        if len(examples) >= 2:
            score += 0.3
        elif len(examples) >= 1:
            score += 0.2

        # Acceptance criteria indicators
        details = req.get('details', '').lower()
        if any(term in details for term in ['must', 'shall', 'should', 'acceptance', 'criteria']):
            score += 0.1

        return min(1.0, score)

    def _score_achievable(self, req: Dict) -> float:
        """Score if requirement is achievable."""
        score = 0.8  # Default: assume achievable

        # Check effort
        effort = req.get('planning', {}).get('estimated_effort', 0) or 0
        req_type = req.get('type', 'user-story')

        if req_type in ['user-story', 'story']:
            if effort > 21:
                score -= 0.4
            elif effort > 13:
                score -= 0.2
        elif req_type == 'task':
            if effort > 8:
                score -= 0.3

        # Check dependencies
        deps = len(req.get('dependencies', {}).get('blocked_by', []))
        if deps > 5:
            score -= 0.3
        elif deps > 3:
            score -= 0.1

        return max(0.0, score)

    def _score_relevant(self, req: Dict) -> float:
        """Score if requirement is relevant to business goals."""
        score = 0.5

        # Has parent (linked to epic/feature)
        if req.get('hierarchy', {}).get('parent_id'):
            score += 0.25

        # Has business value
        if req.get('business_value') or req.get('planning', {}).get('business_value'):
            score += 0.15

        # Summary includes value statement
        summary = req.get('summary', '').lower()
        if 'so that' in summary or 'in order to' in summary or 'to enable' in summary:
            score += 0.1

        return min(1.0, score)

    def _score_time_bound(self, req: Dict) -> float:
        """Score if requirement has timeline."""
        planning = req.get('planning', {})

        if planning.get('target_date'):
            return 1.0
        elif planning.get('sprint'):
            return 0.9
        elif planning.get('target_release'):
            return 0.7
        elif planning.get('milestone'):
            return 0.5
        else:
            return 0.0

    def _score_independent(self, req: Dict) -> float:
        """Score story independence."""
        deps = req.get('dependencies', {}).get('blocked_by', [])

        if len(deps) == 0:
            return 1.0
        elif len(deps) == 1:
            return 0.8
        elif len(deps) == 2:
            return 0.6
        elif len(deps) <= 4:
            return 0.4
        else:
            return 0.2

    def _score_negotiable(self, req: Dict) -> float:
        """Score if details are negotiable (not too prescriptive)."""
        details = req.get('details', '').lower()

        prescriptive_terms = [
            'must use', 'shall use', 'use react', 'use angular', 'use vue',
            'database table', 'column name', 'api endpoint', 'class name',
            'function name', 'variable name', 'implementation'
        ]

        prescriptive_count = sum(1 for term in prescriptive_terms if term in details)

        if prescriptive_count == 0:
            return 1.0
        elif prescriptive_count <= 2:
            return 0.7
        else:
            return 0.4

    def _score_valuable(self, req: Dict) -> float:
        """Score if story delivers clear value."""
        score = 0.0
        summary = req.get('summary', '').lower()

        # Has "so that" clause
        if 'so that' in summary:
            score += 0.4
        elif 'in order to' in summary or 'to be able' in summary:
            score += 0.3

        # Has business value score
        if req.get('business_value') or req.get('planning', {}).get('business_value'):
            score += 0.3

        # Linked to epic
        if req.get('hierarchy', {}).get('epic_id'):
            score += 0.3

        return min(1.0, score)

    def _score_estimable(self, req: Dict) -> float:
        """Score if story can be estimated."""
        effort = req.get('planning', {}).get('estimated_effort')

        if effort is None or effort == 0:
            return 0.2
        elif 1 <= effort <= 13:
            return 1.0
        elif effort <= 21:
            return 0.7
        else:
            return 0.3

    def _score_small(self, req: Dict) -> float:
        """Score if story is small enough for one sprint."""
        effort = req.get('planning', {}).get('estimated_effort', 0) or 0

        if effort == 0:
            return 0.5  # Unknown
        elif effort <= 5:
            return 1.0
        elif effort <= 8:
            return 0.8
        elif effort <= 13:
            return 0.6
        elif effort <= 21:
            return 0.3
        else:
            return 0.1

    def _score_testable(self, req: Dict) -> float:
        """Score if story has testable acceptance criteria."""
        score = 0.0

        examples = req.get('examples', [])
        if len(examples) >= 3:
            score += 0.6
        elif len(examples) >= 1:
            score += 0.4

        details_length = len(req.get('details', ''))
        if details_length > 200:
            score += 0.3
        elif details_length > 100:
            score += 0.2

        details = req.get('details', '').lower()
        if 'given' in details and 'when' in details and 'then' in details:
            score += 0.1

        return min(1.0, score)

    def _calculate_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 0.95: return "A+"
        elif score >= 0.90: return "A"
        elif score >= 0.85: return "A-"
        elif score >= 0.80: return "B+"
        elif score >= 0.75: return "B"
        elif score >= 0.70: return "B-"
        elif score >= 0.65: return "C+"
        elif score >= 0.60: return "C"
        elif score >= 0.50: return "D"
        else: return "F"

    def _identify_smart_issues(self, req: Dict, scores: Dict) -> List[Dict]:
        """Identify quality issues based on scores."""
        issues = []

        if scores['specific'] < 0.6:
            issues.append({
                'criterion': 'Specific',
                'score': scores['specific'],
                'problem': 'Uses vague or subjective terms'
            })

        if scores['measurable'] < 0.6:
            issues.append({
                'criterion': 'Measurable',
                'score': scores['measurable'],
                'problem': 'No clear success criteria or quantifiable metrics'
            })

        if scores['achievable'] < 0.6:
            issues.append({
                'criterion': 'Achievable',
                'score': scores['achievable'],
                'problem': 'Scope may be too large or dependencies too complex'
            })

        if scores['time_bound'] < 0.4:
            issues.append({
                'criterion': 'Time-bound',
                'score': scores['time_bound'],
                'problem': 'No target date, release, or sprint assigned'
            })

        return issues

    def _generate_smart_suggestions(self, scores: Dict) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        if scores['specific'] < 0.7:
            suggestions.append("Replace vague terms (fast, easy, good) with concrete details")

        if scores['measurable'] < 0.7:
            suggestions.append("Add numeric targets (e.g., '< 2 seconds', '99.9% uptime')")
            suggestions.append("Add Gherkin scenarios with concrete examples")

        if scores['time_bound'] < 0.6:
            suggestions.append("Assign to a sprint or set a target release")

        if scores['achievable'] < 0.6:
            suggestions.append("Consider breaking down into smaller requirements")

        return suggestions

    def _get_text(self, req: Dict) -> str:
        """Get searchable text from requirement."""
        parts = [req.get('title', ''), req.get('summary', ''), req.get('details', '')]
        return ' '.join(filter(None, parts))


class CompletenessValidator:
    """Validates requirement completeness."""

    REQUIRED_FIELDS = {
        "epic": ["title", "summary", "area", "priority"],
        "feature": ["title", "summary", "area", "priority"],
        "user-story": ["title", "summary", "area", "priority"],
        "task": ["title", "summary", "area"],
        "constraint": ["title", "summary"],
        "nfr": ["title", "summary", "area"],
        "bug": ["title", "summary", "area"],
    }

    RECOMMENDED_FIELDS = {
        "epic": ["planning.target_release", "stakeholders.owner"],
        "feature": ["planning.estimated_effort", "hierarchy.parent_id"],
        "user-story": ["examples", "details", "planning.estimated_effort"],
        "task": ["planning.estimated_effort", "hierarchy.parent_id"],
        "nfr": ["details"],
    }

    def validate(self, req: Dict) -> Dict:
        """Validate requirement completeness."""
        req_type = req.get('type', 'user-story')

        required = self.REQUIRED_FIELDS.get(req_type, self.REQUIRED_FIELDS['user-story'])
        recommended = self.RECOMMENDED_FIELDS.get(req_type, [])

        missing_required = []
        missing_recommended = []

        for field in required:
            if not self._has_field(req, field):
                missing_required.append(field)

        for field in recommended:
            if not self._has_field(req, field):
                missing_recommended.append(field)

        total_fields = len(required) + len(recommended)
        present_fields = total_fields - len(missing_required) - len(missing_recommended)
        score = present_fields / total_fields if total_fields > 0 else 1.0

        return {
            'complete': len(missing_required) == 0,
            'score': round(score, 2),
            'missing_required': missing_required,
            'missing_recommended': missing_recommended,
            'required_complete': len(missing_required) == 0,
            'recommended_complete': len(missing_recommended) == 0,
        }

    def _has_field(self, req: Dict, field_path: str) -> bool:
        """Check if nested field exists and has value."""
        parts = field_path.split('.')
        current = req

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
                if current is None or current == "" or current == []:
                    return False
            else:
                return False

        return True


# =============================================================================
# MAIN TOOLS CLASS
# =============================================================================

class Tools:
    class Valves(BaseModel):
        requirements_base_path: str = Field(
            default="backend/data/requirements",
            description="Base path for requirements storage"
        )
        auto_index: bool = Field(default=True, description="Auto-rebuild index after storing")
        default_status: str = Field(default="proposed", description="Default status for new requirements")
        enable_gherkin: bool = Field(default=True, description="Enable Gherkin scenario support")
        enable_quality_scoring: bool = Field(default=True, description="Enable SMART/INVEST scoring")
        enable_conflict_detection: bool = Field(default=True, description="Enable conflict detection")
        min_quality_score: float = Field(default=0.5, description="Minimum quality score to pass validation")

    def __init__(self):
        self.valves = self.Valves()
        self._ensure_requirements_structure()
        self.conflict_detector = ConflictDetector()
        self.quality_scorer = QualityScorer()
        self.completeness_validator = CompletenessValidator()

    # =========================================================================
    # PATH AND STRUCTURE MANAGEMENT
    # =========================================================================

    def _get_base_path(self) -> Path:
        """Get the absolute base path for requirements storage."""
        base = self.valves.requirements_base_path
        if not os.path.isabs(base):
            cwd = Path.cwd()
            if (cwd / "backend").exists():
                base_path = cwd / base
            elif (cwd.parent / "backend").exists():
                base_path = cwd.parent / base
            else:
                base_path = Path(base)
        else:
            base_path = Path(base)
        return base_path

    def _ensure_requirements_structure(self):
        """Ensure the requirements folder structure exists."""
        base_path = self._get_base_path()
        folders = [
            base_path,
            base_path / "backlog",
            base_path / "decided",
            base_path / "implemented",
            base_path / "deprecated",
        ]
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)

        index_file = base_path / "index.json"
        if not index_file.exists():
            self._write_index({
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "requirements": [],
                "hierarchy": {}
            })

    def _read_index(self) -> Dict[str, Any]:
        """Read the requirements index."""
        index_file = self._get_base_path() / "index.json"
        try:
            with open(index_file, 'r') as f:
                return json.load(f)
        except:
            return {"last_updated": datetime.utcnow().isoformat() + "Z", "requirements": [], "hierarchy": {}}

    def _write_index(self, index_data: Dict[str, Any]):
        """Write the requirements index."""
        index_file = self._get_base_path() / "index.json"
        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=2)

    def _status_to_folder(self, status: str) -> str:
        """Map status to folder name."""
        status_lower = status.lower()
        if status_lower in ['proposed', 'draft', 'pending', 'in-review']:
            return 'backlog'
        elif status_lower in ['accepted', 'approved', 'decided', 'in-progress']:
            return 'decided'
        elif status_lower in ['implemented', 'done', 'completed']:
            return 'implemented'
        elif status_lower in ['deprecated', 'rejected', 'obsolete']:
            return 'deprecated'
        return 'backlog'

    def _get_prefix_for_type(self, req_type: str) -> str:
        """Get ID prefix for requirement type."""
        return REQUIREMENT_TYPES.get(req_type, {}).get('prefix', 'REQ')

    def _generate_next_id(self, req_type: str = "user-story") -> str:
        """Generate the next available requirement ID."""
        index = self._read_index()
        prefix = self._get_prefix_for_type(req_type)

        existing_ids = [r['id'] for r in index['requirements'] if r['id'].startswith(prefix)]

        if not existing_ids:
            return f"{prefix}-001"

        numbers = []
        for req_id in existing_ids:
            match = re.search(r'-(\d+)$', req_id)
            if match:
                numbers.append(int(match.group(1)))

        next_num = max(numbers) + 1 if numbers else 1
        return f"{prefix}-{next_num:03d}"

    def _parse_requirement_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a requirement markdown file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            parts = content.split('---\n', 2)
            if len(parts) < 3:
                return None

            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()

            return {
                'frontmatter': frontmatter,
                'body': body,
                'file_path': str(file_path)
            }
        except Exception as e:
            return None

    def _get_all_requirements(self) -> List[Dict]:
        """Get all requirements as parsed objects."""
        base_path = self._get_base_path()
        requirements = []

        for subfolder in ['backlog', 'decided', 'implemented', 'deprecated']:
            folder_path = base_path / subfolder
            if not folder_path.exists():
                continue

            for md_file in folder_path.glob("*.md"):
                if md_file.name == "README.md":
                    continue
                parsed = self._parse_requirement_file(md_file)
                if parsed:
                    req = parsed['frontmatter'].copy()
                    req['_body'] = parsed['body']
                    req['_file'] = str(md_file.relative_to(base_path))
                    requirements.append(req)

        return requirements

    def _save_requirement_file(self, req: Dict, body: str = None) -> str:
        """Save requirement to file."""
        base_path = self._get_base_path()
        folder = self._status_to_folder(req.get('status', 'proposed'))

        title_slug = slugify(req.get('title', 'untitled'))[:50]
        filename = f"{req['id']}-{title_slug}.md"

        # Build frontmatter (exclude internal fields)
        frontmatter = {k: v for k, v in req.items() if not k.startswith('_')}
        frontmatter['updated_at'] = datetime.utcnow().isoformat() + "Z"

        # Build body if not provided
        if body is None:
            body = self._build_body(req)

        yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
        content = f"---\n{yaml_str}---\n\n{body}"

        file_path = base_path / folder / filename
        with open(file_path, 'w') as f:
            f.write(content)

        return str(file_path.relative_to(base_path))

    def _build_body(self, req: Dict) -> str:
        """Build markdown body from requirement data."""
        parts = ["## Summary\n"]
        parts.append(req.get('summary', '_No summary provided._'))

        parts.append("\n\n## Details\n")
        parts.append(req.get('details', '_No additional details._'))

        examples = req.get('examples', [])
        if examples and self.valves.enable_gherkin:
            parts.append("\n\n## Examples (Spec-by-Example / BDD)\n")
            for i, ex in enumerate(examples):
                ex_id = ex.get('id', f"EX-{i+1:03d}")
                ex_desc = ex.get('description', 'Example scenario')
                ex_gherkin = ex.get('gherkin', '')

                parts.append(f"\n### {ex_id}: {ex_desc}\n")
                if ex_gherkin:
                    parts.append(f"\n```gherkin\n{ex_gherkin.strip()}\n```\n")
                else:
                    parts.append("\n_Gherkin scenario to be defined._\n")

        return ''.join(parts)

    # =========================================================================
    # CORE TOOLS
    # =========================================================================

    def requirements_store(
        self,
        title: str = Field(..., description="Requirement title"),
        summary: str = Field(..., description="Brief summary or user story"),
        req_id: Optional[str] = Field(None, description="Requirement ID (auto-generated if not provided)"),
        req_type: str = Field(default="user-story", description="Type: epic|feature|user-story|task|constraint|nfr|bug"),
        status: Optional[str] = Field(None, description="Status: proposed|accepted|implemented|deprecated"),
        priority: str = Field(default="medium", description="Priority: low|medium|high|critical"),
        area: str = Field(default="general", description="Area/domain"),
        details: str = Field(default="", description="Detailed description"),
        examples: Optional[str] = Field(None, description="JSON array of examples"),
        parent_id: Optional[str] = Field(None, description="Parent requirement ID for hierarchy"),
        dependencies: Optional[str] = Field(None, description="JSON object with blocked_by, blocks arrays"),
        planning: Optional[str] = Field(None, description="JSON object with estimated_effort, target_release, sprint"),
        stakeholders: Optional[str] = Field(None, description="JSON object with owner, requestor, reviewers"),
        __user__: Optional[dict] = None,
    ) -> str:
        """Create or update a requirement with hierarchy, dependencies, and metadata."""
        try:
            # Parse JSON inputs
            examples_list = json.loads(examples) if examples else []
            deps = json.loads(dependencies) if dependencies else {}
            plan = json.loads(planning) if planning else {}
            stake = json.loads(stakeholders) if stakeholders else {}

            # Generate or use provided ID
            if not req_id:
                req_id = self._generate_next_id(req_type)

            # Set default status
            if not status:
                status = self.valves.default_status

            now = datetime.utcnow().isoformat() + "Z"

            # Check if updating existing
            base_path = self._get_base_path()
            existing = None
            for subfolder in ['backlog', 'decided', 'implemented', 'deprecated']:
                for f in (base_path / subfolder).glob(f"{req_id}-*.md"):
                    existing = self._parse_requirement_file(f)
                    if existing:
                        # Remove old file if status changed
                        old_folder = f.parent.name
                        new_folder = self._status_to_folder(status)
                        if old_folder != new_folder:
                            f.unlink()
                    break
                if existing:
                    break

            # Build requirement object
            req = {
                'id': req_id,
                'title': title,
                'type': req_type,
                'status': status,
                'priority': priority,
                'area': area,
                'summary': summary,
                'details': details,
                'created_at': existing['frontmatter'].get('created_at', now) if existing else now,
                'updated_at': now,
            }

            # Add examples
            if examples_list:
                req['examples'] = [
                    {'id': ex.get('id', f"EX-{i+1:03d}"), 'description': ex.get('description', ''),
                     'gherkin': ex.get('gherkin', ''), 'status': ex.get('status', 'draft')}
                    for i, ex in enumerate(examples_list)
                ]

            # Add hierarchy
            hierarchy = {'level': REQUIREMENT_TYPES.get(req_type, {}).get('level', 3)}
            if parent_id:
                hierarchy['parent_id'] = parent_id
            if existing and existing['frontmatter'].get('hierarchy', {}).get('children_ids'):
                hierarchy['children_ids'] = existing['frontmatter']['hierarchy']['children_ids']
            req['hierarchy'] = hierarchy

            # Add dependencies
            if deps:
                req['dependencies'] = deps

            # Add planning
            if plan:
                req['planning'] = plan

            # Add stakeholders
            if stake:
                req['stakeholders'] = stake

            # Save file
            file_path = self._save_requirement_file(req)

            # Update parent's children list
            if parent_id:
                self._update_parent_children(parent_id, req_id)

            # Auto-index
            if self.valves.auto_index:
                self.requirements_index()

            # Run quality check if enabled
            quality_info = {}
            if self.valves.enable_quality_scoring:
                smart = self.quality_scorer.score_smart(req)
                quality_info = {
                    'quality_score': smart['overall'],
                    'quality_grade': smart['grade'],
                    'quality_issues': smart.get('issues', [])
                }

            result = {
                'status': 'success',
                'action': 'updated' if existing else 'created',
                'id': req_id,
                'type': req_type,
                'file_path': file_path,
                **quality_info
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    def _update_parent_children(self, parent_id: str, child_id: str):
        """Update parent requirement's children list."""
        base_path = self._get_base_path()

        for subfolder in ['backlog', 'decided', 'implemented', 'deprecated']:
            for f in (base_path / subfolder).glob(f"{parent_id}-*.md"):
                parsed = self._parse_requirement_file(f)
                if parsed:
                    fm = parsed['frontmatter']
                    if 'hierarchy' not in fm:
                        fm['hierarchy'] = {}
                    if 'children_ids' not in fm['hierarchy']:
                        fm['hierarchy']['children_ids'] = []
                    if child_id not in fm['hierarchy']['children_ids']:
                        fm['hierarchy']['children_ids'].append(child_id)
                    self._save_requirement_file(fm, parsed['body'])
                return

    def requirements_index(
        self,
        mode: str = Field(default="full", description="Index mode: 'full' or 'incremental'"),
    ) -> str:
        """Build or refresh the requirements index."""
        try:
            requirements = self._get_all_requirements()
            req_map = {r['id']: r for r in requirements}

            # Calculate hierarchy info
            hierarchy_manager = HierarchyManager(None, None)

            index_reqs = []
            for req in requirements:
                # Calculate path and rollup
                path = hierarchy_manager.calculate_path(req['id'], req_map)
                epic_id = hierarchy_manager.get_root_epic(req['id'], req_map)
                rollup = hierarchy_manager.calculate_rollup(req['id'], req_map)

                index_reqs.append({
                    'id': req.get('id', ''),
                    'title': req.get('title', ''),
                    'type': req.get('type', 'user-story'),
                    'status': req.get('status', ''),
                    'priority': req.get('priority', ''),
                    'area': req.get('area', ''),
                    'file': req.get('_file', ''),
                    'created_at': req.get('created_at', ''),
                    'updated_at': req.get('updated_at', ''),
                    'parent_id': req.get('hierarchy', {}).get('parent_id'),
                    'epic_id': epic_id,
                    'path': path,
                    'children_count': rollup.get('total_children', 0),
                    'completion_pct': rollup.get('completion_percentage', 0),
                })

            # Statistics
            stats = defaultdict(int)
            type_stats = defaultdict(int)
            for req in index_reqs:
                stats[req['status']] += 1
                type_stats[req['type']] += 1

            index_data = {
                'last_updated': datetime.utcnow().isoformat() + "Z",
                'requirements': sorted(index_reqs, key=lambda x: x['id']),
                'statistics': {
                    'total': len(index_reqs),
                    'by_status': dict(stats),
                    'by_type': dict(type_stats),
                }
            }

            self._write_index(index_data)

            return json.dumps({
                'status': 'success',
                'mode': mode,
                'requirement_count': len(index_reqs),
                'last_updated': index_data['last_updated'],
                'statistics': index_data['statistics']
            }, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    def requirements_overview(
        self,
        filter_status: Optional[str] = Field(None, description="Filter by status"),
        filter_area: Optional[str] = Field(None, description="Filter by area"),
        filter_type: Optional[str] = Field(None, description="Filter by type"),
        filter_priority: Optional[str] = Field(None, description="Filter by priority"),
        filter_parent: Optional[str] = Field(None, description="Filter by parent ID (show children)"),
        group_by: Optional[str] = Field(None, description="Group by: status|area|type|priority|parent_id"),
        format: str = Field(default="markdown", description="Output format: json|markdown"),
    ) -> str:
        """Generate filtered and grouped requirements overview."""
        try:
            index = self._read_index()
            reqs = index.get('requirements', [])

            # Apply filters
            if filter_status:
                reqs = [r for r in reqs if r['status'].lower() == filter_status.lower()]
            if filter_area:
                reqs = [r for r in reqs if r['area'].lower() == filter_area.lower()]
            if filter_type:
                reqs = [r for r in reqs if r['type'].lower() == filter_type.lower()]
            if filter_priority:
                reqs = [r for r in reqs if r['priority'].lower() == filter_priority.lower()]
            if filter_parent:
                reqs = [r for r in reqs if r.get('parent_id') == filter_parent]

            # Group if requested
            if group_by:
                grouped = defaultdict(list)
                for req in reqs:
                    key = req.get(group_by, 'unknown') or 'none'
                    grouped[key].append(req)

                if format == "markdown":
                    md = [f"# Requirements Overview\n\n**Total:** {len(reqs)} | **Grouped by:** {group_by}\n\n"]
                    for key in sorted(grouped.keys()):
                        items = grouped[key]
                        md.append(f"## {key.replace('-', ' ').title()} ({len(items)})\n\n")
                        md.append("| ID | Title | Type | Status | Priority |\n|---|---|---|---|---|\n")
                        for r in items:
                            md.append(f"| {r['id']} | {r['title'][:40]} | {r['type']} | {r['status']} | {r['priority']} |\n")
                        md.append("\n")
                    return ''.join(md)
                else:
                    return json.dumps({'total': len(reqs), 'grouped_by': group_by, 'groups': dict(grouped)}, indent=2)
            else:
                if format == "markdown":
                    md = [f"# Requirements Overview\n\n**Total:** {len(reqs)}\n\n"]
                    md.append("| ID | Title | Type | Status | Priority | Area |\n|---|---|---|---|---|---|\n")
                    for r in reqs:
                        md.append(f"| {r['id']} | {r['title'][:40]} | {r['type']} | {r['status']} | {r['priority']} | {r['area']} |\n")
                    return ''.join(md)
                else:
                    return json.dumps({'total': len(reqs), 'requirements': reqs}, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    def requirements_get(
        self,
        req_id: str = Field(..., description="Requirement ID to retrieve"),
        include_content: bool = Field(default=True, description="Include full content"),
        include_quality: bool = Field(default=True, description="Include quality scores"),
    ) -> str:
        """Retrieve a specific requirement with all details."""
        try:
            base_path = self._get_base_path()

            for subfolder in ['backlog', 'decided', 'implemented', 'deprecated']:
                for md_file in (base_path / subfolder).glob(f"{req_id}-*.md"):
                    parsed = self._parse_requirement_file(md_file)
                    if parsed and parsed['frontmatter'].get('id') == req_id:
                        result = {
                            'status': 'success',
                            'requirement': parsed['frontmatter'],
                            'file_path': str(md_file.relative_to(base_path))
                        }

                        if include_content:
                            result['content'] = parsed['body']

                        if include_quality and self.valves.enable_quality_scoring:
                            smart = self.quality_scorer.score_smart(parsed['frontmatter'])
                            invest = self.quality_scorer.score_invest(parsed['frontmatter'])
                            completeness = self.completeness_validator.validate(parsed['frontmatter'])

                            result['quality'] = {
                                'smart': smart,
                                'invest': invest if 'error' not in invest else None,
                                'completeness': completeness
                            }

                        return json.dumps(result, indent=2)

            return json.dumps({'status': 'not_found', 'error': f"Requirement {req_id} not found"}, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    def requirements_search(
        self,
        query: str = Field(..., description="Search query"),
        search_area: Optional[str] = Field(None, description="Limit search to area"),
        search_type: Optional[str] = Field(None, description="Limit search to type"),
        max_results: int = Field(default=20, description="Max results"),
    ) -> str:
        """Search requirements by keyword."""
        try:
            requirements = self._get_all_requirements()
            query_lower = query.lower()
            matches = []

            for req in requirements:
                if search_area and req.get('area', '').lower() != search_area.lower():
                    continue
                if search_type and req.get('type', '').lower() != search_type.lower():
                    continue

                # Calculate relevance score
                score = 0
                title = req.get('title', '').lower()
                body = req.get('_body', '').lower()
                summary = req.get('summary', '').lower()

                if query_lower in title:
                    score += 10
                if query_lower in req.get('area', '').lower():
                    score += 5
                if query_lower in summary:
                    score += 3
                if query_lower in body:
                    score += body.count(query_lower)

                if score > 0:
                    matches.append({
                        'score': score,
                        'id': req.get('id'),
                        'title': req.get('title'),
                        'type': req.get('type'),
                        'status': req.get('status'),
                        'area': req.get('area'),
                        'priority': req.get('priority'),
                        'file': req.get('_file')
                    })

            matches.sort(key=lambda x: x['score'], reverse=True)
            matches = matches[:max_results]

            return json.dumps({
                'status': 'success',
                'query': query,
                'total_matches': len(matches),
                'matches': matches
            }, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    # =========================================================================
    # HIERARCHY TOOLS
    # =========================================================================

    def requirements_hierarchy(
        self,
        root_id: Optional[str] = Field(None, description="Start from this requirement (None = all epics)"),
        view: str = Field(default="tree", description="View type: tree|list|json"),
        max_depth: int = Field(default=10, description="Maximum depth"),
        include_metrics: bool = Field(default=True, description="Include rollup metrics"),
    ) -> str:
        """Display requirement hierarchy."""
        try:
            requirements = self._get_all_requirements()
            req_map = {r['id']: r for r in requirements}
            hierarchy_manager = HierarchyManager(None, None)

            def build_tree(req_id: str, depth: int = 0) -> Dict:
                if depth > max_depth:
                    return None

                req = req_map.get(req_id)
                if not req:
                    return None

                node = {
                    'id': req['id'],
                    'title': req.get('title', ''),
                    'type': req.get('type', ''),
                    'status': req.get('status', ''),
                    'priority': req.get('priority', ''),
                }

                if include_metrics:
                    rollup = hierarchy_manager.calculate_rollup(req_id, req_map)
                    node['metrics'] = rollup

                children_ids = req.get('hierarchy', {}).get('children_ids', [])
                if children_ids:
                    node['children'] = [build_tree(cid, depth + 1) for cid in children_ids]
                    node['children'] = [c for c in node['children'] if c]

                return node

            if root_id:
                tree = build_tree(root_id)
                trees = [tree] if tree else []
            else:
                # Find all root requirements (epics or items without parents)
                roots = [r for r in requirements
                         if r.get('type') == 'epic' or not r.get('hierarchy', {}).get('parent_id')]
                trees = [build_tree(r['id']) for r in roots]
                trees = [t for t in trees if t]

            if view == "json":
                return json.dumps({'status': 'success', 'hierarchy': trees}, indent=2)
            elif view == "list":
                lines = []
                def flatten(node, indent=0):
                    if not node:
                        return
                    prefix = "  " * indent
                    status_icon = "✓" if node.get('status') in ['implemented', 'done'] else "○"
                    lines.append(f"{prefix}{status_icon} {node['id']}: {node['title'][:50]}")
                    for child in node.get('children', []):
                        flatten(child, indent + 1)

                for tree in trees:
                    flatten(tree)

                return '\n'.join(lines) if lines else "No requirements found"
            else:  # tree
                lines = []
                def format_tree(node, prefix="", is_last=True):
                    if not node:
                        return

                    connector = "└── " if is_last else "├── "
                    status_icon = {"implemented": "✓", "accepted": "◉", "proposed": "○"}.get(node.get('status'), "○")

                    metrics_str = ""
                    if include_metrics and node.get('metrics'):
                        m = node['metrics']
                        if m.get('total_descendants', 0) > 0:
                            metrics_str = f" [{m['completion_percentage']}% complete, {m['total_effort']} pts]"

                    lines.append(f"{prefix}{connector}{status_icon} {node['id']}: {node['title'][:40]}{metrics_str}")

                    children = node.get('children', [])
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    for i, child in enumerate(children):
                        format_tree(child, new_prefix, i == len(children) - 1)

                for i, tree in enumerate(trees):
                    if i > 0:
                        lines.append("")
                    format_tree(tree, "", True)

                return '\n'.join(lines) if lines else "No requirements found"

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    def requirements_move(
        self,
        req_id: str = Field(..., description="Requirement ID to move"),
        new_parent_id: Optional[str] = Field(None, description="New parent ID (None = make root)"),
    ) -> str:
        """Move a requirement to a new parent in the hierarchy."""
        try:
            requirements = self._get_all_requirements()
            req_map = {r['id']: r for r in requirements}

            req = req_map.get(req_id)
            if not req:
                return json.dumps({'status': 'error', 'error': f"Requirement {req_id} not found"}, indent=2)

            old_parent_id = req.get('hierarchy', {}).get('parent_id')

            # Validate new parent
            if new_parent_id:
                new_parent = req_map.get(new_parent_id)
                if not new_parent:
                    return json.dumps({'status': 'error', 'error': f"Parent {new_parent_id} not found"}, indent=2)

                # Check hierarchy rules
                hierarchy_manager = HierarchyManager(None, None)
                valid, msg = hierarchy_manager.validate_parent_child(req.get('type'), new_parent.get('type'))
                if not valid:
                    return json.dumps({'status': 'error', 'error': msg}, indent=2)

            # Remove from old parent
            if old_parent_id and old_parent_id in req_map:
                old_parent = req_map[old_parent_id]
                children = old_parent.get('hierarchy', {}).get('children_ids', [])
                if req_id in children:
                    children.remove(req_id)
                    old_parent['hierarchy']['children_ids'] = children
                    self._save_requirement_file(old_parent, old_parent.get('_body', ''))

            # Update requirement's parent
            if 'hierarchy' not in req:
                req['hierarchy'] = {}
            req['hierarchy']['parent_id'] = new_parent_id
            self._save_requirement_file(req, req.get('_body', ''))

            # Add to new parent
            if new_parent_id:
                self._update_parent_children(new_parent_id, req_id)

            # Rebuild index
            if self.valves.auto_index:
                self.requirements_index()

            return json.dumps({
                'status': 'success',
                'message': f"Moved {req_id} from {old_parent_id or 'root'} to {new_parent_id or 'root'}"
            }, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    # =========================================================================
    # CONFLICT DETECTION TOOLS
    # =========================================================================

    def requirements_validate(
        self,
        req_id: Optional[str] = Field(None, description="Specific requirement to validate (None = all)"),
        validation_level: str = Field(default="standard", description="Level: quick|standard|full"),
        include_quality: bool = Field(default=True, description="Include quality scoring"),
    ) -> str:
        """Validate requirement(s) for conflicts and quality issues."""
        try:
            requirements = self._get_all_requirements()

            if req_id:
                req = next((r for r in requirements if r['id'] == req_id), None)
                if not req:
                    return json.dumps({'status': 'not_found', 'error': f"Requirement {req_id} not found"}, indent=2)
                targets = [req]
            else:
                targets = requirements

            results = []

            for req in targets:
                validation = {
                    'id': req['id'],
                    'title': req.get('title', ''),
                    'conflicts': [],
                    'quality': {},
                    'completeness': {},
                    'valid': True,
                }

                # Conflict detection
                if self.valves.enable_conflict_detection and validation_level in ['standard', 'full']:
                    conflicts = self.conflict_detector.detect_all_conflicts(req, requirements)
                    validation['conflicts'] = conflicts
                    if any(c.get('severity') == 'critical' for c in conflicts):
                        validation['valid'] = False

                # Quality scoring
                if include_quality and self.valves.enable_quality_scoring:
                    smart = self.quality_scorer.score_smart(req)
                    validation['quality']['smart'] = smart

                    if req.get('type') in ['user-story', 'story', 'functional']:
                        invest = self.quality_scorer.score_invest(req)
                        validation['quality']['invest'] = invest

                    if smart['overall'] < self.valves.min_quality_score:
                        validation['valid'] = False
                        validation['quality']['below_threshold'] = True

                # Completeness
                completeness = self.completeness_validator.validate(req)
                validation['completeness'] = completeness
                if not completeness['required_complete']:
                    validation['valid'] = False

                results.append(validation)

            # Summary
            valid_count = sum(1 for r in results if r['valid'])

            return json.dumps({
                'status': 'success',
                'validation_level': validation_level,
                'total_validated': len(results),
                'valid_count': valid_count,
                'invalid_count': len(results) - valid_count,
                'results': results if len(results) <= 10 else results[:10],
                'truncated': len(results) > 10
            }, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    def requirements_conflicts(
        self,
        req_id: Optional[str] = Field(None, description="Check specific requirement (None = all)"),
        severity_filter: Optional[str] = Field(None, description="Filter by severity: critical|high|medium|low"),
    ) -> str:
        """Find conflicts for requirement(s)."""
        try:
            requirements = self._get_all_requirements()
            all_conflicts = []

            if req_id:
                req = next((r for r in requirements if r['id'] == req_id), None)
                if not req:
                    return json.dumps({'status': 'not_found', 'error': f"Requirement {req_id} not found"}, indent=2)
                targets = [req]
            else:
                targets = requirements

            for req in targets:
                conflicts = self.conflict_detector.detect_all_conflicts(req, requirements)
                for conflict in conflicts:
                    conflict['source_req'] = req['id']
                    if severity_filter and conflict.get('severity') != severity_filter:
                        continue
                    all_conflicts.append(conflict)

            # Deduplicate bilateral conflicts
            seen = set()
            unique_conflicts = []
            for c in all_conflicts:
                key = tuple(sorted([c.get('req1_id', c.get('req_id', '')), c.get('req2_id', c.get('source_req', ''))]))
                if key not in seen:
                    seen.add(key)
                    unique_conflicts.append(c)

            # Group by severity
            by_severity = defaultdict(list)
            for c in unique_conflicts:
                by_severity[c.get('severity', 'unknown')].append(c)

            return json.dumps({
                'status': 'success',
                'total_conflicts': len(unique_conflicts),
                'by_severity': {
                    'critical': len(by_severity.get('critical', [])),
                    'high': len(by_severity.get('high', [])),
                    'medium': len(by_severity.get('medium', [])),
                    'low': len(by_severity.get('low', [])),
                },
                'conflicts': unique_conflicts[:50],  # Limit output
                'truncated': len(unique_conflicts) > 50
            }, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    # =========================================================================
    # QUALITY TOOLS
    # =========================================================================

    def requirements_quality_report(
        self,
        scope: str = Field(default="all", description="Scope: all|area|type"),
        filter_value: Optional[str] = Field(None, description="Filter value for scope"),
        format: str = Field(default="markdown", description="Output format: json|markdown"),
    ) -> str:
        """Generate comprehensive quality report."""
        try:
            requirements = self._get_all_requirements()

            # Apply filter
            if scope == "area" and filter_value:
                requirements = [r for r in requirements if r.get('area', '').lower() == filter_value.lower()]
            elif scope == "type" and filter_value:
                requirements = [r for r in requirements if r.get('type', '').lower() == filter_value.lower()]

            if not requirements:
                return json.dumps({'status': 'success', 'message': 'No requirements found'}, indent=2)

            # Calculate scores
            smart_scores = []
            invest_scores = []
            completeness_scores = []
            grade_distribution = defaultdict(int)

            for req in requirements:
                smart = self.quality_scorer.score_smart(req)
                smart_scores.append(smart['overall'])
                grade_distribution[smart['grade']] += 1

                if req.get('type') in ['user-story', 'story', 'functional']:
                    invest = self.quality_scorer.score_invest(req)
                    if 'overall' in invest:
                        invest_scores.append(invest['overall'])

                completeness = self.completeness_validator.validate(req)
                completeness_scores.append(completeness['score'])

            avg_smart = sum(smart_scores) / len(smart_scores) if smart_scores else 0
            avg_invest = sum(invest_scores) / len(invest_scores) if invest_scores else 0
            avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0

            report = {
                'total_requirements': len(requirements),
                'avg_smart_score': round(avg_smart, 2),
                'avg_invest_score': round(avg_invest, 2),
                'avg_completeness': round(avg_completeness, 2),
                'overall_grade': self.quality_scorer._calculate_grade(avg_smart),
                'grade_distribution': dict(grade_distribution),
                'below_threshold': sum(1 for s in smart_scores if s < self.valves.min_quality_score),
                'recommendations': []
            }

            # Generate recommendations
            if avg_smart < 0.7:
                report['recommendations'].append("Many requirements need improvement - consider a quality review session")
            if avg_completeness < 0.8:
                report['recommendations'].append("Many requirements have missing fields - run completeness check")
            if report['below_threshold'] > len(requirements) * 0.2:
                report['recommendations'].append(f">{report['below_threshold']} requirements below quality threshold")

            if format == "markdown":
                md = [
                    "# Requirements Quality Report\n\n",
                    f"**Total Requirements:** {report['total_requirements']}\n",
                    f"**Overall Grade:** {report['overall_grade']}\n\n",
                    "## Scores\n\n",
                    f"| Metric | Score |\n|---|---|\n",
                    f"| SMART Average | {report['avg_smart_score']:.0%} |\n",
                    f"| INVEST Average | {report['avg_invest_score']:.0%} |\n",
                    f"| Completeness | {report['avg_completeness']:.0%} |\n\n",
                    "## Grade Distribution\n\n",
                    "| Grade | Count |\n|---|---|\n",
                ]
                for grade in ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'D', 'F']:
                    if grade in report['grade_distribution']:
                        md.append(f"| {grade} | {report['grade_distribution'][grade]} |\n")

                if report['recommendations']:
                    md.append("\n## Recommendations\n\n")
                    for rec in report['recommendations']:
                        md.append(f"- {rec}\n")

                return ''.join(md)
            else:
                return json.dumps({'status': 'success', 'report': report}, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    # =========================================================================
    # STAKEHOLDER & APPROVAL TOOLS
    # =========================================================================

    def requirements_approve(
        self,
        req_id: str = Field(..., description="Requirement ID to approve/reject"),
        reviewer: str = Field(..., description="Reviewer name"),
        decision: str = Field(..., description="Decision: approve|reject|request_changes"),
        comments: str = Field(default="", description="Review comments"),
        __user__: Optional[dict] = None,
    ) -> str:
        """Record approval decision for a requirement."""
        try:
            base_path = self._get_base_path()

            # Find requirement
            for subfolder in ['backlog', 'decided', 'implemented', 'deprecated']:
                for f in (base_path / subfolder).glob(f"{req_id}-*.md"):
                    parsed = self._parse_requirement_file(f)
                    if parsed and parsed['frontmatter'].get('id') == req_id:
                        req = parsed['frontmatter']
                        body = parsed['body']

                        # Initialize approval tracking
                        if 'approvals' not in req:
                            req['approvals'] = []

                        # Add approval record
                        approval_record = {
                            'reviewer': reviewer,
                            'decision': decision,
                            'comments': comments,
                            'timestamp': datetime.utcnow().isoformat() + "Z"
                        }
                        req['approvals'].append(approval_record)

                        # Update status based on decision
                        if decision == 'approve':
                            # Check if this meets approval threshold
                            approvals = [a for a in req['approvals'] if a['decision'] == 'approve']
                            if len(approvals) >= 1:  # Can configure threshold
                                if req.get('status') in ['proposed', 'draft', 'in-review']:
                                    req['status'] = 'accepted'
                        elif decision == 'reject':
                            req['status'] = 'deprecated'

                        # Save updated requirement
                        self._save_requirement_file(req, body)

                        # Rebuild index
                        if self.valves.auto_index:
                            self.requirements_index()

                        return json.dumps({
                            'status': 'success',
                            'id': req_id,
                            'decision': decision,
                            'new_status': req['status'],
                            'total_approvals': len([a for a in req['approvals'] if a['decision'] == 'approve'])
                        }, indent=2)

            return json.dumps({'status': 'not_found', 'error': f"Requirement {req_id} not found"}, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    def requirements_assign(
        self,
        req_id: str = Field(..., description="Requirement ID"),
        role: str = Field(..., description="Role: owner|requestor|reviewer|assignee"),
        name: str = Field(..., description="Person name"),
        email: str = Field(default="", description="Person email"),
    ) -> str:
        """Assign stakeholder to a requirement."""
        try:
            base_path = self._get_base_path()

            for subfolder in ['backlog', 'decided', 'implemented', 'deprecated']:
                for f in (base_path / subfolder).glob(f"{req_id}-*.md"):
                    parsed = self._parse_requirement_file(f)
                    if parsed and parsed['frontmatter'].get('id') == req_id:
                        req = parsed['frontmatter']
                        body = parsed['body']

                        if 'stakeholders' not in req:
                            req['stakeholders'] = {}

                        req['stakeholders'][role] = {
                            'name': name,
                            'email': email,
                            'assigned_at': datetime.utcnow().isoformat() + "Z"
                        }

                        self._save_requirement_file(req, body)

                        return json.dumps({
                            'status': 'success',
                            'id': req_id,
                            'role': role,
                            'assigned_to': name
                        }, indent=2)

            return json.dumps({'status': 'not_found', 'error': f"Requirement {req_id} not found"}, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    # =========================================================================
    # ADVANCED FEATURES
    # =========================================================================

    def requirements_prioritize(
        self,
        method: str = Field(default="moscow", description="Method: moscow|wsjf|value_effort"),
        filter_status: Optional[str] = Field(None, description="Filter by status"),
        format: str = Field(default="markdown", description="Output format: json|markdown"),
    ) -> str:
        """Prioritize requirements using various methods."""
        try:
            requirements = self._get_all_requirements()

            if filter_status:
                requirements = [r for r in requirements if r.get('status', '').lower() == filter_status.lower()]

            prioritized = []

            for req in requirements:
                planning = req.get('planning', {})

                item = {
                    'id': req['id'],
                    'title': req.get('title', ''),
                    'priority': req.get('priority', 'medium'),
                    'type': req.get('type', ''),
                    'status': req.get('status', ''),
                }

                if method == "moscow":
                    # MoSCoW: Must/Should/Could/Won't
                    priority_map = {'critical': 'Must', 'high': 'Should', 'medium': 'Could', 'low': 'Wont'}
                    item['moscow'] = priority_map.get(req.get('priority', 'medium'), 'Could')
                    item['sort_key'] = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(req.get('priority', 'medium'), 2)

                elif method == "wsjf":
                    # WSJF: (Business Value + Time Criticality + Risk Reduction) / Job Size
                    bv = planning.get('business_value', 5)
                    tc = planning.get('time_criticality', 5)
                    rr = planning.get('risk_reduction', 5)
                    js = planning.get('estimated_effort', 5) or 5

                    wsjf = (bv + tc + rr) / max(js, 1)
                    item['wsjf_score'] = round(wsjf, 2)
                    item['sort_key'] = -wsjf  # Higher is better

                elif method == "value_effort":
                    # Value vs Effort quadrant
                    value = planning.get('business_value', 5)
                    effort = planning.get('estimated_effort', 5) or 5

                    if value >= 7 and effort <= 5:
                        item['quadrant'] = 'Quick Win'
                        item['sort_key'] = 0
                    elif value >= 7 and effort > 5:
                        item['quadrant'] = 'Strategic'
                        item['sort_key'] = 1
                    elif value < 7 and effort <= 5:
                        item['quadrant'] = 'Fill-in'
                        item['sort_key'] = 2
                    else:
                        item['quadrant'] = 'Avoid'
                        item['sort_key'] = 3

                prioritized.append(item)

            # Sort
            prioritized.sort(key=lambda x: x.get('sort_key', 99))

            if format == "markdown":
                md = [f"# Requirements Prioritization ({method.upper()})\n\n"]

                if method == "moscow":
                    for category in ['Must', 'Should', 'Could', 'Wont']:
                        items = [p for p in prioritized if p.get('moscow') == category]
                        if items:
                            md.append(f"## {category} Have ({len(items)})\n\n")
                            for item in items:
                                md.append(f"- {item['id']}: {item['title']}\n")
                            md.append("\n")

                elif method == "wsjf":
                    md.append("| Rank | ID | Title | WSJF Score |\n|---|---|---|---|\n")
                    for i, item in enumerate(prioritized[:20], 1):
                        md.append(f"| {i} | {item['id']} | {item['title'][:40]} | {item.get('wsjf_score', 0)} |\n")

                elif method == "value_effort":
                    for quadrant in ['Quick Win', 'Strategic', 'Fill-in', 'Avoid']:
                        items = [p for p in prioritized if p.get('quadrant') == quadrant]
                        if items:
                            md.append(f"## {quadrant} ({len(items)})\n\n")
                            for item in items:
                                md.append(f"- {item['id']}: {item['title']}\n")
                            md.append("\n")

                return ''.join(md)
            else:
                return json.dumps({
                    'status': 'success',
                    'method': method,
                    'total': len(prioritized),
                    'prioritized': prioritized
                }, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

    def requirements_roadmap(
        self,
        group_by: str = Field(default="release", description="Group by: release|sprint|status"),
        format: str = Field(default="markdown", description="Output format: json|markdown"),
    ) -> str:
        """Generate requirements roadmap."""
        try:
            requirements = self._get_all_requirements()

            grouped = defaultdict(list)

            for req in requirements:
                planning = req.get('planning', {})

                if group_by == "release":
                    key = planning.get('target_release', 'Unassigned')
                elif group_by == "sprint":
                    key = planning.get('sprint', 'Backlog')
                else:  # status
                    key = req.get('status', 'unknown')

                grouped[key].append({
                    'id': req['id'],
                    'title': req.get('title', ''),
                    'type': req.get('type', ''),
                    'priority': req.get('priority', ''),
                    'status': req.get('status', ''),
                    'effort': planning.get('estimated_effort', 0),
                })

            if format == "markdown":
                md = [f"# Requirements Roadmap (by {group_by})\n\n"]

                for key in sorted(grouped.keys()):
                    items = grouped[key]
                    total_effort = sum(i.get('effort', 0) or 0 for i in items)
                    completed = sum(1 for i in items if i['status'] in ['implemented', 'done'])

                    md.append(f"## {key} ({len(items)} items, {total_effort} pts)\n\n")
                    md.append(f"Progress: {completed}/{len(items)} complete\n\n")
                    md.append("| ID | Title | Type | Status | Effort |\n|---|---|---|---|---|\n")

                    for item in items:
                        status_icon = "✓" if item['status'] in ['implemented', 'done'] else "○"
                        md.append(f"| {item['id']} | {item['title'][:35]} | {item['type']} | {status_icon} {item['status']} | {item['effort']} |\n")

                    md.append("\n")

                return ''.join(md)
            else:
                return json.dumps({
                    'status': 'success',
                    'group_by': group_by,
                    'roadmap': dict(grouped)
                }, indent=2)

        except Exception as e:
            return json.dumps({'status': 'error', 'error': str(e)}, indent=2)

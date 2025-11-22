"""
Unit tests for Requirements Toolkit v2.0
Run with: python -m pytest test_requirements_v2.py -v
"""

import pytest
import sys
sys.path.insert(0, '.')

from requirements_toolkit_v2 import (
    QualityScorer, CompletenessValidator, ConflictDetector,
    HierarchyManager, REQUIREMENT_TYPES, CONTRADICTION_PAIRS
)


class TestQualityScorer:
    """Tests for SMART/INVEST quality scoring."""

    def setup_method(self):
        self.scorer = QualityScorer()

    def test_smart_complete_requirement(self):
        """High-quality requirement should score well."""
        req = {
            'title': 'Password Reset via Email',
            'summary': 'As a user, I want to reset my password via email so that I can regain access.',
            'details': 'Response time must be < 2 seconds. Link expires after 1 hour.',
            'type': 'user-story',
            'priority': 'high',
            'examples': [{'title': 'Happy path', 'scenario': 'Given...When...Then...'}],
            'acceptance_criteria': ['User receives email within 2 minutes', 'Link works once'],
            'planning': {'target_release': 'v2.0', 'estimated_effort': 5}
        }
        result = self.scorer.score_smart(req)
        assert result['overall'] >= 0.5, f"Expected >= 0.5, got {result['overall']}"
        assert result['grade'] in ['A+', 'A', 'B', 'C'], f"Expected passing grade, got {result['grade']}"

    def test_smart_vague_requirement(self):
        """Vague requirement should score poorly on 'specific'."""
        req = {
            'title': 'Make it better',
            'summary': 'The system should be good and user-friendly',
            'type': 'user-story'
        }
        result = self.scorer.score_smart(req)
        assert result['specific'] < 0.5, "Vague terms should reduce specificity score"

    def test_measurable_numeric_patterns(self):
        """Should detect various numeric measurement patterns."""
        req = {
            'title': 'Performance Requirement',
            'summary': 'Response time within 2 seconds',
            'details': 'Must handle at least 1000 requests per second with 99% uptime'
        }
        result = self.scorer.score_smart(req)
        assert result['measurable'] >= 0.5, "Numeric patterns should increase measurability"

    def test_invest_user_story(self):
        """INVEST scoring for user stories."""
        req = {
            'title': 'Login Feature',
            'summary': 'As a user, I want to log in so that I can access my account.',
            'type': 'user-story',
            'acceptance_criteria': ['User can enter credentials', 'Shows error on failure', 'Redirects on success'],
            'planning': {'estimated_effort': 5}
        }
        result = self.scorer.score_invest(req)
        assert 'error' not in result, "Should process user story without error"
        assert result['valuable'] > 0, "'so that' clause should increase value score"
        assert result['testable'] > 0, "Acceptance criteria should increase testability"

    def test_invest_non_story(self):
        """INVEST should error for non-user-story types."""
        req = {'title': 'Epic', 'type': 'epic'}
        result = self.scorer.score_invest(req)
        assert 'error' in result, "Should return error for non-user-story"


class TestConflictDetector:
    """Tests for conflict detection."""

    def setup_method(self):
        self.detector = ConflictDetector()

    def test_semantic_contradiction_mandatory_optional(self):
        """Should detect mandatory vs optional contradiction."""
        req1 = {'id': 'REQ-001', 'title': 'Mandatory Email', 'summary': 'Email verification is mandatory'}
        req2 = {'id': 'REQ-002', 'title': 'Optional Email', 'summary': 'Email verification is optional'}
        conflicts = self.detector.detect_semantic_conflicts(req1, req2)
        assert len(conflicts) > 0, "Should detect mandatory/optional contradiction"
        assert any(c['type'] == 'semantic_contradiction' for c in conflicts)

    def test_constraint_security_priority(self):
        """Security requirements should require high priority."""
        req = {'id': 'REQ-001', 'title': 'Auth Security', 'area': 'security', 'priority': 'low'}
        violations = self.detector.detect_constraint_violations(req)
        assert len(violations) > 0, "Should flag low priority security requirement"

    def test_stakeholder_priority_disagreement(self):
        """Should detect stakeholder priority disagreement."""
        req = {
            'id': 'REQ-001',
            'stakeholder_ratings': [
                {'name': 'Product', 'priority': 'critical'},
                {'name': 'Engineering', 'priority': 'low'}
            ]
        }
        conflicts = self.detector.detect_stakeholder_conflicts(req)
        assert len(conflicts) > 0, "Should detect priority disagreement"
        assert conflicts[0]['type'] == 'priority_disagreement'

    def test_approval_conflict(self):
        """Should detect approval conflicts."""
        req = {
            'id': 'REQ-001',
            'stakeholders': {
                'approvers': [
                    {'name': 'Alice', 'status': 'approved'},
                    {'name': 'Bob', 'status': 'rejected'}
                ]
            }
        }
        conflicts = self.detector.detect_stakeholder_conflicts(req)
        assert len(conflicts) > 0, "Should detect approval conflict"
        assert conflicts[0]['type'] == 'approval_conflict'


class TestCompletenessValidator:
    """Tests for completeness validation."""

    def setup_method(self):
        self.validator = CompletenessValidator()

    def test_complete_requirement(self):
        """Fully complete requirement should pass."""
        req = {
            'id': 'REQ-001',
            'title': 'Test Requirement',
            'type': 'user-story',
            'priority': 'high',
            'summary': 'A complete summary',
            'status': 'proposed',
            'area': 'core'
        }
        result = self.validator.validate(req)
        assert result['complete'] is True, f"Should be complete, missing: {result['missing_required']}"

    def test_incomplete_requirement(self):
        """Missing required fields should fail."""
        req = {'id': 'REQ-001', 'title': 'Incomplete'}
        result = self.validator.validate(req)
        assert result['complete'] is False, "Should be incomplete"
        assert len(result['missing_required']) > 0, "Should list missing fields"


class TestHierarchyManager:
    """Tests for hierarchy management."""

    def setup_method(self):
        self.requirements = {
            'EPIC-001': {'id': 'EPIC-001', 'type': 'epic', 'hierarchy': {'children_ids': ['FEAT-001']}},
            'FEAT-001': {'id': 'FEAT-001', 'type': 'feature', 'hierarchy': {'parent_id': 'EPIC-001', 'children_ids': ['REQ-001']}},
            'REQ-001': {'id': 'REQ-001', 'type': 'user-story', 'hierarchy': {'parent_id': 'FEAT-001', 'children_ids': []}, 'status': 'implemented', 'planning': {'estimated_effort': 5}},
        }
        self.manager = HierarchyManager(lambda x: self.requirements.get(x), lambda x, y: None)

    def test_path_calculation(self):
        """Should calculate correct hierarchy path."""
        path = self.manager.calculate_path('REQ-001', self.requirements)
        assert 'EPIC-001' in path, "Path should include root epic"
        assert 'FEAT-001' in path, "Path should include parent feature"
        assert 'REQ-001' in path, "Path should include the requirement itself"

    def test_root_epic_finding(self):
        """Should find root epic correctly."""
        root = self.manager.get_root_epic('REQ-001', self.requirements)
        assert root == 'EPIC-001', f"Expected EPIC-001, got {root}"

    def test_parent_child_validation(self):
        """Should validate parent-child relationships."""
        valid, _ = self.manager.validate_parent_child('user-story', 'feature')
        assert valid is True, "user-story should be valid under feature"

        valid, _ = self.manager.validate_parent_child('feature', 'task')
        assert valid is False, "feature should not be valid under task"

    def test_rollup_metrics(self):
        """Should calculate rollup metrics correctly."""
        metrics = self.manager.calculate_rollup('FEAT-001', self.requirements)
        assert metrics['total_descendants'] == 1, "Should count 1 descendant"
        assert metrics['completed_descendants'] == 1, "Should count 1 completed"
        assert metrics['completion_percentage'] == 100.0, "Should be 100% complete"


class TestContradictionPairs:
    """Tests for contradiction pair detection."""

    def test_all_pairs_symmetric(self):
        """All contradiction pairs should work in both directions."""
        for word1, word2 in CONTRADICTION_PAIRS:
            assert word1 != word2, f"Pair should have different words: {word1}"


class TestRequirementTypes:
    """Tests for requirement type configuration."""

    def test_hierarchy_levels(self):
        """Hierarchy levels should be in order."""
        assert REQUIREMENT_TYPES['epic']['level'] < REQUIREMENT_TYPES['feature']['level']
        assert REQUIREMENT_TYPES['feature']['level'] < REQUIREMENT_TYPES['user-story']['level']
        assert REQUIREMENT_TYPES['user-story']['level'] < REQUIREMENT_TYPES['task']['level']

    def test_prefixes_unique(self):
        """Each type should have unique prefix."""
        prefixes = [t['prefix'] for t in REQUIREMENT_TYPES.values()]
        assert len(prefixes) == len(set(prefixes)), "Prefixes should be unique"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

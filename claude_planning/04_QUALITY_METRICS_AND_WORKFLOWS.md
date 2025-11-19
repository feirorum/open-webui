# Quality Metrics, Validation & Workflows - Detailed Design

**Date:** 2025-11-19
**Status:** Design Phase
**Priority:** HIGH
**Dependencies:** Conflict Detection, Hierarchy

---

## 1. Overview

### 1.1 Purpose

Build an **automated quality assessment system** that:
- Scores requirements using industry-standard frameworks (SMART, INVEST)
- Validates completeness and consistency
- Enforces approval workflows
- Tracks stakeholder sign-offs
- Provides actionable improvement suggestions

### 1.2 Quality Frameworks

| Framework | Applies To | Purpose |
|-----------|-----------|---------|
| **SMART** | All requirements | Ensure well-formed requirements |
| **INVEST** | User stories | Ensure good agile story quality |
| **Completeness** | All requirements | Check for required fields |
| **Consistency** | All requirements | Internal coherence check |

---

## 2. SMART Scoring

### 2.1 SMART Criteria

**S**pecific - **M**easurable - **A**chievable - **R**elevant - **T**ime-bound

```python
class SMARTScorer:
    """
    Score requirements against SMART criteria.
    """

    def score_requirement(self, req) -> dict:
        """
        Analyze requirement and return SMART scores.

        Returns:
        {
            "specific": 0.85,      # 0-1 score
            "measurable": 0.60,
            "achievable": 0.90,
            "relevant": 1.0,
            "time_bound": 0.40,
            "overall": 0.75,       # Average
            "grade": "B",          # A+ to F
            "issues": [...],       # List of problems
            "suggestions": [...]   # Improvement suggestions
        }
        """

        scores = {
            "specific": self._score_specific(req),
            "measurable": self._score_measurable(req),
            "achievable": self._score_achievable(req),
            "relevant": self._score_relevant(req),
            "time_bound": self._score_time_bound(req),
        }

        overall = sum(scores.values()) / len(scores)
        scores["overall"] = overall
        scores["grade"] = self._calculate_grade(overall)
        scores["issues"] = self._identify_issues(req, scores)
        scores["suggestions"] = self._generate_suggestions(req, scores)

        return scores

    def _score_specific(self, req) -> float:
        """
        Specific: Clear, unambiguous, concrete.

        Check for:
        - Vague words (good, fast, easy, user-friendly)
        - Concrete entities (specific users, features, actions)
        - Quantifiable details (numbers, thresholds)

        Scoring:
        1.0 - Very specific (no vague terms, concrete examples)
        0.7 - Mostly specific (minor vagueness)
        0.4 - Somewhat vague
        0.1 - Very vague
        """

        text = req['title'] + " " + req.get('summary', '') + " " + req.get('details', '')
        text_lower = text.lower()

        # Vague terms (penalties)
        vague_terms = [
            'good', 'bad', 'better', 'worse', 'fast', 'slow', 'easy', 'hard',
            'user-friendly', 'intuitive', 'nice', 'clean', 'modern', 'simple',
            'efficient', 'powerful', 'robust', 'scalable', 'flexible'
        ]

        vague_count = sum(1 for term in vague_terms if term in text_lower)

        # Concrete indicators (bonuses)
        concrete_indicators = [
            r'\d+',  # Numbers
            r'(user|admin|customer|manager)',  # Specific roles
            r'(email|password|username)',  # Specific fields
            r'(click|submit|enter|select)',  # Specific actions
        ]

        concrete_count = sum(1 for pattern in concrete_indicators
                             if re.search(pattern, text_lower))

        # Calculate score
        penalty = min(vague_count * 0.1, 0.6)  # Max 60% penalty
        bonus = min(concrete_count * 0.1, 0.3)  # Max 30% bonus

        score = 0.7 - penalty + bonus
        return max(0.0, min(1.0, score))

    def _score_measurable(self, req) -> float:
        """
        Measurable: Can verify when requirement is met.

        Check for:
        - Quantifiable metrics (< 2 seconds, > 99.9% uptime)
        - Acceptance criteria
        - Gherkin scenarios
        - Test cases

        Scoring:
        1.0 - Fully measurable (numeric targets + test scenarios)
        0.7 - Mostly measurable (some criteria)
        0.4 - Somewhat measurable (vague criteria)
        0.1 - Not measurable
        """

        score = 0.0

        # Check for numeric criteria
        numeric_pattern = r'([<>=]+\s*\d+(?:\.\d+)?|at least \d+|no more than \d+)'
        if re.search(numeric_pattern, req.get('details', '')):
            score += 0.4

        # Check for acceptance criteria
        if len(req.get('details', '')) > 100:  # Substantial details
            score += 0.2

        # Check for examples/scenarios
        if req.get('examples') and len(req['examples']) > 0:
            score += 0.4

        return min(1.0, score)

    def _score_achievable(self, req) -> float:
        """
        Achievable: Realistic scope, not too large.

        Check for:
        - Estimated effort (< 21 story points for story)
        - Dependencies (not too many)
        - Complexity indicators

        Scoring:
        1.0 - Clearly achievable (small scope, few deps)
        0.7 - Probably achievable (moderate scope)
        0.4 - Questionable (large scope or many deps)
        0.1 - Likely unachievable
        """

        score = 0.8  # Default: assume achievable

        # Check estimated effort
        effort = req.get('planning', {}).get('estimated_effort', 0)

        if req['type'] == 'user-story':
            if effort > 21:  # Too large for a single story
                score -= 0.3
            elif effort > 13:
                score -= 0.2
        elif req['type'] == 'task':
            if effort > 8:
                score -= 0.2

        # Check dependencies
        deps = len(req.get('dependencies', {}).get('blocked_by', []))
        if deps > 5:
            score -= 0.2
        elif deps > 3:
            score -= 0.1

        return max(0.0, score)

    def _score_relevant(self, req) -> float:
        """
        Relevant: Aligned with business goals, has clear value.

        Check for:
        - Business value specified
        - Link to epic/parent
        - Rationale/reason provided

        Scoring:
        1.0 - Highly relevant (clear business value, linked to epic)
        0.7 - Probably relevant
        0.4 - Unclear relevance
        """

        score = 0.5  # Default

        # Has parent (linked to epic/feature)
        if req.get('hierarchy', {}).get('parent_id'):
            score += 0.3

        # Has business value
        if 'business_value' in req or 'value' in req.get('planning', {}):
            score += 0.2

        # Summary includes "so that" (user value)
        if 'so that' in req.get('summary', '').lower():
            score += 0.2

        return min(1.0, score)

    def _score_time_bound(self, req) -> float:
        """
        Time-bound: Has target date or release.

        Check for:
        - Target release
        - Sprint assignment
        - Target date
        - Milestone

        Scoring:
        1.0 - Specific date/sprint
        0.7 - Release assigned
        0.4 - Vague timeline
        0.0 - No timeline
        """

        planning = req.get('planning', {})

        if planning.get('target_date'):
            return 1.0
        elif planning.get('sprint'):
            return 1.0
        elif planning.get('target_release'):
            return 0.7
        elif planning.get('milestone'):
            return 0.6
        else:
            return 0.0

    def _calculate_grade(self, overall_score):
        """Convert numeric score to letter grade."""
        if overall_score >= 0.95:
            return "A+"
        elif overall_score >= 0.90:
            return "A"
        elif overall_score >= 0.85:
            return "A-"
        elif overall_score >= 0.80:
            return "B+"
        elif overall_score >= 0.75:
            return "B"
        elif overall_score >= 0.70:
            return "B-"
        elif overall_score >= 0.65:
            return "C+"
        elif overall_score >= 0.60:
            return "C"
        elif overall_score >= 0.50:
            return "D"
        else:
            return "F"

    def _identify_issues(self, req, scores):
        """Identify specific quality issues."""
        issues = []

        if scores['specific'] < 0.6:
            issues.append({
                "criterion": "Specific",
                "severity": "medium",
                "problem": "Requirement uses vague or subjective terms",
                "example_vague_terms": self._find_vague_terms(req)
            })

        if scores['measurable'] < 0.6:
            issues.append({
                "criterion": "Measurable",
                "severity": "high",
                "problem": "No clear success criteria or quantifiable metrics"
            })

        if scores['achievable'] < 0.6:
            issues.append({
                "criterion": "Achievable",
                "severity": "medium",
                "problem": "Scope may be too large or dependencies too complex"
            })

        if scores['time_bound'] < 0.4:
            issues.append({
                "criterion": "Time-bound",
                "severity": "low",
                "problem": "No target date, release, or sprint assigned"
            })

        return issues

    def _generate_suggestions(self, req, scores):
        """Generate actionable improvement suggestions."""
        suggestions = []

        if scores['specific'] < 0.7:
            suggestions.append({
                "criterion": "Specific",
                "suggestion": "Replace vague terms with concrete details",
                "examples": [
                    "Instead of 'fast', specify '< 2 seconds response time'",
                    "Instead of 'user-friendly', describe specific UX requirements"
                ]
            })

        if scores['measurable'] < 0.7:
            suggestions.append({
                "criterion": "Measurable",
                "suggestion": "Add quantifiable acceptance criteria",
                "examples": [
                    "Add numeric targets (e.g., '99.9% uptime')",
                    "Add Gherkin scenarios with concrete examples",
                    "Specify pass/fail conditions"
                ]
            })

        if scores['time_bound'] < 0.6:
            suggestions.append({
                "criterion": "Time-bound",
                "suggestion": "Assign to a release or sprint",
                "action": "Set target_release or sprint in planning section"
            })

        return suggestions
```

---

## 3. INVEST Scoring

### 3.1 INVEST Criteria

**I**ndependent - **N**egotiable - **V**aluable - **E**stimable - **S**mall - **T**estable

```python
class INVESTScorer:
    """
    Score user stories against INVEST criteria.
    Only applies to type='user-story'.
    """

    def score_story(self, req) -> dict:
        """
        Score user story against INVEST criteria.

        Returns:
        {
            "independent": 0.80,
            "negotiable": 0.70,
            "valuable": 0.95,
            "estimable": 0.85,
            "small": 0.60,
            "testable": 1.0,
            "overall": 0.82,
            "grade": "B+",
            "ready_for_sprint": True
        }
        """

        if req['type'] not in ['user-story', 'story']:
            return {"error": "INVEST only applies to user stories"}

        scores = {
            "independent": self._score_independent(req),
            "negotiable": self._score_negotiable(req),
            "valuable": self._score_valuable(req),
            "estimable": self._score_estimable(req),
            "small": self._score_small(req),
            "testable": self._score_testable(req),
        }

        overall = sum(scores.values()) / len(scores)
        scores["overall"] = overall
        scores["grade"] = SMARTScorer._calculate_grade(None, overall)
        scores["ready_for_sprint"] = overall >= 0.75 and scores['small'] >= 0.6

        return scores

    def _score_independent(self, req) -> float:
        """
        Independent: Can be developed without waiting for other stories.

        Check:
        - Number of dependencies
        - Hard vs soft dependencies
        - Coupling with other requirements
        """

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

    def _score_negotiable(self, req) -> float:
        """
        Negotiable: Details can be discussed, not overly prescriptive.

        Check:
        - Avoids implementation details
        - Focuses on what, not how
        - Leaves room for technical decisions
        """

        details = req.get('details', '').lower()

        # Red flags: overly prescriptive terms
        prescriptive_terms = [
            'must use', 'shall use', 'use react', 'use angular',
            'database table', 'class name', 'variable', 'function name',
            'implementation detail'
        ]

        prescriptive_count = sum(1 for term in prescriptive_terms if term in details)

        if prescriptive_count == 0:
            return 1.0
        elif prescriptive_count <= 2:
            return 0.7
        else:
            return 0.4

    def _score_valuable(self, req) -> float:
        """
        Valuable: Delivers value to users or business.

        Check:
        - Includes "so that" clause (value statement)
        - Has business value score
        - Linked to business goal (epic)
        """

        score = 0.0

        # Has "so that" clause
        if 'so that' in req.get('summary', '').lower():
            score += 0.4

        # Has business value
        if 'business_value' in req or 'value' in req.get('planning', {}):
            score += 0.3

        # Linked to epic (business goal)
        if req.get('hierarchy', {}).get('epic_id'):
            score += 0.3

        return min(1.0, score)

    def _score_estimable(self, req) -> float:
        """
        Estimable: Team can estimate effort.

        Check:
        - Has estimated_effort
        - Effort is reasonable (not 0, not huge)
        - Details are clear enough to estimate
        """

        effort = req.get('planning', {}).get('estimated_effort')

        if effort is None or effort == 0:
            return 0.2  # Not estimated
        elif effort <= 13:
            return 1.0  # Well-estimated
        elif effort <= 21:
            return 0.7  # Large but estimable
        else:
            return 0.3  # Too large, probably needs decomposition

    def _score_small(self, req) -> float:
        """
        Small: Can fit in one sprint.

        Check:
        - Estimated effort (< 13 story points ideal, < 21 acceptable)
        - Number of acceptance criteria (< 10 ideal)
        - Number of child tasks (< 8 ideal)
        """

        effort = req.get('planning', {}).get('estimated_effort', 0)

        if effort == 0:
            return 0.5  # Unknown
        elif effort <= 5:
            return 1.0  # Very small
        elif effort <= 8:
            return 0.9  # Small
        elif effort <= 13:
            return 0.7  # Medium (acceptable)
        elif effort <= 21:
            return 0.4  # Large (consider splitting)
        else:
            return 0.1  # Too large

    def _score_testable(self, req) -> float:
        """
        Testable: Can write tests to verify completion.

        Check:
        - Has acceptance criteria
        - Has Gherkin scenarios
        - Has test references
        """

        score = 0.0

        # Has examples/scenarios
        examples = req.get('examples', [])
        if len(examples) >= 3:
            score += 0.6
        elif len(examples) >= 1:
            score += 0.4

        # Has detailed acceptance criteria
        details_length = len(req.get('details', ''))
        if details_length > 200:
            score += 0.3
        elif details_length > 100:
            score += 0.2

        # Has test references
        if req.get('test_ids') or 'test' in req.get('details', '').lower():
            score += 0.1

        return min(1.0, score)
```

---

## 4. Completeness Validation

```python
class CompletenessValidator:
    """
    Check that requirements have all required fields.
    """

    REQUIRED_FIELDS_BY_TYPE = {
        "epic": [
            "title", "summary", "area", "priority",
            "planning.target_release",
            "stakeholders.owner"
        ],

        "feature": [
            "title", "summary", "area", "priority",
            "hierarchy.parent_id",  # Must belong to epic
            "planning.estimated_effort"
        ],

        "user-story": [
            "title", "summary", "details", "area", "priority",
            "hierarchy.parent_id",  # Must belong to feature
            "examples",  # At least one scenario
            "planning.estimated_effort"
        ],

        "task": [
            "title", "summary", "area",
            "hierarchy.parent_id",  # Must belong to story
            "planning.estimated_effort",
            "stakeholders.assignee"
        ],

        "nfr": [
            "title", "summary", "area", "priority",
            "nfr_metric", "nfr_target", "nfr_measurement_method"
        ],

        "constraint": [
            "title", "summary", "constraint_type", "rationale"
        ]
    }

    def validate_completeness(self, req) -> dict:
        """
        Check if requirement has all required fields.

        Returns:
        {
            "complete": True/False,
            "completion_percentage": 0.85,
            "missing_fields": ["examples", "stakeholders.owner"],
            "optional_missing": ["test_ids"],
            "score": 0.85
        }
        """

        req_type = req.get('type', 'user-story')
        required_fields = self.REQUIRED_FIELDS_BY_TYPE.get(req_type, [])

        missing = []
        present = []

        for field_path in required_fields:
            if not self._has_field(req, field_path):
                missing.append(field_path)
            else:
                present.append(field_path)

        completion_pct = len(present) / len(required_fields) if required_fields else 1.0

        return {
            "complete": len(missing) == 0,
            "completion_percentage": completion_pct,
            "missing_fields": missing,
            "present_fields": present,
            "score": completion_pct
        }

    def _has_field(self, req, field_path):
        """Check if nested field exists (e.g., 'planning.target_release')."""
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
```

---

## 5. Approval Workflows

### 5.1 Multi-Stage Approval Process

```yaml
# Workflow configuration
workflow:
  stages:
    - stage: "draft"
      can_edit: ["author", "owner"]
      can_approve: []
      next_stages: ["peer-review"]

    - stage: "peer-review"
      can_edit: ["author", "owner"]
      can_approve: ["reviewer"]
      required_approvals: 1
      next_stages: ["stakeholder-review", "draft"]

    - stage: "stakeholder-review"
      can_edit: ["owner"]
      can_approve: ["stakeholder"]
      required_approvals: 2
      next_stages: ["approved", "peer-review"]

    - stage: "approved"
      can_edit: []  # No edits allowed
      can_approve: []
      next_stages: ["implementation"]

    - stage: "implementation"
      can_edit: []
      can_approve: ["implementer"]  # Can mark as complete
      next_stages: ["completed"]

    - stage: "completed"
      can_edit: []
      can_approve: []
      next_stages: []  # Final stage
```

### 5.2 Approval Tracking

```yaml
---
id: REQ-001
approval_workflow:
  current_stage: "stakeholder-review"
  stage_history:
    - stage: "draft"
      entered: "2025-11-18T10:00:00Z"
      exited: "2025-11-18T14:00:00Z"
      duration_hours: 4

    - stage: "peer-review"
      entered: "2025-11-18T14:00:00Z"
      exited: "2025-11-19T09:00:00Z"
      duration_hours: 19
      approvals:
        - reviewer: "Alice Tech Lead"
          decision: "approved"
          timestamp: "2025-11-19T09:00:00Z"
          comments: "Looks good, minor suggestions in comments"

    - stage: "stakeholder-review"
      entered: "2025-11-19T09:00:00Z"
      required_approvals: 2
      approvals:
        - stakeholder: "Bob Product Manager"
          decision: "approved"
          timestamp: "2025-11-19T11:00:00Z"
        - stakeholder: "Carol CEO"
          decision: "pending"
          notified: "2025-11-19T09:00:00Z"
---
```

### 5.3 New Tool: `requirements_approve`

```python
def requirements_approve(
    req_id: str,
    reviewer: str,
    decision: str,  # approved | rejected | request_changes
    comments: str = "",
    __user__: Optional[dict] = None,
) -> str:
    """
    Record approval/rejection for a requirement.

    Workflow:
    1. Validate reviewer has permission to approve at current stage
    2. Record approval decision
    3. Check if all required approvals are met
    4. If yes, advance to next stage
    5. Notify relevant stakeholders

    Returns:
        Success message with next steps
    """
    pass
```

---

## 6. Quality Dashboard

### 6.1 System-Wide Quality Report

```python
def requirements_quality_report(
    scope: str = "all",  # all | epic | release | area
    filter_value: Optional[str] = None,
) -> str:
    """
    Generate comprehensive quality report.

    Returns:
    - Overall quality score
    - SMART/INVEST distribution
    - Completeness statistics
    - Approval status breakdown
    - Top quality issues
    - Improvement recommendations
    """

    reqs = get_requirements(scope, filter_value)

    report = {
        "summary": {
            "total_requirements": len(reqs),
            "avg_smart_score": 0,
            "avg_invest_score": 0,
            "avg_completeness": 0,
            "approval_rate": 0,
        },

        "quality_distribution": {
            "grade_A": 0,  # >= 0.90
            "grade_B": 0,  # >= 0.75
            "grade_C": 0,  # >= 0.60
            "grade_D": 0,  # >= 0.50
            "grade_F": 0,  # < 0.50
        },

        "top_issues": [],  # Most common quality problems

        "recommendations": [],  # High-impact improvements
    }

    # Calculate metrics for each requirement
    for req in reqs:
        smart = SMARTScorer().score_requirement(req)
        report["summary"]["avg_smart_score"] += smart["overall"]

        if req['type'] == 'user-story':
            invest = INVESTScorer().score_story(req)
            report["summary"]["avg_invest_score"] += invest["overall"]

        completeness = CompletenessValidator().validate_completeness(req)
        report["summary"]["avg_completeness"] += completeness["score"]

    # Calculate averages
    report["summary"]["avg_smart_score"] /= len(reqs)
    report["summary"]["avg_invest_score"] /= len(reqs)
    report["summary"]["avg_completeness"] /= len(reqs)

    return format_quality_report(report)
```

---

## 7. Agent Integration

### 7.1 Proactive Quality Assistance

**Agent behavior when creating a requirement:**

```
User: "Users should be able to search for products."

Agent: [Internal quality check]
- Specific: 40% (vague: "able to search")
- Measurable: 20% (no success criteria)
- Testable: 10% (no examples)

Agent: "I've captured the core idea. Let me ask some questions to improve the quality:

1. SPECIFIC: What exactly should users be able to search?
   - Product name only?
   - Also description, tags, SKU?

2. MEASURABLE: How fast should search results appear?
   - < 2 seconds?
   - < 500ms?

3. TESTABLE: Can you provide an example scenario?
   - Given: User on homepage
   - When: User types 'laptop' in search
   - Then: Show relevant laptops within 2 seconds

Answering these will boost the quality score from D (41%) to B+ (85%)."
```

### 7.2 Quality Gate Enforcement

**Before allowing approval:**

```
User: "Approve REQ-023 and move to implementation."

Agent: [Runs validation]

Agent: "⚠️ Cannot approve REQ-023 yet. Quality gate failed:

SMART Score: 62% (C grade) - Minimum required: 75% (B grade)

Issues:
1. Measurable (40%): No quantifiable success criteria
   → Add specific metrics or acceptance criteria

2. Testable (50%): Only 1 scenario, minimum 2 required
   → Add at least one more Gherkin example

3. Completeness (71%): Missing required fields:
   - stakeholders.owner
   - planning.estimated_effort

Would you like me to help you improve these areas?"
```

---

## 8. Implementation Plan

### Week 1: Core Scoring
- ✅ Implement SMARTScorer
- ✅ Implement INVESTScorer
- ✅ Implement CompletenessValidator
- ✅ Add quality scores to requirement metadata

### Week 2: Workflows
- ✅ Design approval workflow configuration
- ✅ Implement requirements_approve tool
- ✅ Add approval tracking to frontmatter
- ✅ Build stage transition logic

### Week 3: Agent Integration
- ✅ Update agent prompts with quality guidance
- ✅ Add proactive quality suggestions
- ✅ Implement quality gate enforcement
- ✅ Build quality improvement dialog flows

### Week 4: Reporting
- ✅ Implement requirements_quality_report
- ✅ Build quality dashboard views
- ✅ Create improvement recommendation engine
- ✅ Testing and refinement

---

## 9. Success Metrics

**After implementation:**

- ✅ Average SMART score: > 75%
- ✅ Approval workflow adoption: > 80% of requirements
- ✅ Requirement completeness: > 90%
- ✅ User satisfaction with quality features: > 4/5
- ✅ Reduction in rework due to unclear requirements: > 30%

---

**Document Status:** ✅ Complete
**Next Document:** `05_IMPLEMENTATION_ROADMAP.md`

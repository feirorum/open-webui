# Requirement Hierarchy & Organization - Detailed Design

**Date:** 2025-11-19
**Status:** Design Phase
**Priority:** CRITICAL
**Dependencies:** None

---

## 1. Overview

### 1.1 Problem Statement

Current implementation treats all requirements as **flat, independent entities** (REQ-001, REQ-002, etc.). This doesn't reflect real-world software development where requirements exist in **hierarchical relationships**:

```
❌ Current (Flat):
REQ-001: User login
REQ-002: OAuth support
REQ-003: Password reset
REQ-004: User dashboard
REQ-005: Profile editing

😕 Hard to answer:
- Which requirements are part of the "User Management" feature?
- What's the parent epic for REQ-002?
- Can I implement REQ-004 without completing REQ-001?
```

### 1.2 Industry Standard

```
✅ Hierarchical (Industry Standard):

EPIC-001: User Management
  ├── FEAT-001: Authentication
  │   ├── REQ-001: Email/Password Login
  │   ├── REQ-002: OAuth Social Login
  │   └── REQ-003: Password Reset Flow
  └── FEAT-002: User Profile
      ├── REQ-004: Profile Dashboard
      └── REQ-005: Profile Editing

✅ Easy to answer:
- All "User Management" requirements: Query EPIC-001
- Parent of REQ-002: FEAT-001 (Authentication)
- Dependencies: REQ-004 requires REQ-001 (can't view dashboard without login)
```

### 1.3 Goals

- ✅ Support **4-level hierarchy**: Epic → Feature → Story → Task
- ✅ Maintain **parent-child relationships** in metadata
- ✅ Enable **hierarchical queries** (all children of EPIC-001)
- ✅ Calculate **rollup metrics** (effort, completion %)
- ✅ Visualize **requirement trees** (ASCII, Markdown, JSON)
- ✅ Preserve **backward compatibility** (existing flat requirements still work)

---

## 2. Hierarchy Model

### 2.1 Four-Level Hierarchy

| Level | ID Prefix | Description | Typical Scope | Example |
|-------|-----------|-------------|---------------|---------|
| **1. Epic** | `EPIC-` | Business objective, large initiative | 3-6 months | "User Management System" |
| **2. Feature** | `FEAT-` | Major functionality within epic | 1-2 months | "Authentication", "User Profiles" |
| **3. Story** | `REQ-` | User-facing capability | 1-2 weeks | "Login with email/password" |
| **4. Task** | `TASK-` | Implementation work item | 1-3 days | "Create login API endpoint" |

**Additional Types** (special cases):

| Type | ID Prefix | Description | Example |
|------|-----------|-------------|---------|
| **Constraint** | `CONS-` | System-wide constraint | "Must comply with GDPR" |
| **Non-Functional** | `NFR-` | Quality attribute | "Response time < 2s" |
| **Bug** | `BUG-` | Defect to fix | "Login fails on Safari" |

### 2.2 Relationship Rules

```
Epic (EPIC-xxx)
  └── Contains: Multiple Features
      └── Contains: Multiple Stories
          └── Contains: Multiple Tasks

Constraints (CONS-xxx)
  └── Applies to: Any level (Epic, Feature, Story, Task)

Non-Functional Reqs (NFR-xxx)
  └── Usually: Feature or Story level

Bugs (BUG-xxx)
  └── Reference: Story or Feature they relate to
```

### 2.3 Hierarchy Validation Rules

```python
HIERARCHY_RULES = {
    "epic": {
        "can_have_parent": False,  # Epics are top-level
        "can_have_children": ["feature", "constraint"],
        "max_children": None,  # Unlimited
        "required_fields": ["business_value", "strategic_goal"]
    },

    "feature": {
        "can_have_parent": ["epic"],
        "must_have_parent": True,  # Every feature must belong to an epic
        "can_have_children": ["user-story", "nfr"],
        "max_children": 20,  # Warn if more than 20 stories in one feature
        "required_fields": ["area", "estimated_effort"]
    },

    "user-story": {
        "can_have_parent": ["feature"],
        "must_have_parent": True,
        "can_have_children": ["task"],
        "max_children": 10,
        "required_fields": ["acceptance_criteria", "examples"]
    },

    "task": {
        "can_have_parent": ["user-story"],
        "must_have_parent": True,
        "can_have_children": [],  # Tasks are leaf nodes
        "max_children": 0,
        "required_fields": ["assignee", "estimated_hours"]
    },

    "constraint": {
        "can_have_parent": ["epic", "feature", "user-story"],
        "must_have_parent": False,  # Can be system-wide
        "can_have_children": [],
        "required_fields": ["constraint_type", "rationale"]
    },

    "nfr": {
        "can_have_parent": ["epic", "feature"],
        "must_have_parent": False,  # Can be system-wide
        "can_have_children": [],
        "required_fields": ["metric", "target_value", "measurement_method"]
    }
}
```

---

## 3. Data Model Changes

### 3.1 Extended Frontmatter

```yaml
---
# === Core Identity ===
id: REQ-001
type: user-story  # epic | feature | user-story | task | constraint | nfr | bug

# === Hierarchy ===
hierarchy:
  level: 3  # 1=Epic, 2=Feature, 3=Story, 4=Task
  parent_id: FEAT-001
  children_ids: [TASK-001, TASK-002, TASK-003]
  epic_id: EPIC-001  # Root epic (for quick rollup queries)
  path: "EPIC-001 > FEAT-001 > REQ-001"  # Breadcrumb path

# === Existing Fields ===
title: User can log in with email and password
status: proposed
priority: high
area: authentication

# === Rollup Metrics (calculated) ===
rollup:
  total_children: 3  # Direct children count
  total_descendants: 8  # All descendants (children + grandchildren + ...)
  completed_children: 1
  completion_percentage: 33.33
  total_effort: 13  # Sum of effort from all descendants
  accumulated_effort: 5  # Effort completed so far

# === Planning ===
planning:
  estimated_effort: 5  # Story points or hours
  target_release: "v2.0"
  sprint: "Sprint 23"

# === Dependencies (unchanged) ===
dependencies:
  blocks: [REQ-007]
  blocked_by: [FEAT-001]  # Can depend on parent feature

# === Other metadata (unchanged) ===
created_at: 2025-11-18T10:00:00Z
updated_at: 2025-11-19T14:30:00Z
---
```

### 3.2 ID Generation Strategy

```python
class HierarchicalIDGenerator:
    """
    Generate hierarchical IDs with proper prefixes.
    """

    PREFIX_MAP = {
        "epic": "EPIC",
        "feature": "FEAT",
        "user-story": "REQ",
        "task": "TASK",
        "constraint": "CONS",
        "nfr": "NFR",
        "bug": "BUG"
    }

    def generate_id(self, req_type, parent_id=None):
        """
        Generate ID based on type and parent.

        Examples:
        - Epic: EPIC-001, EPIC-002, ...
        - Feature: FEAT-001, FEAT-002, ... (numbered sequentially)
        - Story: REQ-001, REQ-002, ... (or REQ-FEAT001-001 for grouped IDs)
        - Task: TASK-001, TASK-002, ...

        Optional: Use parent-based numbering:
        - EPIC-001
        -   FEAT-001-01 (1st feature of EPIC-001)
        -   FEAT-001-02 (2nd feature of EPIC-001)
        -     REQ-001-01-001 (1st story of FEAT-001-01)
        -     REQ-001-01-002 (2nd story of FEAT-001-01)
        """

        prefix = self.PREFIX_MAP.get(req_type, "REQ")

        # Get next number for this type
        existing_ids = self._get_existing_ids(prefix)
        next_number = self._get_next_number(existing_ids, prefix)

        # Simple sequential numbering (default)
        new_id = f"{prefix}-{next_number:03d}"

        # Optional: Parent-based numbering (commented out for simplicity)
        # if parent_id and self.use_parent_numbering:
        #     parent_number = self._extract_number(parent_id)
        #     new_id = f"{prefix}-{parent_number:03d}-{next_number:02d}"

        return new_id

    def _get_next_number(self, existing_ids, prefix):
        """Find next available number for this prefix."""
        numbers = []
        for id_str in existing_ids:
            if id_str.startswith(prefix):
                # Extract number: EPIC-001 → 1
                match = re.search(r'-(\d+)$', id_str)
                if match:
                    numbers.append(int(match.group(1)))

        return max(numbers) + 1 if numbers else 1
```

---

## 4. Hierarchy Operations

### 4.1 New Tool: `requirements_hierarchy`

```python
def requirements_hierarchy(
    root_id: Optional[str] = None,
    view: str = "tree",  # tree | list | json | matrix
    max_depth: int = 10,
    include_metrics: bool = True,
    filter_status: Optional[str] = None,
) -> str:
    """
    Display requirement hierarchy.

    Args:
        root_id: Start from this requirement (None = show all epics)
        view:
            - tree: ASCII tree visualization
            - list: Indented list
            - json: Nested JSON structure
            - matrix: Flat table with hierarchy indicators
        max_depth: Maximum levels to display
        include_metrics: Show rollup metrics (effort, completion %)
        filter_status: Only show requirements with this status

    Returns:
        Formatted hierarchy view
    """

    if root_id:
        # Show subtree starting from root_id
        root = get_requirement(root_id)
        tree = build_subtree(root, max_depth)
    else:
        # Show all epics
        epics = get_requirements_by_type("epic")
        tree = [build_subtree(epic, max_depth) for epic in epics]

    if view == "tree":
        return format_as_ascii_tree(tree, include_metrics)
    elif view == "list":
        return format_as_list(tree, include_metrics)
    elif view == "json":
        return format_as_json(tree)
    elif view == "matrix":
        return format_as_matrix(tree, include_metrics)
```

**Example Output (ASCII Tree):**

```
EPIC-001: User Management (45 story points, 60% complete) ✓
│
├── FEAT-001: Authentication (21 points, 75% complete) ✓
│   ├── REQ-001: Email/Password Login (8 points) ✓ DONE
│   │   ├── TASK-001: Create login API (3 points) ✓
│   │   ├── TASK-002: Add email validation (2 points) ✓
│   │   └── TASK-003: Implement password hashing (3 points) ✓
│   │
│   ├── REQ-002: OAuth Social Login (8 points) 🔄 IN PROGRESS
│   │   ├── TASK-004: Google OAuth integration (4 points) ✓
│   │   └── TASK-005: GitHub OAuth integration (4 points) ⏳
│   │
│   └── REQ-003: Password Reset (5 points) ⏳ PLANNED
│
├── FEAT-002: User Profiles (16 points, 31% complete)
│   ├── REQ-004: Profile Dashboard (8 points) 🔄 IN PROGRESS
│   └── REQ-005: Profile Editing (8 points) ⏳ PLANNED
│
└── CONS-001: GDPR Compliance (applies to all features) ⚠️

Legend:
✓ Completed | 🔄 In Progress | ⏳ Planned | ⚠️ Constraint

Totals:
- Epics: 1
- Features: 2
- Stories: 5
- Tasks: 5
- Constraints: 1
- Total Effort: 45 story points
- Completed: 27 points (60%)
```

### 4.2 Rollup Calculations

```python
class HierarchyRollupCalculator:
    """
    Calculate rollup metrics for hierarchical requirements.
    """

    def calculate_rollup_metrics(self, req_id):
        """
        Calculate and update rollup metrics for a requirement and all ancestors.

        Metrics:
        - total_children: Direct children count
        - total_descendants: All descendants recursively
        - completed_descendants: Descendants with status=implemented
        - completion_percentage: completed / total * 100
        - total_effort: Sum of estimated_effort from all descendants
        - accumulated_effort: Sum of actual_effort from completed descendants
        - estimated_completion_date: Based on velocity and remaining effort
        """

        req = get_requirement(req_id)

        # Get all descendants
        descendants = self._get_all_descendants(req_id)

        # Calculate metrics
        metrics = {
            "total_children": len(req.get('children_ids', [])),
            "total_descendants": len(descendants),
            "completed_descendants": sum(1 for d in descendants if d['status'] == 'implemented'),
            "completion_percentage": 0,
            "total_effort": 0,
            "accumulated_effort": 0,
        }

        # Calculate effort
        for desc in descendants:
            effort = desc.get('planning', {}).get('estimated_effort', 0)
            metrics['total_effort'] += effort

            if desc['status'] == 'implemented':
                actual_effort = desc.get('planning', {}).get('actual_effort', effort)
                metrics['accumulated_effort'] += actual_effort

        # Calculate completion %
        if metrics['total_descendants'] > 0:
            metrics['completion_percentage'] = round(
                (metrics['completed_descendants'] / metrics['total_descendants']) * 100,
                2
            )

        # Update requirement
        req['rollup'] = metrics
        save_requirement(req)

        # Recursively update parent
        if req.get('hierarchy', {}).get('parent_id'):
            self.calculate_rollup_metrics(req['hierarchy']['parent_id'])

    def _get_all_descendants(self, req_id):
        """Recursively get all descendants."""
        req = get_requirement(req_id)
        descendants = []

        for child_id in req.get('children_ids', []):
            child = get_requirement(child_id)
            descendants.append(child)
            descendants.extend(self._get_all_descendants(child_id))

        return descendants
```

### 4.3 New Tool: `requirements_move`

```python
def requirements_move(
    req_id: str,
    new_parent_id: Optional[str],
    update_dependencies: bool = True,
) -> str:
    """
    Move a requirement to a different parent in the hierarchy.

    Args:
        req_id: Requirement to move
        new_parent_id: New parent (None = make it top-level epic)
        update_dependencies: Update dependencies to reflect new hierarchy

    Returns:
        Success message with updated hierarchy path

    Validation:
    - Check if move is allowed (can't move epic under story)
    - Check for circular references
    - Update all children's epic_id
    - Recalculate rollup metrics
    """

    req = get_requirement(req_id)
    old_parent_id = req.get('hierarchy', {}).get('parent_id')

    # Validate move
    if not self._is_valid_move(req, new_parent_id):
        return error("Invalid move: hierarchy rules violated")

    # Update old parent (remove from children)
    if old_parent_id:
        old_parent = get_requirement(old_parent_id)
        old_parent['children_ids'].remove(req_id)
        save_requirement(old_parent)
        recalculate_rollup(old_parent_id)

    # Update new parent (add to children)
    if new_parent_id:
        new_parent = get_requirement(new_parent_id)
        if 'children_ids' not in new_parent:
            new_parent['children_ids'] = []
        new_parent['children_ids'].append(req_id)
        save_requirement(new_parent)
        recalculate_rollup(new_parent_id)

    # Update requirement
    req['hierarchy']['parent_id'] = new_parent_id
    req['hierarchy']['path'] = build_path(req_id)
    req['hierarchy']['epic_id'] = get_root_epic(req_id)

    # Update all descendants' epic_id
    update_descendants_epic(req_id, req['hierarchy']['epic_id'])

    save_requirement(req)

    return success(f"Moved {req_id} to {new_parent_id or 'top-level'}")
```

---

## 5. Hierarchical Queries

### 5.1 Query Patterns

```python
class HierarchicalQueryEngine:
    """
    Advanced queries over hierarchical requirements.
    """

    def get_all_children(self, req_id, max_depth=None):
        """Get all direct children."""
        req = get_requirement(req_id)
        return [get_requirement(cid) for cid in req.get('children_ids', [])]

    def get_all_descendants(self, req_id, max_depth=None):
        """Get all descendants recursively."""
        descendants = []
        children = self.get_all_children(req_id)

        for child in children:
            descendants.append(child)
            if max_depth is None or max_depth > 1:
                next_depth = None if max_depth is None else max_depth - 1
                descendants.extend(self.get_all_descendants(child['id'], next_depth))

        return descendants

    def get_ancestors(self, req_id):
        """Get all ancestors up to root epic."""
        ancestors = []
        req = get_requirement(req_id)

        while req.get('hierarchy', {}).get('parent_id'):
            parent_id = req['hierarchy']['parent_id']
            parent = get_requirement(parent_id)
            ancestors.append(parent)
            req = parent

        return ancestors

    def get_siblings(self, req_id):
        """Get all sibling requirements (same parent)."""
        req = get_requirement(req_id)
        parent_id = req.get('hierarchy', {}).get('parent_id')

        if not parent_id:
            # Top-level: siblings are other top-level items of same type
            return get_requirements_by_type(req['type'])
        else:
            parent = get_requirement(parent_id)
            sibling_ids = [cid for cid in parent.get('children_ids', []) if cid != req_id]
            return [get_requirement(sid) for sid in sibling_ids]

    def get_leaf_nodes(self, req_id):
        """Get all leaf nodes (no children) under this requirement."""
        descendants = self.get_all_descendants(req_id)
        return [d for d in descendants if not d.get('children_ids')]

    def get_requirements_in_epic(self, epic_id):
        """Get all requirements belonging to this epic."""
        # Fast query using epic_id index
        return get_requirements_where(hierarchy__epic_id=epic_id)

    def get_critical_path_for_epic(self, epic_id):
        """Find critical path (longest dependency chain) for epic."""
        reqs = self.get_requirements_in_epic(epic_id)

        # Build dependency graph
        G = build_dependency_graph(reqs)

        # Find longest path
        critical_path = find_longest_path(G)

        return {
            "epic_id": epic_id,
            "path": critical_path,
            "total_effort": sum(req['estimated_effort'] for req in critical_path),
            "estimated_duration": calculate_duration(critical_path)
        }
```

### 5.2 Agent Query Enhancements

**User queries the agent can answer:**

```
User: "Show me all requirements in the User Management epic"
→ Agent calls: requirements_hierarchy(root_id="EPIC-001", view="tree")

User: "What's the completion status of the Authentication feature?"
→ Agent calls: requirements_get(req_id="FEAT-001", include_metrics=True)
→ Response: "FEAT-001 is 75% complete (3/4 stories done, 21/28 story points)"

User: "Which epic does REQ-042 belong to?"
→ Agent reads: req['hierarchy']['epic_id'] or req['hierarchy']['path']
→ Response: "REQ-042 belongs to EPIC-003 (Payment Processing)"

User: "Show me all leaf tasks ready to implement"
→ Agent queries: get_leaf_nodes(all_epics) where status='decided' and dependencies_met=True

User: "What's blocking EPIC-001 from being completed?"
→ Agent:
  1. Get all incomplete requirements in EPIC-001
  2. Check their blocked_by dependencies
  3. List external blockers
→ Response: "3 requirements in EPIC-001 are blocked:
   - REQ-005 blocked by FEAT-012 (from EPIC-002)
   - REQ-008 blocked by external API integration
   - REQ-011 blocked by pending legal approval"
```

---

## 6. Folder Organization

### 6.1 Hierarchy-Based Folders

**Current:** `requirements/backlog/`, `requirements/decided/`, etc.

**Enhanced:** Dual organization (status + hierarchy)

```
requirements/
  ├── by-status/               # Original (backward compatible)
  │   ├── backlog/
  │   ├── decided/
  │   ├── implemented/
  │   └── deprecated/
  │
  ├── by-hierarchy/            # NEW: Hierarchical folders
  │   ├── EPIC-001-user-management/
  │   │   ├── epic.md
  │   │   ├── FEAT-001-authentication/
  │   │   │   ├── feature.md
  │   │   │   ├── REQ-001-login.md
  │   │   │   ├── REQ-002-oauth.md
  │   │   │   └── tasks/
  │   │   │       ├── TASK-001-login-api.md
  │   │   │       └── TASK-002-email-validation.md
  │   │   └── FEAT-002-profiles/
  │   │       ├── feature.md
  │   │       ├── REQ-004-dashboard.md
  │   │       └── REQ-005-editing.md
  │   └── EPIC-002-payments/
  │       └── ...
  │
  └── index.json               # Enhanced with hierarchy info
```

**Note:** Use **symlinks** to maintain both views without duplicating files:
- Actual file: `by-hierarchy/EPIC-001-user-management/FEAT-001-authentication/REQ-001-login.md`
- Symlink: `by-status/backlog/REQ-001-login.md` → actual file

---

## 7. Visualization

### 7.1 ASCII Tree (for CLI/markdown)

```
EPIC-001: User Management 🎯 [60% ████████░░]
│
├─ FEAT-001: Authentication 🔐 [75% ██████████░░]
│  ├─ REQ-001: Login ✅ [100%]
│  ├─ REQ-002: OAuth 🔄 [50%]
│  └─ REQ-003: Password Reset ⏳ [0%]
│
└─ FEAT-002: Profiles 👤 [31% ████░░░░░░]
   ├─ REQ-004: Dashboard 🔄 [50%]
   └─ REQ-005: Editing ⏳ [0%]
```

### 7.2 Markdown Tables

```markdown
## Epic: EPIC-001 - User Management

| Feature | Stories | Tasks | Effort | Complete |
|---------|---------|-------|--------|----------|
| FEAT-001: Authentication | 3 | 5 | 21 pts | 75% |
| FEAT-002: Profiles | 2 | 4 | 16 pts | 31% |
| **Total** | **5** | **9** | **37 pts** | **56%** |

### Feature: FEAT-001 - Authentication

| Story | Priority | Status | Effort | Assignee |
|-------|----------|--------|--------|----------|
| REQ-001: Login | High | ✅ Done | 8 pts | Alice |
| REQ-002: OAuth | High | 🔄 In Progress | 8 pts | Bob |
| REQ-003: Reset | Medium | ⏳ Planned | 5 pts | Unassigned |
```

### 7.3 JSON (for programmatic access)

```json
{
  "id": "EPIC-001",
  "type": "epic",
  "title": "User Management",
  "metrics": {
    "total_stories": 5,
    "total_effort": 37,
    "completion_percentage": 56
  },
  "children": [
    {
      "id": "FEAT-001",
      "type": "feature",
      "title": "Authentication",
      "metrics": {
        "total_stories": 3,
        "total_effort": 21,
        "completion_percentage": 75
      },
      "children": [
        {
          "id": "REQ-001",
          "type": "user-story",
          "title": "Login",
          "status": "implemented",
          "estimated_effort": 8,
          "children": []
        }
      ]
    }
  ]
}
```

---

## 8. Migration Strategy

### 8.1 Backward Compatibility

**Existing requirements (flat):**
- Continue to work as-is
- No parent_id → treated as top-level
- Can be gradually migrated to hierarchy

**Migration path:**

```python
def migrate_to_hierarchy():
    """
    Migrate existing flat requirements to hierarchical structure.

    Strategy:
    1. Analyze existing requirements by area
    2. Create epics for each major area
    3. Create features for logical groupings
    4. Assign requirements to features
    5. Preserve all existing metadata
    """

    # Group by area
    areas = group_requirements_by_area()

    for area, reqs in areas.items():
        # Create epic
        epic_id = create_epic(title=f"{area.title()} Epic", area=area)

        # Analyze requirements to identify logical features
        features = infer_features_from_requirements(reqs)

        for feature_name, feature_reqs in features.items():
            # Create feature
            feat_id = create_feature(
                title=feature_name,
                parent_id=epic_id,
                area=area
            )

            # Assign requirements to feature
            for req in feature_reqs:
                move_requirement(req['id'], new_parent_id=feat_id)

    return "Migration complete"
```

---

## 9. Implementation Plan

### Week 1: Data Model

- ✅ Update frontmatter schema with hierarchy fields
- ✅ Implement `HierarchicalIDGenerator`
- ✅ Add hierarchy validation rules
- ✅ Update `requirements_store` to handle hierarchy

### Week 2: Hierarchy Operations

- ✅ Implement `requirements_hierarchy` tool
- ✅ Implement `HierarchyRollupCalculator`
- ✅ Implement `requirements_move` tool
- ✅ Build hierarchical query engine

### Week 3: Visualization & Migration

- ✅ ASCII tree formatter
- ✅ Markdown table generator
- ✅ Migration script for existing requirements
- ✅ Dual folder structure (status + hierarchy)

### Week 4: Integration & Testing

- ✅ Update agent prompts to use hierarchy
- ✅ Test all hierarchy operations
- ✅ Documentation updates
- ✅ User acceptance testing

---

## 10. Success Metrics

**After implementation:**

- ✅ Users can create epics, features, stories, tasks
- ✅ Hierarchy queries work correctly (children, descendants, ancestors)
- ✅ Rollup metrics calculate accurately
- ✅ Visualizations render properly
- ✅ Existing flat requirements still work
- ✅ Migration script succeeds on test data

---

**Document Status:** ✅ Complete
**Next Document:** `04_QUALITY_METRICS_DESIGN.md`

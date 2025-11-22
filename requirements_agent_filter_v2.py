"""
title: Requirements Agent Filter v2.0
author: Open WebUI Requirements Agent
author_url: https://github.com/open-webui/open-webui
version: 2.0.0
license: MIT
description: Enhanced requirements engineering agent with hierarchy support, conflict detection, quality scoring, and approval workflows.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import re


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=0, description="Filter priority")
        agent_mode: str = Field(
            default="assistant",
            description="Mode: assistant (helpful) | analyst (proactive) | architect (strategic)"
        )
        enable_auto_extraction: bool = Field(
            default=True,
            description="Auto-detect requirements from conversation"
        )
        enable_quality_check: bool = Field(
            default=True,
            description="Check quality before storing requirements"
        )
        enable_conflict_check: bool = Field(
            default=True,
            description="Check for conflicts with existing requirements"
        )
        require_confirmation: bool = Field(
            default=True,
            description="Ask user to confirm before storing"
        )
        default_type: str = Field(
            default="user-story",
            description="Default requirement type"
        )
        min_quality_threshold: float = Field(
            default=0.5,
            description="Minimum quality score to accept (0-1)"
        )

    class UserValves(BaseModel):
        show_quality_details: bool = Field(
            default=True,
            description="Show detailed quality scores"
        )
        auto_suggest_improvements: bool = Field(
            default=True,
            description="Suggest improvements for low-quality requirements"
        )

    def __init__(self):
        self.valves = self.Valves()
        self.user_valves = self.UserValves()

        # Keywords that suggest requirements
        self.requirement_triggers = {
            'strong': [
                'requirement', 'user story', 'feature request', 'acceptance criteria',
                'as a user', 'as an admin', 'the system shall', 'the system must',
                'epic', 'capability', 'constraint'
            ],
            'medium': [
                'should be able to', 'must be able to', 'needs to', 'want to',
                'given', 'when', 'then', 'scenario', 'acceptance',
            ],
            'weak': [
                'should', 'must', 'shall', 'need', 'want', 'feature',
                'functionality', 'capability', 'ability'
            ]
        }

        # Type detection patterns
        self.type_patterns = {
            'epic': [r'\bepic\b', r'\binitiative\b', r'\bstrategic goal\b'],
            'feature': [r'\bfeature\b', r'\bcapability\b', r'\bmodule\b'],
            'user-story': [r'\bas a\b.*\bi want\b', r'\buser story\b', r'\bstory\b'],
            'task': [r'\btask\b', r'\bimplement\b', r'\bcreate\b.*\bapi\b', r'\bbuild\b'],
            'constraint': [r'\bconstraint\b', r'\blimitation\b', r'\brestriction\b', r'\bmust not\b'],
            'nfr': [r'\bperformance\b', r'\bscalability\b', r'\bsecurity\b', r'\bavailability\b', r'\b\d+\s*(ms|seconds?|%)\b'],
            'bug': [r'\bbug\b', r'\bdefect\b', r'\bissue\b', r'\bfix\b', r'\bbroken\b']
        }

    def _get_system_prompt(self) -> str:
        """Generate the comprehensive system prompt."""
        mode = self.valves.agent_mode

        mode_descriptions = {
            "assistant": "helpful, collaborative, and supportive",
            "analyst": "proactive, detail-oriented, and thorough",
            "architect": "strategic, big-picture focused, and systematic"
        }

        prompt = f"""You are a **Requirements Engineering Expert** with a {mode_descriptions.get(mode, 'helpful')} approach.

## Your Capabilities

You help users capture, organize, and manage software requirements using enterprise-grade practices:

### Requirement Types (Hierarchical)
- **EPIC**: High-level business objective (months of work)
- **FEAT**: Major feature/capability within an epic (weeks of work)
- **REQ**: User story - specific user capability (days of work)
- **TASK**: Implementation task (hours of work)
- **CONS**: Constraint - limitation or restriction
- **NFR**: Non-functional requirement (performance, security, etc.)
- **BUG**: Defect to be fixed

### Methodology Support
- **User Stories**: "As a [role], I want [capability], so that [benefit]"
- **Spec-by-Example / BDD**: Given-When-Then scenarios in Gherkin
- **Acceptance Criteria**: Testable conditions for completion
- **SMART Requirements**: Specific, Measurable, Achievable, Relevant, Time-bound
- **INVEST Stories**: Independent, Negotiable, Valuable, Estimable, Small, Testable

## Available Tools

You have access to these requirements management tools:

### Core Tools
- `requirements_store` - Create/update requirements with full metadata
- `requirements_index` - Rebuild the requirements index
- `requirements_overview` - Generate filtered views and tables
- `requirements_get` - Retrieve specific requirement details
- `requirements_search` - Search requirements by keyword

### Hierarchy Tools
- `requirements_hierarchy` - Display requirement tree structure
- `requirements_move` - Move requirement to different parent

### Quality Tools
- `requirements_validate` - Check for conflicts and quality issues
- `requirements_conflicts` - Find conflicts between requirements
- `requirements_quality_report` - Generate quality assessment

### Workflow Tools
- `requirements_approve` - Record approval decisions
- `requirements_assign` - Assign stakeholders to requirements

### Planning Tools
- `requirements_prioritize` - Prioritize using MoSCoW, WSJF, Value/Effort
- `requirements_roadmap` - Generate roadmap views

## Interaction Guidelines

### When Users Discuss Features/Systems:

1. **Listen** for requirement-like statements
2. **Identify** the requirement type (epic, feature, story, task, etc.)
3. **Extract** key information:
   - WHO: User role/persona
   - WHAT: Capability/action
   - WHY: Value/benefit
   - HOW: Acceptance criteria
   - WHEN: Timeline/priority
4. **{"Proactively suggest" if mode == "analyst" else "Ask if user wants to"} capture as a requirement**
5. **Request** Gherkin scenarios for concrete examples
6. **{"Store immediately" if not self.valves.require_confirmation else "Confirm before storing"}**

### When Users Ask for Requirements:

- Use `requirements_overview` for lists and summaries
- Use `requirements_hierarchy` for tree visualization
- Use `requirements_get` for specific requirement details
- Use `requirements_search` for keyword-based lookup
- Use `requirements_quality_report` for quality assessment

### Quality Guidance

{"When storing requirements, I will:" if self.valves.enable_quality_check else "Quality checks are disabled, but consider:"}

1. **SMART Check**: Is it Specific, Measurable, Achievable, Relevant, Time-bound?
2. **INVEST Check** (for stories): Is it Independent, Negotiable, Valuable, Estimable, Small, Testable?
3. **Completeness Check**: Are all required fields present?
4. **Conflict Check**: Does it contradict existing requirements?

{"I'll suggest improvements for requirements scoring below " + str(self.valves.min_quality_threshold * 100) + "%." if self.user_valves.auto_suggest_improvements else ""}

### Conflict Detection

{"When storing or updating requirements:" if self.valves.enable_conflict_check else ""}
{"1. Check for semantic contradictions with existing requirements" if self.valves.enable_conflict_check else ""}
{"2. Detect circular dependencies" if self.valves.enable_conflict_check else ""}
{"3. Identify missing parent/dependency references" if self.valves.enable_conflict_check else ""}
{"4. Flag constraint violations (e.g., security requirements with low priority)" if self.valves.enable_conflict_check else ""}

### Hierarchy Best Practices

When creating requirements:
- **Epics** should represent major business objectives (3-6 months scope)
- **Features** should group related user stories (1-2 months scope)
- **User Stories** should be completable in 1-2 weeks
- **Tasks** should be completable in 1-3 days

Always ask about parent requirement when creating features, stories, or tasks.

### Example Interactions

**Creating a User Story:**
```
User: "Users should be able to reset their password via email"

You: "I'll capture this as a user story. Let me structure it:

**REQ-XXX: Password Reset via Email**
Type: user-story
Priority: {suggest based on context}

As a registered user,
I want to reset my password via email link,
So that I can regain access to my account when I forget my password.

**Suggested Acceptance Criteria:**
- User receives reset link within 2 minutes
- Link expires after 1 hour
- User must set a new password meeting complexity requirements

Should I add Gherkin scenarios? And does this belong to a specific feature (parent requirement)?"
```

**Checking Quality:**
```
User: "Store this requirement: Users can search"

You: "This requirement needs more detail to meet quality standards.

Current Quality Score: 35% (Grade: F)

Issues:
- Not Specific: What can users search for?
- Not Measurable: What are the success criteria?
- Not Testable: No acceptance criteria provided

Let me help improve it. What exactly should users be able to search?"
```

## Important Rules

1. **Never invent requirements** - only capture what users express
2. **Always clarify ambiguity** - ask questions when uncertain
3. **Maintain hierarchy** - assign parents when appropriate
4. **Track quality** - flag low-quality requirements
5. **Detect conflicts** - warn about contradictions
6. **Use the tools** - don't just discuss requirements, store them
7. **Be {"proactive" if mode == "analyst" else "helpful"}** in extraction

You are now ready to help with requirements engineering!
"""
        return prompt

    def _detect_requirement_type(self, text: str) -> str:
        """Detect the most likely requirement type from text."""
        text_lower = text.lower()

        for req_type, patterns in self.type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return req_type

        return self.valves.default_type

    def _calculate_requirement_likelihood(self, text: str) -> float:
        """Calculate likelihood that text contains a requirement."""
        text_lower = text.lower()
        score = 0.0

        for word in self.requirement_triggers['strong']:
            if word in text_lower:
                score += 0.4

        for word in self.requirement_triggers['medium']:
            if word in text_lower:
                score += 0.2

        for word in self.requirement_triggers['weak']:
            if word in text_lower:
                score += 0.1

        return min(1.0, score)

    def _extract_requirement_hints(self, messages: List[Dict]) -> Dict:
        """Extract hints about potential requirements from recent messages."""
        hints = {
            'likely_type': self.valves.default_type,
            'confidence': 0.0,
            'suggested_title': '',
            'suggested_area': 'general',
        }

        # Analyze last few user messages
        recent_user_messages = [
            m.get('content', '') for m in messages[-5:]
            if m.get('role') == 'user'
        ]

        combined_text = ' '.join(recent_user_messages)

        if combined_text:
            hints['likely_type'] = self._detect_requirement_type(combined_text)
            hints['confidence'] = self._calculate_requirement_likelihood(combined_text)

            # Try to extract potential area
            area_patterns = [
                (r'\b(auth|login|password|credential)s?\b', 'authentication'),
                (r'\b(payment|checkout|billing|invoice)s?\b', 'payments'),
                (r'\b(user|profile|account|registration)s?\b', 'user-management'),
                (r'\b(search|filter|query)(?:ing)?\b', 'search'),
                (r'\b(report|dashboard|analytics|metric)s?\b', 'reporting'),
                (r'\b(api|endpoint|integration)s?\b', 'api'),
                (r'\b(security|permission|access|role)s?\b', 'security'),
                (r'\b(notification|alert|email|sms)s?\b', 'notifications'),
            ]

            for pattern, area in area_patterns:
                if re.search(pattern, combined_text.lower()):
                    hints['suggested_area'] = area
                    break

        return hints

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """Pre-process requests before sending to LLM."""
        messages = body.get("messages", [])

        if not messages:
            return body

        # Inject system prompt
        system_prompt = self._get_system_prompt()

        # Check for existing system message
        has_system = any(msg.get("role") == "system" for msg in messages)

        if has_system:
            for msg in messages:
                if msg.get("role") == "system":
                    msg["content"] = system_prompt + "\n\n---\n\n" + msg["content"]
                    break
        else:
            messages.insert(0, {
                "role": "system",
                "content": system_prompt
            })

        # If analyst mode, check for requirements and add hints
        if self.valves.agent_mode == "analyst" and self.valves.enable_auto_extraction:
            hints = self._extract_requirement_hints(messages)

            if hints['confidence'] > 0.5:
                last_user_msg = messages[-1]
                if last_user_msg.get('role') == 'user':
                    hint_text = f"\n\n[AGENT NOTE: Detected potential {hints['likely_type']} requirement " \
                               f"(confidence: {hints['confidence']:.0%}). " \
                               f"Suggested area: {hints['suggested_area']}. " \
                               f"Consider offering to capture this as a requirement.]"
                    # Add as system note, not visible to user
                    messages.append({
                        "role": "system",
                        "content": hint_text
                    })

        body["messages"] = messages
        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """Post-process responses from LLM."""
        # For now, pass through without modification
        # Could add formatting, requirement ID highlighting, etc.
        return body

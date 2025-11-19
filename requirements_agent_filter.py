"""
title: Requirements Agent Filter
author: Open WebUI Requirements Agent
author_url: https://github.com/open-webui/open-webui
version: 1.0.0
license: MIT
description: A specialized agent filter that extracts requirements from conversations using Spec-by-Example methodology. Works in conjunction with the Requirements Management Toolkit.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import re


class Filter:
    class Valves(BaseModel):
        priority: int = Field(
            default=0,
            description="Priority level for the filter operations."
        )
        enable_auto_extraction: bool = Field(
            default=True,
            description="Automatically detect and extract requirements from conversations"
        )
        enable_conflict_detection: bool = Field(
            default=True,
            description="Automatically check for conflicts with existing requirements"
        )
        require_confirmation: bool = Field(
            default=True,
            description="Ask user to confirm before storing requirements"
        )
        agent_mode: str = Field(
            default="assistant",
            description="Agent mode: 'assistant' (helpful), 'analyst' (proactive extraction), 'silent' (only responds when asked)"
        )
        enable_gherkin_prompts: bool = Field(
            default=True,
            description="Prompt users to provide Gherkin/BDD scenarios"
        )
        default_area: str = Field(
            default="general",
            description="Default area for requirements when not specified"
        )

    class UserValves(BaseModel):
        show_internal_thoughts: bool = Field(
            default=False,
            description="Show the agent's internal reasoning process"
        )

    def __init__(self):
        self.valves = self.Valves()
        self.user_valves = self.UserValves()

        # Agent personality and behavior
        self.agent_personality = {
            "assistant": "helpful and collaborative",
            "analyst": "proactive and detail-oriented",
            "silent": "responsive only when addressed"
        }

        # Keywords that trigger requirement extraction
        self.requirement_triggers = [
            "requirement", "requirements", "user story", "feature",
            "should", "must", "shall", "need to", "want to",
            "as a", "given", "when", "then", "scenario",
            "acceptance criteria", "specification", "spec"
        ]

    def _get_system_prompt(self) -> str:
        """Generate the system prompt for the Requirements Agent."""
        mode = self.valves.agent_mode
        personality = self.agent_personality.get(mode, "helpful")

        prompt = f"""You are a **Requirements and Spec-by-Example Assistant** with a {personality} personality.

## Your Role

You help users define, capture, and manage requirements for software systems using:
- **Spec-by-Example / BDD methodology** (Given-When-Then scenarios)
- **User stories** (As a... I want... So that...)
- **Acceptance criteria** and examples
- **Structured requirement tracking** in markdown format

## Core Responsibilities

1. **Listen & Extract**: Identify requirements, constraints, and examples from natural conversations
2. **Clarify**: Ask questions when requirements are ambiguous or incomplete
3. **Structure**: Convert informal discussions into well-formed requirements
4. **Store**: Use the Requirements Management Tools to persist requirements
5. **Recall**: Use existing requirements (via search/RAG) to:
   - Detect duplicates and conflicts
   - Provide context for new requirements
   - Answer questions about existing requirements
6. **Overview**: Generate summaries, lists, and matrices on demand

## Tools Available

You have access to these requirement management tools:
- `requirements_store` - Create or update a requirement
- `requirements_index` - Rebuild the requirements index
- `requirements_overview` - Generate summaries and filtered views
- `requirements_get` - Retrieve a specific requirement by ID
- `requirements_search` - Search requirements by keyword

## Interaction Patterns

### When users discuss features/needs:
1. Listen for requirement-like statements
2. Extract key information (what, why, who, examples)
3. {"Automatically propose storing as a requirement" if mode == "analyst" else "Ask if they want to capture this as a requirement"}
4. Request Gherkin scenarios for concrete examples
5. {"Ask for confirmation before storing" if self.valves.require_confirmation else "Store immediately"}

### When users ask for overviews:
- Use `requirements_overview` with appropriate filters
- Present results in clear tables or lists
- Highlight important patterns or gaps

### When users mention existing functionality:
- Use `requirements_search` or RAG to find related requirements
- Check for conflicts or duplicates
- Show relevant existing requirements for context

### For ambiguous requirements:
- Ask clarifying questions about:
  - Actors (who?)
  - Actions (what?)
  - Outcomes (why? what value?)
  - Constraints (limits, rules, policies)
  - Examples (concrete scenarios)

## Requirement Structure

When capturing requirements, ensure you gather:

**Metadata:**
- Title (clear, concise)
- Area/Domain (e.g., authentication, payments, reporting)
- Type (functional, non-functional, constraint)
- Priority (low, medium, high, critical)
- Status (proposed, accepted, implemented, deprecated)

**Content:**
- Summary (user story format preferred: "As a [user], I want [action] so that [value]")
- Details (acceptance criteria, constraints, business rules)
- Examples (Given-When-Then scenarios in Gherkin format)

**Context:**
- Source conversation (track where requirement came from)

## Spec-by-Example / BDD Guidance

{"Actively encourage" if self.valves.enable_gherkin_prompts else "Accept"} Gherkin scenarios:

```gherkin
Scenario: [Descriptive name]
  Given [initial context/state]
  When [action/event occurs]
  Then [expected outcome]
  And [additional expectations]
```

Examples make requirements concrete and testable.

## Conflict Detection

{"When storing new requirements:" if self.valves.enable_conflict_detection else ""}
{"1. Search for similar existing requirements" if self.valves.enable_conflict_detection else ""}
{"2. Check for contradictions in:" if self.valves.enable_conflict_detection else ""}
{"   - Acceptance criteria" if self.valves.enable_conflict_detection else ""}
{"   - Business rules" if self.valves.enable_conflict_detection else ""}
{"   - Technical constraints" if self.valves.enable_conflict_detection else ""}
{"3. Present conflicts to user for resolution" if self.valves.enable_conflict_detection else ""}

## Tone & Style

- Be {personality}
- Use clear, precise language
- Focus on value and outcomes
- Encourage concrete examples
- Respect user's time and decisions
{"- Show internal reasoning when requested" if self.user_valves.show_internal_thoughts else ""}

## Important

- **Never** make up requirements - only capture what users express
- **Always** seek clarification when uncertain
- **Maintain** traceability to source conversations
- **Respect** user's final decisions on requirement content
- **Use** the tools to persist requirements - don't just discuss them

You are now ready to help the user manage their requirements effectively!
"""
        return prompt

    def _contains_requirement_keywords(self, text: str) -> bool:
        """Check if text contains requirement-related keywords."""
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in self.requirement_triggers)

    def _extract_potential_requirements(self, messages: List[Dict]) -> List[str]:
        """Extract messages that might contain requirements."""
        candidates = []

        for msg in messages[-5:]:  # Check last 5 messages
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if self._contains_requirement_keywords(content):
                    candidates.append(content)

        return candidates

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        Pre-process requests before sending to LLM.

        Injects the Requirements Agent system prompt and context.
        """
        messages = body.get("messages", [])

        if not messages:
            return body

        # Check if this is a requirements-related conversation
        last_message = messages[-1].get("content", "") if messages else ""

        # Inject system prompt
        system_prompt = self._get_system_prompt()

        # Check if system message already exists
        has_system = any(msg.get("role") == "system" for msg in messages)

        if has_system:
            # Update existing system message
            for msg in messages:
                if msg.get("role") == "system":
                    # Prepend our requirements agent prompt
                    msg["content"] = system_prompt + "\n\n---\n\n" + msg["content"]
                    break
        else:
            # Insert new system message at the beginning
            messages.insert(0, {
                "role": "system",
                "content": system_prompt
            })

        # If auto-extraction is enabled and we detect requirement keywords
        if self.valves.enable_auto_extraction and self.valves.agent_mode == "analyst":
            potential_reqs = self._extract_potential_requirements(messages)

            if potential_reqs and not self._is_already_handling_requirements(messages):
                # Add a subtle hint for the agent to consider extracting requirements
                hint = "\n\n*[Internal note: The recent conversation contains requirement-like statements. Consider offering to capture them as structured requirements.]*"
                messages[-1]["content"] = messages[-1].get("content", "") + hint

        body["messages"] = messages
        return body

    def _is_already_handling_requirements(self, messages: List[Dict]) -> bool:
        """Check if the conversation is already discussing requirements extraction."""
        recent_messages = messages[-3:] if len(messages) >= 3 else messages

        for msg in recent_messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "").lower()
                if any(phrase in content for phrase in [
                    "capture this requirement",
                    "store this requirement",
                    "requirements_store",
                    "shall i store",
                    "would you like me to store"
                ]):
                    return True

        return False

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        Post-process responses from LLM.

        Can be used to format requirements output or add helpful hints.
        """
        # For now, just pass through
        # Could add formatting, markdown rendering hints, etc.
        return body

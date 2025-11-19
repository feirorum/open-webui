"""
title: Requirements Management Toolkit
author: Open WebUI Requirements Agent
author_url: https://github.com/open-webui/open-webui
version: 1.0.0
requirements: pyyaml, python-slugify
license: MIT
description: A comprehensive toolkit for managing requirements using Spec-by-Example methodology. Supports creating, updating, indexing, and querying requirements stored as markdown files with YAML frontmatter.
"""

import os
import json
import yaml
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field

try:
    from slugify import slugify
except ImportError:
    # Fallback slugify if python-slugify not available
    def slugify(text):
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        return text.strip('-')


class Tools:
    class Valves(BaseModel):
        requirements_base_path: str = Field(
            default="backend/data/requirements",
            description="Base path for requirements storage (relative to Open WebUI root or absolute path)"
        )
        auto_index: bool = Field(
            default=True,
            description="Automatically rebuild index after storing requirements"
        )
        default_status: str = Field(
            default="proposed",
            description="Default status for new requirements (proposed|accepted|implemented|deprecated)"
        )
        id_prefix: str = Field(
            default="REQ",
            description="Prefix for requirement IDs (e.g., REQ, STORY, FEAT)"
        )
        enable_gherkin: bool = Field(
            default=True,
            description="Enable Gherkin/BDD scenario support in examples"
        )

    def __init__(self):
        self.valves = self.Valves()
        self._ensure_requirements_structure()

    def _get_base_path(self) -> Path:
        """Get the absolute base path for requirements storage."""
        base = self.valves.requirements_base_path

        # If relative path, make it relative to current working directory
        if not os.path.isabs(base):
            # Try to find Open WebUI root
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

        # Create folder structure
        folders = [
            base_path,
            base_path / "backlog",
            base_path / "decided",
            base_path / "implemented",
            base_path / "deprecated",
        ]

        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)

        # Create index if it doesn't exist
        index_file = base_path / "index.json"
        if not index_file.exists():
            self._write_index({
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "requirements": []
            })

        # Create README if it doesn't exist
        readme_file = base_path / "README.md"
        if not readme_file.exists():
            readme_content = """# Requirements Database

This folder contains requirements managed by the Open WebUI Requirements Agent.

## Structure

- `backlog/` - Proposed requirements awaiting review
- `decided/` - Accepted requirements ready for implementation
- `implemented/` - Implemented requirements
- `deprecated/` - Deprecated or rejected requirements
- `index.json` - Quick lookup index of all requirements

## Requirement Format

Each requirement is stored as a markdown file with YAML frontmatter containing:

- Metadata (ID, title, status, type, priority, area)
- Timestamps (created_at, updated_at)
- Source conversation tracking
- Examples (Spec-by-Example/BDD scenarios)

## Usage

Requirements are managed through the Open WebUI Requirements Agent using natural language conversation.
You can also manually edit requirements files - they will be picked up on the next index rebuild.
"""
            with open(readme_file, 'w') as f:
                f.write(readme_content)

    def _read_index(self) -> Dict[str, Any]:
        """Read the requirements index."""
        index_file = self._get_base_path() / "index.json"
        try:
            with open(index_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"last_updated": datetime.utcnow().isoformat() + "Z", "requirements": []}

    def _write_index(self, index_data: Dict[str, Any]):
        """Write the requirements index."""
        index_file = self._get_base_path() / "index.json"
        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=2)

    def _generate_next_id(self) -> str:
        """Generate the next available requirement ID."""
        index = self._read_index()
        prefix = self.valves.id_prefix

        existing_ids = [
            req['id'] for req in index['requirements']
            if req['id'].startswith(prefix)
        ]

        if not existing_ids:
            return f"{prefix}-001"

        # Extract numbers and find max
        numbers = []
        for req_id in existing_ids:
            match = re.search(r'-(\d+)$', req_id)
            if match:
                numbers.append(int(match.group(1)))

        next_num = max(numbers) + 1 if numbers else 1
        return f"{prefix}-{next_num:03d}"

    def _status_to_folder(self, status: str) -> str:
        """Map status to folder name."""
        status_lower = status.lower()
        if status_lower in ['proposed', 'draft', 'pending']:
            return 'backlog'
        elif status_lower in ['accepted', 'approved', 'decided']:
            return 'decided'
        elif status_lower in ['implemented', 'done', 'completed']:
            return 'implemented'
        elif status_lower in ['deprecated', 'rejected', 'obsolete']:
            return 'deprecated'
        else:
            return 'backlog'

    def _parse_requirement_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a requirement markdown file and extract frontmatter + content."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Split frontmatter and body
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
            print(f"Error parsing {file_path}: {e}")
            return None

    def _create_requirement_content(
        self,
        req_id: str,
        title: str,
        status: str,
        req_type: str,
        priority: str,
        area: str,
        summary: str,
        details: str,
        examples: List[Dict[str, Any]],
        source_conversation: Dict[str, Any],
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ) -> str:
        """Create requirement file content with frontmatter and body."""
        now = datetime.utcnow().isoformat() + "Z"

        frontmatter = {
            'id': req_id,
            'title': title,
            'status': status,
            'type': req_type,
            'priority': priority,
            'area': area,
            'created_at': created_at or now,
            'updated_at': updated_at or now,
            'source_conversations': [source_conversation] if source_conversation else [],
        }

        if examples:
            frontmatter['examples'] = [
                {
                    'id': ex.get('id', f"EX-{i+1:03d}"),
                    'description': ex.get('description', ''),
                    'status': ex.get('status', 'draft')
                }
                for i, ex in enumerate(examples)
            ]

        # Build body
        body_parts = [
            "## Summary\n",
            summary.strip(),
            "\n\n## Details\n",
            details.strip() if details else "_No additional details provided._",
        ]

        if examples and self.valves.enable_gherkin:
            body_parts.append("\n\n## Examples (Spec-by-Example / BDD)\n")
            for i, example in enumerate(examples):
                ex_id = example.get('id', f"EX-{i+1:03d}")
                ex_desc = example.get('description', 'Example scenario')
                ex_gherkin = example.get('gherkin', '')

                body_parts.append(f"\n### {ex_id}: {ex_desc}\n")
                if ex_gherkin:
                    body_parts.append(f"\n```gherkin\n{ex_gherkin.strip()}\n```\n")
                else:
                    body_parts.append("\n_Gherkin scenario to be defined._\n")

        # Combine
        yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_str}---\n\n{''.join(body_parts)}"

    def requirements_store(
        self,
        title: str = Field(..., description="The title/name of the requirement"),
        summary: str = Field(..., description="Brief summary or user story of the requirement"),
        req_id: Optional[str] = Field(None, description="Requirement ID (auto-generated if not provided)"),
        status: Optional[str] = Field(None, description="Status: proposed|accepted|implemented|deprecated"),
        req_type: str = Field(default="functional", description="Type: functional|non-functional|constraint"),
        priority: str = Field(default="medium", description="Priority: low|medium|high|critical"),
        area: str = Field(default="general", description="Area/domain/component this requirement belongs to"),
        details: str = Field(default="", description="Detailed description, acceptance criteria, etc."),
        examples: Optional[str] = Field(None, description="JSON array of examples/scenarios with optional Gherkin"),
        source_conversation: Optional[str] = Field(None, description="JSON object with conversation context {convo_id, message_ids}"),
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Create or update a requirement and store it as a markdown file.

        Returns a JSON string with the result including the requirement ID and file path.
        """
        try:
            # Parse JSON strings
            examples_list = json.loads(examples) if examples else []
            source_conv = json.loads(source_conversation) if source_conversation else {}

            # Generate ID if not provided
            if not req_id:
                req_id = self._generate_next_id()

            # Use default status if not provided
            if not status:
                status = self.valves.default_status

            # Determine folder based on status
            folder = self._status_to_folder(status)

            # Create filename
            title_slug = slugify(title)[:50]  # Limit slug length
            filename = f"{req_id}-{title_slug}.md"

            # Check if requirement already exists (search all folders)
            base_path = self._get_base_path()
            existing_file = None
            for subfolder in ['backlog', 'decided', 'implemented', 'deprecated']:
                potential_file = base_path / subfolder / filename
                if potential_file.exists():
                    existing_file = potential_file
                    break
                # Also check with different title slugs (same ID)
                for f in (base_path / subfolder).glob(f"{req_id}-*.md"):
                    existing_file = f
                    break
                if existing_file:
                    break

            # Load existing data if updating
            created_at = None
            if existing_file:
                parsed = self._parse_requirement_file(existing_file)
                if parsed:
                    created_at = parsed['frontmatter'].get('created_at')
                    # Merge source conversations
                    existing_convs = parsed['frontmatter'].get('source_conversations', [])
                    if source_conv and source_conv not in existing_convs:
                        existing_convs.append(source_conv)
                        source_conv = existing_convs[0]  # Keep first as primary
                    # Delete old file if status changed (moving folders)
                    if existing_file.parent.name != folder:
                        existing_file.unlink()

            # Create content
            content = self._create_requirement_content(
                req_id=req_id,
                title=title,
                status=status,
                req_type=req_type,
                priority=priority,
                area=area,
                summary=summary,
                details=details,
                examples=examples_list,
                source_conversation=source_conv,
                created_at=created_at
            )

            # Write file
            target_path = base_path / folder / filename
            with open(target_path, 'w') as f:
                f.write(content)

            # Auto-index if enabled
            if self.valves.auto_index:
                self.requirements_index()

            result = {
                "status": "success",
                "action": "updated" if existing_file else "created",
                "id": req_id,
                "file_path": str(target_path.relative_to(base_path)),
                "title": title
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e)
            }, indent=2)

    def requirements_index(
        self,
        mode: str = Field(default="full", description="Index mode: 'full' or 'incremental'"),
    ) -> str:
        """
        Build or refresh the requirements index by scanning all requirement markdown files.

        Returns a JSON string with indexing statistics.
        """
        try:
            base_path = self._get_base_path()
            requirements = []

            # Scan all folders
            for subfolder in ['backlog', 'decided', 'implemented', 'deprecated']:
                folder_path = base_path / subfolder
                if not folder_path.exists():
                    continue

                for md_file in folder_path.glob("*.md"):
                    if md_file.name == "README.md":
                        continue

                    parsed = self._parse_requirement_file(md_file)
                    if not parsed:
                        continue

                    fm = parsed['frontmatter']
                    requirements.append({
                        'id': fm.get('id', ''),
                        'title': fm.get('title', ''),
                        'status': fm.get('status', ''),
                        'type': fm.get('type', ''),
                        'priority': fm.get('priority', ''),
                        'area': fm.get('area', ''),
                        'file': str(md_file.relative_to(base_path)),
                        'created_at': fm.get('created_at', ''),
                        'updated_at': fm.get('updated_at', ''),
                    })

            # Write index
            index_data = {
                'last_updated': datetime.utcnow().isoformat() + "Z",
                'requirements': sorted(requirements, key=lambda x: x['id'])
            }
            self._write_index(index_data)

            # Statistics by status
            stats = {}
            for req in requirements:
                status = req['status']
                stats[status] = stats.get(status, 0) + 1

            result = {
                'status': 'success',
                'mode': mode,
                'requirement_count': len(requirements),
                'last_updated': index_data['last_updated'],
                'statistics': stats
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({
                'status': 'error',
                'error': str(e)
            }, indent=2)

    def requirements_overview(
        self,
        filter_status: Optional[str] = Field(None, description="Filter by status (e.g., 'proposed', 'accepted')"),
        filter_area: Optional[str] = Field(None, description="Filter by area/domain"),
        filter_type: Optional[str] = Field(None, description="Filter by type (e.g., 'functional', 'non-functional')"),
        filter_priority: Optional[str] = Field(None, description="Filter by priority (e.g., 'high', 'critical')"),
        group_by: Optional[str] = Field(None, description="Group results by: 'status', 'area', 'type', or 'priority'"),
        format: str = Field(default="json", description="Output format: 'json' or 'markdown'"),
    ) -> str:
        """
        Generate an overview of requirements based on filters and grouping.

        Returns a JSON string or markdown table with filtered and grouped requirements.
        """
        try:
            index = self._read_index()
            requirements = index.get('requirements', [])

            # Apply filters
            if filter_status:
                requirements = [r for r in requirements if r['status'].lower() == filter_status.lower()]
            if filter_area:
                requirements = [r for r in requirements if r['area'].lower() == filter_area.lower()]
            if filter_type:
                requirements = [r for r in requirements if r['type'].lower() == filter_type.lower()]
            if filter_priority:
                requirements = [r for r in requirements if r['priority'].lower() == filter_priority.lower()]

            # Group if requested
            if group_by:
                grouped = {}
                for req in requirements:
                    key = req.get(group_by, 'unknown')
                    if key not in grouped:
                        grouped[key] = []
                    grouped[key].append(req)

                if format == "markdown":
                    # Generate markdown tables
                    md_parts = [f"# Requirements Overview\n\n"]
                    md_parts.append(f"**Total**: {len(requirements)} requirements\n")
                    md_parts.append(f"**Grouped by**: {group_by}\n")
                    md_parts.append(f"**Last updated**: {index.get('last_updated', 'unknown')}\n\n")

                    for group_key in sorted(grouped.keys()):
                        group_reqs = grouped[group_key]
                        md_parts.append(f"## {group_key.capitalize()} ({len(group_reqs)})\n\n")
                        md_parts.append("| ID | Title | Status | Priority | Area |\n")
                        md_parts.append("|---|---|---|---|---|\n")
                        for req in group_reqs:
                            md_parts.append(
                                f"| {req['id']} | {req['title']} | {req['status']} | "
                                f"{req['priority']} | {req['area']} |\n"
                            )
                        md_parts.append("\n")

                    return ''.join(md_parts)
                else:
                    return json.dumps({
                        'total': len(requirements),
                        'grouped_by': group_by,
                        'groups': grouped,
                        'last_updated': index.get('last_updated')
                    }, indent=2)
            else:
                if format == "markdown":
                    md_parts = [f"# Requirements Overview\n\n"]
                    md_parts.append(f"**Total**: {len(requirements)} requirements\n")
                    md_parts.append(f"**Last updated**: {index.get('last_updated', 'unknown')}\n\n")
                    md_parts.append("| ID | Title | Status | Type | Priority | Area |\n")
                    md_parts.append("|---|---|---|---|---|---|\n")
                    for req in requirements:
                        md_parts.append(
                            f"| {req['id']} | {req['title']} | {req['status']} | "
                            f"{req['type']} | {req['priority']} | {req['area']} |\n"
                        )
                    return ''.join(md_parts)
                else:
                    return json.dumps({
                        'total': len(requirements),
                        'requirements': requirements,
                        'last_updated': index.get('last_updated')
                    }, indent=2)

        except Exception as e:
            return json.dumps({
                'status': 'error',
                'error': str(e)
            }, indent=2)

    def requirements_get(
        self,
        req_id: str = Field(..., description="The requirement ID to retrieve (e.g., 'REQ-001')"),
        include_content: bool = Field(default=True, description="Include full markdown content"),
    ) -> str:
        """
        Retrieve a specific requirement by ID.

        Returns the requirement metadata and optionally the full content.
        """
        try:
            base_path = self._get_base_path()

            # Search for the requirement file
            for subfolder in ['backlog', 'decided', 'implemented', 'deprecated']:
                folder_path = base_path / subfolder
                for md_file in folder_path.glob(f"{req_id}-*.md"):
                    parsed = self._parse_requirement_file(md_file)
                    if parsed and parsed['frontmatter'].get('id') == req_id:
                        result = {
                            'status': 'success',
                            'requirement': parsed['frontmatter'],
                            'file_path': str(md_file.relative_to(base_path))
                        }
                        if include_content:
                            result['content'] = parsed['body']
                            result['full_markdown'] = f"---\n{yaml.dump(parsed['frontmatter'])}---\n\n{parsed['body']}"
                        return json.dumps(result, indent=2)

            return json.dumps({
                'status': 'not_found',
                'error': f"Requirement {req_id} not found"
            }, indent=2)

        except Exception as e:
            return json.dumps({
                'status': 'error',
                'error': str(e)
            }, indent=2)

    def requirements_search(
        self,
        query: str = Field(..., description="Search query (searches in title, summary, and details)"),
        search_area: Optional[str] = Field(None, description="Limit search to specific area"),
        max_results: int = Field(default=10, description="Maximum number of results to return"),
    ) -> str:
        """
        Search requirements by keyword in title and content.

        Returns matching requirements ranked by relevance.
        """
        try:
            base_path = self._get_base_path()
            matches = []
            query_lower = query.lower()

            # Search all requirement files
            for subfolder in ['backlog', 'decided', 'implemented', 'deprecated']:
                folder_path = base_path / subfolder
                if not folder_path.exists():
                    continue

                for md_file in folder_path.glob("*.md"):
                    if md_file.name == "README.md":
                        continue

                    parsed = self._parse_requirement_file(md_file)
                    if not parsed:
                        continue

                    fm = parsed['frontmatter']

                    # Filter by area if specified
                    if search_area and fm.get('area', '').lower() != search_area.lower():
                        continue

                    # Calculate relevance score
                    score = 0
                    title = fm.get('title', '').lower()
                    body = parsed['body'].lower()

                    if query_lower in title:
                        score += 10
                    if query_lower in fm.get('area', '').lower():
                        score += 5
                    if query_lower in body:
                        score += body.count(query_lower)

                    if score > 0:
                        matches.append({
                            'score': score,
                            'id': fm.get('id'),
                            'title': fm.get('title'),
                            'status': fm.get('status'),
                            'area': fm.get('area'),
                            'priority': fm.get('priority'),
                            'file': str(md_file.relative_to(base_path))
                        })

            # Sort by score and limit
            matches.sort(key=lambda x: x['score'], reverse=True)
            matches = matches[:max_results]

            return json.dumps({
                'status': 'success',
                'query': query,
                'total_matches': len(matches),
                'matches': matches
            }, indent=2)

        except Exception as e:
            return json.dumps({
                'status': 'error',
                'error': str(e)
            }, indent=2)

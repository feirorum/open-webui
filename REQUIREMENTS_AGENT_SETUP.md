# Requirements Agent - Setup & Usage Guide

A comprehensive **Spec-by-Example Requirements Extraction System** for Open WebUI that helps you capture, manage, and track software requirements through natural conversation.

## Overview

This system provides:

- **Natural Language Requirements Extraction** - Discuss your system, and the agent extracts structured requirements
- **Spec-by-Example / BDD Support** - Capture concrete examples using Given-When-Then scenarios
- **Structured Storage** - Requirements stored as markdown files with YAML frontmatter (git-friendly)
- **RAG Integration** - Automatically detect duplicates, conflicts, and gaps using semantic search
- **Requirement Management Tools** - Create, update, search, and overview requirements
- **Requirements Agent Character** - Dedicated AI assistant specialized in requirements engineering

## Components

### 1. Requirements Management Toolkit (`requirements_toolkit.py`)

Five powerful tools for managing requirements:

- `requirements_store` - Create or update requirements
- `requirements_index` - Rebuild the requirements index
- `requirements_overview` - Generate filtered summaries and tables
- `requirements_get` - Retrieve specific requirements by ID
- `requirements_search` - Search requirements by keyword

### 2. Requirements Agent Filter (`requirements_agent_filter.py`)

An intelligent filter that:
- Injects specialized system prompts for requirements extraction
- Auto-detects requirement-like statements in conversations
- Guides users through proper requirements capture
- Orchestrates the use of requirements tools

### 3. Requirements Storage Structure

```
backend/data/requirements/
  ├── README.md           # Documentation
  ├── index.json          # Quick lookup index
  ├── backlog/            # Proposed requirements
  ├── decided/            # Accepted requirements
  ├── implemented/        # Implemented requirements
  └── deprecated/         # Deprecated/rejected requirements
```

Each requirement is a markdown file with YAML frontmatter:

```markdown
---
id: REQ-001
title: User can log in with email and password
status: proposed
type: functional
priority: high
area: authentication
created_at: 2025-11-18T10:30:00Z
updated_at: 2025-11-18T10:30:00Z
source_conversations:
  - convo_id: chat-2025-11-18
    message_ids: ["msg_1", "msg_2"]
examples:
  - id: EX-001
    description: Successful login
    status: draft
---

## Summary

As a registered user, I want to log in with my email and password so that I can access my account securely.

## Details

- Password must be at least 10 characters
- Account locks after 5 failed attempts within 10 minutes
- Support "Remember me" functionality

## Examples (Spec-by-Example / BDD)

### EX-001: Successful login

\`\`\`gherkin
Scenario: User logs in successfully
  Given a registered user with email "user@example.com"
  And a valid password
  When they submit the login form with correct credentials
  Then they should be redirected to their dashboard
  And their last-login timestamp should be updated
\`\`\`
```

## Installation

### Step 1: Install the Requirements Toolkit

1. **Navigate to Open WebUI** → **Workspace** → **Tools**
2. Click **"+ Create New Tool"** or **"Import Tool"**
3. Copy the contents of `requirements_toolkit.py`
4. Paste into the tool editor
5. Click **"Save"**

The tool will automatically:
- Create the `backend/data/requirements/` folder structure
- Generate a `README.md` and `index.json`
- Set up subfolders for different requirement statuses

### Step 2: Install Dependencies

The toolkit requires:
- `pyyaml` - For YAML frontmatter parsing
- `python-slugify` - For generating URL-friendly filenames

#### Option A: Via Open WebUI Admin Panel

1. Go to **Admin Panel** → **Settings** → **Tools**
2. Add to the "Requirements" field in the tool's frontmatter:

```python
requirements: pyyaml, python-slugify
```

Open WebUI will automatically install these when the tool is loaded.

#### Option B: Manual Installation

If running Open WebUI locally:

```bash
cd backend
source venv/bin/activate  # or wherever your virtualenv is
pip install pyyaml python-slugify
```

### Step 3: Install the Requirements Agent Filter

1. **Navigate to** → **Admin Panel** → **Functions**
2. Click **"+ Create New Function"**
3. Select type: **"Filter"**
4. Copy the contents of `requirements_agent_filter.py`
5. Paste into the function editor
6. Configure the valves (settings):
   - `agent_mode`: Choose "assistant", "analyst", or "silent"
   - `enable_auto_extraction`: Auto-detect requirements (recommended: `true`)
   - `enable_conflict_detection`: Check for duplicates (recommended: `true`)
   - `require_confirmation`: Ask before storing (recommended: `true`)
7. Click **"Save"**
8. **Enable the function** globally or for specific models

### Step 4: Configure Valves (Optional)

#### Toolkit Valves

In **Workspace → Tools → Requirements Management Toolkit → Settings**:

- `requirements_base_path` - Where to store requirements (default: `backend/data/requirements`)
- `auto_index` - Auto-rebuild index after storing (default: `true`)
- `default_status` - Default status for new requirements (default: `proposed`)
- `id_prefix` - Prefix for requirement IDs (default: `REQ`)
- `enable_gherkin` - Support Gherkin scenarios (default: `true`)

#### Filter Valves

In **Admin Panel → Functions → Requirements Agent Filter → Settings**:

- `agent_mode` - Behavior mode:
  - `assistant` (helpful and collaborative - recommended for most users)
  - `analyst` (proactive extraction - best for requirements sessions)
  - `silent` (only responds when asked - minimal interference)
- `enable_auto_extraction` - Auto-detect requirements in conversation
- `enable_conflict_detection` - Check for duplicates/conflicts
- `require_confirmation` - Ask user before storing
- `enable_gherkin_prompts` - Encourage Given-When-Then scenarios

### Step 5: Enable Tools in Chat

1. Start a new chat
2. Click the **Tools** icon (🔧) in the chat interface
3. Enable **"Requirements Management Toolkit"**
4. The agent can now use all requirement tools

### Step 6: Configure RAG Integration (Recommended)

To enable semantic search and duplicate detection:

1. **Create a Knowledge Base**:
   - Go to **Workspace** → **Knowledge**
   - Click **"+ Create Knowledge Base"**
   - Name it "Requirements Database"
   - Description: "Structured requirements for [Your Project]"

2. **Add Requirements Folder**:
   - Click on your new Knowledge Base
   - Click **"+ Add Files"** or **"Add from Path"**
   - Add files from: `backend/data/requirements/`
   - Or manually upload `.md` files from the requirements folders

3. **Link Knowledge Base to Model**:
   - Start a chat
   - Click **Knowledge** icon
   - Select "Requirements Database"
   - Now the LLM can semantically search requirements

4. **Set up Auto-Sync** (Optional):
   - Configure periodic re-indexing of the requirements folder
   - Or manually re-upload when requirements change
   - Future enhancement: Auto-sync via webhook/file watcher

## Usage

### Basic Workflow

#### 1. Start a Requirements Session

Simply start chatting about your system:

```
User: "Let's talk about the login feature for our app."

Agent: "Great! I'd be happy to help capture requirements for the login feature.
Could you tell me more about:
- Who will be logging in? (end users, admins, etc.)
- What authentication methods do you want to support?
- Are there any specific security requirements?"
```

#### 2. Discuss Requirements Naturally

```
User: "Users should be able to log in with email and password.
After 5 failed attempts, lock the account for 15 minutes."

Agent: "Excellent! I've identified a security requirement here. Let me structure this:

**Title**: User login with email/password and account lockout
**Area**: Authentication
**Type**: Functional with security constraints

**Summary**: As a registered user, I want to log in with my email and password,
with account protection against brute-force attacks.

**Details**:
- Support email + password authentication
- Lock account after 5 failed login attempts
- Lockout duration: 15 minutes

Would you like me to capture any specific examples or scenarios for this requirement?"
```

#### 3. Add Spec-by-Example Scenarios

```
User: "Yes, add scenarios for successful login and lockout."

Agent: "Perfect! Let me add Gherkin scenarios:

**Scenario 1: Successful Login**
Given a registered user with email "user@example.com"
When they enter correct credentials
Then they should see their dashboard
And last-login timestamp should update

**Scenario 2: Account Lockout**
Given a user has failed login 4 times
When they fail the 5th attempt
Then their account should be locked
And they should see 'Account locked for 15 minutes'

Shall I store this requirement now?"
```

#### 4. Store the Requirement

```
User: "Yes, store it."

Agent: [Calls requirements_store tool]

"✅ Requirement stored successfully!

- **ID**: REQ-001
- **File**: backlog/REQ-001-user-login-email-password-lockout.md
- **Status**: proposed

You can find it in the requirements backlog. Would you like to discuss more requirements?"
```

### Advanced Usage

#### Search Existing Requirements

```
User: "Show me all authentication requirements."

Agent: [Calls requirements_overview with filter_area="authentication"]

"Here are the authentication requirements:

| ID | Title | Status | Priority |
|---|---|---|---|
| REQ-001 | User login with email/password | proposed | high |
| REQ-003 | Password reset flow | accepted | medium |
| REQ-007 | Two-factor authentication | backlog | low |

Would you like details on any of these?"
```

#### Get Specific Requirement

```
User: "Show me REQ-003 in detail."

Agent: [Calls requirements_get with req_id="REQ-003"]

"**REQ-003: Password reset flow**

**Status**: accepted
**Priority**: medium
**Area**: authentication

**Summary**: As a user who forgot their password, I want to reset it securely
via email so I can regain access to my account.

**Details**:
- Send reset link to registered email
- Link expires after 1 hour
- Require email verification before allowing reset
- Log all reset attempts

**Examples**: [Shows Gherkin scenarios]

This requirement has been accepted and is ready for implementation."
```

#### Check for Duplicates

```
User: "We need a feature for users to log in."

Agent: [Searches existing requirements via RAG]

"I found an existing requirement that might be related:

**REQ-001: User login with email/password**
Status: proposed
Area: authentication

Is this the same requirement, or are you thinking of something different
(e.g., social login, SSO)?"
```

#### Generate Overview Reports

```
User: "Show me all high-priority requirements."

Agent: [Calls requirements_overview with filter_priority="high", format="markdown"]

[Displays markdown table of high-priority requirements grouped by area]
```

#### Update Existing Requirements

```
User: "Change REQ-001 status to accepted."

Agent: [Calls requirements_get to retrieve REQ-001, then requirements_store to update]

"✅ Updated REQ-001:
- Status changed: proposed → accepted
- File moved: backlog/ → decided/

The requirement is now ready for implementation planning."
```

## Configuration Examples

### Configuration 1: Strict Requirements Analyst

Best for: Formal requirements engineering, regulated industries

```python
# Filter Valves
agent_mode = "analyst"
enable_auto_extraction = True
enable_conflict_detection = True
require_confirmation = True
enable_gherkin_prompts = True

# Toolkit Valves
default_status = "proposed"
id_prefix = "REQ"
```

**Behavior**: Proactively extracts requirements, always confirms, enforces Gherkin.

### Configuration 2: Casual Assistant

Best for: Startup projects, rapid prototyping

```python
# Filter Valves
agent_mode = "assistant"
enable_auto_extraction = False
enable_conflict_detection = False
require_confirmation = False

# Toolkit Valves
default_status = "accepted"
id_prefix = "FEAT"
```

**Behavior**: Only extracts when asked, stores immediately without confirmation.

### Configuration 3: Silent Documentation

Best for: Background documentation, meeting notes

```python
# Filter Valves
agent_mode = "silent"
enable_auto_extraction = False

# Toolkit Valves
id_prefix = "DOC"
```

**Behavior**: Only responds to direct commands, doesn't interrupt conversation.

## RAG Integration Details

### How RAG Enhances Requirements Management

1. **Duplicate Detection**: Semantic similarity search finds related requirements even with different wording
2. **Conflict Identification**: Compares new requirements against existing ones for contradictions
3. **Context Awareness**: Recalls previous discussions and decisions
4. **Gap Analysis**: Identifies missing requirements in specific areas
5. **Traceability**: Links requirements to conversations, examples, and decisions

### Setting Up Vector Search

The requirements files are indexed by Open WebUI's vector database (Chroma, Qdrant, etc.).

**Best Practices**:
- Re-index after bulk requirement updates
- Use descriptive titles and summaries for better semantic search
- Tag requirements with areas/domains for filtering
- Include synonyms in requirement descriptions

### Querying with RAG

The agent automatically uses RAG when:
- User mentions keywords related to existing requirements
- Storing new requirements (checks for duplicates)
- User asks "Do we have a requirement for X?"
- User asks "Show me requirements about Y"

## Maintenance

### Rebuilding the Index

Manually rebuild when:
- You edit requirement files directly
- After bulk imports
- After deleting requirements

```
User: "Rebuild the requirements index."

Agent: [Calls requirements_index]

"✅ Index rebuilt:
- 47 requirements indexed
- Last updated: 2025-11-18T15:30:00Z
- Status breakdown:
  - proposed: 12
  - accepted: 18
  - implemented: 15
  - deprecated: 2"
```

### Backing Up Requirements

Since requirements are just markdown files:

```bash
# Backup
cd backend/data
tar -czf requirements-backup-$(date +%Y%m%d).tar.gz requirements/

# Restore
tar -xzf requirements-backup-20251118.tar.gz
```

### Git Integration

The requirements folder is git-friendly:

```bash
cd backend/data/requirements
git init
git add .
git commit -m "Initial requirements capture"
git remote add origin <your-repo>
git push
```

**Benefits**:
- Version history of requirements
- Track changes over time
- Collaborate on requirements
- Code review for requirements
- Branch-based requirement proposals

## Troubleshooting

### Tools Not Available in Chat

**Problem**: Requirements tools don't appear in the chat tools menu.

**Solution**:
1. Verify the tool is saved in **Workspace → Tools**
2. Refresh the chat page
3. Click the tools icon (🔧) and ensure it's toggled on

### Requirements Not Storing

**Problem**: Agent calls `requirements_store` but files aren't created.

**Solution**:
1. Check `requirements_base_path` valve - ensure it's writable
2. Verify Python dependencies: `pyyaml`, `python-slugify`
3. Check Open WebUI logs for permission errors
4. Try absolute path: `/home/user/open-webui/backend/data/requirements`

### Agent Not Extracting Requirements

**Problem**: Agent doesn't recognize requirement-like statements.

**Solution**:
1. Check Filter is enabled (Admin Panel → Functions)
2. Verify `agent_mode` is set to "analyst" or "assistant"
3. Set `enable_auto_extraction = True`
4. Use explicit language: "This is a requirement:", "User story:"

### RAG Not Finding Requirements

**Problem**: Duplicate detection and semantic search not working.

**Solution**:
1. Ensure Knowledge Base is created and linked to the chat
2. Re-upload/re-index requirements files in Knowledge Base
3. Check vector database is configured (Admin Settings → Database)
4. Verify requirements files are in the Knowledge Base file list

### Index Out of Sync

**Problem**: `requirements_overview` shows old/missing requirements.

**Solution**:
```
User: "Rebuild the requirements index with mode full."
```

Or manually:
1. Go to Workspace → Tools → Requirements Toolkit
2. Test the `requirements_index` function with `mode: "full"`

## Examples Repository

See the `/backend/data/requirements/examples/` folder for sample requirements showing:
- Different requirement types (functional, non-functional, constraints)
- Various Gherkin scenario styles
- User stories with acceptance criteria
- Complex multi-example requirements
- Linked/dependent requirements

## Best Practices

### Writing Good Requirements

1. **Use User Story Format**: "As a [role], I want [feature], so that [benefit]"
2. **Be Specific**: Avoid vague terms like "fast", "easy", "good UX"
3. **Include Examples**: Concrete scenarios make requirements testable
4. **Define Acceptance Criteria**: Clear pass/fail conditions
5. **One Concern Per Requirement**: Don't bundle multiple features

### Organizing Requirements

1. **Use Meaningful Areas**: Group by feature, domain, or subsystem
2. **Set Realistic Priorities**: Not everything can be "critical"
3. **Track Status Changes**: Move requirements through backlog → decided → implemented
4. **Link Related Requirements**: Reference dependencies in details

### Spec-by-Example Tips

1. **Focus on User Behavior**: Not implementation details
2. **Use Concrete Data**: Real examples, not "user X" or "value Y"
3. **Cover Edge Cases**: Happy path + error scenarios
4. **Keep Scenarios Focused**: One scenario = one behavior
5. **Make Scenarios Reviewable**: Non-technical stakeholders should understand

## Roadmap

### Phase 1: Basic Storage ✅
- Requirements toolkit with store/index/overview
- Basic filter for agent behavior
- File-based storage

### Phase 2: RAG Integration ✅
- Knowledge Base integration
- Semantic search
- Duplicate detection

### Phase 3: Conflict Detection (Planned)
- Automated conflict analysis
- Requirement dependency graph
- Impact analysis

### Phase 4: Advanced Views (Planned)
- Traceability matrices (Requirements ↔ Tests ↔ Code)
- Release planning views
- Requirement coverage reports
- Export to JIRA, GitHub Issues, etc.

## Support

For issues, questions, or contributions:
- Open an issue on the Open WebUI GitHub repository
- Tag with `requirements-agent`
- Include your configuration (valves) and Open WebUI version

## License

MIT License - Free to use, modify, and distribute.

---

**Happy Requirements Engineering! 🎯**

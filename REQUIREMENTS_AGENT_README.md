# Requirements Agent for Open WebUI

> **Extract, manage, and track software requirements through natural conversation using Spec-by-Example methodology**

A comprehensive RAG-powered requirements engineering system built as an Open WebUI extension. Turn informal discussions into structured, testable requirements with BDD scenarios.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Open WebUI](https://img.shields.io/badge/Open_WebUI-Compatible-blue)](https://github.com/open-webui/open-webui)

---

## ✨ Features

### 🤖 Conversational Requirements Extraction

- **Natural Language Input**: Discuss your system naturally; the agent structures the requirements
- **Smart Clarification**: Agent asks targeted questions to eliminate ambiguity
- **Context-Aware**: Remembers previous requirements and detects duplicates

### 📋 Spec-by-Example / BDD Support

- **Gherkin Scenarios**: Capture concrete examples using Given-When-Then format
- **Testable Requirements**: Every requirement can include executable scenarios
- **User Story Format**: "As a [user], I want [feature], so that [benefit]"

### 🗂️ Structured Storage

- **Git-Friendly Format**: Markdown files with YAML frontmatter
- **Version Control Ready**: Track requirement changes over time
- **Status Workflow**: proposed → accepted → implemented → deprecated
- **Organized by Area**: Group requirements by feature, domain, or component

### 🔍 RAG-Powered Intelligence

- **Semantic Search**: Find related requirements using vector similarity
- **Duplicate Detection**: Automatically identify overlapping requirements
- **Conflict Analysis**: Detect contradictions in acceptance criteria
- **Context Recall**: Reference previous decisions and discussions

### 🛠️ Powerful Tools

- **requirements_store**: Create/update requirements with full metadata
- **requirements_index**: Fast indexing of all requirements
- **requirements_overview**: Generate filtered summaries and tables
- **requirements_get**: Retrieve specific requirements by ID
- **requirements_search**: Keyword search across all requirements

---

## 📚 Documentation

- **[Quick Start Guide](REQUIREMENTS_QUICKSTART.md)** - Get running in 5 minutes
- **[Setup Guide](REQUIREMENTS_AGENT_SETUP.md)** - Complete installation and configuration
- **[Examples](REQUIREMENTS_EXAMPLES.md)** - Real-world requirement templates and best practices

---

## 🚀 Quick Start

### 1. Install (5 minutes)

```bash
# Clone or copy these files to your Open WebUI directory:
requirements_toolkit.py
requirements_agent_filter.py
```

**Via Open WebUI UI**:

1. **Workspace → Tools** → Create New Tool → Paste `requirements_toolkit.py`
2. **Admin → Functions** → Create New Function → Filter → Paste `requirements_agent_filter.py`
3. **Start a chat** → Enable "Requirements Management Toolkit"

**Dependencies**:
```bash
pip install pyyaml python-slugify
```

### 2. First Requirement (1 minute)

Start a chat and say:

```
Let's capture requirements for user authentication.
Users should log in with email and password.
After 5 failed attempts, lock the account for 15 minutes.
```

The agent will:
1. Extract the requirement
2. Ask clarifying questions
3. Generate Gherkin scenarios
4. Store as `REQ-001-user-login.md`

### 3. Query Requirements

```
Show me all authentication requirements
Find requirements about passwords
Show me REQ-001 in detail
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Open WebUI Chat                       │
│  (User discusses features, constraints, examples)            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Requirements Agent Filter                       │
│  • Injects system prompt for requirements extraction        │
│  • Detects requirement-like statements                       │
│  • Guides conversation towards structured capture           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Requirements Management Toolkit (Tools)            │
│                                                              │
│  requirements_store      → Create/update requirement files   │
│  requirements_index      → Rebuild search index              │
│  requirements_overview   → Generate summaries/tables         │
│  requirements_get        → Retrieve by ID                    │
│  requirements_search     → Keyword search                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Requirements Storage (File System)                │
│                                                              │
│  backend/data/requirements/                                  │
│    ├── README.md                                             │
│    ├── index.json          ← Quick lookup                    │
│    ├── backlog/            ← Proposed requirements           │
│    ├── decided/            ← Accepted requirements           │
│    ├── implemented/        ← Done requirements               │
│    └── deprecated/         ← Obsolete requirements           │
│                                                              │
│  Each requirement: YAML frontmatter + Markdown body          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Open WebUI Knowledge Base (RAG)                 │
│  • Vector embeddings of requirement files                    │
│  • Semantic similarity search                                │
│  • Duplicate detection via cosine similarity                 │
│  • Context retrieval for conflict detection                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📄 Requirement File Format

Each requirement is a markdown file with YAML frontmatter:

```yaml
---
id: REQ-001
title: User can log in with email and password
status: accepted
type: functional
priority: high
area: authentication
created_at: 2025-11-18T10:00:00Z
updated_at: 2025-11-18T14:30:00Z
source_conversations:
  - convo_id: chat-2025-11-18
    message_ids: ["msg_42", "msg_45"]
examples:
  - id: EX-001
    description: Successful login
    status: approved
---

## Summary

As a registered user, I want to log in with email and password
so that I can access my account securely.

## Details

- Password must be at least 10 characters
- Lock account after 5 failed attempts within 10 minutes
- Support "Remember me" functionality

## Examples (Spec-by-Example / BDD)

### EX-001: Successful login

```gherkin
Scenario: User logs in with valid credentials
  Given a registered user with email "user@example.com"
  When they enter correct credentials
  Then they should see their dashboard
  And last-login timestamp should update
```
```

---

## 🎯 Use Cases

### For Product Managers

- Capture user stories during stakeholder interviews
- Track requirement status (backlog → implementation → done)
- Generate requirement reports for documentation
- Ensure traceability from conversation to implementation

### For Business Analysts

- Extract acceptance criteria from meetings
- Detect conflicts between stakeholder requests
- Maintain a single source of truth for requirements
- Generate traceability matrices

### For Developers

- Understand requirements through concrete examples
- Reference Gherkin scenarios when writing tests
- Update requirement status as features are built
- Query requirements by area/feature during planning

### For QA Engineers

- Use Gherkin scenarios as test specifications
- Verify implementation against acceptance criteria
- Track which requirements have test coverage
- Reference examples when writing automated tests

### For Agile Teams

- Capture requirements incrementally during sprints
- Refine backlog items with Spec-by-Example
- Track requirement evolution over time (git history)
- Link requirements to conversations and decisions

---

## ⚙️ Configuration

### Agent Modes

Configure in **Admin Panel → Functions → Requirements Agent Filter → Valves**:

| Mode | Behavior | Best For |
|------|----------|----------|
| `assistant` | Helpful, waits for explicit requests | General use, mixed conversations |
| `analyst` | Proactive, auto-detects requirements | Dedicated requirements sessions |
| `silent` | Only responds when directly asked | Background mode, minimal interference |

### Toolkit Settings

Configure in **Workspace → Tools → Requirements Management Toolkit → Valves**:

| Setting | Default | Description |
|---------|---------|-------------|
| `requirements_base_path` | `backend/data/requirements` | Storage location |
| `auto_index` | `true` | Rebuild index after updates |
| `default_status` | `proposed` | Initial status for new requirements |
| `id_prefix` | `REQ` | Prefix for requirement IDs |
| `enable_gherkin` | `true` | Support BDD scenarios |

---

## 🔧 Advanced Features

### Conflict Detection

When enabled, the agent checks new requirements against existing ones:

```
User: "Users should be able to log in with username."

Agent: "⚠️ Potential conflict detected!

Existing requirement REQ-001 specifies login with email and password.
Your new requirement mentions username login.

Options:
1. Replace REQ-001 (email → username)
2. Extend REQ-001 (support both email and username)
3. Create alternative requirement REQ-005 (username as optional)

Which approach do you prefer?"
```

### Requirement Dependencies

Link related requirements in the details section:

```markdown
## Details

This requirement depends on:
- REQ-001 (User authentication)
- REQ-007 (Session management)

This requirement blocks:
- REQ-012 (User profile customization)
```

### Traceability

Track requirements back to source conversations:

```yaml
source_conversations:
  - convo_id: chat-2025-11-18-stakeholder-meeting
    message_ids: ["msg_42", "msg_45", "msg_48"]
  - convo_id: chat-2025-11-20-refinement
    message_ids: ["msg_103"]
```

---

## 🔄 Workflow

### Typical Requirement Lifecycle

```
1. DISCUSSION
   └─> User discusses feature/constraint
       └─> Agent asks clarifying questions

2. EXTRACTION
   └─> Agent structures requirement
       └─> User confirms/refines

3. EXAMPLES
   └─> Agent generates Gherkin scenarios
       └─> User validates/adds more examples

4. STORAGE
   └─> Requirement stored as proposed
       └─> File: backlog/REQ-XXX-title.md

5. REVIEW
   └─> Team reviews requirement
       └─> Status: proposed → accepted

6. IMPLEMENTATION
   └─> Development starts
       └─> Status: accepted → implemented
       └─> File moved to implemented/

7. MAINTENANCE
   └─> Requirement updated/deprecated as needed
       └─> Git tracks all changes
```

---

## 🤝 Integration with Other Tools

### Git / GitHub

```bash
cd backend/data/requirements
git init
git add .
git commit -m "Add authentication requirements"
git push
```

**Benefits**:
- Pull requests for requirement changes
- Code review for requirements
- Blame/history for requirement evolution
- Branch-based requirement proposals

### JIRA / Linear / GitHub Issues

Export requirements to issue trackers:

```python
# Future enhancement: Export tool
requirements_export(
    filter_status="accepted",
    format="jira",
    output="requirements.json"
)
```

### Test Frameworks

Use Gherkin scenarios directly in testing:

```python
# Cucumber, Behave, pytest-bdd
# Copy Gherkin from requirements files
```

### Documentation Generators

Generate requirement documentation:

```python
# Future enhancement: Documentation tool
requirements_generate_docs(
    format="markdown",
    group_by="area",
    include_examples=True
)
```

---

## 📊 Examples

See **[REQUIREMENTS_EXAMPLES.md](REQUIREMENTS_EXAMPLES.md)** for:

- Functional requirements with Gherkin scenarios
- Non-functional requirements (performance, security)
- Constraint requirements (compliance, regulations)
- User stories with acceptance criteria
- Best practices and anti-patterns

---

## 🛤️ Roadmap

### Phase 1: Basic Storage ✅
- [x] Requirements toolkit (store, index, overview)
- [x] Requirements agent filter
- [x] File-based storage
- [x] Documentation

### Phase 2: RAG Integration ✅
- [x] Knowledge Base integration guide
- [x] Semantic search support
- [x] Duplicate detection

### Phase 3: Advanced Analysis (Planned)
- [ ] Automated conflict detection algorithm
- [ ] Requirement dependency graph visualization
- [ ] Impact analysis (what breaks if we change X?)
- [ ] Coverage reports (requirements vs. tests)

### Phase 4: Integrations (Planned)
- [ ] Export to JIRA, Linear, GitHub Issues
- [ ] Import from existing tools
- [ ] Traceability matrix generator
- [ ] Real-time collaboration features

### Phase 5: AI Enhancements (Planned)
- [ ] Auto-generate Gherkin from natural language
- [ ] Suggest missing acceptance criteria
- [ ] Detect implicit requirements
- [ ] Requirement quality scoring

---

## 🧪 Testing

The requirements system is self-documenting! Use it to capture its own requirements:

```
User: "The requirements agent should detect duplicate requirements."

Agent: [Creates REQ-META-001 describing the duplication detection feature]
```

---

## 🤝 Contributing

Contributions welcome! This is an open-source extension to Open WebUI.

### How to Contribute

1. **Report Issues**: Found a bug? Open an issue with tag `requirements-agent`
2. **Suggest Features**: Have ideas? Create a feature request
3. **Submit Pull Requests**: Improve the toolkit, agent, or docs
4. **Share Examples**: Add your requirement templates to the examples

### Development Setup

```bash
# Clone Open WebUI
git clone https://github.com/open-webui/open-webui
cd open-webui

# Add requirements agent files
cp requirements_toolkit.py .
cp requirements_agent_filter.py .

# Install dependencies
cd backend
pip install pyyaml python-slugify

# Run Open WebUI
# Follow Open WebUI setup instructions
```

---

## 📜 License

MIT License - Free to use, modify, and distribute.

See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **Open WebUI Team** - For the extensible AI interface
- **BDD Community** - For Spec-by-Example and Gherkin methodology
- **Requirements Engineering Practitioners** - For best practices

---

## 📞 Support

- **Documentation**: [REQUIREMENTS_AGENT_SETUP.md](REQUIREMENTS_AGENT_SETUP.md)
- **Quick Start**: [REQUIREMENTS_QUICKSTART.md](REQUIREMENTS_QUICKSTART.md)
- **Examples**: [REQUIREMENTS_EXAMPLES.md](REQUIREMENTS_EXAMPLES.md)
- **Issues**: [Open WebUI GitHub Issues](https://github.com/open-webui/open-webui/issues) (tag: `requirements-agent`)

---

## 🎯 Philosophy

### Why Requirements Matter

Good requirements are:
- **Clear**: Everyone understands what's needed
- **Testable**: You can verify when it's done
- **Traceable**: You know why decisions were made
- **Valuable**: They solve real user problems

### Why Spec-by-Example?

Examples make requirements:
- **Concrete**: No ambiguity about expected behavior
- **Testable**: Examples become test cases
- **Collaborative**: Non-technical stakeholders can validate
- **Living Documentation**: Examples evolve with the system

### Why Conversational?

Requirements extraction should be:
- **Natural**: Discuss ideas freely, not fill forms
- **Iterative**: Refine through dialogue
- **Contextual**: AI remembers previous decisions
- **Efficient**: Capture requirements in real-time

---

**Built with ❤️ for better software through better requirements**

Made for [Open WebUI](https://github.com/open-webui/open-webui) | [Star on GitHub](https://github.com/open-webui/open-webui) | [Report Issue](https://github.com/open-webui/open-webui/issues)

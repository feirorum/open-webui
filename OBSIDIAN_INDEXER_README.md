# Obsidian Vault → Open WebUI RAG Indexer

A robust, incremental indexer that syncs your Obsidian vault into Open WebUI's RAG (Retrieval-Augmented Generation) system. This allows you to query your notes using AI-powered semantic search.

## Features

- **Incremental Indexing**: Only processes new or modified files since last run
- **Full Reindex Support**: Option to rebuild entire index from scratch
- **Dual Mode Operation**:
  - **Direct Mode**: Copies files directly to Open WebUI's docs directory
  - **API Mode**: Uses Open WebUI's REST API for proper file upload and indexing
- **Change Detection**: Uses file hashes and modification times to detect changes
- **State Tracking**: Maintains metadata about indexed files in `state.json`
- **Flexible Configuration**: Configure via JSON file or CLI arguments
- **Dry-Run Mode**: Preview changes without modifying anything
- **Comprehensive Logging**: Detailed output of what's happening
- **Pattern Matching**: Include/exclude files using glob patterns

## Installation

### Prerequisites

- Python 3.9 or higher
- Open WebUI instance (running locally or in Docker)
- Access to your Obsidian vault

### Install Dependencies

```bash
pip install -r requirements-indexer.txt
```

Or manually:

```bash
pip install requests
```

## Configuration

### Option 1: Using a Config File (Recommended)

Create `vault_indexer.config.json`:

```json
{
  "vault_root": "/home/user/Obsidian/MyVault",
  "docs_root": "/home/user/open-webui/backend/data/docs/vault",
  "state_file": "/home/user/Obsidian/MyVault/.vault-indexer/state.json",
  "include_patterns": ["**/*.md"],
  "exclude_patterns": [
    ".obsidian/**",
    "**/Templates/**",
    "**/.trash/**"
  ],
  "mode": "incremental"
}
```

### Option 2: Using CLI Arguments

```bash
python vault_indexer.py \
  --vault-root /home/user/Obsidian/MyVault \
  --docs-root /home/user/open-webui/backend/data/docs/vault \
  --mode incremental
```

### Configuration Options

| Option | Description | Required |
|--------|-------------|----------|
| `vault_root` | Path to your Obsidian vault | Yes |
| `docs_root` | Path to Open WebUI docs directory | Yes (direct mode) |
| `state_file` | Path to state tracking file | No (defaults to `{vault}/.vault-indexer/state.json`) |
| `include_patterns` | Glob patterns for files to include | No (defaults to `**/*.md`) |
| `exclude_patterns` | Glob patterns for files to exclude | No (defaults to `.obsidian/**`, `**/Templates/**`) |
| `mode` | Index mode: `incremental` or `full` | No (defaults to `incremental`) |
| `use_api` | Use API mode instead of direct file copy | No (defaults to `false`) |
| `api_url` | Open WebUI API base URL | Yes (if `use_api=true`) |
| `api_token` | Open WebUI API token | Yes (if `use_api=true`) |
| `knowledge_base_id` | Knowledge base ID for organizing docs | No |

## Usage

### Basic Usage

```bash
# Incremental index using config file
python vault_indexer.py --config vault_indexer.config.json

# Full reindex
python vault_indexer.py --config vault_indexer.config.json --mode full

# Dry run (see what would happen without making changes)
python vault_indexer.py --config vault_indexer.config.json --dry-run

# Verbose logging
python vault_indexer.py --config vault_indexer.config.json --verbose
```

### Direct Mode (File Copy)

This mode directly copies markdown files to Open WebUI's docs directory. Requires filesystem access.

```bash
python vault_indexer.py \
  --vault-root /vault \
  --docs-root /app/backend/data/docs/vault \
  --mode incremental
```

**Pros**: Simple, fast, no API required
**Cons**: May not trigger automatic reindexing in Open WebUI

### API Mode (Recommended)

This mode uses Open WebUI's REST API to upload and index files properly.

```bash
python vault_indexer.py \
  --vault-root /vault \
  --use-api \
  --api-url http://localhost:8080 \
  --api-token sk-your-token-here \
  --knowledge-base-id obsidian-vault \
  --mode incremental
```

**Pros**: Proper indexing, works remotely, triggers vector embedding
**Cons**: Requires API token, slightly slower

#### Getting an API Token

1. Open Open WebUI in your browser
2. Go to **Settings** → **Account** → **API Keys**
3. Click **Create new API key**
4. Copy the token and use it in your config

Alternatively, set it as an environment variable:

```bash
export OPEN_WEBUI_API_TOKEN="sk-your-token-here"
```

## Docker Integration

### Running Indexer Inside Open WebUI Container

1. Mount your vault into the container:

```yaml
# docker-compose.yml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    volumes:
      - ./data:/app/backend/data
      - /home/user/Obsidian/MyVault:/vault:ro  # Read-only mount
    # ...
```

2. Copy indexer into container:

```bash
docker cp vault_indexer.py open-webui:/app/vault_indexer.py
docker cp vault_indexer_docker.config.example.json open-webui:/app/vault_indexer.config.json
```

3. Run inside container:

```bash
docker exec open-webui python /app/vault_indexer.py --config /app/vault_indexer.config.json
```

### Running Indexer on Host (API Mode)

1. Create config with API settings:

```json
{
  "vault_root": "/home/user/Obsidian/MyVault",
  "use_api": true,
  "api_url": "http://localhost:3000",
  "api_token": "sk-your-token-here",
  "knowledge_base_id": "obsidian-vault",
  "mode": "incremental"
}
```

2. Run on host:

```bash
python vault_indexer.py --config vault_indexer.config.json
```

## Automation

### Using Cron (Linux/Mac)

Run incremental indexing every hour:

```bash
# Edit crontab
crontab -e

# Add this line
0 * * * * cd /path/to/open-webui && /usr/bin/python3 vault_indexer.py --config vault_indexer.config.json >> /var/log/vault_indexer.log 2>&1
```

### Using Systemd Timer

See `vault-indexer.service` and `vault-indexer.timer` examples in the repository.

1. Copy service files:

```bash
sudo cp vault-indexer.service /etc/systemd/system/
sudo cp vault-indexer.timer /etc/systemd/system/
```

2. Edit paths in the service files

3. Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vault-indexer.timer
sudo systemctl start vault-indexer.timer
```

4. Check status:

```bash
sudo systemctl status vault-indexer.timer
sudo journalctl -u vault-indexer.service -f
```

### Using Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 9 AM)
4. Action: Start a program
   - Program: `python.exe`
   - Arguments: `C:\path\to\vault_indexer.py --config C:\path\to\config.json`
   - Start in: `C:\path\to\open-webui`

## How It Works

### Incremental Indexing Algorithm

1. **Load State**: Read `state.json` containing metadata about previously indexed files
2. **Scan Vault**: Find all markdown files matching include/exclude patterns
3. **Detect Changes**: For each file:
   - If file is new → index it
   - If file hash/mtime changed → reindex it
   - If file unchanged → skip it
4. **Handle Deletions**: Remove files that exist in state but not in vault
5. **Update State**: Save updated metadata to `state.json`

### State File Structure

```json
{
  "version": 1,
  "last_full_index": "2025-11-20T12:00:00Z",
  "last_incremental_index": "2025-11-20T18:00:00Z",
  "files": {
    "notes/project-alpha/spec.md": {
      "source_mtime": "2025-11-20T17:59:00Z",
      "indexed_at": "2025-11-20T18:00:00Z",
      "doc_path": "notes/project-alpha/spec.md",
      "hash": "abc123...",
      "file_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

### Frontmatter Injection

By default, the indexer adds YAML frontmatter to each file:

```markdown
---
source_vault_path: notes/project-alpha/spec.md
indexed_at: 2025-11-20T18:00:00Z
---

# Original content here
```

This helps track the source of documents. Disable with `--no-frontmatter`.

## Use Cases

### 1. PARA Method + AI Assistance

Organize your Obsidian vault using PARA (Projects, Areas, Resources, Archives), then query it with AI:

```
User: What are the key decisions from the ProjectX meetings?
AI: [Searches indexed notes in projects/ProjectX/meetings/]
```

### 2. Learning System

Index your learning notes and ask questions:

```
User: What did I learn about transformer architecture last month?
AI: [Searches learnings/ folder with date filters]
```

### 3. Spec-by-Example

Keep specs in Obsidian, auto-index them, and have AI extract requirements:

```
User: Generate test cases for the user authentication spec
AI: [Reads specs/authentication.md and generates tests]
```

### 4. Knowledge Base

Build a personal knowledge base that's queryable via RAG:

```
User: What are my notes about Python async programming?
AI: [Searches all notes with semantic understanding]
```

## Troubleshooting

### Error: "vault_root must be specified"

**Solution**: Provide `--vault-root` argument or set it in config file.

### Error: "docs_root must be specified"

**Solution**: When using direct mode (not API), you must specify where to copy files.

### Error: "API URL and token required for API indexing"

**Solution**: When using `--use-api`, you must provide both `--api-url` and `--api-token`.

### Files Not Showing Up in Open WebUI

**Solutions**:
1. If using direct mode, check if Open WebUI automatically monitors the docs directory
2. Try API mode instead, which properly triggers indexing
3. Check Open WebUI logs for errors
4. Verify file permissions

### Incremental Index Not Detecting Changes

**Solution**:
- Run with `--mode full` to rebuild index
- Check if state file is writable
- Verify file modification times are updating

### Permission Denied Errors

**Solution**:
- Ensure indexer has read access to vault
- Ensure indexer has write access to docs directory or can call API
- Check Docker volume mount permissions

## Advanced Usage

### Custom Include/Exclude Patterns

```json
{
  "include_patterns": [
    "projects/**/*.md",
    "learnings/**/*.md",
    "resources/AI/**/*.md"
  ],
  "exclude_patterns": [
    ".obsidian/**",
    "**/Templates/**",
    "**/.trash/**",
    "**/Archive/**",
    "**/private/**",
    "**/*.excalidraw.md"
  ]
}
```

### Multiple Knowledge Bases

Index different parts of your vault to different knowledge bases:

```bash
# Index projects to one knowledge base
python vault_indexer.py \
  --vault-root /vault \
  --use-api \
  --api-url http://localhost:8080 \
  --api-token $TOKEN \
  --knowledge-base-id vault-projects \
  --include-patterns "projects/**/*.md"

# Index learnings to another
python vault_indexer.py \
  --vault-root /vault \
  --use-api \
  --api-url http://localhost:8080 \
  --api-token $TOKEN \
  --knowledge-base-id vault-learnings \
  --include-patterns "learnings/**/*.md"
```

### Filtering by Tags

To only index files with specific tags, you could preprocess with a script or modify the indexer to parse frontmatter.

## Future Enhancements

Potential improvements (not yet implemented):

- **Bi-directional sync**: Sync changes from Open WebUI back to Obsidian
- **Metadata extraction**: Parse frontmatter tags/metadata for better filtering
- **Image support**: Index images referenced in notes
- **Link preservation**: Maintain Obsidian wiki-links in indexed docs
- **Conflict resolution**: Handle concurrent modifications
- **Web UI**: Simple web interface for monitoring indexing status
- **Webhook support**: Trigger indexing via webhook when vault changes

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- **Issues**: Report bugs or request features on GitHub Issues
- **Discussions**: Ask questions in GitHub Discussions
- **Docs**: See Open WebUI documentation for RAG configuration

## Acknowledgments

- Built for use with [Open WebUI](https://github.com/open-webui/open-webui)
- Designed to work with [Obsidian](https://obsidian.md) vaults
- Inspired by the PARA method and Building a Second Brain principles

---

**Happy indexing! May your notes be ever searchable. 🔍✨**

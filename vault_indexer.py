#!/usr/bin/env python3
"""
Obsidian Vault → Open WebUI RAG Indexer (Incremental)

This script indexes an Obsidian vault into Open WebUI's RAG system,
supporting incremental updates to only process changed files.

Usage:
    python vault_indexer.py --config vault_indexer.config.json
    python vault_indexer.py --vault-root /vault --docs-root /docs/vault --mode incremental
    python vault_indexer.py --mode full --dry-run
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import fnmatch
import shutil
import requests
from dataclasses import dataclass, asdict


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class FileMetadata:
    """Metadata for a single indexed file."""
    source_mtime: str  # ISO 8601 timestamp
    indexed_at: str    # ISO 8601 timestamp
    doc_path: str      # Relative path in docs
    hash: str          # SHA256 content hash
    file_id: Optional[str] = None  # Open WebUI file ID (if using API)


@dataclass
class IndexerState:
    """Complete indexer state."""
    version: int
    last_full_index: Optional[str]
    last_incremental_index: Optional[str]
    files: Dict[str, FileMetadata]

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "last_full_index": self.last_full_index,
            "last_incremental_index": self.last_incremental_index,
            "files": {
                path: asdict(meta) for path, meta in self.files.items()
            }
        }

    @staticmethod
    def from_dict(data: dict) -> 'IndexerState':
        """Load from dictionary."""
        files = {}
        for path, meta_dict in data.get("files", {}).items():
            files[path] = FileMetadata(**meta_dict)

        return IndexerState(
            version=data.get("version", 1),
            last_full_index=data.get("last_full_index"),
            last_incremental_index=data.get("last_incremental_index"),
            files=files
        )


@dataclass
class IndexerConfig:
    """Configuration for the indexer."""
    vault_root: Path
    docs_root: Optional[Path]
    state_file: Path
    include_patterns: List[str]
    exclude_patterns: List[str]
    mode: str
    api_url: Optional[str] = None
    api_token: Optional[str] = None
    knowledge_base_id: Optional[str] = None
    use_api: bool = False
    add_frontmatter: bool = True
    dry_run: bool = False


# ============================================================================
# Utilities
# ============================================================================

def get_iso_timestamp() -> str:
    """Get current timestamp in ISO 8601 format with UTC timezone."""
    return datetime.now(timezone.utc).isoformat()


def get_file_mtime_iso(file_path: Path) -> str:
    """Get file modification time as ISO 8601 string."""
    mtime = file_path.stat().st_mtime
    return datetime.fromtimestamp(mtime, timezone.utc).isoformat()


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file content."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def matches_patterns(path: Path, patterns: List[str]) -> bool:
    """Check if path matches any of the glob patterns."""
    for pattern in patterns:
        # Use Path.match() for proper glob pattern matching including **
        if path.match(pattern):
            return True
    return False


def should_include_file(file_path: Path, vault_root: Path,
                       include_patterns: List[str],
                       exclude_patterns: List[str]) -> bool:
    """Determine if a file should be included in indexing."""
    relative_path = file_path.relative_to(vault_root)

    # Check exclude patterns first
    if exclude_patterns and matches_patterns(relative_path, exclude_patterns):
        return False

    # Check include patterns
    if include_patterns:
        return matches_patterns(relative_path, include_patterns)

    return True


def add_frontmatter_to_content(content: str, source_path: str, indexed_at: str) -> str:
    """Add YAML frontmatter to markdown content if not present."""
    # Check if content already has frontmatter
    if content.startswith("---\n"):
        return content

    frontmatter = f"""---
source_vault_path: {source_path}
indexed_at: {indexed_at}
---

"""
    return frontmatter + content


# ============================================================================
# State Management
# ============================================================================

class StateManager:
    """Manages indexer state persistence."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.logger = logging.getLogger(__name__)

    def load_state(self) -> IndexerState:
        """Load state from file, or return empty state if not exists."""
        if not self.state_file.exists():
            self.logger.info(f"No existing state file at {self.state_file}, starting fresh")
            return IndexerState(
                version=1,
                last_full_index=None,
                last_incremental_index=None,
                files={}
            )

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            state = IndexerState.from_dict(data)
            self.logger.info(f"Loaded state with {len(state.files)} files")
            return state
        except Exception as e:
            self.logger.error(f"Failed to load state file: {e}")
            self.logger.warning("Starting with empty state")
            return IndexerState(
                version=1,
                last_full_index=None,
                last_incremental_index=None,
                files={}
            )

    def save_state(self, state: IndexerState) -> None:
        """Save state to file."""
        # Ensure parent directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved state to {self.state_file}")
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            raise


# ============================================================================
# File Operations
# ============================================================================

class FileIndexer:
    """Handles indexing of individual files."""

    def __init__(self, config: IndexerConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def scan_vault(self) -> List[Path]:
        """Scan vault and return list of files to consider for indexing."""
        files = []
        vault_root = self.config.vault_root

        for file_path in vault_root.rglob("*"):
            if not file_path.is_file():
                continue

            if should_include_file(
                file_path,
                vault_root,
                self.config.include_patterns,
                self.config.exclude_patterns
            ):
                files.append(file_path)

        self.logger.info(f"Found {len(files)} files in vault")
        return files

    def get_relative_path(self, file_path: Path) -> str:
        """Get relative path from vault root."""
        return file_path.relative_to(self.config.vault_root).as_posix()

    def needs_reindex(self, file_path: Path, existing_meta: Optional[FileMetadata]) -> bool:
        """Determine if a file needs reindexing."""
        if existing_meta is None:
            return True

        # Check file hash
        current_hash = compute_file_hash(file_path)
        if current_hash != existing_meta.hash:
            return True

        # Check mtime as fallback
        current_mtime = get_file_mtime_iso(file_path)
        if current_mtime != existing_meta.source_mtime:
            return True

        return False

    def index_file_direct(self, file_path: Path) -> FileMetadata:
        """Index a file by copying to docs directory."""
        relative_path = self.get_relative_path(file_path)
        doc_path = relative_path

        if self.config.docs_root is None:
            raise ValueError("docs_root must be specified for direct file indexing")

        target_path = self.config.docs_root / doc_path

        # Read content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add frontmatter if enabled
        if self.config.add_frontmatter:
            indexed_at = get_iso_timestamp()
            content = add_frontmatter_to_content(content, relative_path, indexed_at)
        else:
            indexed_at = get_iso_timestamp()

        # Write to target
        if not self.config.dry_run:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.debug(f"Wrote file to {target_path}")

        # Create metadata
        metadata = FileMetadata(
            source_mtime=get_file_mtime_iso(file_path),
            indexed_at=indexed_at,
            doc_path=doc_path,
            hash=compute_file_hash(file_path)
        )

        return metadata

    def index_file_api(self, file_path: Path) -> FileMetadata:
        """Index a file using Open WebUI API."""
        if not self.config.api_url or not self.config.api_token:
            raise ValueError("API URL and token required for API indexing")

        relative_path = self.get_relative_path(file_path)

        # Read content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add frontmatter if enabled
        if self.config.add_frontmatter:
            indexed_at = get_iso_timestamp()
            content = add_frontmatter_to_content(content, relative_path, indexed_at)
        else:
            indexed_at = get_iso_timestamp()

        if self.config.dry_run:
            # In dry-run mode, just create metadata without API call
            metadata = FileMetadata(
                source_mtime=get_file_mtime_iso(file_path),
                indexed_at=indexed_at,
                doc_path=relative_path,
                hash=compute_file_hash(file_path),
                file_id=f"dry-run-{relative_path}"
            )
            return metadata

        # Upload file to Open WebUI
        try:
            # Step 1: Upload file
            headers = {"Authorization": f"Bearer {self.config.api_token}"}
            files = {
                'file': (file_path.name, content.encode('utf-8'), 'text/markdown')
            }

            upload_url = f"{self.config.api_url}/api/files/"
            response = requests.post(upload_url, headers=headers, files=files)
            response.raise_for_status()

            file_data = response.json()
            file_id = file_data.get('id')

            self.logger.debug(f"Uploaded file {relative_path} -> {file_id}")

            # Step 2: Process file for RAG indexing
            if self.config.knowledge_base_id:
                process_url = f"{self.config.api_url}/api/retrieval/process/file"
                process_data = {
                    "file_id": file_id,
                    "collection_name": self.config.knowledge_base_id
                }
                response = requests.post(process_url, headers=headers, json=process_data)
                response.raise_for_status()
                self.logger.debug(f"Processed file {file_id} into collection {self.config.knowledge_base_id}")

            # Create metadata
            metadata = FileMetadata(
                source_mtime=get_file_mtime_iso(file_path),
                indexed_at=indexed_at,
                doc_path=relative_path,
                hash=compute_file_hash(file_path),
                file_id=file_id
            )

            return metadata

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API error indexing {relative_path}: {e}")
            raise

    def index_file(self, file_path: Path) -> FileMetadata:
        """Index a file using configured method (API or direct)."""
        if self.config.use_api:
            return self.index_file_api(file_path)
        else:
            return self.index_file_direct(file_path)

    def remove_file_direct(self, metadata: FileMetadata) -> None:
        """Remove a file from docs directory."""
        if self.config.docs_root is None:
            return

        target_path = self.config.docs_root / metadata.doc_path

        if target_path.exists():
            if not self.config.dry_run:
                target_path.unlink()
                self.logger.debug(f"Removed {target_path}")
            else:
                self.logger.debug(f"Would remove {target_path}")

    def remove_file_api(self, metadata: FileMetadata) -> None:
        """Remove a file using Open WebUI API."""
        if not metadata.file_id or self.config.dry_run:
            return

        try:
            headers = {"Authorization": f"Bearer {self.config.api_token}"}
            delete_url = f"{self.config.api_url}/api/files/{metadata.file_id}"
            response = requests.delete(delete_url, headers=headers)
            response.raise_for_status()
            self.logger.debug(f"Deleted file {metadata.file_id}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API error deleting {metadata.file_id}: {e}")

    def remove_file(self, metadata: FileMetadata) -> None:
        """Remove a file using configured method."""
        if self.config.use_api:
            self.remove_file_api(metadata)
        else:
            self.remove_file_direct(metadata)


# ============================================================================
# Main Indexer
# ============================================================================

class VaultIndexer:
    """Main indexer orchestrator."""

    def __init__(self, config: IndexerConfig):
        self.config = config
        self.state_manager = StateManager(config.state_file)
        self.file_indexer = FileIndexer(config)
        self.logger = logging.getLogger(__name__)

    def run_full_index(self) -> None:
        """Run a full reindex of the vault."""
        self.logger.info("Starting FULL index")

        # Load existing state
        state = self.state_manager.load_state()

        # Scan all files
        current_files = self.file_indexer.scan_vault()
        current_paths = {
            self.file_indexer.get_relative_path(f): f
            for f in current_files
        }

        # Track statistics
        stats = {
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'deleted': 0,
            'errors': 0
        }

        # Index all current files
        new_file_metadata = {}
        for relative_path, file_path in current_paths.items():
            try:
                self.logger.info(f"Indexing {relative_path}")
                metadata = self.file_indexer.index_file(file_path)
                new_file_metadata[relative_path] = metadata

                if relative_path in state.files:
                    stats['updated'] += 1
                else:
                    stats['new'] += 1

            except Exception as e:
                self.logger.error(f"Error indexing {relative_path}: {e}")
                stats['errors'] += 1

        # Find and remove deleted files
        for relative_path, metadata in state.files.items():
            if relative_path not in current_paths:
                try:
                    self.logger.info(f"Removing deleted file {relative_path}")
                    self.file_indexer.remove_file(metadata)
                    stats['deleted'] += 1
                except Exception as e:
                    self.logger.error(f"Error removing {relative_path}: {e}")
                    stats['errors'] += 1

        # Update state
        state.files = new_file_metadata
        state.last_full_index = get_iso_timestamp()
        state.last_incremental_index = state.last_full_index

        if not self.config.dry_run:
            self.state_manager.save_state(state)

        # Print summary
        self.logger.info("=" * 60)
        self.logger.info("FULL INDEX COMPLETE")
        self.logger.info(f"  New files:     {stats['new']}")
        self.logger.info(f"  Updated files: {stats['updated']}")
        self.logger.info(f"  Deleted files: {stats['deleted']}")
        self.logger.info(f"  Errors:        {stats['errors']}")
        self.logger.info(f"  Total indexed: {len(new_file_metadata)}")
        self.logger.info("=" * 60)

    def run_incremental_index(self) -> None:
        """Run an incremental index (only changed files)."""
        self.logger.info("Starting INCREMENTAL index")

        # Load existing state
        state = self.state_manager.load_state()

        # If no previous index, fall back to full
        if not state.last_incremental_index:
            self.logger.warning("No previous index found, running full index")
            return self.run_full_index()

        # Scan all files
        current_files = self.file_indexer.scan_vault()
        current_paths = {
            self.file_indexer.get_relative_path(f): f
            for f in current_files
        }

        # Track statistics
        stats = {
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'deleted': 0,
            'errors': 0
        }

        # Check each current file
        for relative_path, file_path in current_paths.items():
            existing_meta = state.files.get(relative_path)

            # Determine if reindex needed
            if self.file_indexer.needs_reindex(file_path, existing_meta):
                try:
                    if existing_meta:
                        self.logger.info(f"Reindexing modified file {relative_path}")
                        stats['updated'] += 1
                    else:
                        self.logger.info(f"Indexing new file {relative_path}")
                        stats['new'] += 1

                    metadata = self.file_indexer.index_file(file_path)
                    state.files[relative_path] = metadata

                except Exception as e:
                    self.logger.error(f"Error indexing {relative_path}: {e}")
                    stats['errors'] += 1
            else:
                stats['unchanged'] += 1
                self.logger.debug(f"Skipping unchanged file {relative_path}")

        # Find and remove deleted files
        deleted_paths = set(state.files.keys()) - set(current_paths.keys())
        for relative_path in deleted_paths:
            try:
                self.logger.info(f"Removing deleted file {relative_path}")
                self.file_indexer.remove_file(state.files[relative_path])
                del state.files[relative_path]
                stats['deleted'] += 1
            except Exception as e:
                self.logger.error(f"Error removing {relative_path}: {e}")
                stats['errors'] += 1

        # Update state
        state.last_incremental_index = get_iso_timestamp()

        if not self.config.dry_run:
            self.state_manager.save_state(state)

        # Print summary
        self.logger.info("=" * 60)
        self.logger.info("INCREMENTAL INDEX COMPLETE")
        self.logger.info(f"  New files:       {stats['new']}")
        self.logger.info(f"  Updated files:   {stats['updated']}")
        self.logger.info(f"  Unchanged files: {stats['unchanged']}")
        self.logger.info(f"  Deleted files:   {stats['deleted']}")
        self.logger.info(f"  Errors:          {stats['errors']}")
        self.logger.info(f"  Total indexed:   {len(state.files)}")
        self.logger.info("=" * 60)

    def run(self) -> None:
        """Run indexer based on configured mode."""
        if self.config.mode == "full":
            self.run_full_index()
        elif self.config.mode == "incremental":
            self.run_incremental_index()
        else:
            raise ValueError(f"Unknown mode: {self.config.mode}")


# ============================================================================
# CLI and Configuration
# ============================================================================

def load_config_file(config_path: Path) -> dict:
    """Load configuration from JSON file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Obsidian Vault → Open WebUI RAG Indexer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using config file
  python vault_indexer.py --config vault_indexer.config.json

  # Using CLI arguments
  python vault_indexer.py --vault-root /vault --docs-root /docs/vault --mode incremental

  # Full reindex with dry-run
  python vault_indexer.py --mode full --dry-run --verbose

  # Using API mode
  python vault_indexer.py --vault-root /vault --use-api --api-url http://localhost:8080 \\
      --api-token your-token --knowledge-base-id obsidian-vault
        """
    )

    parser.add_argument('--config', type=Path, help='Path to config JSON file')
    parser.add_argument('--vault-root', type=Path, help='Path to Obsidian vault root')
    parser.add_argument('--docs-root', type=Path, help='Path to Open WebUI docs root (for direct mode)')
    parser.add_argument('--state-file', type=Path, help='Path to state file')
    parser.add_argument('--mode', choices=['incremental', 'full'],
                       default='incremental', help='Index mode')
    parser.add_argument('--include-patterns', nargs='+', help='Glob patterns to include')
    parser.add_argument('--exclude-patterns', nargs='+', help='Glob patterns to exclude')
    parser.add_argument('--use-api', action='store_true', help='Use Open WebUI API instead of direct file copy')
    parser.add_argument('--api-url', help='Open WebUI API base URL')
    parser.add_argument('--api-token', help='Open WebUI API token')
    parser.add_argument('--knowledge-base-id', help='Knowledge base ID for API mode')
    parser.add_argument('--no-frontmatter', action='store_true',
                       help='Do not add frontmatter to files')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without writing')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')

    return parser.parse_args()


def build_config(args: argparse.Namespace) -> IndexerConfig:
    """Build IndexerConfig from CLI arguments and config file."""
    config_data = {}

    # Load config file if specified
    if args.config:
        config_data = load_config_file(args.config)

    # CLI arguments override config file
    vault_root = args.vault_root or config_data.get('vault_root')
    docs_root = args.docs_root or config_data.get('docs_root')
    state_file = args.state_file or config_data.get('state_file')

    if not vault_root:
        raise ValueError("vault_root must be specified via --vault-root or config file")

    vault_root = Path(vault_root).resolve()

    # Default state file location
    if not state_file:
        state_file = vault_root / '.vault-indexer' / 'state.json'
    else:
        state_file = Path(state_file)

    # docs_root handling
    if docs_root:
        docs_root = Path(docs_root).resolve()

    # Include/exclude patterns
    include_patterns = args.include_patterns or config_data.get('include_patterns', ['*.md', '**/*.md'])
    exclude_patterns = args.exclude_patterns or config_data.get('exclude_patterns',
                                                                ['.obsidian/**', 'Templates/**'])

    # API settings
    use_api = args.use_api or config_data.get('use_api', False)
    api_url = args.api_url or config_data.get('api_url')
    api_token = args.api_token or config_data.get('api_token') or os.getenv('OPEN_WEBUI_API_TOKEN')
    knowledge_base_id = args.knowledge_base_id or config_data.get('knowledge_base_id')

    # Validate configuration
    if use_api:
        if not api_url or not api_token:
            raise ValueError("When using API mode, api_url and api_token must be specified")
    else:
        if not docs_root:
            raise ValueError("When not using API mode, docs_root must be specified")

    return IndexerConfig(
        vault_root=vault_root,
        docs_root=docs_root,
        state_file=state_file,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        mode=args.mode,
        api_url=api_url,
        api_token=api_token,
        knowledge_base_id=knowledge_base_id,
        use_api=use_api,
        add_frontmatter=not args.no_frontmatter,
        dry_run=args.dry_run
    )


def setup_logging(verbose: bool) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point."""
    args = parse_arguments()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)

    try:
        # Build configuration
        config = build_config(args)

        # Log configuration
        logger.info("=" * 60)
        logger.info("Obsidian Vault → Open WebUI RAG Indexer")
        logger.info("=" * 60)
        logger.info(f"Vault root:     {config.vault_root}")
        if config.use_api:
            logger.info(f"Mode:           API")
            logger.info(f"API URL:        {config.api_url}")
            logger.info(f"Knowledge base: {config.knowledge_base_id or '(default)'}")
        else:
            logger.info(f"Mode:           Direct file copy")
            logger.info(f"Docs root:      {config.docs_root}")
        logger.info(f"State file:     {config.state_file}")
        logger.info(f"Index mode:     {config.mode.upper()}")
        logger.info(f"Dry run:        {config.dry_run}")
        logger.info("=" * 60)

        # Validate vault exists
        if not config.vault_root.exists():
            raise ValueError(f"Vault root does not exist: {config.vault_root}")

        # Run indexer
        indexer = VaultIndexer(config)
        indexer.run()

        logger.info("Indexing completed successfully")

    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

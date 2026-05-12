"""Metadata parsing utilities for Confluence and Jira documents."""

import re
from pathlib import Path
from typing import Any, Dict, Optional


def parse_jira_metadata(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Parse Jira issue metadata from markdown file.

    Args:
        file_path: Path to the Jira markdown file

    Returns:
        Dictionary containing issue metadata, or None if parsing fails
    """
    try:
        content = file_path.read_text(encoding='utf-8')

        # Extract issue key from filename or content
        issue_key_match = re.search(r'([A-Z]+-\d+)', file_path.name)
        if not issue_key_match:
            return None

        issue_key = issue_key_match.group(1)

        # Parse metadata from content
        metadata = {'issue_key': issue_key, 'file_path': str(file_path)}

        # Extract status
        status_match = re.search(r'\*\*Status\*\*:\s*(.+)', content)
        if status_match:
            metadata['status'] = status_match.group(1).strip()

        # Extract priority
        priority_match = re.search(r'\*\*Priority\*\*:\s*(.+)', content)
        if priority_match:
            metadata['priority'] = priority_match.group(1).strip()

        # Extract issue type
        type_match = re.search(r'\*\*Issue Type\*\*:\s*(.+)', content)
        if type_match:
            metadata['issue_type'] = type_match.group(1).strip()

        # Extract assignee
        assignee_match = re.search(r'\*\*Assignee\*\*:\s*(.+)', content)
        if assignee_match:
            metadata['assignee'] = assignee_match.group(1).strip()

        # Extract reporter
        reporter_match = re.search(r'\*\*Reporter\*\*:\s*(.+)', content)
        if reporter_match:
            metadata['reporter'] = reporter_match.group(1).strip()

        # Extract created date
        created_match = re.search(r'\*\*Created\*\*:\s*(.+)', content)
        if created_match:
            metadata['created'] = created_match.group(1).strip()

        # Extract updated date
        updated_match = re.search(r'\*\*Updated\*\*:\s*(.+)', content)
        if updated_match:
            metadata['updated'] = updated_match.group(1).strip()

        # Extract summary/title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['summary'] = title_match.group(1).strip()

        return metadata

    except Exception:
        return None


def parse_confluence_metadata(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Parse Confluence page metadata from markdown file.

    Args:
        file_path: Path to the Confluence markdown file

    Returns:
        Dictionary containing page metadata, or None if parsing fails
    """
    try:
        content = file_path.read_text(encoding='utf-8')

        metadata = {'file_path': str(file_path)}

        # Extract page title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()

        # Extract space key
        space_match = re.search(r'\*\*Space\*\*:\s*(.+)', content)
        if space_match:
            metadata['space'] = space_match.group(1).strip()

        # Extract page ID
        id_match = re.search(r'\*\*Page ID\*\*:\s*(\d+)', content)
        if id_match:
            metadata['page_id'] = id_match.group(1).strip()

        # Extract author
        author_match = re.search(r'\*\*Author\*\*:\s*(.+)', content)
        if author_match:
            metadata['author'] = author_match.group(1).strip()

        # Extract created date
        created_match = re.search(r'\*\*Created\*\*:\s*(.+)', content)
        if created_match:
            metadata['created'] = created_match.group(1).strip()

        # Extract last modified date
        modified_match = re.search(r'\*\*Last Modified\*\*:\s*(.+)', content)
        if modified_match:
            metadata['last_modified'] = modified_match.group(1).strip()

        # Extract version
        version_match = re.search(r'\*\*Version\*\*:\s*(\d+)', content)
        if version_match:
            metadata['version'] = version_match.group(1).strip()

        # Extract labels/tags
        labels_match = re.search(r'\*\*Labels\*\*:\s*(.+)', content)
        if labels_match:
            labels_str = labels_match.group(1).strip()
            metadata['labels'] = [l.strip() for l in labels_str.split(',') if l.strip()]

        return metadata

    except Exception:
        return None


def extract_metadata_from_directory(
    directory: Path,
    doc_type: str = 'all'
) -> Dict[str, Dict[str, Any]]:
    """
    Extract metadata from all documents in a directory.

    Args:
        directory: Directory to scan
        doc_type: Type of documents to extract ('jira', 'confluence', or 'all')

    Returns:
        Dictionary mapping file paths to metadata
    """
    results = {}

    if doc_type in ('jira', 'all'):
        jira_files = directory.glob('**/jira/**/*.md')
        for file_path in jira_files:
            metadata = parse_jira_metadata(file_path)
            if metadata:
                results[str(file_path)] = metadata

    if doc_type in ('confluence', 'all'):
        confluence_files = directory.glob('**/confluence/**/*.md')
        for file_path in confluence_files:
            metadata = parse_confluence_metadata(file_path)
            if metadata:
                results[str(file_path)] = metadata

    return results

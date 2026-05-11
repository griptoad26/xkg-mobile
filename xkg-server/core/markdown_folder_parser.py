#!/usr/bin/env python3
"""
Markdown Folder Parser - Parse markdown files from local folders and convert to knowledge graph nodes.
Supports Jekyll/Obsidian-style markdown with frontmatter.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class MarkdownDocument:
    """Represents a markdown document"""
    id: str
    title: str
    content: str
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    file_path: str = ""
    file_name: str = ""
    tags: List[str] = field(default_factory=list)
    created: str = ""
    modified: str = ""
    word_count: int = 0
    links: List[str] = field(default_factory=list)


class MarkdownFolderParser:
    """Parse markdown files from a folder"""
    
    # Common frontmatter delimiters
    FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    
    # Common markdown link patterns
    WIKILINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')
    MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    
    # Title extraction patterns
    H1_PATTERN = re.compile(r'^#\s+(.+)$', re.MULTILINE)
    TITLE_FROM_FILENAME = re.compile(r'[-_\s]+')
    
    def __init__(self):
        self.documents: Dict[str, MarkdownDocument] = {}
        self.wiki_links: Dict[str, List[str]] = {}
    
    def parse(self, folder_path: str) -> Dict:
        """
        Parse markdown files from a folder.
        
        Args:
            folder_path: Path to folder containing markdown files
            
        Returns:
            Dict with documents, stats, and errors
        """
        result = {
            'documents': [],
            'stats': {},
            'errors': []
        }
        
        if not os.path.exists(folder_path):
            result['errors'].append(f"Folder not found: {folder_path}")
            return result
        
        if not os.path.isdir(folder_path):
            result['errors'].append(f"Path is not a folder: {folder_path}")
            return result
        
        # Find all markdown files
        md_files = self._find_markdown_files(folder_path)
        
        if not md_files:
            result['errors'].append("No markdown files found in folder")
            return result
        
        print(f"Found {len(md_files)} markdown files")
        
        # Parse each file
        for filepath in md_files:
            try:
                self._parse_file(filepath, folder_path)
            except Exception as e:
                result['errors'].append(f"Error parsing {os.path.basename(filepath)}: {str(e)}")
        
        # Extract wikilinks between documents
        self._extract_links()
        
        # Convert documents to dict format
        for doc in self.documents.values():
            result['documents'].append(self._doc_to_dict(doc))
        
        # Count total links
        total_links = sum(len(links) for links in self.wiki_links.values())
        
        # Count all tags
        all_tags = set()
        for doc in self.documents.values():
            all_tags.update(doc.tags)
        
        result['stats'] = {
            'total_documents': len(self.documents),
            'total_tags': len(all_tags),
            'tags': sorted(all_tags),
            'total_links': total_links,
            'total_words': sum(doc.word_count for doc in self.documents.values())
        }
        
        return result
    
    def _find_markdown_files(self, directory: str) -> List[str]:
        """Find all markdown files in the directory"""
        files = []
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith(('.md', '.markdown')):
                    files.append(os.path.join(root, filename))
        return sorted(files)
    
    def _parse_file(self, filepath: str, base_path: str):
        """Parse a single markdown file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get file info
        file_path = os.path.relpath(filepath, base_path)
        file_name = os.path.basename(filepath)
        
        # Extract frontmatter
        frontmatter, body = self._extract_frontmatter(content)
        
        # Extract title
        title = self._extract_title(body, frontmatter, file_name)
        
        # Extract tags from frontmatter
        tags = self._extract_tags(frontmatter)
        
        # Extract tags from body (e.g., #hashtags)
        body_tags = self._extract_hashtags(body)
        tags.extend(body_tags)
        tags = list(set(tags))  # Remove duplicates
        
        # Get timestamps
        created = frontmatter.get('created', frontmatter.get('date', ''))
        modified = frontmatter.get('modified', frontmatter.get('updated', ''))
        
        if not created:
            try:
                stat = os.stat(filepath)
                created = datetime.fromtimestamp(stat.st_ctime).isoformat()
            except:
                created = ''
        
        if not modified:
            try:
                stat = os.stat(filepath)
                modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except:
                modified = ''
        
        # Generate ID
        doc_id = self._generate_id(file_path)
        
        # Count words
        word_count = len(body.split())
        
        # Create document
        doc = MarkdownDocument(
            id=doc_id,
            title=title,
            content=body,
            frontmatter=frontmatter,
            file_path=file_path,
            file_name=file_name,
            tags=tags,
            created=created,
            modified=modified,
            word_count=word_count
        )
        
        self.documents[doc_id] = doc
        
        # Extract wikilinks for later processing
        wikilinks = self.WIKILINK_PATTERN.findall(body)
        if wikilinks:
            self.wiki_links[doc_id] = wikilinks
    
    def _extract_frontmatter(self, content: str) -> tuple:
        """
        Extract YAML frontmatter from markdown content.
        
        Returns:
            Tuple of (frontmatter_dict, body_content)
        """
        match = self.FRONTMATTER_PATTERN.match(content)
        
        if not match:
            return {}, content
        
        fm_text = match.group(1)
        body = content[match.end():]
        
        # Parse YAML-like frontmatter
        frontmatter = {}
        current_key = None
        current_value = []
        
        lines = fm_text.split('\n')
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check for list items
            if line.startswith('- '):
                if current_key:
                    current_value.append(line[2:].strip())
                continue
            
            # Check for key: value pattern
            colon_idx = line.find(':')
            if colon_idx > 0:
                # Save previous key-value if exists
                if current_key:
                    if len(current_value) == 1:
                        frontmatter[current_key] = current_value[0]
                    elif current_value:
                        frontmatter[current_key] = current_value
                    current_value = []
                
                # Start new key
                key = line[:colon_idx].strip()
                value = line[colon_idx + 1:].strip()
                
                if value:
                    frontmatter[key] = value
                else:
                    current_key = key
        
        # Save last key-value
        if current_key and current_value:
            if len(current_value) == 1:
                frontmatter[current_key] = current_value[0]
            else:
                frontmatter[current_key] = current_value
        
        return frontmatter, body
    
    def _extract_title(self, body: str, frontmatter: Dict, filename: str) -> str:
        """Extract title from frontmatter, H1, or filename"""
        # Try frontmatter first
        for key in ['title', 'Title', 'name', 'Name']:
            if key in frontmatter:
                return str(frontmatter[key])
        
        # Try H1 heading
        h1_match = self.H1_PATTERN.search(body)
        if h1_match:
            return h1_match.group(1).strip()
        
        # Fall back to filename
        # Remove extension and convert to title case
        name = Path(filename).stem
        name = self.TITLE_FROM_FILENAME.sub(' ', name)
        return name.strip().title()
    
    def _extract_tags(self, frontmatter: Dict) -> List[str]:
        """Extract tags from frontmatter"""
        tags = []
        
        # Check common tag fields
        tag_fields = ['tags', 'tag', 'categories', 'category', 'topics', 'keywords']
        
        for field_name in tag_fields:
            if field_name in frontmatter:
                value = frontmatter[field_name]
                
                if isinstance(value, list):
                    tags.extend(str(v) for v in value)
                elif isinstance(value, str):
                    # Handle comma-separated tags
                    tags.extend([t.strip() for t in value.split(',')])
        
        return tags
    
    def _extract_hashtags(self, content: str) -> List[str]:
        """Extract #hashtags from markdown body"""
        hashtag_pattern = re.compile(r'#(\w+)')
        return hashtag_pattern.findall(content)
    
    def _generate_id(self, file_path: str) -> str:
        """Generate a unique ID for a document"""
        # Use relative path with slashes as ID
        return file_path.replace('/', '_').replace('\\', '_').replace(' ', '_')
    
    def _extract_links(self):
        """Extract links between documents for graph edges"""
        # This is called after all documents are parsed
        # The links are stored in self.wiki_links for use in to_graph_nodes
        pass
    
    def _doc_to_dict(self, doc: MarkdownDocument) -> Dict:
        """Convert MarkdownDocument to a dictionary"""
        return {
            'id': doc.id,
            'title': doc.title,
            'content': doc.content,
            'frontmatter': doc.frontmatter,
            'file_path': doc.file_path,
            'file_name': doc.file_name,
            'tags': doc.tags,
            'created': doc.created,
            'modified': doc.modified,
            'word_count': doc.word_count,
            'links': doc.links
        }


def markdown_to_graph_nodes(parse_result: Dict, wiki_links: Dict = None) -> Dict:
    """
    Convert markdown parse result to knowledge graph format.
    
    Args:
        parse_result: Result from MarkdownFolderParser.parse()
        wiki_links: Dictionary of wiki links between documents
        
    Returns:
        Dict with nodes and edges for knowledge graph
    """
    nodes = []
    edges = []
    
    for doc_data in parse_result.get('documents', []):
        # Create node
        node = {
            'id': f"markdown_{doc_data['id']}",
            'type': 'document',
            'label': doc_data['title'][:50] + ('...' if len(doc_data['title']) > 50 else ''),
            'title': doc_data['title'],
            'text': doc_data['content'][:1000] if doc_data['content'] else '',
            'full_content': doc_data['content'],
            'source': 'markdown',
            'created': doc_data['created'],
            'modified': doc_data['modified'],
            'tags': doc_data['tags'],
            'file_path': doc_data['file_path'],
            'word_count': doc_data['word_count']
        }
        nodes.append(node)
        
        # Create edges for tags as topics
        for tag in doc_data.get('tags', []):
            edges.append({
                'source': f"markdown_{doc_data['id']}",
                'target': f"topic_{tag.lower().replace(' ', '_')}",
                'type': 'tagged_with'
            })
        
        # Create edges for wikilinks
        if wiki_links and doc_data['id'] in wiki_links:
            for link_target in wiki_links[doc_data['id']]:
                # Normalize link target to match document ID format
                target_id = link_target.replace('/', '_').replace(' ', '_')
                edges.append({
                    'source': f"markdown_{doc_data['id']}",
                    'target': f"markdown_{target_id}",
                    'type': 'links_to'
                })
    
    return {
        'nodes': nodes,
        'edges': edges,
        'stats': parse_result.get('stats', {})
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python markdown_folder_parser.py <folder_path>")
        sys.exit(1)
    
    parser = MarkdownFolderParser()
    result = parser.parse(sys.argv[1])
    
    print(f"\nParsed {result['stats']['total_documents']} documents")
    print(f"Tags: {result['stats']['total_tags']}")
    print(f"Total links: {result['stats']['total_links']}")
    print(f"Total words: {result['stats']['total_words']}")
    
    if result['errors']:
        print(f"\nErrors: {len(result['errors'])}")
        for error in result['errors'][:5]:
            print(f"  - {error}")
    
    # Show first few documents
    for doc in result['documents'][:3]:
        print(f"\n--- {doc['title']} ---")
        print(f"File: {doc['file_path']}")
        print(f"Tags: {', '.join(doc['tags']) if doc['tags'] else 'None'}")
        print(f"Preview: {doc['content'][:200]}...")

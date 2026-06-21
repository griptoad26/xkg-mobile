#!/usr/bin/env python3
"""
Notion JSON Parser - Parse Notion export JSON files and convert to knowledge graph nodes.
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NotionPage:
    """Represents a Notion page from export"""
    id: str
    title: str
    content: str
    created_time: str
    last_edited_time: str
    properties: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    parent_type: str = "workspace"
    archived: bool = False
    url: str = ""
    children: List['NotionPage'] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class NotionParser:
    """Parse Notion export JSON files"""
    
    def __init__(self):
        self.pages: Dict[str, NotionPage] = {}
        self.root_pages: List[str] = []
    
    def parse(self, export_path: str) -> Dict:
        """
        Parse Notion export folder and extract all pages.
        
        Args:
            export_path: Path to Notion export folder containing JSON files
            
        Returns:
            Dict with pages, stats, and errors
        """
        result = {
            'pages': [],
            'stats': {},
            'errors': []
        }
        
        if not os.path.exists(export_path):
            result['errors'].append(f"Export path not found: {export_path}")
            return result
        
        # Find all JSON files
        json_files = self._find_json_files(export_path)
        
        if not json_files:
            result['errors'].append("No JSON files found in export folder")
            return result
        
        print(f"Found {len(json_files)} JSON files in Notion export")
        
        # First pass: load all pages
        for filepath in json_files:
            try:
                self._parse_file(filepath)
            except Exception as e:
                result['errors'].append(f"Error parsing {os.path.basename(filepath)}: {str(e)}")
        
        # Build parent-child relationships
        self._build_hierarchy()
        
        # Convert pages to dict format
        for page in self.pages.values():
            result['pages'].append(self._page_to_dict(page))
        
        # Count items by type
        content_blocks = sum(len(p.content) for p in self.pages.values())
        
        result['stats'] = {
            'total_pages': len(self.pages),
            'root_pages': len(self.root_pages),
            'content_blocks': content_blocks
        }
        
        return result
    
    def _find_json_files(self, directory: str) -> List[str]:
        """Find all JSON files in the export directory"""
        files = []
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith('.json'):
                    files.append(os.path.join(root, filename))
        return sorted(files)
    
    def _parse_file(self, filepath: str):
        """Parse a single Notion JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both single object and array formats
        if isinstance(data, list):
            for item in data:
                self._process_item(item)
        else:
            self._process_item(data)
    
    def _process_item(self, item: Dict):
        """Process a single Notion export item"""
        if not isinstance(item, dict):
            return
        
        item_type = item.get('type', '')
        
        if item_type == 'page':
            self._process_page(item)
        elif item_type == 'block':
            self._process_block(item)
    
    def _process_page(self, item: Dict) -> Optional[NotionPage]:
        """Process a page item"""
        page_id = item.get('id', '')
        
        if not page_id:
            return None
        
        # Extract title
        title = self._extract_title(item)
        
        # Extract properties
        properties = item.get('properties', {})
        
        # Extract timestamps
        created_time = item.get('created_time', '')
        last_edited_time = item.get('last_edited_time', '')
        
        # Extract parent info
        parent_id = None
        parent_type = item.get('parent_type', 'workspace')
        if 'parent' in item:
            parent = item['parent']
            if isinstance(parent, dict):
                parent_id = parent.get('id')
        
        # Check if archived
        archived = item.get('archived', False)
        
        # Get URL
        url = item.get('url', '')
        
        # Extract content from blocks
        content = self._extract_content(item)
        
        # Extract tags
        tags = self._extract_tags(properties)
        
        page = NotionPage(
            id=page_id,
            title=title,
            content=content,
            created_time=created_time,
            last_edited_time=last_edited_time,
            properties=properties,
            parent_id=parent_id,
            parent_type=parent_type,
            archived=archived,
            url=url,
            tags=tags
        )
        
        self.pages[page_id] = page
        
        # Check if root page (no parent or workspace parent)
        if not parent_id or parent_type == 'workspace':
            self.root_pages.append(page_id)
        
        return page
    
    def _process_block(self, item: Dict):
        """Process a block item (content block)"""
        # For now, we mainly care about pages
        # Content blocks are embedded in pages
        pass
    
    def _extract_title(self, item: Dict) -> str:
        """Extract title from a Notion item"""
        properties = item.get('properties', {})
        
        # Try 'title' property first
        if 'title' in properties:
            title_prop = properties['title']
            if isinstance(title_prop, list) and len(title_prop) > 0:
                first = title_prop[0]
                if isinstance(first, dict) and 'plain_text' in first:
                    return first['plain_text']
        
        # Try 'name' property
        if 'name' in properties:
            name_prop = properties['name']
            if isinstance(name_prop, list) and len(name_prop) > 0:
                first = name_prop[0]
                if isinstance(first, dict) and 'plain_text' in first:
                    return first['plain_text']
        
        # Try common title extraction
        for key in ['title', 'Name', 'name', 'title_text']:
            if key in properties:
                prop = properties[key]
                if isinstance(prop, list) and len(prop) > 0:
                    first = prop[0]
                    if isinstance(first, dict):
                        if 'plain_text' in first:
                            return first['plain_text']
                        if 'text' in first and isinstance(first['text'], dict):
                            return first['text'].get('content', '')
        
        # Use first text property found
        for key, value in properties.items():
            if isinstance(value, list) and len(value) > 0:
                first = value[0]
                if isinstance(first, dict):
                    if 'plain_text' in first:
                        return first['plain_text']
        
        # Return empty string if no title found
        return "Untitled"
    
    def _extract_content(self, item: Dict) -> str:
        """Extract text content from a Notion page"""
        content_parts = []
        
        # Get blocks
        blocks = item.get('blocks', [])
        if not blocks:
            # Try alternative key
            blocks = item.get('content', [])
        
        for block in blocks:
            block_text = self._extract_block_content(block)
            if block_text:
                content_parts.append(block_text)
        
        return '\n\n'.join(content_parts)
    
    def _extract_block_content(self, block: Dict) -> str:
        """Extract text from a single block"""
        if not isinstance(block, dict):
            return ""
        
        block_type = block.get('type', '')
        
        # Get the content based on type
        content_getters = {
            'paragraph': lambda: self._get_block_text(block, 'paragraph'),
            'heading_1': lambda: f"# {self._get_block_text(block, 'heading_1')}",
            'heading_2': lambda: f"## {self._get_block_text(block, 'heading_2')}",
            'heading_3': lambda: f"### {self._get_block_text(block, 'heading_3')}",
            'bulleted_list_item': lambda: f"- {self._get_block_text(block, 'bulleted_list_item')}",
            'numbered_list_item': lambda: f"1. {self._get_block_text(block, 'numbered_list_item')}",
            'to_do': lambda: self._get_todo_text(block),
            'toggle': lambda: f"**{self._get_block_text(block, 'toggle')}**",
            'quote': lambda: f"> {self._get_block_text(block, 'quote')}",
            'code': lambda: self._get_code_text(block),
            'divider': lambda: "---",
            'callout': lambda: self._get_callout_text(block),
            'image': lambda: f"![Image]({block.get('id', '')})",
            'bookmark': lambda: block.get('url', ''),
        }
        
        getter = content_getters.get(block_type)
        if getter:
            return getter()
        
        # Fallback: try to extract text from any text field
        return self._get_block_text(block, block_type)
    
    def _get_block_text(self, block: Dict, block_type: str) -> str:
        """Get text content from a block"""
        content = block.get(block_type, {})
        if isinstance(content, dict):
            rich_text = content.get('rich_text', [])
            if isinstance(rich_text, list):
                return ''.join(t.get('plain_text', '') for t in rich_text)
        return ""
    
    def _get_todo_text(self, block: Dict) -> str:
        """Get todo block text with checkbox"""
        text = self._get_block_text(block, 'to_do')
        checked = block.get('to_do', {}).get('checked', False)
        return f"[{'x' if checked else ' '}] {text}"
    
    def _get_code_text(self, block: Dict) -> str:
        """Get code block text with language"""
        content = block.get('code', {})
        code_text = content.get('rich_text', [])
        language = content.get('language', '')
        
        text = ''.join(t.get('plain_text', '') for t in code_text)
        if language:
            return f"```{language}\n{text}\n```"
        return f"```\n{text}\n```"
    
    def _get_callout_text(self, block: Dict) -> str:
        """Get callout block text"""
        content = block.get('callout', {})
        icon = content.get('icon', {})
        emoji = icon.get('emoji', '💡')
        text = self._get_block_text(block, 'callout')
        return f"{emoji} {text}"
    
    def _extract_tags(self, properties: Dict) -> List[str]:
        """Extract tags from page properties"""
        tags = []
        
        # Check for 'tags' or 'multi_select' property
        for key, value in properties.items():
            if isinstance(value, dict) and value.get('type') == 'multi_select':
                multi_select = value.get('multi_select', [])
                for item in multi_select:
                    if isinstance(item, dict):
                        tag = item.get('name', '')
                        if tag:
                            tags.append(tag)
        
        # Also check for 'select' property
        for key, value in properties.items():
            if isinstance(value, dict) and value.get('type') == 'select':
                select = value.get('select', {})
                if isinstance(select, dict):
                    tag = select.get('name', '')
                    if tag:
                        tags.append(tag)
        
        return tags
    
    def _build_hierarchy(self):
        """Build parent-child relationships between pages"""
        for page_id, page in self.pages.items():
            if page.parent_id and page.parent_id in self.pages:
                parent_page = self.pages[page.parent_id]
                parent_page.children.append(page)
                
                # Remove from root pages if it has a valid parent
                if page_id in self.root_pages:
                    self.root_pages.remove(page_id)
    
    def _page_to_dict(self, page: NotionPage) -> Dict:
        """Convert a NotionPage to a dictionary"""
        return {
            'id': page.id,
            'title': page.title,
            'content': page.content,
            'created_time': page.created_time,
            'last_edited_time': page.last_edited_time,
            'properties': page.properties,
            'parent_id': page.parent_id,
            'parent_type': page.parent_type,
            'archived': page.archived,
            'url': page.url,
            'tags': page.tags,
            'children_count': len(page.children),
            'hierarchy_level': self._get_hierarchy_level(page.id)
        }
    
    def _get_hierarchy_level(self, page_id: str, level: int = 0) -> int:
        """Get the hierarchy level of a page"""
        page = self.pages.get(page_id)
        if not page or not page.parent_id:
            return level
        return self._get_hierarchy_level(page.parent_id, level + 1)


def notion_to_graph_nodes(parse_result: Dict) -> Dict:
    """
    Convert Notion parse result to knowledge graph format.
    
    Args:
        parse_result: Result from NotionParser.parse()
        
    Returns:
        Dict with nodes and edges for knowledge graph
    """
    nodes = []
    edges = []
    
    for page_data in parse_result.get('pages', []):
        # Create node
        node = {
            'id': f"notion_{page_data['id']}",
            'type': 'document',
            'label': page_data['title'][:50] + ('...' if len(page_data['title']) > 50 else ''),
            'title': page_data['title'],
            'text': page_data['content'][:1000] if page_data['content'] else '',
            'full_content': page_data['content'],
            'source': 'notion',
            'created': page_data['created_time'],
            'last_edited': page_data['last_edited_time'],
            'url': page_data['url'],
            'tags': page_data['tags'],
            'archived': page_data['archived'],
            'hierarchy_level': page_data['hierarchy_level']
        }
        nodes.append(node)
        
        # Create edge to parent
        if page_data.get('parent_id'):
            edges.append({
                'source': f"notion_{page_data['parent_id']}",
                'target': f"notion_{page_data['id']}",
                'type': 'contains'
            })
        
        # Create edges for tags as topics
        for tag in page_data.get('tags', []):
            edges.append({
                'source': f"notion_{page_data['id']}",
                'target': f"topic_{tag.lower().replace(' ', '_')}",
                'type': 'tagged_with'
            })
    
    return {
        'nodes': nodes,
        'edges': edges,
        'stats': parse_result.get('stats', {})
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python notion_parser.py <export_path>")
        sys.exit(1)
    
    parser = NotionParser()
    result = parser.parse(sys.argv[1])
    
    print(f"\nParsed {result['stats']['total_pages']} pages")
    print(f"Root pages: {result['stats']['root_pages']}")
    
    if result['errors']:
        print(f"\nErrors: {len(result['errors'])}")
        for error in result['errors'][:5]:
            print(f"  - {error}")

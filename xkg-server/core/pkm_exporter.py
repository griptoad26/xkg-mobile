#!/usr/bin/env python3
"""
PKM Exporter - Export knowledge graph data as Markdown files with frontmatter
for Obsidian, Logseq, and Roam Research compatibility.
"""

import os
import json
import tempfile
import zipfile
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class PKMExporter:
    """Export knowledge graph data to PKM-compatible Markdown files"""
    
    # Source type mapping
    SOURCE_MAP = {
        'x': 'x',
        'tweet': 'x',
        'grok': 'grok',
        'grok_post': 'grok',
        'ai_openai': 'openai',
        'ai_anthropic': 'claude',
        'ai_google': 'gemini',
        'openai': 'openai',
        'claude': 'claude',
        'gemini': 'gemini',
        'action': 'x'
    }
    
    # Node type to folder mapping
    TYPE_FOLDERS = {
        'tweet': 'tweets',
        'grok': 'grok',
        'grok_conversation': 'conversations',
        'action': 'actions',
        'topic': 'topics',
        'conversation': 'conversations',
        'message': 'conversations'
    }
    
    def __init__(self):
        self.temp_dir = None
    
    def export(self, 
               graph_data: Dict,
               format: str = 'obsidian',
               include_edges: bool = True) -> bytes:
        """
        Export graph data to PKM format as a ZIP file.
        
        Args:
            graph_data: Dictionary containing:
                - graph: {nodes: [], edges: []}
                - actions: []
                - topics: {}
                - grok_conversations: []
                - ai_conversations: []
            format: 'obsidian', 'logseq', or 'markdown'
            include_edges: Whether to include bidirectional links
            
        Returns:
            ZIP file bytes
        """
        self.temp_dir = tempfile.mkdtemp()
        
        # Ensure all directories exist
        for folder in ['tweets', 'grok', 'actions', 'topics', 'conversations']:
            os.makedirs(os.path.join(self.temp_dir, folder), exist_ok=True)
        
        nodes = graph_data.get('graph', {}).get('nodes', [])
        edges = graph_data.get('graph', {}).get('edges', [])
        actions = graph_data.get('actions', [])
        topics = graph_data.get('topics', {})
        grok_conversations = graph_data.get('grok_conversations', [])
        ai_conversations = graph_data.get('ai_conversations', [])
        
        # Track links for bidirectional linking
        links_map = self._build_links_map(edges, nodes)
        
        # Export nodes
        exported_files = []
        for node in nodes:
            filename = self._export_node(node, format, links_map.get(node.get('id', ''), []))
            if filename:
                exported_files.append(filename)
        
        # Export actions
        for action in actions:
            filename = self._export_action(action, format)
            if filename:
                exported_files.append(filename)
        
        # Export topics
        for topic_name, topic_data in topics.items():
            filename = self._export_topic(topic_name, topic_data, format)
            if filename:
                exported_files.append(filename)
        
        # Export Grok conversations
        for conv in grok_conversations:
            filename = self._export_grok_conversation(conv, format)
            if filename:
                exported_files.append(filename)
        
        # Export AI conversations
        for conv in ai_conversations:
            filename = self._export_ai_conversation(conv, format)
            if filename:
                exported_files.append(filename)
        
        # Create ZIP file
        zip_buffer = self._create_zip(exported_files)
        
        # Cleanup
        self._cleanup()
        
        return zip_buffer
    
    def _build_links_map(self, edges: List[Dict], nodes: List[Dict]) -> Dict[str, List[str]]:
        """Build a map of node_id -> list of linked node_ids"""
        links_map = {}
        node_ids = {n.get('id') for n in nodes}
        
        for edge in edges:
            source = edge.get('source', '')
            target = edge.get('target', '')
            
            if source in node_ids and target in node_ids:
                if source not in links_map:
                    links_map[source] = []
                if target not in links_map[source]:
                    links_map[source].append(target)
        
        return links_map
    
    def _get_filename(self, node_id: str, node_type: str, title: str) -> str:
        """Generate a safe filename for a node"""
        # Determine folder based on type
        folder = self.TYPE_FOLDERS.get(node_type, 'misc')
        
        # Create safe filename from title or ID
        safe_title = self._sanitize_filename(title or node_id)
        
        return os.path.join(folder, f"{safe_title[:50]}.md")
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string to be safe for filenames"""
        # Remove or replace unsafe characters
        safe = name.replace('/', '-').replace('\\', '-')
        safe = safe.replace(':', '-').replace('*', '')
        safe = safe.replace('?', '').replace('"', '')
        safe = safe.replace('<', '').replace('>', '')
        safe = safe.replace('|', '-').replace('\n', ' ')
        safe = safe.replace('  ', ' ').strip()
        
        # If empty or too long, use a hash
        if not safe or len(safe) > 100:
            return f"node_{hash(name) % 100000}"
        
        return safe
    
    def _export_node(self, node: Dict, format: str, linked_nodes: List[str]) -> Optional[str]:
        """Export a single node as a Markdown file"""
        node_id = node.get('id', '')
        node_type = node.get('type', 'unknown')
        title = node.get('label', node.get('text', '')[:50])
        text = node.get('text', '')
        source = self.SOURCE_MAP.get(node.get('source', ''), 'x')
        
        # Get creation date if available
        created = node.get('created', node.get('timestamp', ''))
        if isinstance(created, str) and 'T' not in created and created:
            # Try to parse as date
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created = dt.isoformat()
            except:
                created = datetime.now().isoformat()
        elif not created:
            created = datetime.now().isoformat()
        
        # Get tags
        tags = node.get('tags', [])
        if not tags and node.get('topic'):
            tags = [node.get('topic')]
        
        # Get source-specific fields
        x_url = node.get('x_url', '')
        amazon_link = node.get('amazon_link', '')
        
        # Generate filename
        filename = self._get_filename(node_id, node_type, title)
        
        # Build wikilinks for linked nodes
        wikilinks = self._build_wikilinks(linked_nodes, format)
        
        # Create frontmatter and content
        content = self._create_frontmatter(
            title=title,
            node_type=node_type,
            source=source,
            created=created,
            tags=tags,
            x_url=x_url,
            amazon_link=amazon_link
        )
        
        # Add body content
        content += text + '\n\n'
        
        # Add wikilinks
        if wikilinks:
            content += '## Linked\n\n' + wikilinks + '\n'
        
        # Write file
        filepath = os.path.join(self.temp_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filename
    
    def _export_action(self, action: Dict, format: str) -> Optional[str]:
        """Export an action as a Markdown file"""
        action_id = action.get('id', '')
        text = action.get('text', '')
        priority = action.get('priority', 'medium')
        topic = action.get('topic', 'general')
        status = action.get('status', 'pending')
        source_type = self.SOURCE_MAP.get(action.get('source_type', 'x'), 'x')
        
        # Generate filename
        safe_text = self._sanitize_filename(text)
        filename = os.path.join('actions', f"{safe_text[:40]}.md")
        
        # Get dates
        created = action.get('created', datetime.now().isoformat())
        due = action.get('due', '')
        
        # Create content
        content = self._create_frontmatter(
            title=text[:50] + ('...' if len(text) > 50 else ''),
            node_type='action',
            source=source_type,
            created=created,
            tags=[topic, priority, status],
            due_date=due
        )
        
        # Add action details
        content += text + '\n\n'
        content += f"**Priority:** {priority}\n"
        content += f"**Status:** {status}\n"
        
        if due:
            content += f"**Due:** {due}\n"
        
        content += f"**Topic:** {topic}\n"
        
        # Write file
        filepath = os.path.join(self.temp_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filename
    
    def _export_topic(self, topic_name: str, topic_data: Dict, format: str) -> str:
        """Export a topic as a Markdown file"""
        filename = os.path.join('topics', f"topic-{self._sanitize_filename(topic_name)}.md")
        
        actions = topic_data.get('actions', [])
        tweets = topic_data.get('tweets', [])
        
        content = self._create_frontmatter(
            title=topic_name,
            node_type='topic',
            source='x',
            created=datetime.now().isoformat(),
            tags=[topic_name]
        )
        
        content += f"# {topic_name}\n\n"
        
        if actions:
            content += "## Actions\n\n"
            for action_id in actions[:20]:  # Limit to 20
                content += f"- [[{action_id}]]\n"
            content += '\n'
        
        if tweets:
            content += f"## Tweets ({len(tweets)} total)\n\n"
            for tweet_id in tweets[:10]:  # Limit to 10
                content += f"- [[tweet_{tweet_id}]]\n"
            content += '\n'
        
        filepath = os.path.join(self.temp_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filename
    
    def _export_grok_conversation(self, conv: Dict, format: str) -> str:
        """Export a Grok conversation as a Markdown file"""
        conv_id = conv.get('id', '')
        title = conv.get('title', f'Conversation {conv_id}')
        
        filename = os.path.join('conversations', f"conversation-{self._sanitize_filename(title)}.md")
        
        # Get messages
        messages = conv.get('messages', [])
        
        content = self._create_frontmatter(
            title=title,
            node_type='conversation',
            source='grok',
            created=datetime.now().isoformat(),
            tags=['grok', 'conversation']
        )
        
        content += f"# {title}\n\n"
        
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            text = msg.get('content', '')
            content += f"### {role.capitalize()}\n\n{text}\n\n---\n\n"
        
        filepath = os.path.join(self.temp_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filename
    
    def _export_ai_conversation(self, conv: Dict, format: str) -> str:
        """Export an AI conversation as a Markdown file"""
        conv_id = conv.get('id', '')
        title = conv.get('title', conv.get('name', f'AI Conversation {conv_id}'))
        
        # Determine source
        source = 'openai'  # Default
        if conv.get('source') == 'anthropic':
            source = 'claude'
        elif conv.get('source') == 'google':
            source = 'gemini'
        
        filename = os.path.join('conversations', f"conversation-{self._sanitize_filename(title)}.md")
        
        # Get messages
        messages = conv.get('messages', [])
        
        content = self._create_frontmatter(
            title=title,
            node_type='conversation',
            source=source,
            created=datetime.now().isoformat(),
            tags=['ai', 'conversation', source]
        )
        
        content += f"# {title}\n\n"
        
        for msg in messages:
            role = msg.get('role', 'unknown')
            content_parts = []
            
            # Handle different message content formats
            content = msg.get('content', '')
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        if part.get('type') == 'text':
                            content_parts.append(part.get('text', ''))
                        elif part.get('type') == 'tool_use':
                            content_parts.append(f"[Tool: {part.get('name')}]")
            else:
                content_parts.append(str(content))
            
            content += f"### {role.capitalize()}\n\n" + '\n'.join(content_parts) + "\n\n---\n\n"
        
        filepath = os.path.join(self.temp_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filename
    
    def _create_frontmatter(self,
                           title: str,
                           node_type: str,
                           source: str,
                           created: str,
                           tags: List[str] = None,
                           x_url: str = '',
                           amazon_link: str = '',
                           due_date: str = '') -> str:
        """Create YAML frontmatter for a Markdown file"""
        if tags is None:
            tags = []
        
        # Filter out empty tags
        tags = [str(t) for t in tags if t]
        
        lines = ['---']
        lines.append(f'title: "{title}"')
        lines.append(f'type: {node_type}')
        lines.append(f'source: {source}')
        lines.append(f'created: {created}')
        
        if tags:
            tags_str = ", ".join(f'"{t}"' for t in tags)
            lines.append(f'tags: [{tags_str}]')
        
        if x_url:
            lines.append(f'x_url: "{x_url}"')
        
        if amazon_link:
            lines.append(f'amazon_link: "{amazon_link}"')
        
        if due_date:
            lines.append(f'due: "{due_date}"')
        
        lines.append('---')
        lines.append('')  # Empty line after frontmatter
        
        return '\n'.join(lines) + '\n'
    
    def _build_wikilinks(self, linked_nodes: List[str], format: str) -> str:
        """Build wikilinks from a list of node IDs"""
        if not linked_nodes:
            return ''
        
        links = []
        for node_id in linked_nodes[:20]:  # Limit to 20 links
            # Convert node_id to a readable link title
            link_title = node_id.replace('_', ' ').replace('-', ' ')
            links.append(f'[[{node_id}]]')
        
        return '\n'.join(links)
    
    def _create_zip(self, filenames: List[str]) -> bytes:
        """Create a ZIP file from the exported files"""
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in filenames:
                filepath = os.path.join(self.temp_dir, filename)
                if os.path.exists(filepath):
                    zf.write(filepath, filename)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    def _cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)


class BytesIO:
    """Simple BytesIO replacement for Python < 3.11"""
    def __init__(self):
        self._buffer = bytearray()
    
    def write(self, data):
        self._buffer.extend(data)
    
    def seek(self, pos):
        pass
    
    def getvalue(self):
        return bytes(self._buffer)


# For Python 3.11+, use the standard library
import io
BytesIO = io.BytesIO


def export_pkm(graph_data: Dict, format: str = 'obsidian') -> bytes:
    """
    Convenience function to export graph data to PKM format.
    
    Args:
        graph_data: Dictionary containing graph data
        format: 'obsidian', 'logseq', or 'markdown'
        
    Returns:
        ZIP file bytes
    """
    exporter = PKMExporter()
    return exporter.export(graph_data, format=format)

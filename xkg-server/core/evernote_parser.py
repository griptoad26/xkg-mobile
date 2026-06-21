#!/usr/bin/env python3
"""
Evernote ENEX Parser - Parse Evernote export files and convert to knowledge graph nodes.
"""

import os
import re
from datetime import datetime
from xml.etree import ElementTree
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class EvernoteNote:
    """Represents an Evernote note from ENEX export"""
    id: str
    title: str
    content: str
    content_html: str
    created: str
    updated: str
    tags: List[str] = field(default_factory=list)
    author: str = ""
    source: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None


class HTMLToTextParser(HTMLParser):
    """Convert HTML content to plain text"""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.current_text = []
        self.skip_tag = False
        self.list_counter = 0
        self.in_list = False
        self.in_ordered_list = False
        self.in_pre = False
    
    def handle_starttag(self, tag: str, attrs: List[tuple]):
        if tag in ['script', 'style', 'head', 'meta', 'link']:
            self.skip_tag = True
            return
        
        if tag == 'br':
            if self.current_text:
                self.text_parts.append(''.join(self.current_text))
                self.current_text = []
            return
        
        if tag == 'p':
            if self.text_parts and self.text_parts[-1]:
                self.text_parts.append('')
            return
        
        if tag == 'li':
            if self.in_ordered_list:
                self.current_text.append(f"{self.list_counter}. ")
            else:
                self.current_text.append("• ")
            self.list_counter += 1
            return
        
        if tag == 'ul':
            self.in_list = True
            return
        
        if tag == 'ol':
            self.in_ordered_list = True
            self.list_counter = 1
            return
        
        if tag == 'pre':
            self.in_pre = True
            return
        
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if self.current_text:
                self.text_parts.append(''.join(self.current_text))
                self.current_text = []
            return
    
    def handle_endtag(self, tag: str):
        if tag in ['script', 'style', 'head', 'meta', 'link']:
            self.skip_tag = False
            return
        
        if tag in ['p', 'div', 'br']:
            if self.current_text:
                self.text_parts.append(''.join(self.current_text))
                self.current_text = []
            return
        
        if tag == 'li':
            if self.current_text:
                self.text_parts.append(''.join(self.current_text))
                self.current_text = []
            return
        
        if tag == 'ul':
            self.in_list = False
            self.text_parts.append('')
            return
        
        if tag == 'ol':
            self.in_ordered_list = False
            self.list_counter = 0
            self.text_parts.append('')
            return
        
        if tag == 'pre':
            self.in_pre = False
            if self.current_text:
                self.text_parts.append(''.join(self.current_text))
                self.current_text = []
            return
        
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if self.current_text:
                self.text_parts.append(''.join(self.current_text))
                self.current_text = []
            self.text_parts.append('')
            return
    
    def handle_data(self, data: str):
        if self.skip_tag:
            return
        
        clean_data = data.strip()
        if clean_data:
            self.current_text.append(clean_data)
    
    def get_text(self) -> str:
        if self.current_text:
            self.text_parts.append(''.join(self.current_text))
        
        # Join with appropriate spacing
        result = []
        for part in self.text_parts:
            part = part.strip()
            if part:
                result.append(part)
        
        return '\n\n'.join(result)


class ENEXParser:
    """Parse Evernote ENEX XML files"""
    
    def __init__(self):
        self.notes: List[EvernoteNote] = []
    
    def parse(self, enex_path: str) -> Dict:
        """
        Parse a ENEX file and extract notes.
        
        Args:
            enex_path: Path to ENEX file
            
        Returns:
            Dict with notes, stats, and errors
        """
        result = {
            'notes': [],
            'stats': {},
            'errors': []
        }
        
        if not os.path.exists(enex_path):
            result['errors'].append(f"File not found: {enex_path}")
            return result
        
        if not enex_path.lower().endswith('.enex'):
            result['errors'].append(f"File must have .enex extension: {enex_path}")
            return result
        
        try:
            # Parse XML
            tree = ElementTree.parse(enex_path)
            root = tree.getroot()
            
            # Check root element
            if root.tag != 'en-export':
                result['errors'].append("Invalid ENEX format: expected 'en-export' root element")
                return result
            
            # Process export info
            export_info = self._parse_export_info(root)
            
            # Process notes
            notes_count = 0
            for note_elem in root.findall('.//note'):
                try:
                    note = self._parse_note_element(note_elem)
                    if note:
                        self.notes.append(note)
                        notes_count += 1
                except Exception as e:
                    result['errors'].append(f"Error parsing note: {str(e)}")
            
            print(f"Parsed {notes_count} notes from ENEX file")
            
        except ElementTree.ParseError as e:
            result['errors'].append(f"XML parse error: {str(e)}")
            return result
        except Exception as e:
            result['errors'].append(f"Error reading file: {str(e)}")
            return result
        
        # Convert notes to dict format
        for note in self.notes:
            result['notes'].append(self._note_to_dict(note))
        
        # Extract all unique tags
        all_tags = set()
        for note in self.notes:
            all_tags.update(note.tags)
        
        result['stats'] = {
            'total_notes': len(self.notes),
            'total_tags': len(all_tags),
            'tags': sorted(all_tags)
        }
        
        return result
    
    def _parse_export_info(self, root: ElementTree.Element) -> Dict:
        """Parse export metadata"""
        info = {}
        
        export_info = root.find('.//export-info')
        if export_info is not None:
            export_date = export_info.find('export-date')
            if export_date is not None:
                info['export_date'] = export_date.text or ''
            
            application = export_info.find('application')
            if application is not None:
                info['application'] = application.text or ''
            
            version = export_info.find('application-version')
            if version is not None:
                info['version'] = version.text or ''
        
        return info
    
    def _parse_note_element(self, note_elem: ElementTree.Element) -> Optional[EvernoteNote]:
        """Parse a single note element"""
        # Get note ID
        guid = note_elem.find('guid')
        note_id = guid.text if guid is not None else ''
        
        # Get title
        title_elem = note_elem.find('title')
        title = title_elem.text if title_elem is not None else 'Untitled'
        
        # Get content
        content_elem = note_elem.find('content')
        content_html = ''
        if content_elem is not None and content_elem.text:
            content_html = content_elem.text
        
        # Convert HTML to plain text
        content = self._html_to_text(content_html)
        
        # Get timestamps
        created_elem = note_elem.find('created')
        created = created_elem.text if created_elem is not None else ''
        
        updated_elem = note_elem.find('updated')
        updated = updated_elem.text if updated_elem is not None else ''
        
        # Get tags
        tags = []
        for tag_elem in note_elem.findall('.//tag'):
            if tag_elem.text:
                tags.append(tag_elem.text)
        
        # Get author
        author_elem = note_elem.find('author')
        author = author_elem.text if author_elem is not None else ''
        
        # Get source (for web clippings)
        source_elem = note_elem.find('source')
        source = source_elem.text if source_elem is not None else ''
        
        # Get location if available
        latitude = None
        longitude = None
        altitude = None
        
        location_elem = note_elem.find('latitude')
        if location_elem is not None and location_elem.text:
            try:
                latitude = float(location_elem.text)
            except ValueError:
                pass
        
        location_elem = note_elem.find('longitude')
        if location_elem is not None and location_elem.text:
            try:
                longitude = float(location_elem.text)
            except ValueError:
                pass
        
        location_elem = note_elem.find('altitude')
        if location_elem is not None and location_elem.text:
            try:
                altitude = float(location_elem.text)
            except ValueError:
                pass
        
        return EvernoteNote(
            id=note_id,
            title=title,
            content=content,
            content_html=content_html,
            created=created,
            updated=updated,
            tags=tags,
            author=author,
            source=source,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude
        )
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML content to plain text"""
        if not html:
            return ''
        
        parser = HTMLToTextParser()
        try:
            # Wrap in a div if not already
            if '<html' not in html.lower() and '<body' not in html.lower():
                html = f'<div>{html}</div>'
            
            parser.feed(html)
            return parser.get_text()
        except Exception:
            # Fallback: strip tags manually
            clean = re.sub(r'<[^>]+>', ' ', html)
            clean = re.sub(r'\s+', ' ', clean)
            return clean.strip()
    
    def _note_to_dict(self, note: EvernoteNote) -> Dict:
        """Convert EvernoteNote to a dictionary"""
        return {
            'id': note.id,
            'title': note.title,
            'content': note.content,
            'content_html': note.content_html,
            'created': note.created,
            'updated': note.updated,
            'tags': note.tags,
            'author': note.author,
            'source': note.source,
            'latitude': note.latitude,
            'longitude': note.longitude,
            'altitude': note.altitude,
            'word_count': len(note.content.split()),
            'char_count': len(note.content)
        }


def enex_to_graph_nodes(parse_result: Dict) -> Dict:
    """
    Convert ENEX parse result to knowledge graph format.
    
    Args:
        parse_result: Result from ENEXParser.parse()
        
    Returns:
        Dict with nodes and edges for knowledge graph
    """
    nodes = []
    edges = []
    
    for note_data in parse_result.get('notes', []):
        # Create node
        node = {
            'id': f"evernote_{note_data['id']}",
            'type': 'note',
            'label': note_data['title'][:50] + ('...' if len(note_data['title']) > 50 else ''),
            'title': note_data['title'],
            'text': note_data['content'][:1000] if note_data['content'] else '',
            'full_content': note_data['content'],
            'source': 'evernote',
            'created': note_data['created'],
            'updated': note_data['updated'],
            'tags': note_data['tags'],
            'author': note_data['author'],
            'source_url': note_data['source'],
            'word_count': note_data.get('word_count', 0),
            'char_count': note_data.get('char_count', 0)
        }
        nodes.append(node)
        
        # Create edges for tags as topics
        for tag in note_data.get('tags', []):
            edges.append({
                'source': f"evernote_{note_data['id']}",
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
        print("Usage: python evernote_parser.py <export.enex>")
        sys.exit(1)
    
    parser = ENEXParser()
    result = parser.parse(sys.argv[1])
    
    print(f"\nParsed {result['stats']['total_notes']} notes")
    print(f"Tags: {result['stats']['total_tags']}")
    
    if result['errors']:
        print(f"\nErrors: {len(result['errors'])}")
        for error in result['errors'][:5]:
            print(f"  - {error}")
    
    # Show first few notes
    for note in result['notes'][:3]:
        print(f"\n--- {note['title']} ---")
        print(f"Content preview: {note['content'][:200]}...")

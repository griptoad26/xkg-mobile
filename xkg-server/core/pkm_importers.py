#!/usr/bin/env python3
"""
PKM Importers - Unified facade for importing from Notion, Evernote, and Markdown sources.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ImportResult:
    """Result of an import operation"""
    success: bool
    nodes: List[Dict]
    edges: List[Dict]
    stats: Dict[str, Any]
    errors: List[str]
    source_type: str
    source_path: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'success': self.success,
            'nodes': self.nodes,
            'edges': self.edges,
            'stats': self.stats,
            'errors': self.errors,
            'source_type': self.source_type,
            'source_path': self.source_path
        }


class PKMImporter:
    """
    Unified PKM importer facade for Notion, Evernote, and Markdown sources.
    """
    
    def __init__(self):
        self._notion_parser = None
        self._evernote_parser = None
        self._markdown_parser = None
    
    def _get_notion_parser(self):
        """Lazy import Notion parser"""
        if self._notion_parser is None:
            try:
                from .notion_parser import NotionParser, notion_to_graph_nodes
                self._notion_parser = NotionParser
                self._notion_to_graph = notion_to_graph_nodes
            except ImportError:
                raise ImportError("notion_parser module not found. Ensure the file exists.")
        return self._notion_parser
    
    def _get_evernote_parser(self):
        """Lazy import Evernote parser"""
        if self._evernote_parser is None:
            try:
                from .evernote_parser import ENEXParser, enex_to_graph_nodes
                self._evernote_parser = ENEXParser
                self._evernote_to_graph = enex_to_graph_nodes
            except ImportError:
                raise ImportError("evernote_parser module not found. Ensure the file exists.")
        return self._evernote_parser
    
    def _get_markdown_parser(self):
        """Lazy import Markdown parser"""
        if self._markdown_parser is None:
            try:
                from .markdown_folder_parser import MarkdownFolderParser, markdown_to_graph_nodes
                self._markdown_parser = MarkdownFolderParser
                self._markdown_to_graph = markdown_to_graph_nodes
            except ImportError:
                raise ImportError("markdown_folder_parser module not found. Ensure the file exists.")
        return self._markdown_parser
    
    def import_notion(self, export_path: str) -> ImportResult:
        """
        Import from Notion export.
        
        Args:
            export_path: Path to Notion export folder
            
        Returns:
            ImportResult with nodes and edges
        """
        try:
            parser_class = self._get_notion_parser()
            parser = parser_class()
            parse_result = parser.parse(export_path)
            
            if parse_result.get('errors'):
                return ImportResult(
                    success=False,
                    nodes=[],
                    edges=[],
                    stats={},
                    errors=parse_result['errors'],
                    source_type='notion',
                    source_path=export_path
                )
            
            # Convert to graph format
            from .notion_parser import notion_to_graph_nodes
            graph_data = notion_to_graph_nodes(parse_result)
            
            return ImportResult(
                success=True,
                nodes=graph_data['nodes'],
                edges=graph_data['edges'],
                stats=graph_data['stats'],
                errors=parse_result.get('errors', []),
                source_type='notion',
                source_path=export_path
            )
            
        except ImportError as e:
            return ImportResult(
                success=False,
                nodes=[],
                edges=[],
                stats={},
                errors=[str(e)],
                source_type='notion',
                source_path=export_path
            )
        except Exception as e:
            return ImportResult(
                success=False,
                nodes=[],
                edges=[],
                stats={},
                errors=[f"Import failed: {str(e)}"],
                source_type='notion',
                source_path=export_path
            )
    
    def import_evernote(self, enex_path: str) -> ImportResult:
        """
        Import from Evernote ENEX file.
        
        Args:
            enex_path: Path to ENEX file
            
        Returns:
            ImportResult with nodes and edges
        """
        try:
            parser_class = self._get_evernote_parser()
            parser = parser_class()
            parse_result = parser.parse(enex_path)
            
            if parse_result.get('errors'):
                return ImportResult(
                    success=False,
                    nodes=[],
                    edges=[],
                    stats={},
                    errors=parse_result['errors'],
                    source_type='evernote',
                    source_path=enex_path
                )
            
            # Convert to graph format
            from .evernote_parser import enex_to_graph_nodes
            graph_data = enex_to_graph_nodes(parse_result)
            
            return ImportResult(
                success=True,
                nodes=graph_data['nodes'],
                edges=graph_data['edges'],
                stats=graph_data['stats'],
                errors=parse_result.get('errors', []),
                source_type='evernote',
                source_path=enex_path
            )
            
        except ImportError as e:
            return ImportResult(
                success=False,
                nodes=[],
                edges=[],
                stats={},
                errors=[str(e)],
                source_type='evernote',
                source_path=enex_path
            )
        except Exception as e:
            return ImportResult(
                success=False,
                nodes=[],
                edges=[],
                stats={},
                errors=[f"Import failed: {str(e)}"],
                source_type='evernote',
                source_path=enex_path
            )
    
    def import_markdown_folder(self, folder_path: str) -> ImportResult:
        """
        Import from markdown files in a folder.
        
        Args:
            folder_path: Path to folder containing markdown files
            
        Returns:
            ImportResult with nodes and edges
        """
        try:
            parser_class = self._get_markdown_parser()
            parser = parser_class()
            parse_result = parser.parse(folder_path)
            
            if parse_result.get('errors'):
                return ImportResult(
                    success=False,
                    nodes=[],
                    edges=[],
                    stats={},
                    errors=parse_result['errors'],
                    source_type='markdown',
                    source_path=folder_path
                )
            
            # Convert to graph format
            from .markdown_folder_parser import markdown_to_graph_nodes
            graph_data = markdown_to_graph_nodes(parse_result)
            
            return ImportResult(
                success=True,
                nodes=graph_data['nodes'],
                edges=graph_data['edges'],
                stats=graph_data['stats'],
                errors=parse_result.get('errors', []),
                source_type='markdown',
                source_path=folder_path
            )
            
        except ImportError as e:
            return ImportResult(
                success=False,
                nodes=[],
                edges=[],
                stats={},
                errors=[str(e)],
                source_type='markdown',
                source_path=folder_path
            )
        except Exception as e:
            return ImportResult(
                success=False,
                nodes=[],
                edges=[],
                stats={},
                errors=[f"Import failed: {str(e)}"],
                source_type='markdown',
                source_path=folder_path
            )
    
    def merge_into_graph(self, 
                         existing_nodes: List[Dict], 
                         existing_edges: List[Dict],
                         import_result: ImportResult) -> tuple:
        """
        Merge imported nodes and edges into existing graph.
        
        Args:
            existing_nodes: Current graph nodes
            existing_edges: Current graph edges
            import_result: ImportResult to merge
            
        Returns:
            Tuple of (merged_nodes, merged_edges)
        """
        if not import_result.success:
            return existing_nodes, existing_edges
        
        # Track existing node IDs to avoid duplicates
        existing_node_ids = {n.get('id') for n in existing_nodes}
        existing_edge_set = {(e.get('source'), e.get('target'), e.get('type')) 
                           for e in existing_edges}
        
        # Merge nodes
        merged_nodes = list(existing_nodes)
        for node in import_result.nodes:
            if node.get('id') not in existing_node_ids:
                merged_nodes.append(node)
        
        # Merge edges
        merged_edges = list(existing_edges)
        for edge in import_result.edges:
            key = (edge.get('source'), edge.get('target'), edge.get('type'))
            if key not in existing_edge_set:
                merged_edges.append(edge)
        
        return merged_nodes, merged_edges


# Convenience functions

def import_notion(export_path: str) -> ImportResult:
    """Import from Notion export"""
    importer = PKMImporter()
    return importer.import_notion(export_path)


def import_evernote(enex_path: str) -> ImportResult:
    """Import from Evernote ENEX file"""
    importer = PKMImporter()
    return importer.import_evernote(enex_path)


def import_markdown_folder(folder_path: str) -> ImportResult:
    """Import from markdown folder"""
    importer = PKMImporter()
    return importer.import_markdown_folder(folder_path)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pkm_importers.py <command> <path>")
        print("\nCommands:")
        print("  notion <path>      - Import Notion export folder")
        print("  evernote <path>    - Import Evernote ENEX file")
        print("  markdown <path>    - Import markdown folder")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    path = sys.argv[2] if len(sys.argv) > 2 else ''
    
    if not path:
        print("Error: Path is required")
        sys.exit(1)
    
    importer = PKMImporter()
    
    if command == 'notion':
        result = importer.import_notion(path)
    elif command == 'evernote':
        result = importer.import_evernote(path)
    elif command == 'markdown':
        result = importer.import_markdown_folder(path)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    print(f"\nImport Result:")
    print(f"  Success: {result.success}")
    print(f"  Nodes: {len(result.nodes)}")
    print(f"  Edges: {len(result.edges)}")
    print(f"  Stats: {result.stats}")
    
    if result.errors:
        print(f"\nErrors: {len(result.errors)}")
        for error in result.errors[:5]:
            print(f"  - {error}")

"""
Semantic Search Module for X Knowledge Graph
Provides keyword and semantic search across tweets, Grok posts, AI conversations, and actions.
"""

import sqlite3
import json
import os
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict
import numpy as np

# Try to import sentence-transformers for semantic search
try:
    from sentence_transformers import SentenceTransformer
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False


@dataclass
class SearchResult:
    """Represents a single search result"""
    id: str
    type: str  # 'tweet', 'grok', 'ai_message', 'action', 'conversation'
    title: str
    content: str
    source: str  # 'x', 'grok', 'ai'
    score: float
    highlights: List[str] = None
    metadata: Dict = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'content': self.content,
            'source': self.source,
            'score': self.score,
            'highlights': self.highlights or [],
            'metadata': self.metadata or {}
        }


class SemanticSearchEngine:
    """
    Unified search engine supporting both keyword and semantic search.
    Uses SQLite for storing embeddings and fast lookups.
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), 'search_embeddings.db')
        self.embeddings_model = None
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
        self.items_indexed = 0
        
        # Initialize database
        self._init_database()
        
        # Load model if available
        if SEMANTIC_AVAILABLE:
            try:
                self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"Warning: Could not load sentence-transformers model: {e}")
                self.embeddings_model = None
    
    def _init_database(self):
        """Initialize SQLite database for embeddings storage"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables for embeddings and search index
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                text TEXT NOT NULL,
                source TEXT,
                embedding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_index (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                label TEXT,
                content TEXT NOT NULL,
                source TEXT,
                topics TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_search_type ON search_index(type)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_search_source ON search_index(source)
        ''')
        
        conn.commit()
        conn.close()
    
    def index_items(self, items: List[Dict], item_type: str, source: str = 'x'):
        """
        Index a list of items for search.
        
        Args:
            items: List of dictionaries containing 'id', 'text', 'label', etc.
            item_type: Type of items ('tweet', 'grok', 'action', 'ai_message', 'conversation')
            source: Source of items ('x', 'grok', 'ai')
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        indexed_count = 0
        
        for item in items:
            item_id = item.get('id', '')
            if not item_id:
                continue
            
            # Extract searchable text
            text = item.get('text', item.get('content', item.get('label', '')))
            label = item.get('label', item.get('title', text[:100]))
            topics = json.dumps(item.get('topics', item.get('topic', [])))
            metadata = json.dumps(item.get('metadata', {}))
            
            # Store in search index
            cursor.execute('''
                INSERT OR REPLACE INTO search_index 
                (id, type, label, content, source, topics, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (item_id, item_type, label[:200], text, source, topics, metadata))
            
            # Generate embedding if model is available
            if self.embeddings_model and text:
                try:
                    embedding = self.embeddings_model.encode(text)
                    cursor.execute('''
                        INSERT OR REPLACE INTO embeddings 
                        (id, type, text, source, embedding)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (item_id, item_type, text, source, embedding.tobytes()))
                    indexed_count += 1
                except Exception as e:
                    print(f"Warning: Could not embed item {item_id}: {e}")
        
        conn.commit()
        conn.close()
        
        self.items_indexed += indexed_count
        return indexed_count
    
    def keyword_search(
        self, 
        query: str, 
        item_types: List[str] = None,
        sources: List[str] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Perform keyword search across indexed items.
        
        Args:
            query: Search query string
            item_types: Filter by types ('tweet', 'grok', 'action', 'ai_message', 'conversation')
            sources: Filter by sources ('x', 'grok', 'ai')
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects sorted by relevance
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query with filters
        where_clauses = []
        params = []
        
        # Add full-text search on content and label
        search_terms = query.lower().split()
        for term in search_terms:
            where_clauses.append('(LOWER(content) LIKE ? OR LOWER(label) LIKE ?)')
            params.extend([f'%{term}%', f'%{term}%'])
        
        if item_types:
            placeholders = ','.join(['?' for _ in item_types])
            where_clauses.append(f'type IN ({placeholders})')
            params.extend(item_types)
        
        if sources:
            placeholders = ','.join(['?' for _ in sources])
            where_clauses.append(f'source IN ({placeholders})')
            params.extend(sources)
        
        where_str = ' AND '.join(where_clauses) if where_clauses else '1=1'
        
        cursor.execute(f'''
            SELECT id, type, label, content, source, topics, metadata
            FROM search_index
            WHERE {where_str}
            ORDER BY 
                CASE 
                    WHEN LOWER(label) LIKE LOWER(?) THEN 3
                    WHEN LOWER(content) LIKE LOWER(?) THEN 2
                    ELSE 1
                END,
                LENGTH(content) ASC
            LIMIT ?
        ''', params + [f'%{query}%', f'%{query}%', limit])
        
        results = []
        for row in cursor.fetchall():
            highlights = self._highlight_matches(row[3], query)
            results.append(SearchResult(
                id=row[0],
                type=row[1],
                title=row[2],
                content=row[3],
                source=row[4],
                score=self._calculate_keyword_score(row[3], query),
                highlights=highlights,
                metadata=json.loads(row[6]) if row[6] else {}
            ))
        
        conn.close()
        return results
    
    def semantic_search(
        self, 
        query: str, 
        item_types: List[str] = None,
        sources: List[str] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Perform semantic search using embeddings.
        
        Args:
            query: Search query string
            item_types: Filter by types
            sources: Filter by sources
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects sorted by similarity
        """
        if not self.embeddings_model:
            # Fallback to keyword search if embeddings not available
            return self.keyword_search(query, item_types, sources, limit)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Generate query embedding
        query_embedding = self.embeddings_model.encode(query)
        query_vector = query_embedding.tobytes()
        
        # Get items with embeddings
        where_clauses = ['embedding IS NOT NULL']
        params = []
        
        if item_types:
            placeholders = ','.join(['?' for _ in item_types])
            where_clauses.append(f't.type IN ({placeholders})')
            params.extend(item_types)
        
        if sources:
            placeholders = ','.join(['?' for _ in sources])
            where_clauses.append(f't.source IN ({placeholders})')
            params.extend(sources)
        
        where_str = ' AND '.join(where_clauses)
        
        cursor.execute(f'''
            SELECT t.id, t.type, t.label, t.content, t.source, t.topics, t.metadata,
                   e.embedding
            FROM search_index t
            JOIN embeddings e ON t.id = e.id
            WHERE {where_str}
        ''', params)
        
        results = []
        for row in cursor.fetchall():
            embedding = np.frombuffer(row[7], dtype=np.float32)
            similarity = self._cosine_similarity(query_embedding, embedding)
            
            results.append(SearchResult(
                id=row[0],
                type=row[1],
                title=row[2],
                content=row[3],
                source=row[4],
                score=similarity,
                highlights=[],
                metadata=json.loads(row[6]) if row[6] else {}
            ))
        
        # Sort by similarity and limit
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:limit]
        
        # Add keyword highlights
        for result in results:
            result.highlights = self._highlight_matches(result.content, query)
        
        conn.close()
        return results
    
    def unified_search(
        self, 
        query: str, 
        search_type: str = 'keyword',
        item_types: List[str] = None,
        sources: List[str] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Unified search endpoint that can do both keyword and semantic search.
        
        Args:
            query: Search query string
            search_type: 'keyword', 'semantic', or 'hybrid'
            item_types: Filter by types
            sources: Filter by sources
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        if search_type == 'semantic':
            return self.semantic_search(query, item_types, sources, limit)
        elif search_type == 'hybrid':
            # Combine results from both searches with re-ranking
            keyword_results = {r.id: r for r in self.keyword_search(query, item_types, sources, limit * 2)}
            semantic_results = {r.id: r for r in self.semantic_search(query, item_types, sources, limit * 2)}
            
            # Combine and re-rank
            all_results = {}
            for result in list(keyword_results.values()) + list(semantic_results.values()):
                if result.id in all_results:
                    # Average scores for duplicate results
                    all_results[result.id].score = (all_results[result.id].score + result.score) / 2
                else:
                    all_results[result.id] = result
            
            results = sorted(all_results.values(), key=lambda x: x.score, reverse=True)
            return results[:limit]
        else:
            return self.keyword_search(query, item_types, sources, limit)
    
    def _highlight_matches(self, text: str, query: str) -> List[str]:
        """Extract highlighted snippets matching the query"""
        if not text or not query:
            return []
        
        highlights = []
        query_lower = query.lower()
        text_lower = text.lower()
        
        # Find all occurrences
        for match in re.finditer(query_lower, text_lower):
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            
            snippet = text[start:end]
            if start > 0:
                snippet = '...' + snippet
            if end < len(text):
                snippet = snippet + '...'
            
            # Highlight the matched term
            matched_term = match.group()
            snippet = re.sub(
                f'({re.escape(matched_term)})',
                r'<mark>\1</mark>',
                snippet,
                flags=re.IGNORECASE
            )
            
            if snippet not in highlights:
                highlights.append(snippet)
        
        # If no exact matches, show first 200 chars
        if not highlights and text:
            highlights = [text[:200] + ('...' if len(text) > 200 else '')]
        
        return highlights
    
    def _calculate_keyword_score(self, text: str, query: str) -> float:
        """Calculate keyword relevance score"""
        if not text or not query:
            return 0.0
        
        text_lower = text.lower()
        query_lower = query.lower()
        
        score = 0.0
        query_terms = query_lower.split()
        
        for term in query_terms:
            if term in text_lower:
                # Exact match in title/label would be higher
                score += 1.0
                # Bonus for word boundary match
                if re.search(rf'\b{re.escape(term)}\b', text_lower):
                    score += 0.5
        
        # Normalize by query length
        return min(score / len(query_terms), 1.0)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def clear_index(self, source: str = None):
        """Clear the search index"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if source:
            cursor.execute('DELETE FROM search_index WHERE source = ?', (source,))
            cursor.execute('DELETE FROM embeddings WHERE source = ?', (source,))
        else:
            cursor.execute('DELETE FROM search_index')
            cursor.execute('DELETE FROM embeddings')
        
        conn.commit()
        conn.close()
        
        self.items_indexed = 0
    
    def get_index_stats(self) -> Dict:
        """Get statistics about the search index"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM search_index')
        total_items = cursor.fetchone()[0]
        
        cursor.execute('SELECT type, COUNT(*) FROM search_index GROUP BY type')
        type_counts = dict(cursor.fetchall())
        
        cursor.execute('SELECT source, COUNT(*) FROM search_index GROUP BY source')
        source_counts = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_items': total_items,
            'by_type': type_counts,
            'by_source': source_counts,
            'semantic_available': SEMANTIC_AVAILABLE,
            'model_loaded': self.embeddings_model is not None
        }


# ==================== SEARCH INDEXER HELPER ====================

def index_knowledge_graph(kg, search_engine: SemanticSearchEngine):
    """
    Index all data from a KnowledgeGraph object.
    
    Args:
        kg: KnowledgeGraph instance
        search_engine: SemanticSearchEngine instance
    """
    # Index tweets
    tweets = []
    for tweet_id, tweet in kg.tweets.items():
        tweets.append({
            'id': f'tweet_{tweet_id}',
            'type': 'tweet',
            'text': tweet.text,
            'label': f'Tweet: {tweet.text[:50]}...',
            'source': 'x',
            'topic': 'general',
            'metadata': {
                'created_at': tweet.created_at,
                'metrics': tweet.metrics
            }
        })
    search_engine.index_items(tweets, 'tweet', 'x')
    
    # Index Grok posts
    posts = []
    for post_id, post in kg.posts.items():
        posts.append({
            'id': f'grok_{post_id}',
            'type': 'grok',
            'text': post.text,
            'label': f'Grok: {post.text[:50]}...',
            'source': 'grok',
            'topic': 'general',
            'metadata': {
                'created_at': post.created_at,
                'metrics': post.metrics
            }
        })
    search_engine.index_items(posts, 'grok', 'grok')
    
    # Index actions
    actions = []
    for action in kg.actions:
        actions.append({
            'id': action.id,
            'type': 'action',
            'text': action.text,
            'label': f'[{"🔴" if action.priority == "urgent" else "🟠" if action.priority == "high" else "🟡" if action.priority == "medium" else "⚪"}] {action.text[:50]}...',
            'source': action.source_type,
            'topic': action.topic,
            'metadata': {
                'priority': action.priority,
                'status': action.status,
                'source_id': action.source_id
            }
        })
    search_engine.index_items(actions, 'action', action.source_type)
    
    # Index Grok conversations
    conversations = []
    for conv_id, conv in kg.grok_conversations.items():
        content = f"Title: {conv.title}\nMessages:\n"
        for msg in conv.messages:
            content += f"- {msg.get('role', 'unknown')}: {msg.get('content', '')[:200]}\n"
        
        conversations.append({
            'id': f'conv_{conv_id}',
            'type': 'conversation',
            'text': content,
            'label': f'Conversation: {conv.title}',
            'source': 'grok',
            'topic': 'general',
            'metadata': {
                'message_count': len(conv.messages),
                'create_time': conv.create_time
            }
        })
    search_engine.index_items(conversations, 'conversation', 'grok')
    
    # Index AI conversations
    ai_conversations = []
    for conv in kg.ai_conversations:
        content = f"Title: {conv.title}\nMessages:\n"
        for msg in conv.messages:
            content += f"- {msg.role}: {msg.content[:200]}\n"
        
        ai_conversations.append({
            'id': f'ai_{conv.id}',
            'type': 'ai_conversation',
            'text': content,
            'label': f'AI: {conv.title} ({conv.source})',
            'source': 'ai',
            'topic': 'general',
            'metadata': {
                'source': conv.source,
                'message_count': len(conv.messages)
            }
        })
    search_engine.index_items(ai_conversations, 'ai_conversation', 'ai')
    
    return {
        'tweets': len(tweets),
        'posts': len(posts),
        'actions': len(actions),
        'conversations': len(conversations),
        'ai_conversations': len(ai_conversations)
    }

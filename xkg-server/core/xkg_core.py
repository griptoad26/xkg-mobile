"""
X Knowledge Graph v0.4.33 - Core Engine
Parses X and Grok exports, builds conversation trees, extracts actions, links topics.
Supports ANY files in export folder - auto-detects format from content.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from collections import defaultdict

# Import Todoist exporter (try relative first, then absolute for bundled exe)
try:
    from .todoist_exporter import TodoistExporter, export_actions_to_todoist
except ImportError:
    try:
        from todoist_exporter import TodoistExporter, export_actions_to_todoist
    except ImportError:
        TodoistExporter = None
        export_actions_to_todoist = None

# Import Amazon product linker
try:
    from .amazon_product_linker import AmazonProductLinker, detect_purchase_intent
except ImportError:
    from amazon_product_linker import AmazonProductLinker, detect_purchase_intent

# Import AI export parser
try:
    from .ai_export_parser import (
        UnifiedAIExportParser,
        convert_ai_conversations_to_graph,
        detect_ai_export_type,
        AIConversation,
        AIMessage,
        AIExportResult
    )
except ImportError:
    from ai_export_parser import (
        UnifiedAIExportParser,
        convert_ai_conversations_to_graph,
        detect_ai_export_type,
        AIConversation,
        AIMessage,
        AIExportResult
    )


# ==================== DATA MODELS ====================



def parse_timestamp(ts: str) -> str:
    """Parse various timestamp formats to ISO 8601"""
    if not ts:
        return ""
    
    # Already ISO format - clean it up
    if ts.startswith('20'):  # Starts with year like 2024-
        # Handle various formats
        if '.' in ts:
            ts = ts.split('.')[0]
        if 'Z' not in ts:
            ts = ts + 'Z'
        return ts
    
    return ""

@dataclass
class Tweet:
    id: str
    text: str
    created_at: str
    author_id: str
    source_type: str = 'tweet'  # 'tweet', 'like', etc.
    in_reply_to_status_id: Optional[str] = None
    conversation_id: Optional[str] = None
    referenced_tweets: List[str] = field(default_factory=list)
    entities: Dict = field(default_factory=dict)
    metrics: Dict = field(default_factory=dict)

    @property
    def is_reply(self) -> bool:
        return bool(self.in_reply_to_status_id)

    @property
    def is_retweet(self) -> bool:
        return self.text.startswith('RT @')


@dataclass
class GrokPost:
    id: str
    text: str
    created_at: str
    author_id: str
    conversation_id: Optional[str] = None
    in_reply_to_id: Optional[str] = None
    metrics: Dict = field(default_factory=dict)
    entities: List = field(default_factory=list)
    source: str = "grok"


@dataclass
class GrokConversation:
    """Full Grok conversation with all messages"""
    id: str
    title: str
    create_time: str
    messages: List[Dict] = field(default_factory=list)  # List of {role, content, timestamp}
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'create_time': self.create_time,
            'messages': self.messages,
            'message_count': len(self.messages)
        }


@dataclass
class ActionItem:
    id: str
    text: str
    source_id: str
    source_type: str  # 'tweet', 'grok', 'ai_openai', 'ai_anthropic', 'ai_google'
    topic: str
    priority: str  # urgent, high, medium, low
    status: str = "pending"
    depends_on: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    amazon_link: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'text': self.text,
            'source_id': self.source_id,
            'source_type': self.source_type,
            'topic': self.topic,
            'priority': self.priority,
            'status': self.status,
            'depends_on': self.depends_on,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'amazon_link': self.amazon_link
        }


# AI Conversation data class (simplified for backward compatibility)
@dataclass
class AIConversationData:
    """Simple AI conversation data class for backward compatibility"""
    id: str
    title: str
    source: str  # 'openai', 'anthropic', 'google'
    created_at: str
    messages_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'source': self.source,
            'created_at': self.created_at,
            'messages_count': self.messages_count
        }


# ==================== FLEXIBLE FILE DISCOVERY ====================

def find_all_export_files(directory: str, extensions: List[str] = None) -> List[str]:
    """Find all files in directory matching extensions (recursive)"""
    if extensions is None:
        extensions = ['.json', '.js']
    
    files = []
    directory = Path(directory)
    
    if not directory.exists():
        return files
    
    # Always recurse into subdirectories
    for path in directory.rglob('*'):
        if path.is_file():
            # Match by extension OR by name containing any of the patterns
            suffix = path.suffix.lower()
            name_lower = path.name.lower()
            if suffix in extensions or any(ext in name_lower for ext in extensions):
                files.append(str(path))
    
    return sorted(set(files))  # Remove duplicates


def detect_export_format(filepath: str) -> str:
    """Auto-detect if file is X, Grok, or Production Log format based on content"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for grok-conversations-parsed.jsonl format FIRST (grok jsonl with message_count)
        # Must check before X format since .part0 = appears in conversation text
        if '"message_count"' in content and '"title"' in content and 'created_at' in content and 'updated_at' in content:
            return 'grok'
        
        # Check for X export format (window.YTD)
        if 'window.YTD.grok_chat_item' in content:
            return 'grok'
        elif 'window.YTD' in content and re.search(r'^window\.YTD\.\w+\.part\d+\s*=', content, re.MULTILINE):
            return 'x'
        elif re.search(r'^window\.YTD\.\w+\.part\d+\s*=', content, re.MULTILINE):
            return 'x'
        
        # Try parsing as JSON
        try:
            data = json.loads(content)
            
            # Check for Grok format (list of posts with 'source': 'grok')
            if isinstance(data, list):
                if any(item.get('source') == 'grok' for item in data if isinstance(item, dict)):
                    return 'grok'
                # Check for common Grok fields
                first_item = data[0] if data else {}
                if any(field in first_item for field in ['author_id', 'conversation_id']):
                    if not any(field in str(first_item).lower() for field in ['retweet', 'in_reply_to']):
                        return 'grok'
            
            # Check for X format (dict with 'tweet' key)
            if isinstance(data, dict):
                if 'tweet' in data:
                    return 'x'
                if any(k for k in data.keys() if 'tweet' in k.lower()):
                    return 'x'
                
                # Check for Grok conversations export format
                if 'conversations' in data and isinstance(data['conversations'], list):
                    if len(data['conversations']) > 0:
                        first_conv = data['conversations'][0]
                        if 'conversation' in first_conv and 'responses' in first_conv:
                            return 'grok'
            
            # Check for Production Log / Search History format
            if isinstance(data, list) and len(data) > 0:
                first_item = data[0] if data else {}
                
                # Check for Brave Search History (url, title, description)
                if 'url' in first_item and 'title' in first_item:
                    return 'prodlog'
                
                # Check for production log (timestamp/level/message)
                has_log_fields = (
                    ('timestamp' in first_item or 'time' in first_item or 'created_at' in first_item) and
                    ('level' in first_item or 'severity' in first_item or 'log_level' in first_item or 'level' in str(first_item).lower())
                )
                has_message = 'message' in first_item or 'msg' in first_item or 'log_message' in first_item
                if has_log_fields or has_message:
                    return 'prodlog'
            
            # Check for prod-*.json filename pattern (production log files)
            filename = Path(filepath).name.lower()
            if filename.startswith('prod-') and filename.endswith('.json'):
                return 'prodlog'
        
        except json.JSONDecodeError:
            pass
        
        return 'unknown'
    
    except Exception:
        return 'unknown'


# ==================== FLEXIBLE X EXPORT PARSER ====================

class FlexibleXParser:
    """Parse X exports - handles ANY files in folder, auto-detects format"""
    
    def __init__(self):
        self.tweets: Dict[str, Tweet] = {}
        self.likes: Dict[str, Dict] = {}
        self.replies: Dict[str, Dict] = {}
        self.conversations: Dict[str, Dict] = {}
    
    def parse(self, export_path: str) -> Dict:
        """Parse X export folder - scans for all JSON/JS files"""
        result = {
            'tweets': [],
            'likes': [],
            'replies': [],
            'stats': {}
        }
        
        # Find all potential export files
        files = find_all_export_files(export_path, ['.json', '.js', 'tweet', 'like', 'reply'])
        
        if not files:
            return {'error': f'No export files found in {export_path}'}
        
        print(f"Found {len(files)} files in X export folder")
        
        for filepath in files:
            print(f"  Processing: {os.path.basename(filepath)}")
            format_type = detect_export_format(filepath)
            print(f"    Detected format: {format_type}")
            
            if format_type == 'x':
                self._parse_x_file(filepath)
            elif format_type == 'grok':
                # Skip grok files in X export
                print(f"    Skipping (Grok format)")
            else:
                # Try parsing as generic tweet format
                self._parse_generic_file(filepath)
        
        # Build conversations
        self._build_conversations()
        
        result['tweets'] = list(self.tweets.values())
        result['likes'] = list(self.likes.values())
        result['replies'] = list(self.replies.values())
        result['stats'] = {
            'total_tweets': len(self.tweets),
            'total_likes': len(self.likes),
            'total_replies': len(self.replies),
            'conversations': len(self.conversations)
        }
        
        return result
    
    def _parse_x_file(self, filepath: str):
        """Parse X export format (window.YTD or direct JSON)"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Handle window.YTD format
            if 'window.YTD' in content:
                content = re.sub(r'^window\.YTD\.\w+\.part\d*\s*=\s*', '', content)
            
            data = json.loads(content)
            
            # Handle list of tweets (including like.js format with 'like' wrapper)
            if isinstance(data, list):
                for item in data:
                    if 'tweet' in item:
                        tweet_data = item['tweet']
                        source_type = 'tweet'
                    elif 'like' in item:
                        like_data = item['like']
                        like_text = like_data.get('fullText', '') or ''
                        like_id = like_data.get('tweetId', '') or ''
                        if like_id and like_text:
                            tweet_data = {
                                'id': like_id,
                                'full_text': like_text,
                                'created_at': like_data.get('created_at', ''),
                                '_source_type': 'like',
                            }
                            source_type = 'like'
                        else:
                            continue  # Skip likes with no id or text
                    else:
                        tweet_data = item
                        source_type = 'tweet'
                    
                    # Tag source type for _create_tweet to pick up
                    tweet_data['_source_type'] = source_type
                    tweet = self._create_tweet(tweet_data)
                    if tweet:
                        self.tweets[tweet.id] = tweet
            
            # Handle dict with tweets key
            elif isinstance(data, dict):
                if 'tweets' in data:
                    for item in data['tweets']:
                        tweet = self._create_tweet(item)
                        if tweet:
                            self.tweets[tweet.id] = tweet
                elif 'tweet' in data:
                    tweet = self._create_tweet(data['tweet'])
                    if tweet:
                        self.tweets[tweet.id] = tweet
        
        except Exception as e:
            print(f"    Error parsing {os.path.basename(filepath)}: {e}")
    
    def _parse_generic_file(self, filepath: str):
        """Parse generic JSON array of tweets"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data:
                    tweet = self._create_tweet(item)
                    if tweet:
                        self.tweets[tweet.id] = tweet
            elif isinstance(data, dict):
                tweet = self._create_tweet(data)
                if tweet:
                    self.tweets[tweet.id] = tweet
        
        except Exception as e:
            print(f"    Error parsing {os.path.basename(filepath)}: {e}")
    
    def _create_tweet(self, data: Dict) -> Optional[Tweet]:
        """Create Tweet object from parsed data"""
        try:
            tweet_id = str(data.get('id', data.get('id_str', '')))
            if not tweet_id:
                return None
            
            # Handle nested structure (tweet.js and like.js use different wrappers)
            if 'tweet' in data:
                data = data['tweet']
            elif 'like' in data:
                # like.js format: {'like': {'tweetId': ..., 'fullText': ...}}
                like_data = data['like']
                data = {
                    'id': like_data.get('tweetId', ''),
                    'text': like_data.get('fullText', ''),
                    'created_at': like_data.get('created_at', ''),
                }
            
            text = data.get('full_text') or data.get('text', '')
            created_at = data.get('created_at', datetime.now().isoformat())
            
            # Handle user/author_id
            user = data.get('user', {})
            author_id = str(user.get('id', data.get('author_id', '')))
            
            # Handle metrics
            metrics = data.get('metrics', {})
            if not metrics and 'public_metrics' in data:
                metrics = data['public_metrics']
            
            # Handle entities
            entities = data.get('entities', {})
            
            source_type = data.get('_source_type', 'tweet')
            return Tweet(
                id=tweet_id,
                text=text,
                created_at=created_at,
                author_id=author_id,
                source_type=source_type,
                in_reply_to_status_id=data.get('in_reply_to_status_id'),
                conversation_id=data.get('conversation_id'),
                entities=entities,
                metrics=metrics
            )
        
        except Exception:
            return None
    
    def _build_conversations(self):
        """Build conversation threads from replies"""
        for tweet_id, tweet in self.tweets.items():
            if tweet.in_reply_to_status_id:
                if tweet.in_reply_to_status_id not in self.conversations:
                    self.conversations[tweet.in_reply_to_status_id] = {
                        'root_id': tweet.in_reply_to_status_id,
                        'replies': []
                    }
                self.conversations[tweet.in_reply_to_status_id]['replies'].append(tweet_id)


# ==================== FLEXIBLE GROK EXPORT PARSER ====================

class FlexibleGrokParser:
    """Parse Grok exports - handles ANY files in folder, auto-detects format"""
    
    def __init__(self):
        self.posts: Dict[str, GrokPost] = {}
        self.conversations: Dict[str, GrokConversation] = {}  # Store full conversations
    
    def parse(self, export_path: str) -> Dict:
        """Parse Grok export folder - scans for all JSON files recursively"""
        result = {
            'posts': [],
            'conversations': [],
            'stats': {}
        }
        
        # Find all potential export files (recursive)
        files = find_all_export_files(export_path, ['.json', '.js'])
        
        if not files:
            # Also try finding any files that might contain conversation/grok data
            files = find_all_export_files(export_path, ['*'])
        
        print(f"Scanning: {export_path}")
        print(f"Found {len(files)} files")
        
        # Show first few files for debugging
        for f in sorted(files)[:10]:
            print(f"  {f}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
        
        if not files:
            return {'error': f'No export files found in {export_path}'}
        
        for filepath in files:
            # Skip directories
            if os.path.isdir(filepath):
                continue
            print(f"  Processing: {os.path.basename(filepath)}")
            format_type = detect_export_format(filepath)
            print(f"    Detected format: {format_type}")
            
            if format_type == 'grok':
                self._parse_grok_file(filepath)
            elif format_type == 'prodlog':
                self._parse_prodlog_file(filepath)
            elif format_type == 'x':
                print(f"    Skipping (X format)")
            else:
                # Try as generic post format
                self._parse_generic_file(filepath)
        
        result['posts'] = list(self.posts.values())
        result['conversations'] = [c.to_dict() for c in self.conversations.values()]
        result['stats'] = {
            'total_posts': len(self.posts),
            'total_conversations': len(self.conversations)
        }
        
        return result
    
    def _is_valid_json(self, s: str) -> bool:
        """Check if string is valid JSON"""
        try:
            json.loads(s)
            return True
        except:
            return False
    
    def _parse_grok_file(self, filepath: str):
        """Parse Grok export format - builds full conversation structures"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Handle window.YTD.grok_chat_item format (like X export)
            if 'window.YTD' in content:
                content = re.sub(r'^window\.YTD\.\w+\.part\d*\s*=\s*', '', content)
            
            # Check for JSONL format (newline-delimited JSON - grok-conversations-parsed.jsonl)
            lines = content.strip().split('\n')
            if len(lines) > 1 and all(self._is_valid_json(l) for l in lines[:3]):
                # JSONL format - each line is a separate JSON object
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                        if 'grokChatItem' in item:
                            item = item['grokChatItem']
                        post = self._create_post(item)
                        if post:
                            self.posts[post.id] = post
                    except:
                        pass
                return
            
            data = json.loads(content)
            
            if isinstance(data, list):
                for item in data:
                    # Handle {'grokChatItem': {...}} wrapper format
                    if isinstance(item, dict) and 'grokChatItem' in item:
                        item = item['grokChatItem']
                    post = self._create_post(item)
                    if post:
                        self.posts[post.id] = post
            elif isinstance(data, dict):
                # Handle wrapper format at dict level
                if 'grokChatItem' in data:
                    data = data['grokChatItem']
                # Check for standard Grok formats
                if 'posts' in data:
                    for item in data['posts']:
                        post = self._create_post(item)
                        if post:
                            self.posts[post.id] = post
                elif 'conversations' in data:
                    for conv in data['conversations']:
                        self._build_conversation(conv)
                elif 'results' in data:
                    for item in data['results']:
                        post = self._create_post_from_grok_result(item)
                        if post:
                            self.posts[post.id] = post
                elif 'task' in data and 'results' in data.get('task', {}):
                    for item in data['task']['results']:
                        post = self._create_post_from_grok_result(item)
                        if post:
                            self.posts[post.id] = post
        
        except Exception as e:
            print(f"    Error parsing {os.path.basename(filepath)}: {e}")
    
    def _build_conversation(self, conv_data: Dict):
        """Build a full GrokConversation from conversation data"""
        try:
            conv = conv_data.get('conversation', conv_data)
            conv_id = conv.get('id', '')
            if not conv_id:
                return
            
            # Get conversation title
            title = conv.get('title', '')
            if not title:
                title = conv_data.get('summary', 'Untitled Conversation')
            if not title:
                title = f"Conversation {conv_id[:8]}"
            
            create_time = conv.get('create_time', conv.get('modify_time', ''))
            
            # Build messages list from responses
            messages = []
            responses = conv_data.get('responses', conv_data.get('messages', []))
            
            for resp in responses:
                # Handle nested 'response' key
                resp_data = resp.get('response', resp)
                
                role = resp_data.get('sender', 'unknown')
                # Map sender to role
                if role == 'human':
                    role = 'user'
                elif role in ['ai', 'grok', 'system']:
                    role = 'assistant'
                
                content = resp_data.get('message', '')
                
                # Get timestamp - handle both string and object formats
                timestamp = resp_data.get('create_time', '')
                if isinstance(timestamp, dict) and '$date' in timestamp:
                    ts_val = timestamp['$date'].get('$numberLong', '')
                    if ts_val:
                        timestamp = str(int(int(ts_val) / 1000))  # Convert milliseconds to seconds
                
                messages.append({
                    'role': role,
                    'content': content,
                    'timestamp': timestamp
                })
            
            # Create the conversation
            conversation = GrokConversation(
                id=conv_id,
                title=title,
                create_time=create_time,
                messages=messages
            )
            
            self.conversations[conv_id] = conversation
            
            # Also create individual posts for each message
            for idx, msg in enumerate(messages):
                post_id = f"{conv_id}_{idx}"
                self.posts[post_id] = GrokPost(
                    id=post_id,
                    text=msg['content'][:500] if msg['content'] else '',
                    created_at=msg['timestamp'],
                    author_id=msg['role'],
                    conversation_id=conv_id,
                    in_reply_to_id=None,
                    metrics={'source': 'grok_conversation'},
                    entities=[],
                    source='grok'
                )
        
        except Exception as e:
            print(f"    Error building conversation: {e}")
    
    def _create_post_from_grok_result(self, data: Dict) -> Optional[GrokPost]:
        """Create GrokPost from new Grok result format (conversations with tasks)"""
        try:
            # Extract post info from task/conversation structure
            conversation_id = data.get('conversation_id', '')
            task_id = data.get('task_id', '')
            post_id = f"grok_{conversation_id}_{task_id}" if conversation_id and task_id else data.get('task_result_id', f"grok_{data.get('create_time', '')}")
            
            # Extract text from metadata.response_preview (may be HTML)
            metadata = data.get('metadata', {})
            response_preview = metadata.get('response_preview', '') or ''
            
            # Strip HTML tags for clean text - ensure str() to handle None
            import re
            text = re.sub(r'<[^>]+>', '', str(response_preview)).strip()
            if not text:
                text = data.get('title', '')
            
            created_at = data.get('create_time', data.get('update_time', datetime.now().isoformat()))
            status = data.get('status', '')
            error = data.get('error')
            
            # Only create post for successful results
            if error or status != 'Success':
                return None
            
            return GrokPost(
                id=post_id,
                text=text[:500] if text else '[No content]',  # Truncate long HTML
                created_at=created_at,
                author_id='grok',
                conversation_id=conversation_id,
                in_reply_to_id=None,
                metrics={'exec_time': metadata.get('exec_time', 0)},
                entities=[],
                source='grok'
            )
        
        except Exception:
            return None
    
    def _parse_prodlog_file(self, filepath: str):
        """Parse production log files or search history as pseudo-posts"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                data = [data]
            
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    continue
                
                # Detect format based on available fields
                has_url = 'url' in item
                has_timestamp = 'timestamp' in item or 'time' in item or 'created_at' in item
                has_message = 'message' in item or 'msg' in item
                
                # Format 1: Brave Search History (url, title, description, preview)
                if has_url:
                    title = item.get('title', '')
                    description = item.get('description', '')
                    preview = item.get('preview', '')
                    url = item.get('url', '')
                    site_name = item.get('site_name', '')
                    
                    # Combine text fields
                    text_parts = []
                    if title: text_parts.append(title)
                    if description: text_parts.append(description)
                    if preview: text_parts.append(preview)
                    text = ' | '.join(text_parts)
                    
                    if not text:
                        continue
                    
                    # Create ID from URL
                    post_id = f"search_{idx}_{hash(url) % 100000}"
                    timestamp = item.get('timestamp', item.get('time', ''))
                    author_id = f"search_{site_name}" if site_name else "search_history"
                
                # Format 2: Production Log (timestamp, level, message, service)
                elif has_timestamp or has_message:
                    timestamp = item.get('timestamp', item.get('time', item.get('created_at', '')))
                    level = item.get('level', item.get('severity', item.get('log_level', '')))
                    message = item.get('message', item.get('msg', item.get('log_message', '')))
                    service = item.get('service', item.get('logger', item.get('name', 'unknown')))
                    
                    # Skip empty messages
                    if not message:
                        continue
                    
                    text = message
                    post_id = f"log_{Path(filepath).stem}_{idx}"
                    author_id = f"{service}_{level}" if level else service
                
                else:
                    # Unknown format - skip
                    continue
                
                # Create the post
                post = GrokPost(
                    id=post_id,
                    text=text,
                    created_at=timestamp,
                    author_id=author_id,
                    conversation_id=None,
                    in_reply_to_id=None,
                    metrics={'source': 'prodlog'},
                    entities=[],
                    source='prodlog'
                )
                
                self.posts[post.id] = post
        
        except Exception as e:
            print(f"    Error parsing prodlog {os.path.basename(filepath)}: {e}")
    
    def _parse_generic_file(self, filepath: str):
        """Parse generic JSON as posts"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data:
                    post = self._create_post(item)
                    if post:
                        self.posts[post.id] = post
            elif isinstance(data, dict):
                if 'items' in data:
                    for item in data['items']:
                        post = self._create_post(item)
                        if post:
                            self.posts[post.id] = post
        
        except Exception as e:
            print(f"    Error parsing {os.path.basename(filepath)}: {e}")
    
    def _create_post(self, data: Dict) -> Optional[GrokPost]:
        """Create GrokPost from parsed data"""
        try:
            # Handle Grok export formats - chatId and conversationId (grok-chat-item.js)
            post_id = str(data.get('id', data.get('id_str', data.get('chatId', data.get('_id', '')))))
            if not post_id:
                return None
            
            conversation_id = data.get('conversation_id') or data.get('chatId')
            
            # Handle 'message' field from Grok conversations (fall back to 'text' or 'content')
            text = data.get('message', data.get('text', data.get('content', '')))
            created_at = data.get('created_at', data.get('create_time', data.get('createdAt', datetime.now().isoformat())))
            author_id = str(data.get('author_id', data.get('user_id', data.get('sender', data.get('accountId', 'grok_user')))))
            
            return GrokPost(
                id=post_id,
                text=text,
                created_at=created_at,
                author_id=author_id,
                conversation_id=data.get('conversation_id'),
                in_reply_to_id=data.get('in_reply_to_id'),
                metrics=data.get('metrics', data.get('stats', {})),
                entities=data.get('entities', []),
                source=data.get('source', 'grok')
            )
        
        except Exception:
            return None


# ==================== MAIN KNOWLEDGE GRAPH ====================

class KnowledgeGraph:
    """Main knowledge graph that combines X, Grok, and AI conversation exports"""
    
    def __init__(self):
        self.tweets: Dict[str, Tweet] = {}
        self.posts: Dict[str, GrokPost] = {}
        self.grok_conversations: Dict[str, GrokConversation] = {}  # Full Grok conversations
        self.ai_conversations: List[AIConversation] = []  # AI conversations (ChatGPT, Claude, Gemini)
        self.actions: List[ActionItem] = []
        self.topics: Dict[str, Dict] = {}
        self.grok_topics: Dict[str, Dict] = {}  # Separate topics for Grok
        self.ai_topics: Dict[str, Dict] = {}  # Separate topics for AI conversations
        self.flows: Dict[str, List[str]] = {}
        
        # Priority keywords for action detection
        self.priority_keywords = {
            'urgent': ['urgent', 'asap', 'immediately', 'critical', 'emergency', 'blocking', 'priority 1'],
            'high': ['important', 'high priority', 'must', 'required', 'deadline', 'due'],
            'medium': ['should', 'need to', 'remember to', 'todo', 'fix', 'update', 'review'],
            'low': ['would be nice', 'consider', 'maybe', 'sometime', 'low priority']
        }
        
        # Initialize Amazon product linker
        self.amazon_linker = AmazonProductLinker()
        
        # Initialize AI parser
        self.ai_parser = UnifiedAIExportParser()
    
    def build_from_export(self, export_path: str, export_type: str = 'x') -> Dict:
        """Build knowledge graph from a single export"""
        
        if export_type == 'grok':
            parser = FlexibleGrokParser()
            result = parser.parse(export_path)
            self.posts = parser.posts
            self.grok_conversations = parser.conversations  # Store full conversations
            tweets_count = 0
            posts_count = result['stats'].get('total_posts', 0)
            conversations_count = result['stats'].get('total_conversations', 0)
            ai_conversations_count = 0
        elif export_type == 'ai':
            # Parse AI conversation exports
            result = self._parse_ai_export(export_path)
            tweets_count = 0
            posts_count = 0
            conversations_count = 0
            ai_conversations_count = result['stats'].get('total_conversations', 0)
        else:
            parser = FlexibleXParser()
            result = parser.parse(export_path)
            self.tweets = parser.tweets
            tweets_count = result['stats'].get('total_tweets', 0)
            posts_count = 0
            conversations_count = 0
            ai_conversations_count = 0
        
        # Extract actions from parsed data
        self._extract_actions()
        
        # Cluster topics - separate X, Grok, and AI
        self._cluster_topics()
        
        # Build task flows
        self._build_flows()
        
        return {
            'stats': {
                'total_tweets': tweets_count,
                'total_posts': posts_count,
                'total_conversations': conversations_count,
                'total_ai_conversations': ai_conversations_count,
                'total_actions': len(self.actions),
                'topics_count': len(self.topics),
                'grok_topics_count': len(self.grok_topics),
                'ai_topics_count': len(self.ai_topics),
                'flows_count': len(self.flows)
            },
            'actions': [a.to_dict() for a in self.actions],
            'topics': self.topics,
            'grok_topics': self.grok_topics,
            'ai_topics': self.ai_topics,
            'grok_conversations': [c.to_dict() for c in self.grok_conversations.values()],
            'ai_conversations': [c.to_dict() for c in self.ai_conversations],
            'flows': self.flows
        }
    
    def _parse_ai_export(self, export_path: str) -> Dict:
        """Parse AI conversation exports (OpenAI, Anthropic, Google)"""
        print(f"\nParsing AI export from: {export_path}")
        
        # Use the unified AI parser
        result = self.ai_parser.parse(export_path)
        
        if result.errors:
            for error in result.errors:
                print(f"  Warning: {error}")
        
        # Store conversations
        self.ai_conversations = result.conversations
        
        print(f"  Found {len(result.conversations)} AI conversations with {result.messages_total} messages")

        # Build AI-specific posts (similar to Grok posts)
        for conv in result.conversations:
            for idx, msg in enumerate(conv.messages):
                post_id = f"ai_{conv.source}_{conv.id}_{idx}"
                self.posts[post_id] = GrokPost(
                    id=post_id,
                    text=msg.content[:1000] if msg.content else '',
                    created_at=msg.timestamp or conv.created_at,
                    author_id=f"ai_{msg.role}",
                    conversation_id=conv.id,
                    in_reply_to_id=None,
                    metrics={'source': f'ai_{conv.source}', 'message_role': msg.role},
                    entities=[],
                    source=f'ai_{conv.source}'
                )
        # Note: Actions will be extracted by the main _extract_actions() method called in build_from_export()
        
        return {
            'stats': {
                'total_conversations': len(result.conversations),
                'total_messages': result.messages_total,
                'total_posts': len(self.posts)
            },
            'conversations': result.conversations,
            'messages': result.messages_total
        }
    
    def _extract_ai_actions(self):
        """Extract action items from AI conversations"""
        action_id = len(self.actions)
        
        for conv in self.ai_conversations:
            for msg in conv.messages:
                # Find actions in the message content
                actions = self._find_actions_in_text(msg.content, f"ai_{msg.id}", f'ai_{conv.source}')
                for action_text, priority in actions:
                    amazon_link = self.amazon_linker.generate_amazon_url(action_text)
                    self.actions.append(ActionItem(
                        id=f'action_{action_id}',
                        text=action_text,
                        source_id=msg.id,
                        source_type=f'ai_{conv.source}',
                        topic=self._extract_topic(action_text),
                        priority=priority,
                        amazon_link=amazon_link
                    ))
                    action_id += 1
    
    def build_from_both(self, x_path: str, grok_path: str) -> Dict:
        """Build knowledge graph from both X and Grok exports"""
        
        print(f"\nParsing X export from: {x_path}")
        x_result = self.build_from_export(x_path, 'x')
        
        print(f"\nParsing Grok export from: {grok_path}")
        grok_result = self.build_from_export(grok_path, 'grok')
        
        # Combine stats
        combined_stats = {
            'total_tweets': x_result['stats']['total_tweets'] + grok_result['stats']['total_posts'],
            'total_posts': grok_result['stats']['total_posts'],
            'total_conversations': grok_result['stats']['total_conversations'],
            'total_actions': len(self.actions),
            'topics_count': len(self.topics),
            'grok_topics_count': len(self.grok_topics),
            'flows_count': len(self.flows)
        }
        
        return {
            'stats': combined_stats,
            'actions': [a.to_dict() for a in self.actions],
            'topics': self.topics,
            'grok_topics': self.grok_topics,
            'grok_conversations': grok_result.get('grok_conversations', []),
            'flows': self.flows
        }
    
    def _extract_actions(self):
        """Extract action items from tweets and posts.
        Every tweet/post becomes an action so the UI always shows content.
        Keyword-matched items get priority labels; all others get 'medium'.
        """
        action_id = 0
        
        # Process tweets (X) and likes — ALL become actions
        for tweet_id, tweet in self.tweets.items():
            stype = getattr(tweet, 'source_type', 'tweet')
            # First: keyword-matched actions (high priority items)
            keyword_actions = self._find_actions_in_text(tweet.text, tweet_id, stype)
            for action_text, priority in keyword_actions:
                amazon_link = self.amazon_linker.generate_amazon_url(action_text)
                self.actions.append(ActionItem(
                    id=f'action_{action_id}',
                    text=action_text,
                    source_id=tweet_id,
                    source_type=stype,
                    topic=self._extract_topic(action_text),
                    priority=priority,
                    amazon_link=amazon_link
                ))
                action_id += 1
            
            # Always add the tweet itself as an action
            if tweet.text:
                self.actions.append(ActionItem(
                    id=f'action_{action_id}',
                    text=tweet.text[:1000],  # cap at 1000 chars
                    source_id=tweet_id,
                    source_type=stype,
                    topic=self._extract_topic(tweet.text),
                    priority='medium',
                    amazon_link=None
                ))
                action_id += 1
        
        # Process Grok posts — ALL posts become actions
        for post_id, post in self.posts.items():
            keyword_actions = self._find_actions_in_text(post.text, post_id, 'grok')
            for action_text, priority in keyword_actions:
                amazon_link = self.amazon_linker.generate_amazon_url(action_text)
                self.actions.append(ActionItem(
                    id=f'action_{action_id}',
                    text=action_text,
                    source_id=post_id,
                    source_type='grok',
                    topic=self._extract_topic(action_text),
                    priority=priority,
                    amazon_link=amazon_link
                ))
                action_id += 1
            
            if post.text:
                self.actions.append(ActionItem(
                    id=f'action_{action_id}',
                    text=post.text[:1000],
                    source_id=post_id,
                    source_type='grok',
                    topic=self._extract_topic(post.text),
                    priority='medium',
                    amazon_link=None
                ))
                action_id += 1
    
    def _find_actions_in_text(self, text: str, source_id: str, source_type: str) -> List[tuple]:
        """Find action items in text and their priorities"""
        actions = []
        
        # Defensive: ensure text is a string
        if not text:
            return []
        
        text_lower = str(text).lower()
        
        for priority, keywords in self.priority_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Extract sentence containing the keyword - defensive check for None
                    sentences = re.split(r'[.!?\n]', str(text)) if text else []
                    for sentence in sentences:
                        if keyword in str(sentence).lower():
                            sentence = str(sentence).strip()
                            if len(sentence) > 10 and len(sentence) < 500:
                                actions.append((sentence, priority))
                    break
        
        return actions
    
    def _extract_topic(self, text: str) -> str:
        """Extract topic from action text"""
        topic_keywords = {
            'api': ['api', 'endpoint', 'rest', 'json'],
            'database': ['database', 'db', 'sql', 'query'],
            'authentication': ['auth', 'login', 'password', 'oauth'],
            'performance': ['performance', 'speed', 'optimize', 'slow'],
            'documentation': ['docs', 'documentation', 'readme'],
            'testing': ['test', 'testing', 'qa', 'bug'],
            'ui': ['ui', 'interface', 'design', 'frontend'],
            'deployment': ['deploy', 'production', 'server', 'infrastructure'],
            'business': ['meeting', 'schedule', 'business', 'team'],
            'personal': ['buy', 'order', 'keyboard', 'office']
        }
        
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return topic
        
        return 'general'
    
    def _cluster_topics(self):
        """Cluster actions by topic with full action data - separate X and Grok"""
        # Separate actions by source type
        tweet_actions = [a for a in self.actions if a.source_type == 'tweet']
        grok_actions = [a for a in self.actions if a.source_type == 'grok']
        
        # Cluster X (tweet) actions
        topic_actions = defaultdict(list)
        for action in tweet_actions:
            topic_actions[action.topic].append({
                'id': action.id,
                'text': action.text,
                'priority': action.priority,
                'status': action.status,
                'source_type': action.source_type,
                'source_id': action.source_id,
                'created_at': action.created_at,
                'amazon_link': action.amazon_link
            })
        
        self.topics = {
            topic: {
                'name': topic,
                'action_count': len(action_list),
                'items': action_list,
                'keywords': [topic],
                'source': 'x'
            }
            for topic, action_list in topic_actions.items()
        }
        
        # Cluster Grok actions separately
        grok_topic_actions = defaultdict(list)
        for action in grok_actions:
            grok_topic_actions[action.topic].append({
                'id': action.id,
                'text': action.text,
                'priority': action.priority,
                'status': action.status,
                'source_type': action.source_type,
                'source_id': action.source_id,
                'created_at': action.created_at,
                'amazon_link': action.amazon_link
            })
        
        # Build Grok topics
        grok_topic_dict = defaultdict(list)
        for action in grok_actions:
            grok_topic_dict[action.topic].append({
                'id': action.id,
                'text': action.text,
                'priority': action.priority,
                'status': action.status,
                'source_type': action.source_type,
                'source_id': action.source_id,
                'created_at': action.created_at,
                'amazon_link': action.amazon_link
            })
        
        self.grok_topics = {
            topic: {
                'name': topic,
                'action_count': len(action_list),
                'items': action_list,
                'keywords': [topic],
                'source': 'grok'
            }
            for topic, action_list in grok_topic_dict.items()
        }
    
    def _build_flows(self):
        """Build task flows (simplified - orders by priority)"""
        # Sort actions by priority
        priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
        
        sorted_actions = sorted(
            self.actions,
            key=lambda a: (priority_order.get(a.priority, 3), a.created_at)
        )
        
        # Group by topic for flows
        topic_flows = defaultdict(list)
        for action in sorted_actions:
            topic_flows[action.topic].append(action.id)
        
        self.flows = dict(topic_flows)
    
    def export_for_d3(self) -> Dict:
        """Export graph in D3.js format with proper timestamps"""
        nodes = []
        edges = []
        
        # Tweet nodes with parsed timestamps
        for tweet_id, tweet in self.tweets.items():
            created_at = parse_timestamp(tweet.created_at)
            nodes.append({
                'id': f'tweet_{tweet_id}',
                'type': 'tweet',
                'label': tweet.text[:50] + '...' if len(tweet.text) > 50 else tweet.text,
                'text': tweet.text,
                'topic': 'general',
                'source': 'x',
                'created_at': created_at,
                'author_id': tweet.author_id,
                'conversation_id': tweet.conversation_id or ''
            })
        
        # Grok post nodes with parsed timestamps
        for post_id, post in self.posts.items():
            created_at = parse_timestamp(post.created_at)
            conv_title = ''
            if post.conversation_id and post.conversation_id in self.grok_conversations:
                conv_title = self.grok_conversations[post.conversation_id].title
            
            nodes.append({
                'id': f'grok_{post_id}',
                'type': 'grok',
                'label': post.text[:50] + '...' if len(post.text) > 50 else post.text,
                'text': post.text,
                'topic': 'general',
                'source': 'grok',
                'created_at': created_at,
                'conversation_id': post.conversation_id or '',
                'conversation_title': conv_title,
                'author_id': post.author_id
            })
        
        # Add Grok conversation nodes for better organization
        for conv_id, conv in self.grok_conversations.items():
            nodes.append({
                'id': f'grok_conv_{conv_id}',
                'type': 'grok_conversation',
                'label': conv.title[:50] + '...' if len(conv.title) > 50 else conv.title,
                'text': f"Conversation: {conv.title}\n{len(conv.messages)} messages",
                'topic': 'grok',
                'source': 'grok',
                'message_count': len(conv.messages)
            })
        
        # Action nodes - separate by source
        for action in self.actions:
            # Map source_type to node prefix
            source_prefix_map = {'tweet': 'tweet', 'grok': 'grok', 'ai_openai': 'ai_openai', 'ai_anthropic': 'ai_anthropic', 'ai_google': 'ai_google'}
            source_prefix = source_prefix_map.get(action.source_type, action.source_type[:4])
            source_id = f"{source_prefix}_{action.source_id}"
            nodes.append({
                'id': action.id,
                'type': 'action',
                'label': action.text[:40] + '...' if len(action.text) > 40 else action.text,
                'text': action.text,
                'priority': action.priority,
                'topic': action.topic,
                'source': action.source_type
            })
            
            # Edge from source to action
            edges.append({
                'source': source_id,
                'target': action.id,
                'type': 'extracts'
            })
        
        # Topic nodes - separate X and Grok topics
        for topic, data in self.topics.items():
            nodes.append({
                'id': f'topic_{topic}',
                'type': 'topic',
                'label': topic.upper(),
                'topic': topic,
                'source': 'x'
            })
            
            # Edges from actions to topic
            for action_item in data.get('items', []):
                edges.append({
                    'source': action_item.get('id'),
                    'target': f'topic_{topic}',
                    'type': 'belongs_to'
                })
        
        # Grok topic nodes
        for topic, data in self.grok_topics.items():
            nodes.append({
                'id': f'grok_topic_{topic}',
                'type': 'topic',
                'label': topic.upper(),
                'topic': topic,
                'source': 'grok'
            })
            
            # Edges from grok actions to grok topic
            for action_item in data.get('items', []):
                edges.append({
                    'source': action_item.get('id'),
                    'target': f'grok_topic_{topic}',
                    'type': 'belongs_to'
                })
        
        return {'nodes': nodes, 'edges': edges}

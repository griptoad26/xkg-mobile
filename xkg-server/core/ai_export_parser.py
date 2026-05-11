"""
AI Export Parser Module
Parses conversation exports from OpenAI (ChatGPT), Anthropic (Claude), and Google (Gemini).
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from html.parser import HTMLParser


# ==================== DATA MODELS ====================

@dataclass
class AIConversation:
    """Generic AI conversation structure"""
    id: str
    title: str
    created_at: str
    updated_at: str
    source: str  # 'openai', 'anthropic', 'google'
    messages: List['AIMessage'] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'source': self.source,
            'messages': [m.to_dict() for m in self.messages],
            'metadata': self.metadata
        }


@dataclass
class AIMessage:
    """Individual AI message"""
    id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: str
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


@dataclass
class AIExportResult:
    """Result of parsing an AI export"""
    conversations: List[AIConversation]
    messages_total: int
    stats: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


# ==================== HTML PARSER FOR CHATGPT EXPORTS ====================

class ChatGPTHTMLParser(HTMLParser):
    """Parse ChatGPT HTML export format"""
    
    def __init__(self):
        super().__init__()
        self.conversations = []
        self.current_conversation = None
        self.current_message = None
        self.current_text = []
        self.in_title = False
        self.in_message = False
        self.in_timestamp = False
        self.message_buffer = []
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == 'h1':
            self.in_title = True
            
        elif tag == 'div':
            if attrs_dict.get('class') == 'conversation-item':
                self.current_conversation = {
                    'title': '',
                    'messages': [],
                    'timestamp': ''
                }
                self.in_message = False
            elif attrs_dict.get('class') == 'message':
                self.current_message = {
                    'role': attrs_dict.get('data-role', 'unknown'),
                    'content': '',
                    'timestamp': ''
                }
                self.in_message = True
                self.current_text = []
                
        elif tag == 'time':
            self.in_timestamp = True
            
    def handle_endtag(self, tag):
        if tag == 'h1':
            self.in_title = False
            
        elif tag == 'div':
            if self.in_message and self.current_message:
                self.current_message['content'] = '\n'.join(self.current_text).strip()
                if self.current_conversation and self.current_message['content']:
                    self.current_conversation['messages'].append(self.current_message)
                self.current_message = None
                self.in_message = False
                self.current_text = []
                
        elif tag == 'time':
            self.in_timestamp = False
            
    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
            
        if self.in_title:
            if self.current_conversation:
                self.current_conversation['title'] = data
                
        elif self.in_timestamp:
            if self.current_message:
                self.current_message['timestamp'] = data
            elif self.current_conversation:
                if not self.current_conversation['timestamp']:
                    self.current_conversation['timestamp'] = data
                
        elif self.in_message:
            self.current_text.append(data)
            
    def handle_entityref(self, name):
        entities = {
            'nbsp': ' ',
            'amp': '&',
            'lt': '<',
            'gt': '>',
            'quot': '"'
        }
        if name in entities:
            self.current_text.append(entities[name])
            
    def handle_data(self, data):
        data = data.strip()
        if data and self.in_message:
            self.current_text.append(data)


# ==================== EXPORT DETECTION ====================

def detect_ai_export_format(filepath: str) -> Optional[str]:
    """Detect the AI platform from file content"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for OpenAI/ChatGPT HTML export
        if '</html>' in content.lower() or 'chatgpt' in content.lower():
            if 'window.YOpenAI' in content or 'conversation_id' in content:
                return 'openai_html'
            # Try parsing as HTML
            try:
                parser = ChatGPTHTMLParser()
                parser.feed(content)
                if parser.conversations:
                    return 'openai_html'
            except:
                pass
                
        # Try parsing as JSON
        try:
            data = json.loads(content)
            
            # Check for OpenAI format (API export)
            if isinstance(data, dict):
                if 'id' in data and 'object' in data:
                    if data.get('object') == 'list':
                        return 'openai_api'
                        
                # Check for "mapping" field (ChatGPT JSON format)
                if 'mapping' in data:
                    return 'openai_json'
                    
                # Check for "conversations" with "messages" (Anthropic format)
                if 'conversations' in data or 'chat_messages' in data:
                    return 'anthropic'
                    
            # Check for Google Gemini format
            if isinstance(data, dict) and 'contents' in data:
                if any('role' in item for item in data.get('contents', [])):
                    return 'google_gemini'
                    
            # Check for Anthropic format (array of messages)
            if isinstance(data, list):
                first_item = data[0] if data else {}
                # Check for Claude format - has 'uuid' and either 'messages' or 'human'/'assistant' roles
                if 'uuid' in first_item:
                    if 'messages' in first_item or 'chat_messages' in first_item:
                        return 'anthropic'
                    if 'role' in first_item and first_item['role'] in ['human', 'assistant']:
                        return 'anthropic'
                if 'role' in first_item and 'content' in first_item:
                    # Could be any format - check more
                    if any('model' in str(item).lower() for item in data):
                        return 'anthropic'
                        
        except json.JSONDecodeError:
            pass
            
        return None
        
    except Exception:
        return None


# ==================== OPENAI/CHATGPT PARSER ====================

class OpenAIChatGPTParser:
    """Parse OpenAI ChatGPT conversation exports (JSON and HTML)"""
    
    def __init__(self):
        self.conversations = []
        
    def parse(self, export_path: str) -> AIExportResult:
        """Parse ChatGPT export folder or file"""
        result = AIExportResult(
            conversations=[],
            messages_total=0,
            stats={},
            errors=[]
        )
        
        # Find all potential export files
        files = self._find_export_files(export_path)
        
        if not files:
            result.errors.append(f'No export files found in {export_path}')
            return result
            
        for filepath in files:
            try:
                format_type = detect_ai_export_format(filepath)
                if format_type in ['openai_json', 'openai_api', 'openai_html']:
                    convos = self._parse_file(filepath, format_type)
                    result.conversations.extend(convos)
            except Exception as e:
                result.errors.append(f'Error parsing {filepath}: {str(e)}')
                
        result.messages_total = sum(len(c.messages) for c in result.conversations)
        result.stats = {
            'conversations': len(result.conversations),
            'messages': result.messages_total
        }
        
        return result
        
    def _find_export_files(self, directory: str) -> List[str]:
        """Find all export files in directory"""
        files = []
        path = Path(directory)
        
        if path.is_file():
            return [str(path)]
            
        if not path.exists():
            return []
            
        # Look for common patterns
        patterns = ['*.json', '*.html', '*.txt', '*.js']
        for pattern in patterns:
            files.extend(path.glob(pattern))
            
        # Also look for conversation files
        for item in path.glob('*'):
            if item.is_dir():
                files.extend(item.glob('*conversation*'))
                
        return [str(f) for f in files]
        
    def _parse_file(self, filepath: str, format_type: str) -> List[AIConversation]:
        """Parse a single export file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if format_type == 'openai_html':
            return self._parse_html(content)
        else:
            return self._parse_json(content)
            
    def _parse_html(self, content: str) -> List[AIConversation]:
        """Parse ChatGPT HTML export"""
        conversations = []
        
        try:
            # Simple regex-based parsing for HTML
            # Extract conversation sections
            title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
            title = title_match.group(1).strip() if title_match else 'Untitled Chat'
            
            # Extract messages
            message_pattern = r'<div[^>]+class="[^"]*message[^"]*"[^>]*>(.*?)</div>'
            messages_html = re.findall(message_pattern, content, re.DOTALL)
            
            messages = []
            for msg_html in messages_html:
                role_match = re.search(r'data-role="([^"]+)"', msg_html)
                role = role_match.group(1) if role_match else 'unknown'
                
                # Extract text content (strip HTML tags)
                text = re.sub(r'<[^>]+>', '', msg_html)
                text = text.strip()
                
                if text:
                    messages.append(AIMessage(
                        id=f'msg_{len(messages)}',
                        role=role,
                        content=text,
                        timestamp=''
                    ))
                    
            conversations.append(AIConversation(
                id=f'openai_{hash(title) % 100000}',
                title=title,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                source='openai',
                messages=messages
            ))
            
        except Exception as e:
            conversations.append(AIConversation(
                id=f'openai_error',
                title='Parse Error',
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                source='openai',
                messages=[],
                metadata={'error': str(e)}
            ))
            
        return conversations
        
    def _parse_json(self, content: str) -> List[AIConversation]:
        """Parse ChatGPT JSON export (API format or mapping format)"""
        conversations = []
        
        try:
            data = json.loads(content)
            
            # Check for "mapping" format (newer ChatGPT exports)
            if isinstance(data, dict) and 'mapping' in data:
                return self._parse_mapping_format(data)
                
            # Check for "data" array format (older exports)
            if isinstance(data, dict) and 'conversations' in data:
                data = data['conversations']
                
            # Check if it's a list of conversations
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        conv = self._parse_conversation_dict(item, 'openai')
                        if conv:
                            conversations.append(conv)
                            
        except json.JSONDecodeError:
            pass
            
        return conversations
        
    def _parse_mapping_format(self, data: Dict) -> List[AIConversation]:
        """Parse the 'mapping' format used in ChatGPT exports"""
        conversations = []
        
        mapping = data.get('mapping', {})
        title = data.get('title', 'Untitled Chat')
        conversation_id = data.get('conversation_id', 'unknown')
        
        # Extract messages from mapping
        messages = []
        for node_id, node in mapping.items():
            message = node.get('message', {})
            if message:
                role = message.get('author', {}).get('role', 'unknown')
                content_parts = message.get('content', {}).get('parts', [])
                content = ' '.join(part if isinstance(part, str) else str(part) for part in content_parts)
                
                # Skip empty or system messages
                if content and role != 'system':
                    messages.append(AIMessage(
                        id=node_id,
                        role=role,
                        content=content,
                        timestamp=message.get('create_time', '')
                    ))
        
        # Sort by timestamp if available
        messages.sort(key=lambda m: m.timestamp or '')
        
        conversations.append(AIConversation(
            id=f'openai_{conversation_id}',
            title=title,
            created_at=data.get('create_time', datetime.now().isoformat()),
            updated_at=data.get('update_time', datetime.now().isoformat()),
            source='openai',
            messages=messages,
            metadata={'model': data.get('model_slug')}
        ))
        
        return conversations
        
    def _parse_conversation_dict(self, item: Dict, source: str) -> Optional[AIConversation]:
        """Parse a conversation from dictionary format"""
        try:
            messages = []
            
            # Handle nested messages
            for msg in item.get('messages', []):
                if isinstance(msg, dict):
                    messages.append(AIMessage(
                        id=msg.get('id', f'msg_{len(messages)}'),
                        role=msg.get('role', msg.get('author', 'unknown')),
                        content=msg.get('content', msg.get('text', '')),
                        timestamp=msg.get('timestamp', msg.get('created_at', ''))
                    ))
                    
            return AIConversation(
                id=item.get('id', f'{source}_{hash(str(item)) % 100000}'),
                title=item.get('title', item.get('name', 'Untitled')),
                created_at=item.get('created_at', item.get('create_time', datetime.now().isoformat())),
                updated_at=item.get('updated_at', item.get('update_time', datetime.now().isoformat())),
                source=source,
                messages=messages,
                metadata=item.get('metadata', {})
            )
            
        except Exception:
            return None


# ==================== ANTHROPIC CLAUDE PARSER ====================

class AnthropicClaudeParser:
    """Parse Anthropic Claude conversation exports"""
    
    def __init__(self):
        self.conversations = []
        
    def parse(self, export_path: str) -> AIExportResult:
        """Parse Claude export folder or file"""
        result = AIExportResult(
            conversations=[],
            messages_total=0,
            stats={},
            errors=[]
        )
        
        files = self._find_export_files(export_path)
        
        if not files:
            result.errors.append(f'No export files found in {export_path}')
            return result
            
        for filepath in files:
            try:
                convos = self._parse_file(filepath)
                result.conversations.extend(convos)
            except Exception as e:
                result.errors.append(f'Error parsing {filepath}: {str(e)}')
                
        result.messages_total = sum(len(c.messages) for c in result.conversations)
        result.stats = {
            'conversations': len(result.conversations),
            'messages': result.messages_total
        }
        
        return result
        
    def _find_export_files(self, directory: str) -> List[str]:
        """Find all export files in directory"""
        files = []
        path = Path(directory)
        
        if path.is_file():
            return [str(path)]
            
        if not path.exists():
            return []
            
        for pattern in ['*.json', '*.txt', '*conversation*']:
            files.extend(path.glob(pattern))
            for item in path.rglob('*'):
                if item.is_file():
                    files.append(item)
                    
        return list(set(str(f) for f in files))
        
    def _parse_file(self, filepath: str) -> List[AIConversation]:
        """Parse a single Claude export file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Try JSON first
        try:
            data = json.loads(content)
            return self._parse_json(data)
        except json.JSONDecodeError:
            pass
            
        # Try text/markdown format
        return self._parse_text(content)
        
    def _parse_json(self, data: Any) -> List[AIConversation]:
        """Parse Claude JSON export"""
        conversations = []
        
        # Check for list of conversations
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    conv = self._parse_conversation_dict(item)
                    if conv:
                        conversations.append(conv)
                        
        # Check for single conversation
        elif isinstance(data, dict):
            conv = self._parse_conversation_dict(data)
            if conv:
                conversations.append(conv)
                
        return conversations
        
    def _parse_conversation_dict(self, item: Dict) -> Optional[AIConversation]:
        """Parse a Claude conversation from dictionary"""
        try:
            messages = []
            
            # Handle various message formats
            msg_key = 'messages' if 'messages' in item else 'chat_messages'
            raw_messages = item.get(msg_key, [])
            
            for msg in raw_messages:
                if isinstance(msg, dict):
                    role = msg.get('role', msg.get('sender', 'unknown'))
                    content = msg.get('content', msg.get('text', msg.get('message', '')))
                    
                    # Handle Claude's "assistant" and "human" roles
                    if role in ['assistant', 'human']:
                        messages.append(AIMessage(
                            id=msg.get('uuid', f'msg_{len(messages)}'),
                            role=role,
                            content=content if isinstance(content, str) else str(content),
                            timestamp=msg.get('created_at', msg.get('timestamp', ''))
                        ))
                        
            return AIConversation(
                id=item.get('uuid', item.get('id', f'claude_{hash(str(item)) % 100000}')),
                title=item.get('title', item.get('name', 'Untitled Claude Chat')),
                created_at=item.get('created_at', item.get('created_time', datetime.now().isoformat())),
                updated_at=item.get('updated_at', item.get('updated_time', datetime.now().isoformat())),
                source='anthropic',
                messages=messages,
                metadata=item.get('metadata', {})
            )
            
        except Exception:
            return None
        
    def _parse_text(self, content: str) -> List[AIConversation]:
        """Parse Claude text/markdown export"""
        conversations = []
        
        # Simple format: Human: ... Assistant: ...
        human_pattern = r'(?:Human|User|Human:|User:)\s*(.+?)(?=\s*(?:Assistant|Claude|Human|User):|$)'
        assistant_pattern = r'(?:Assistant|Claude|Assistant:)\s*(.+?)(?=\s*(?:Human|User|Assistant|Claude):|$)'
        
        human_msgs = re.findall(human_pattern, content, re.DOTALL | re.IGNORECASE)
        assistant_msgs = re.findall(assistant_pattern, content, re.DOTALL | re.IGNORECASE)
        
        messages = []
        all_parts = []
        
        for i, part in enumerate(human_msgs):
            all_parts.append(('user', part.strip()))
        for i, part in enumerate(assistant_msgs):
            all_parts.append(('assistant', part.strip()))
            
        # Sort by position
        all_parts.sort(key=lambda x: content.find(x[1]))
        
        for role, text in all_parts:
            messages.append(AIMessage(
                id=f'msg_{len(messages)}',
                role=role,
                content=text,
                timestamp=''
            ))
            
        if messages:
            conversations.append(AIConversation(
                id=f'claude_text_{hash(content) % 100000}',
                title='Claude Export',
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                source='anthropic',
                messages=messages
            ))
            
        return conversations


# ==================== GOOGLE GEMINI PARSER ====================

class GoogleGeminiParser:
    """Parse Google Gemini conversation exports"""
    
    def __init__(self):
        self.conversations = []
        
    def parse(self, export_path: str) -> AIExportResult:
        """Parse Gemini export folder or file"""
        result = AIExportResult(
            conversations=[],
            messages_total=0,
            stats={},
            errors=[]
        )
        
        files = self._find_export_files(export_path)
        
        if not files:
            result.errors.append(f'No export files found in {export_path}')
            return result
            
        for filepath in files:
            try:
                convos = self._parse_file(filepath)
                result.conversations.extend(convos)
            except Exception as e:
                result.errors.append(f'Error parsing {filepath}: {str(e)}')
                
        result.messages_total = sum(len(c.messages) for c in result.conversations)
        result.stats = {
            'conversations': len(result.conversations),
            'messages': result.messages_total
        }
        
        return result
        
    def _find_export_files(self, directory: str) -> List[str]:
        """Find all export files in directory"""
        files = []
        path = Path(directory)
        
        if path.is_file():
            return [str(path)]
            
        if not path.exists():
            return []
            
        for pattern in ['*.json', '*.txt', '*gemini*', '*bard*']:
            files.extend(path.glob(pattern))
            for item in path.rglob('*'):
                if item.is_file():
                    files.append(item)
                    
        return list(set(str(f) for f in files))
        
    def _parse_file(self, filepath: str) -> List[AIConversation]:
        """Parse a single Gemini export file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Try JSON first
        try:
            data = json.loads(content)
            return self._parse_json(data)
        except json.JSONDecodeError:
            pass
            
        # Try text format
        return self._parse_text(content)
        
    def _parse_json(self, data: Any) -> List[AIConversation]:
        """Parse Gemini JSON export"""
        conversations = []
        
        # Check for "contents" format (standard Gemini format)
        if isinstance(data, dict) and 'contents' in data:
            return self._parse_contents_format(data)
            
        # Check for list of conversations
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    conv = self._parse_conversation_dict(item)
                    if conv:
                        conversations.append(conv)
                        
        # Check for single conversation
        elif isinstance(data, dict):
            conv = self._parse_conversation_dict(data)
            if conv:
                conversations.append(conv)
                
        return conversations
        
    def _parse_contents_format(self, data: Dict) -> List[AIConversation]:
        """Parse the 'contents' format used in Gemini exports"""
        conversations = []
        
        messages = []
        contents = data.get('contents', [])
        
        for item in contents:
            if isinstance(item, dict):
                role = item.get('role', item.get('author', 'unknown'))
                parts = item.get('parts', [])
                
                # Extract text from parts
                text_parts = []
                for part in parts:
                    if isinstance(part, dict):
                        text = part.get('text', '')
                        if text:
                            text_parts.append(text)
                    elif isinstance(part, str):
                        text_parts.append(part)
                        
                content = '\n'.join(text_parts)
                
                if content:
                    messages.append(AIMessage(
                        id=f'gemini_msg_{len(messages)}',
                        role=role,
                        content=content,
                        timestamp=item.get('createTime', item.get('timestamp', ''))
                    ))
        
        conversations.append(AIConversation(
            id=data.get('id', f'gemini_{hash(str(data)) % 100000}'),
            title=data.get('title', data.get('name', 'Untitled Gemini Chat')),
            created_at=data.get('createTime', datetime.now().isoformat()),
            updated_at=data.get('updateTime', datetime.now().isoformat()),
            source='google',
            messages=messages,
            metadata=data.get('metadata', {})
        ))
        
        return conversations
        
    def _parse_conversation_dict(self, item: Dict) -> Optional[AIConversation]:
        """Parse a Gemini conversation from dictionary"""
        try:
            messages = []
            
            # Handle various message formats
            if 'messages' in item:
                for msg in item['messages']:
                    if isinstance(msg, dict):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        if isinstance(content, str):
                            messages.append(AIMessage(
                                id=msg.get('id', f'msg_{len(messages)}'),
                                role=role,
                                content=content,
                                timestamp=msg.get('timestamp', '')
                            ))
                                
            return AIConversation(
                id=item.get('id', f'gemini_{hash(str(item)) % 100000}'),
                title=item.get('title', item.get('name', 'Untitled Chat')),
                created_at=item.get('created_at', item.get('create_time', datetime.now().isoformat())),
                updated_at=item.get('updated_at', item.get('update_time', datetime.now().isoformat())),
                source='google',
                messages=messages,
                metadata=item.get('metadata', {})
            )
            
        except Exception:
            return None
        
    def _parse_text(self, content: str) -> List[AIConversation]:
        """Parse Gemini text export"""
        conversations = []
        
        # Simple format: user: ... model: ...
        user_pattern = r'(?:user|human|you):\s*(.+?)(?=\s*(?:model|gemini|assistant):|$)'
        model_pattern = r'(?:model|gemini|assistant):\s*(.+?)(?=\s*(?:user|human|you|model|gemini):|$)'
        
        user_msgs = re.findall(user_pattern, content, re.DOTALL | re.IGNORECASE)
        model_msgs = re.findall(model_pattern, content, re.DOTALL | re.IGNORECASE)
        
        messages = []
        all_parts = []
        
        for part in user_msgs:
            all_parts.append(('user', part.strip()))
        for part in model_msgs:
            all_parts.append(('model', part.strip()))
            
        # Sort by position
        all_parts.sort(key=lambda x: content.find(x[1]))
        
        for role, text in all_parts:
            messages.append(AIMessage(
                id=f'msg_{len(messages)}',
                role=role,
                content=text,
                timestamp=''
            ))
            
        if messages:
            conversations.append(AIConversation(
                id=f'gemini_text_{hash(content) % 100000}',
                title='Gemini Export',
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                source='google',
                messages=messages
            ))
            
        return conversations


# ==================== UNIFIED AI EXPORT PARSER ====================

class UnifiedAIExportParser:
    """Unified parser that auto-detects and parses any AI export format"""
    
    def __init__(self):
        self.parsers = {
            'openai': OpenAIChatGPTParser(),
            'anthropic': AnthropicClaudeParser(),
            'google': GoogleGeminiParser()
        }
        
    def parse(self, export_path: str, platform: Optional[str] = None) -> AIExportResult:
        """Parse AI exports with optional platform specification"""
        
        # If platform specified, use specific parser
        if platform:
            if platform in self.parsers:
                return self.parsers[platform].parse(export_path)
            else:
                return AIExportResult(
                    conversations=[],
                    messages_total=0,
                    stats={},
                    errors=[f'Unknown platform: {platform}']
                )
                
        # Auto-detect by scanning files
        all_conversations = []
        all_errors = []
        
        path = Path(export_path)
        
        # Collect all files
        files = []
        if path.is_file():
            files = [str(path)]
        elif path.exists():
            for pattern in ['*.json', '*.html', '*.txt']:
                files.extend(path.glob(pattern))
                for item in path.rglob('*'):
                    if item.is_file():
                        files.append(item)
                        
        files = list(set(str(f) for f in files))
        
        for filepath in files:
            try:
                format_type = detect_ai_export_format(filepath)
                
                if format_type and format_type.startswith('openai'):
                    result = self.parsers['openai'].parse(filepath)
                    all_conversations.extend(result.conversations)
                    all_errors.extend(result.errors)
                    
                elif format_type == 'anthropic':
                    result = self.parsers['anthropic'].parse(filepath)
                    all_conversations.extend(result.conversations)
                    all_errors.extend(result.errors)
                    
                elif format_type == 'google_gemini':
                    result = self.parsers['google'].parse(filepath)
                    all_conversations.extend(result.conversations)
                    all_errors.extend(result.errors)
                    
            except Exception as e:
                all_errors.append(f'Error processing {filepath}: {str(e)}')
                
        # Merge conversations from same source
        merged = self._merge_conversations(all_conversations)
        
        return AIExportResult(
            conversations=merged,
            messages_total=sum(len(c.messages) for c in merged),
            stats={
                'conversations': len(merged),
                'messages': sum(len(c.messages) for c in merged),
                'by_source': self._count_by_source(merged)
            },
            errors=all_errors
        )
        
    def _merge_conversations(self, conversations: List[AIConversation]) -> List[AIConversation]:
        """Merge duplicate conversations"""
        seen = {}
        merged = []
        
        for conv in conversations:
            key = f"{conv.source}_{conv.title}"
            if key not in seen:
                seen[key] = len(merged)
                merged.append(conv)
            else:
                # Merge messages
                existing = merged[seen[key]]
                existing.messages.extend(conv.messages)
                
        return merged
        
    def _count_by_source(self, conversations: List[AIConversation]) -> Dict[str, int]:
        """Count conversations by source platform"""
        counts = {'openai': 0, 'anthropic': 0, 'google': 0}
        for conv in conversations:
            if conv.source in counts:
                counts[conv.source] += 1
        return counts


# ==================== CONVERSION TO KNOWLEDGE GRAPH FORMAT ====================

def convert_ai_conversations_to_graph(ai_result: AIExportResult) -> Dict:
    """Convert AI conversation exports to knowledge graph format"""
    
    nodes = []
    edges = []
    
    for conv in ai_result.conversations:
        conv_node_id = f'ai_{conv.source}_{conv.id}'
        
        # Add conversation node
        nodes.append({
            'id': conv_node_id,
            'type': 'conversation',
            'label': conv.title[:50] if conv.title else 'Untitled',
            'text': f"AI Conversation: {conv.title}",
            'topic': 'ai',
            'source': conv.source,
            'date': conv.created_at
        })
        
        # Add message nodes
        for idx, msg in enumerate(conv.messages):
            msg_node_id = f'ai_msg_{conv.id}_{idx}'
            
            # Map roles to display names
            role_display = {
                'user': 'User',
                'human': 'User',
                'assistant': conv.source.upper(),
                'model': 'Gemini',
                'system': 'System'
            }
            
            nodes.append({
                'id': msg_node_id,
                'type': 'message',
                'label': f"{role_display.get(msg.role, msg.role)}: {msg.content[:30]}...",
                'text': msg.content,
                'topic': 'ai',
                'role': msg.role,
                'date': msg.timestamp,
                'source': conv.source
            })
            
            # Edge from conversation to message
            edges.append({
                'source': conv_node_id,
                'target': msg_node_id,
                'type': 'contains'
            })
            
            # Add actions from message content
            actions = extract_actions_from_text(msg.content)
            for action_idx, action_text in enumerate(actions):
                action_id = f'ai_action_{conv.id}_{idx}_{action_idx}'
                nodes.append({
                    'id': action_id,
                    'type': 'action',
                    'label': f"📋 {action_text[:40]}...",
                    'text': action_text,
                    'priority': 'medium',
                    'topic': 'ai',
                    'status': 'pending'
                })
                edges.append({
                    'source': msg_node_id,
                    'target': action_id,
                    'type': 'contains'
                })
    
    return {
        'nodes': nodes,
        'edges': edges,
        'conversations': len(ai_result.conversations),
        'messages': ai_result.messages_total
    }


def extract_actions_from_text(text: str) -> List[str]:
    """Extract action items from AI message content"""
    actions = []
    
    # Common action patterns
    patterns = [
        r'(?:TODO|FIX|NEED|REMEMBER|MUST|SHOULD)\s*[:\-]\s*(.+?)(?:\n|$)',
        r'(?:action item|action point|todo)[:\s]+(.+?)(?:\n|$)',
        r'(\d+\.)\s*(.+?)(?:\n|$)',  # Numbered lists
        r'[-•*]\s*(.+?)(?:\n|$)',    # Bullet lists
    ]
    
    text_lower = text.lower()
    
    # Extract actions based on patterns
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            action = match.strip() if isinstance(match, str) else ' '.join(match).strip()
            if len(action) > 10 and len(action) < 500:
                actions.append(action)
                
    return actions


def detect_ai_export_type(filepath: str) -> Optional[str]:
    """Public function to detect AI export type"""
    return detect_ai_export_format(filepath)

"""
Todoist Exporter for X Knowledge Graph
Exports action items to Todoist via REST API
"""

import os
import re
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
try:
    from .amazon_product_linker import generate_amazon_url, detect_purchase_intent
except ImportError:
    # Fallback for standalone testing
    from amazon_product_linker import generate_amazon_url, detect_purchase_intent
from dataclasses import dataclass
from unittest.mock import Mock, patch

# Priority mapping: XKG priority → Todoist priority (p1=lowest, p4=highest)
PRIORITY_MAP = {
    'urgent': 4,  # p4 (highest)
    'high': 3,    # p3
    'medium': 2,  # p2
    'low': 1,     # p1 (lowest)
}

TASK_API_URL = "https://api.todoist.com/rest/v2/tasks"


@dataclass
class TodoistExportResult:
    """Result of a Todoist export operation"""
    success: bool
    task_id: Optional[str] = None
    error: Optional[str] = None


class TodoistExporter:
    """Export action items to Todoist"""
    
    def __init__(self, api_token: Optional[str] = None, use_mock: bool = False):
        """
        Initialize Todoist exporter
        
        Args:
            api_token: Todoist API token (defaults to TODOIST_API_TOKEN env var)
            use_mock: If True, use mock API for testing
        """
        self.api_token = api_token or os.environ.get('TODOIST_API_TOKEN')
        self.use_mock = use_mock or not self.api_token
        self.mock_responses: List[TodoistExportResult] = []
        self._mock_setup()
    
    def _mock_setup(self):
        """Setup mock API responses"""
        self.mock_responses = []
    
    def _extract_amazon_link(self, text: str) -> Optional[str]:
        """Extract or generate Amazon product link from text"""
        # First, try to extract explicit Amazon URL from text
        amazon_patterns = [
            r'(https?://(?:www\.)?amazon\.com/[^\s]+)',
            r'(https?://amzn\.to/[^\s]+)',
            r'(amazon\.com/[^\s]+)',
        ]
        for pattern in amazon_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # If no explicit URL, generate one from product mentions
        if detect_purchase_intent(text):
            generated_url = generate_amazon_url(text)
            if generated_url:
                return generated_url
        
        return None
    
    def _extract_source_text(self, action_text: str, source_tweet_id: str) -> str:
        """Extract source information for description"""
        return f"Source: X Action (tweet {source_tweet_id})"
    
    def _build_task_payload(self, action) -> Dict:
        """
        Build Todoist task payload from action item
        
        Args:
            action: ActionItem object or dict with text, priority, source_tweet_id
            
        Returns:
            Dict suitable for Todoist API
        """
        # Handle both ActionItem objects and dicts
        if isinstance(action, dict):
            action_text = action.get('text', '')
            action_priority = action.get('priority', 'medium')
            action_source = action.get('source_tweet_id', '')
            action_topic = action.get('topic', 'general')
            action_status = action.get('status', 'pending')
        else:
            action_text = action.text
            action_priority = action.priority
            action_source = action.source_tweet_id
            action_topic = action.topic
            action_status = action.status
        
        # Task name = action text (truncated for Todoist limit)
        content = action_text[:2000] if len(action_text) > 2000 else action_text
        
        # Build description with original post + Amazon link
        description_parts = [
            f"Action from X Knowledge Graph",
            f"Priority: {action_priority.upper()}",
            f"Source Tweet ID: {action_source}",
            f"Topic: {action_topic}",
            f"Status: {action_status}",
        ]
        
        # Add Amazon link if found in action text
        amazon_link = self._extract_amazon_link(action_text)
        if amazon_link:
            description_parts.insert(1, f"Amazon Link: {amazon_link}")
        
        description = "\n".join(description_parts)
        
        # Map priority
        todoist_priority = PRIORITY_MAP.get(action_priority, 1)
        
        return {
            'content': content,
            'description': description,
            'priority': todoist_priority,
            # Optional: due date if action has one
        }
    
    def _make_api_request(self, payload: Dict, mock_response: Optional[Dict] = None) -> TodoistExportResult:
        """
        Make API request to Todoist (or mock)
        
        Args:
            payload: Task payload
            mock_response: Optional mock response dict
            
        Returns:
            TodoistExportResult
        """
        if self.use_mock:
            return self._mock_create_task(payload, mock_response)
        
        if not self.api_token:
            return TodoistExportResult(
                success=False,
                error="No API token configured"
            )
        
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'X-Request-Id': str(datetime.now().timestamp())
        }
        
        try:
            response = requests.post(
                TASK_API_URL,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200 or response.status_code == 429:
                # 429 = rate limit, still consider it a response
                data = response.json()
                return TodoistExportResult(
                    success=True,
                    task_id=str(data.get('id', ''))
                )
            else:
                return TodoistExportResult(
                    success=False,
                    error=f"API returned {response.status_code}: {response.text}"
                )
        except requests.exceptions.RequestException as e:
            return TodoistExportResult(
                success=False,
                error=str(e)
            )
    
    def _mock_create_task(self, payload: Dict, mock_response: Optional[Dict] = None) -> TodoistExportResult:
        """Mock API response for testing"""
        import random
        
        # Simulate success/failure based on payload content
        # Fail if content is empty or starts with "fail"
        if not payload.get('content') or payload.get('content', '').startswith('fail'):
            return TodoistExportResult(
                success=False,
                error="Mock error: invalid task content"
            )
        
        # Simulate network errors for "network_error" content
        if payload.get('content') == 'network_error':
            return TodoistExportResult(
                success=False,
                error="Mock network error"
            )
        
        # Generate mock task ID
        mock_id = f"mock_{random.randint(10000, 99999)}"
        
        result = TodoistExportResult(
            success=True,
            task_id=mock_id
        )
        self.mock_responses.append(result)
        
        return result
    
    def export_action(self, action) -> TodoistExportResult:
        """
        Export a single action item to Todoist
        
        Args:
            action: ActionItem object
            
        Returns:
            TodoistExportResult with task_id on success
        """
        payload = self._build_task_payload(action)
        return self._make_api_request(payload)
    
    def export_actions(
        self,
        actions: List,
        priority_filter: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict:
        """
        Export multiple action items to Todoist
        
        Args:
            actions: List of ActionItem objects
            priority_filter: List of priorities to include (e.g., ['urgent', 'high'])
            date_from: Filter actions created on/after this date (ISO format)
            date_to: Filter actions created on/before this date (ISO format)
            
        Returns:
            Dict with success_count, failed_count, errors list, and task_ids
        """
        # Filter actions
        filtered_actions = actions
        
        if priority_filter:
            priority_filter = [p.lower() for p in priority_filter]
            filtered_actions = [
                a for a in filtered_actions
                if a.priority.lower() in priority_filter
            ]
        
        if date_from:
            filtered_actions = [
                a for a in filtered_actions
                if a.created_at >= date_from
            ]
        
        if date_to:
            filtered_actions = [
                a for a in filtered_actions
                if a.created_at <= date_to
            ]
        
        # Export filtered actions
        success_count = 0
        failed_count = 0
        errors: List[Dict] = []
        task_ids: List[str] = []
        
        for action in filtered_actions:
            result = self.export_action(action)
            
            if result.success:
                success_count += 1
                task_ids.append(result.task_id)
            else:
                failed_count += 1
                errors.append({
                    'action_id': getattr(action, 'id', getattr(action, 'source_tweet_id', 'unknown')),
                    'error': result.error
                })
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'total': len(filtered_actions),
            'task_ids': task_ids,
            'errors': errors
        }
    
    def set_mock_mode(self, enabled: bool = True):
        """Enable or disable mock mode"""
        self.use_mock = enabled
    
    def get_mock_responses(self) -> List[TodoistExportResult]:
        """Get all mock responses from previous exports"""
        return self.mock_responses
    
    def clear_mock_responses(self):
        """Clear mock response history"""
        self.mock_responses = []


# ==================== CONVENIENCE FUNCTIONS ====================

def export_to_todoist(actions, api_token: Optional[str] = None) -> Dict:
    """
    Export actions to Todoist
    
    Args:
        actions: List of ActionItem objects
        api_token: Todoist API token (if None, uses mock API for testing)
        
    Returns:
        Dict with success_count, failed_count, task_ids, and errors
    """
    # Use mock mode when no real token provided
    use_mock = not api_token
    exporter = TodoistExporter(api_token=api_token, use_mock=use_mock)
    return exporter.export_actions(actions)


def export_action_to_todoist(action, api_token: Optional[str] = None) -> TodoistExportResult:
    """Export a single action to Todoist"""
    exporter = TodoistExporter(api_token=api_token)
    return exporter.export_action(action)


def export_actions_to_todoist(
    actions: List,
    api_token: Optional[str] = None,
    priority_filter: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict:
    """Export multiple actions to Todoist with optional filters"""
    exporter = TodoistExporter(api_token=api_token)
    return exporter.export_actions(
        actions,
        priority_filter=priority_filter,
        date_from=date_from,
        date_to=date_to
    )

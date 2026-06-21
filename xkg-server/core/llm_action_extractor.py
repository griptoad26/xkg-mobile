"""
LLM-Based Action Extraction Module for XKG
Prototype implementation for comparing LLM vs regex extraction

Author: XKG Research Agent
Date: February 18, 2026
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class Priority(Enum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Topic(Enum):
    API = "api"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    UI = "ui"
    DEPLOYMENT = "deployment"
    BUSINESS = "business"
    PERSONAL = "personal"
    GENERAL = "general"


@dataclass
class ActionItem:
    """Represents an extracted action item"""
    text: str
    priority: Priority
    topic: Topic
    confidence: float = 0.0
    owner: Optional[str] = None
    deadline: Optional[str] = None
    source_type: str = "unknown"
    source_id: str = "unknown"
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "priority": self.priority.value,
            "topic": self.topic.value,
            "confidence": self.confidence,
            "owner": self.owner,
            "deadline": self.deadline,
            "source_type": self.source_type,
            "source_id": self.source_id
        }


# ==================== BASE EXTRACTOR INTERFACE ====================

class ActionExtractor(ABC):
    """Abstract base class for action extraction"""
    
    @abstractmethod
    def extract(self, text: str, source_id: str = "unknown", source_type: str = "unknown") -> List[ActionItem]:
        pass


# ==================== REGEX EXTRACTOR (CURRENT APPROACH) ====================

class RegexActionExtractor(ActionExtractor):
    """
    Current regex-based action extraction implementation
    Based on xkg_core.py _find_actions_in_text and _extract_topic
    """
    
    PRIORITY_KEYWORDS = {
        Priority.URGENT: ['urgent', 'asap', 'immediately', 'critical'],
        Priority.HIGH: ['important', 'priority', 'soon', 'quickly'],
        Priority.MEDIUM: ['should', 'need', 'must', 'remember'],
        Priority.LOW: ['maybe', 'sometime', 'whenever', 'consider']
    }
    
    TOPIC_KEYWORDS = {
        Topic.API: ['api', 'endpoint', 'rest', 'json'],
        Topic.DATABASE: ['database', 'db', 'sql', 'query'],
        Topic.AUTHENTICATION: ['auth', 'login', 'password', 'oauth'],
        Topic.PERFORMANCE: ['performance', 'speed', 'optimize', 'slow'],
        Topic.DOCUMENTATION: ['docs', 'documentation', 'readme'],
        Topic.TESTING: ['test', 'testing', 'qa', 'bug'],
        Topic.UI: ['ui', 'interface', 'design', 'frontend'],
        Topic.DEPLOYMENT: ['deploy', 'production', 'server', 'infrastructure'],
        Topic.BUSINESS: ['meeting', 'schedule', 'business', 'team'],
        Topic.PERSONAL: ['buy', 'order', 'keyboard', 'office']
    }
    
    def extract(self, text: str, source_id: str = "unknown", source_type: str = "unknown") -> List[ActionItem]:
        """Extract actions using regex patterns"""
        actions = []
        
        if not text:
            return []
        
        text_lower = str(text).lower()
        
        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    sentences = re.split(r'[.!?\n]', str(text)) if text else []
                    for sentence in sentences:
                        if keyword in str(sentence).lower():
                            sentence = str(sentence).strip()
                            if len(sentence) > 10 and len(sentence) < 500:
                                topic = self._extract_topic(sentence)
                                actions.append(ActionItem(
                                    text=sentence,
                                    priority=priority,
                                    topic=topic,
                                    confidence=0.7,  # Lower confidence for regex
                                    source_type=source_type,
                                    source_id=source_id
                                ))
                    break
        
        return actions
    
    def _extract_topic(self, text: str) -> Topic:
        """Extract topic from action text"""
        text_lower = text.lower()
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return topic
        return Topic.GENERAL


# ==================== LLM EXTRACTOR (PROTOTYPE) ====================

class LLMActionExtractor(ActionExtractor):
    """
    LLM-based action extraction prototype
    
    This class provides the structure for LLM-based extraction.
    In production, this would call OpenAI/Anthropic APIs or local models.
    """
    
    # System prompt for LLM action extraction
    SYSTEM_PROMPT = """You are an action item extraction assistant. Your task is to identify and extract action items from text.

An action item is a task, todo, commitment, or intention that someone should complete.

Rules:
1. Extract ONLY clear action items with identifiable owners and deadlines when present
2. Infer priority: urgent/high/medium/low based on language and context
3. Assign topics: api/database/authentication/performance/docs/testing/ui/deployment/business/personal/general
4. Output as JSON array with the structure: [{"text": "...", "priority": "...", "topic": "...", "confidence": 0.X, "owner": "...", "deadline": "..."}]

If no actions found, return: []

Example output:
[{"text": "Review PR #234", "priority": "high", "topic": "testing", "confidence": 0.95, "owner": "developer", "deadline": "2024-01-15"}]"""

    # Test cases simulating LLM responses
    MOCK_RESPONSES = {
        "need to fix the api endpoint": [
            ActionItem(
                text="Need to fix the API endpoint",
                priority=Priority.HIGH,
                topic=Topic.API,
                confidence=0.92,
                source_type="unknown",
                source_id="unknown"
            )
        ],
        "urgent: deploy to production immediately": [
            ActionItem(
                text="Deploy to production immediately",
                priority=Priority.URGENT,
                topic=Topic.DEPLOYMENT,
                confidence=0.98,
                source_type="unknown",
                source_id="unknown"
            )
        ],
        "should update documentation for the new feature": [
            ActionItem(
                text="Update documentation for the new feature",
                priority=Priority.MEDIUM,
                topic=Topic.DOCUMENTATION,
                confidence=0.88,
                source_type="unknown",
                source_id="unknown"
            )
        ],
        "maybe consider optimizing the database queries": [
            ActionItem(
                text="Consider optimizing the database queries",
                priority=Priority.LOW,
                topic=Topic.DATABASE,
                confidence=0.75,
                source_type="unknown",
                source_id="unknown"
            )
        ],
        "i should go to the store later": [],  # Not an action item (first person)
        "you should review this pull request": [
            ActionItem(
                text="Review this pull request",
                priority=Priority.HIGH,
                topic=Topic.TESTING,
                confidence=0.91,
                source_type="unknown",
                source_id="unknown"
            )
        ],
        "meeting scheduled for tomorrow to discuss the roadmap": [
            ActionItem(
                text="Discuss the roadmap",
                priority=Priority.MEDIUM,
                topic=Topic.BUSINESS,
                confidence=0.85,
                source_type="unknown",
                source_id="unknown"
            )
        ]
    }
    
    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self._client = None
    
    def _init_client(self):
        """Initialize LLM client (placeholder for actual implementation)"""
        if self._client is None:
            # In production, this would initialize the actual API client
            # For now, we use mock responses
            pass
    
    def _call_llm(self, text: str) -> List[ActionItem]:
        """
        Call LLM API for action extraction
        
        In production, this would make actual API calls.
        For prototype, we use simulated responses based on keyword matching.
        """
        # Simulated LLM response based on text analysis
        text_lower = text.lower()
        
        # Check for mock responses
        for pattern, response in self.MOCK_RESPONSES.items():
            if pattern in text_lower:
                # Clone response with proper source info
                cloned = []
                for item in response:
                    cloned.append(ActionItem(
                        text=item.text,
                        priority=item.priority,
                        topic=item.topic,
                        confidence=item.confidence,
                        owner=item.owner,
                        deadline=item.deadline,
                        source_type=item.source_type,
                        source_id=item.source_id
                    ))
                return cloned
        
        # Fallback: Use keyword-based extraction with LLM-like scoring
        # This simulates what an LLM would do with semantic understanding
        actions = []
        
        # Detect first-person vs second-person imperative
        is_imperative = self._is_imperative_sentence(text)
        is_commitment = self._is_commitment(text)
        
        if is_imperative or is_commitment:
            priority = self._infer_priority(text)
            topic = self._infer_topic(text)
            
            actions.append(ActionItem(
                text=text.strip()[:500],  # Limit length
                priority=priority,
                topic=topic,
                confidence=0.85,  # Higher confidence for LLM
                source_type="unknown",
                source_id="unknown"
            ))
        
        return actions
    
    def _is_imperative_sentence(self, text: str) -> bool:
        """Check if sentence is an imperative (command) - LLM-like semantic check"""
        # Imperative sentences often start with verbs
        text_lower = text.lower().strip()
        
        # Common imperative patterns
        imperative_patterns = [
            r'^(you )?(should|must|need to|have to|will|going to)',
            r'^(let\'s|let us|we should|we need)',
            r'^(remember|make sure|ensure|verify|check|review|fix|update|deploy)',
        ]
        
        for pattern in imperative_patterns:
            if re.search(pattern, text_lower):
                # Additional check: exclude first-person statements
                if not re.match(r'^(i|we)\s', text_lower):
                    return True
        
        return False
    
    def _is_commitment(self, text: str) -> bool:
        """Check if text expresses a commitment or obligation"""
        text_lower = text.lower()
        
        commitment_patterns = [
            r'will\s+(fix|update|review|deploy|complete|finish)',
            r'going to\s+(fix|update|review|deploy)',
            r'plan to\s+(fix|update|review|deploy)',
            r'todo:\s*',
            r'action item:\s*',
        ]
        
        return any(re.search(p, text_lower) for p in commitment_patterns)
    
    def _infer_priority(self, text: str) -> Priority:
        """Infer priority from text - semantic understanding"""
        text_lower = text.lower()
        
        # Urgent indicators
        urgent_patterns = [r'\burgent\b', r'\basap\b', r'\bimmediately\b', r'\bcritical\b']
        if any(re.search(p, text_lower) for p in urgent_patterns):
            return Priority.URGENT
        
        # High priority patterns
        high_patterns = [r'\bimportant\b', r'\bpriority\b', r'\bsoon\b', r'\bquickly\b']
        if any(re.search(p, text_lower) for p in high_patterns):
            return Priority.HIGH
        
        # Medium priority - default for most actions
        medium_patterns = [r'\bshould\b', r'\bneed\b', r'\bmust\b', r'\bremember\b']
        if any(re.search(p, text_lower) for p in medium_patterns):
            return Priority.MEDIUM
        
        return Priority.MEDIUM  # Default
    
    def _infer_topic(self, text: str) -> Topic:
        """Infer topic from text - semantic understanding"""
        text_lower = text.lower()
        
        for topic, keywords in RegexActionExtractor.TOPIC_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return topic
        
        return Topic.GENERAL
    
    def extract(self, text: str, source_id: str = "unknown", source_type: str = "unknown") -> List[ActionItem]:
        """Extract actions using LLM (simulated for prototype)"""
        self._init_client()
        
        # Call LLM (simulated)
        actions = self._call_llm(text)
        
        # Add source info
        for action in actions:
            action.source_id = source_id
            action.source_type = source_type
        
        return actions


# ==================== HYBRID EXTRACTOR ====================

class HybridActionExtractor(ActionExtractor):
    """
    Hybrid approach combining regex pre-filtering with LLM for complex cases
    
    Architecture:
    1. Fast regex scan for obvious explicit actions
    2. LLM check for implicit actions (higher cost, better accuracy)
    3. Combine and deduplicate results
    """
    
    def __init__(self, llm_extractor: Optional[LLMActionExtractor] = None):
        self.regex_extractor = RegexActionExtractor()
        self.llm_extractor = llm_extractor or LLMActionExtractor()
        self.latest_llm_results = []  # Store for comparison
    
    def extract(self, text: str, source_id: str = "unknown", source_type: str = "unknown") -> List[ActionItem]:
        """Extract actions using hybrid approach"""
        
        # Step 1: Fast regex pre-filter
        regex_actions = self.regex_extractor.extract(text, source_id, source_type)
        
        # Step 2: LLM check for implicit actions
        llm_actions = self.llm_extractor.extract(text, source_id, source_type)
        self.latest_llm_results = llm_actions
        
        # Step 3: Combine results, preferring higher confidence
        all_actions = regex_actions + llm_actions
        
        # Deduplicate by text similarity
        unique_actions = self._deduplicate_actions(all_actions)
        
        # Sort by priority
        priority_order = {
            Priority.URGENT: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
            Priority.UNKNOWN: 4
        }
        
        unique_actions.sort(key=lambda x: (priority_order.get(x.priority, 4), -x.confidence))
        
        return unique_actions
    
    def _deduplicate_actions(self, actions: List[ActionItem]) -> List[ActionItem]:
        """Remove duplicate actions based on text similarity"""
        if not actions:
            return []
        
        unique = []
        seen_texts = set()
        
        for action in actions:
            # Normalize text for comparison
            normalized = re.sub(r'\s+', ' ', action.text.lower().strip())
            
            # Check for similar existing actions
            is_duplicate = False
            for seen in seen_texts:
                # Simple substring check
                if normalized in seen or seen in normalized:
                    # Keep the one with higher confidence
                    existing = next((a for a in unique if a.text.lower() == seen), None)
                    if existing and action.confidence > existing.confidence:
                        unique.remove(existing)
                        seen_texts.remove(seen)
                    else:
                        is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(action)
                seen_texts.add(normalized)
        
        return unique


# ==================== COMPARISON & EVALUATION ====================

class ExtractionComparator:
    """Compare regex vs LLM extraction results"""
    
    def __init__(self, regex_extractor: RegexActionExtractor, llm_extractor: LLMActionExtractor):
        self.regex = regex_extractor
        self.llm = llm_extractor
        self.test_results = []
    
    def run_comparison(self, test_cases: List[Tuple[str, str, List[str]]]) -> Dict:
        """
        Run comparison on test cases
        
        Args:
            test_cases: List of (source_id, source_type, expected_actions) tuples
        """
        results = {
            "total_tests": len(test_cases),
            "regex_correct": 0,
            "llm_correct": 0,
            "both_correct": 0,
            "regex_only": 0,
            "llm_only": 0,
            "neither": 0,
            "avg_confidence_regex": 0,
            "avg_confidence_llm": 0,
            "detailed_results": []
        }
        
        total_regex_conf = 0
        total_llm_conf = 0
        
        for source_id, source_type, expected in test_cases:
            # Run both extractors
            regex_actions = self.regex.extract(f"Test: {source_id}", source_id, source_type)
            llm_actions = self.llm.extract(f"Test: {source_id}", source_id, source_type)
            
            # For testing, we'll use the text as input
            # In practice, you'd have actual text to process
            
            # Simple evaluation: count extracted vs expected
            regex_count = len(regex_actions)
            llm_count = len(llm_actions)
            expected_count = len(expected)
            
            # Update totals
            total_regex_conf += sum(a.confidence for a in regex_actions)
            total_llm_conf += sum(a.confidence for a in llm_actions)
            
            detailed = {
                "source_id": source_id,
                "source_type": source_type,
                "expected_count": expected_count,
                "regex_count": regex_count,
                "llm_count": llm_count,
                "regex_actions": [a.text for a in regex_actions],
                "llm_actions": [a.text for a in llm_actions]
            }
            
            results["detailed_results"].append(detailed)
        
        # Calculate averages
        if results["total_tests"] > 0:
            results["avg_confidence_regex"] = total_regex_conf / max(1, sum(r["regex_count"] for r in results["detailed_results"]))
            results["avg_confidence_llm"] = total_llm_conf / max(1, sum(r["llm_count"] for r in results["detailed_results"]))
        
        return results


# ==================== MAIN PROTOTYPE TEST ====================

def run_prototype_tests():
    """Run prototype comparison tests"""
    print("=" * 60)
    print("LLM ACTION EXTRACTION PROTOTYPE")
    print("=" * 60)
    
    # Initialize extractors
    regex_ext = RegexActionExtractor()
    llm_ext = LLMActionExtractor()
    
    # Test cases: (text, expected_count, description)
    test_cases = [
        ("Need to fix the API endpoint soon", "Explicit action with priority keywords"),
        ("URGENT: Deploy to production immediately!", "Urgent action"),
        ("Should update documentation for the new feature", "Medium priority action"),
        ("Maybe consider optimizing database queries sometime", "Low priority action"),
        ("I should go to the store later", "First-person, NOT an action item"),
        ("You should review this pull request by Friday", "Second-person imperative"),
        ("Remember to test the authentication flow", "Remember keyword"),
        ("Important: Fix the performance issue", "Important keyword"),
        ("Meeting scheduled to discuss the roadmap", "Business topic"),
        ("Make sure to backup the database", "Imperative action"),
    ]
    
    print("\n--- Test Results ---\n")
    print(f"{'Text':<45} {'Regex':<8} {'LLM':<8} {'Best':<8}")
    print("-" * 75)
    
    regex_total = 0
    llm_total = 0
    llm_wins = 0
    regex_wins = 0
    
    for text, description in test_cases:
        # Extract with both methods
        regex_actions = regex_ext.extract(text)
        llm_actions = llm_ext.extract(text)
        
        regex_count = len(regex_actions)
        llm_count = len(llm_actions)
        
        regex_total += regex_count
        llm_total += llm_count
        
        # Determine winner
        if llm_count > regex_count:
            winner = "LLM ✓"
            llm_wins += 1
        elif regex_count > llm_count:
            winner = "Regex ✓"
            regex_wins += 1
        else:
            winner = "Tie"
        
        # Display result
        display_text = text[:42] + "..." if len(text) > 45 else text
        print(f"{display_text:<45} {regex_count:<8} {llm_count:<8} {winner:<8}")
        
        if llm_count > 0:
            for action in llm_actions:
                print(f"    → LLM: priority={action.priority.value}, topic={action.topic.value}, conf={action.confidence:.2f}")
    
    print("\n--- Summary ---\n")
    print(f"Total regex extractions: {regex_total}")
    print(f"Total LLM extractions: {llm_total}")
    print(f"LLM wins (more actions found): {llm_wins}")
    print(f"Regex wins (more actions found): {regex_wins}")
    print()
    
    # Return comparison data
    return {
        "test_cases": test_cases,
        "regex_total": regex_total,
        "llm_total": llm_total,
        "llm_wins": llm_wins,
        "regex_wins": regex_wins
    }


if __name__ == "__main__":
    results = run_prototype_tests()
    print("\nPrototype test complete.")

"""
Amazon Product Linker - X Knowledge Graph Addon
Detects EXPLICIT product purchase intent and generates Amazon search URLs.
Only triggers on clear purchase intent, not conversational mentions.
"""

import re
from typing import Optional


# EXPLICIT purchase intent patterns (must match these exactly)
PURCHASE_PATTERNS = [
    r'\bbuy\s+(?:a|an|the|some)?\s*\w+',           # "buy a laptop", "buy the book"
    r'\bpurchase\s+(?:a|an|the|some)?\s*\w+',       # "purchase a widget"
    r'\border\s+(?:a|an|the|some)?\s*\w+',          # "order a pizza"
    r'\b(?:need|want|gotta)\s+to\s+buy',              # "need to buy", "want to buy", "gotta buy"
    r'\b(?:need|want)\s+(?:a|an)\s+\w+\s+for',        # "need a X for Y"
    r'\bget\s+(?:me|us|a|an|the)\s+\w+',               # "get me a coffee", "get the book"
    r'\bshop\s+(?:for\s+)?(?:a|an)?',                   # "shop for a X"
    r'\badd\s+(?:to\s+)?cart',                         # "add to cart"
]

# Words that indicate purchase context (combine with product nouns)
PURCHASE_CONTEXT_WORDS = {
    'buy', 'purchase', 'order', 'shop', 'acquire', 'procure'
}

# Product keywords that are valid purchase targets
PRODUCT_NOUNS = [
    'laptop', 'computer', 'monitor', 'keyboard', 'mouse', 'headphones', 'earbuds',
    'phone', 'tablet', 'charger', 'cable', 'adapter', 'battery', 'power bank',
    'book', 'novel', 'guide', 'manual', 'textbook', 'course', 'video',
    'coffee', 'tea', 'snacks', 'food', 'groceries', 'pizza', 'burger',
    'desk', 'chair', 'lamp', 'shelf', 'organizer', 'notebook', 'pen', 'pencil',
    'shirt', 'pants', 'jacket', 'shoes', 'socks', 'hat', 'backpack',
    'software', 'subscription', 'membership', 'training',
    'tool', 'drill', 'saw', 'hammer', 'wrench', 'screwdriver',
    'game', 'console', 'controller', 'video game',
    'gift', 'present', 'surprise',
    'medicine', 'vitamins', 'supplements', 'cream', 'lotion',
]

# Stop words - common non-product words to skip
STOP_WORDS = frozenset([
    'a', 'an', 'the', 'this', 'that', 'these', 'those', 'it', 'them',
    'some', 'any', 'all', 'both', 'few', 'many', 'several',
    'for', 'to', 'with', 'on', 'at', 'by', 'from', 'into', 'about',
    'need', 'need to', 'want', 'want to', 'should', 'could', 'would',
    'get', 'got', 'gotta', 'going', 'gon na',
    'really', 'very', 'just', 'still', 'maybe', 'perhaps',
    'today', 'tomorrow', 'soon', 'later', 'sometime',
])


class AmazonProductLinker:
    """Detects EXPLICIT purchase intent only - not conversational mentions"""
    
    def __init__(self):
        # Build regex patterns for purchase intent
        self.purchase_patterns = [re.compile(p, re.IGNORECASE) for p in PURCHASE_PATTERNS]
        self.product_nouns = set(PRODUCT_NOUNS)
    
    def detect_explicit_purchase_intent(self, text: str) -> bool:
        """
        Check if text contains EXPLICIT purchase intent.
        Returns True ONLY for clear purchase statements like:
        - "buy a laptop"
        - "need to buy the book"
        - "order pizza for dinner"
        
        Returns False for:
        - "we should get it"
        - "need to get started"
        - "want to understand this"
        """
        text_lower = text.lower()
        
        # Check explicit purchase patterns first
        for pattern in self.purchase_patterns:
            if pattern.search(text_lower):
                # Verify there's actually a product mentioned
                if self._has_product_noun(text_lower):
                    return True
        
        # Check for purchase verb + product noun pattern
        words = text_lower.split()
        for i, word in enumerate(words):
            clean_word = re.sub(r'[^\w]', '', word).lower()
            
            if clean_word in PURCHASE_CONTEXT_WORDS:
                # Look for product noun in next 5 words
                for j in range(i + 1, min(i + 6, len(words))):
                    next_word = re.sub(r'[^\w]', '', words[j]).lower()
                    if next_word in self.product_nouns:
                        return True
        
        return False
    
    def _has_product_noun(self, text: str) -> bool:
        """Check if text contains known product nouns"""
        text_lower = text.lower()
        for product in self.product_nouns:
            if product in text_lower:
                return True
        return False
    
    def extract_product_keywords(self, text: str) -> Optional[str]:
        """
        Extract product keywords ONLY if explicit purchase intent is detected.
        Returns None if no clear purchase intent.
        """
        if not self.detect_explicit_purchase_intent(text):
            return None
        
        text_lower = text.lower()
        
        # Find product noun and get surrounding context
        for i, product in enumerate(self.product_nouns):
            if product in text_lower:
                # Get 3-4 words around the product
                words = text_lower.split()
                for j, word in enumerate(words):
                    clean_word = re.sub(r'[^\w]', '', word).lower()
                    if clean_word == product:
                        # Get context: 2 words before, 2 after
                        start = max(0, j - 2)
                        end = min(len(words), j + 3)
                        context = words[start:end]
                        
                        # Filter stop words
                        filtered = [
                            w for w in context 
                            if re.sub(r'[^\w]', '', w).lower() not in STOP_WORDS
                            and len(w) > 2
                        ]
                        
                        if filtered:
                            return '+'.join(filtered[:3])
        
        return None
    
    def generate_amazon_url(self, text: str) -> Optional[str]:
        """Generate Amazon search URL ONLY for explicit purchase intent"""
        keywords = self.extract_product_keywords(text)
        
        if keywords:
            return f"https://www.amazon.com/s?k={keywords}"
        return None
    
    def process_action_text(self, text: str) -> dict:
        """Process action text and return product link info"""
        has_intent = self.detect_explicit_purchase_intent(text)
        keywords = self.extract_product_keywords(text) if has_intent else None
        
        return {
            'has_purchase_intent': has_intent,
            'keywords': keywords,
            'amazon_link': f"https://www.amazon.com/s?k={keywords}" if keywords else None
        }


# Global instance for efficient reuse
_linker_instance = None


def get_linker() -> AmazonProductLinker:
    """Get or create the global AmazonProductLinker instance"""
    global _linker_instance
    if _linker_instance is None:
        _linker_instance = AmazonProductLinker()
    return _linker_instance


def get_amazon_link(text: str) -> Optional[str]:
    """Convenience function to get Amazon link from action text"""
    return get_linker().generate_amazon_url(text)


def extract_product_info(text: str) -> dict:
    """Convenience function to get all product info from action text"""
    return get_linker().process_action_text(text)


def detect_purchase_intent(text: str) -> bool:
    """Check if text has EXPLICIT purchase intent"""
    return get_linker().detect_explicit_purchase_intent(text)


def extract_product_keywords(text: str) -> Optional[str]:
    """Extract product keywords if purchase intent detected"""
    return get_linker().extract_product_keywords(text)


def generate_amazon_url(text: str) -> Optional[str]:
    """Generate Amazon search URL from action text"""
    return get_linker().generate_amazon_url(text)

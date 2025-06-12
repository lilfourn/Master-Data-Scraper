"""
Relevance Analyzer - Intelligent content relevance scoring for web scraping

This module provides functionality to analyze and score the relevance of URLs
and content based on the initial seed URL, helping crawlers stay focused on
related content while avoiding unrelated links.
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from urllib.parse import urlparse, urljoin
from collections import Counter
import difflib
from bs4 import BeautifulSoup
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string

logger = logging.getLogger(__name__)

# Download required NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


class RelevanceAnalyzer:
    """Analyzes and scores the relevance of URLs and content"""
    
    def __init__(self, similarity_threshold: float = 0.3):
        """
        Initialize the relevance analyzer
        
        Args:
            similarity_threshold: Minimum similarity score to consider content related (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.seed_keywords: Set[str] = set()
        self.seed_domain: str = ""
        self.seed_path_tokens: List[str] = []
        self.stop_words = set(stopwords.words('english'))
        self.visited_patterns: Set[str] = set()
        
        # Patterns that typically indicate unrelated content
        self.unrelated_patterns = [
            r'/privacy[-_]?policy',
            r'/terms[-_]?(of[-_]?use|and[-_]?conditions)?',
            r'/cookie[-_]?policy',
            r'/contact[-_]?us?',
            r'/about[-_]?us?',
            r'/careers?',
            r'/jobs?',
            r'/advertise',
            r'/ads?/',
            r'/login',
            r'/signin',
            r'/signup',
            r'/register',
            r'/logout',
            r'/cart',
            r'/checkout',
            r'/share',
            r'/print',
            r'/email',
            r'/(twitter|facebook|linkedin|instagram|youtube)\.com',
            r'/rss',
            r'/feed',
            r'#comments?',
            r'\.(pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar)$',
        ]
        
        # Keywords that often indicate navigation or unrelated links
        self.navigation_keywords = {
            'home', 'menu', 'navigation', 'footer', 'header', 'sidebar',
            'copyright', 'legal', 'disclaimer', 'accessibility', 'sitemap',
            'help', 'support', 'faq', 'social', 'follow', 'share', 'subscribe'
        }
    
    def analyze_seed_content(self, url: str, content: str) -> None:
        """
        Analyze the seed URL and content to establish relevance baseline
        
        Args:
            url: The seed URL
            content: The HTML content of the seed page
        """
        # Parse seed URL
        parsed = urlparse(url)
        self.seed_domain = parsed.netloc
        self.seed_path_tokens = [t for t in parsed.path.split('/') if t]
        
        # Extract text and keywords from content
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Extract keywords from various sources
        self.seed_keywords = self._extract_keywords(text)
        
        # Add keywords from title
        if soup.title:
            title_keywords = self._extract_keywords(soup.title.string or "")
            self.seed_keywords.update(title_keywords)
        
        # Add keywords from headings
        for heading in soup.find_all(['h1', 'h2', 'h3']):
            heading_keywords = self._extract_keywords(heading.get_text())
            self.seed_keywords.update(heading_keywords)
        
        # Add keywords from meta tags
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            keywords = [k.strip().lower() for k in meta_keywords['content'].split(',')]
            self.seed_keywords.update(keywords)
        
        meta_description = soup.find('meta', attrs={'name': 'description'})
        if meta_description and meta_description.get('content'):
            desc_keywords = self._extract_keywords(meta_description['content'])
            self.seed_keywords.update(desc_keywords)
        
        logger.info(f"Analyzed seed URL: {url}")
        logger.info(f"Extracted {len(self.seed_keywords)} keywords")
        logger.debug(f"Top keywords: {list(self.seed_keywords)[:10]}")
    
    def _extract_keywords(self, text: str, min_length: int = 3) -> Set[str]:
        """
        Extract meaningful keywords from text
        
        Args:
            text: The text to extract keywords from
            min_length: Minimum keyword length
            
        Returns:
            Set of keywords
        """
        # Convert to lowercase and remove punctuation
        text = text.lower()
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Filter keywords
        keywords = {
            token for token in tokens
            if len(token) >= min_length
            and token not in self.stop_words
            and not token.isdigit()
        }
        
        return keywords
    
    def calculate_relevance_score(self, url: str, 
                                link_text: Optional[str] = None,
                                link_context: Optional[str] = None,
                                page_content: Optional[str] = None) -> float:
        """
        Calculate relevance score for a URL
        
        Args:
            url: The URL to score
            link_text: The anchor text of the link
            link_context: Surrounding text context
            page_content: Full page content if available
            
        Returns:
            Relevance score between 0 and 1
        """
        scores = []
        weights = []
        
        # 1. URL similarity (weight: 0.2)
        url_score = self._score_url_similarity(url)
        scores.append(url_score)
        weights.append(0.2)
        
        # 2. Domain similarity (weight: 0.1)
        domain_score = self._score_domain_similarity(url)
        scores.append(domain_score)
        weights.append(0.1)
        
        # 3. Link text relevance (weight: 0.3)
        if link_text:
            text_score = self._score_text_relevance(link_text)
            scores.append(text_score)
            weights.append(0.3)
        
        # 4. Context relevance (weight: 0.2)
        if link_context:
            context_score = self._score_text_relevance(link_context)
            scores.append(context_score)
            weights.append(0.2)
        
        # 5. Page content relevance (weight: 0.2)
        if page_content:
            content_score = self._score_content_relevance(page_content)
            scores.append(content_score)
            weights.append(0.2)
        
        # Calculate weighted average
        if not scores:
            return 0.0
        
        # Normalize weights
        total_weight = sum(weights[:len(scores)])
        normalized_weights = [w / total_weight for w in weights[:len(scores)]]
        
        relevance_score = sum(s * w for s, w in zip(scores, normalized_weights))
        
        # Apply penalties
        if self._is_unrelated_url(url):
            relevance_score *= 0.1  # Heavy penalty for known unrelated patterns
        
        if link_text and self._is_navigation_link(link_text):
            relevance_score *= 0.5  # Moderate penalty for navigation links
        
        return min(max(relevance_score, 0.0), 1.0)
    
    def _score_url_similarity(self, url: str) -> float:
        """Score URL path similarity to seed URL"""
        parsed = urlparse(url)
        url_tokens = [t for t in parsed.path.split('/') if t]
        
        if not url_tokens or not self.seed_path_tokens:
            return 0.5  # Neutral score for root paths
        
        # Check for common path segments
        common_tokens = set(url_tokens) & set(self.seed_path_tokens)
        if common_tokens:
            return len(common_tokens) / max(len(url_tokens), len(self.seed_path_tokens))
        
        # Check for similar patterns
        similarity = difflib.SequenceMatcher(None, 
                                           '/'.join(self.seed_path_tokens),
                                           '/'.join(url_tokens)).ratio()
        return similarity
    
    def _score_domain_similarity(self, url: str) -> float:
        """Score domain similarity"""
        parsed = urlparse(url)
        
        # Same domain gets high score
        if parsed.netloc == self.seed_domain:
            return 1.0
        
        # Subdomain of seed domain
        if parsed.netloc.endswith(f'.{self.seed_domain}'):
            return 0.8
        
        # Seed is subdomain of this domain
        if self.seed_domain.endswith(f'.{parsed.netloc}'):
            return 0.7
        
        # Check for common base domain
        seed_parts = self.seed_domain.split('.')
        url_parts = parsed.netloc.split('.')
        
        if len(seed_parts) >= 2 and len(url_parts) >= 2:
            if seed_parts[-2:] == url_parts[-2:]:  # Same base domain
                return 0.5
        
        return 0.0
    
    def _score_text_relevance(self, text: str) -> float:
        """Score text relevance based on keyword overlap"""
        if not text or not self.seed_keywords:
            return 0.0
        
        text_keywords = self._extract_keywords(text)
        if not text_keywords:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(text_keywords & self.seed_keywords)
        union = len(text_keywords | self.seed_keywords)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _score_content_relevance(self, content: str) -> float:
        """Score full page content relevance"""
        if not content:
            return 0.0
        
        # Extract keywords from content
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove non-content elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        
        text = soup.get_text()
        content_keywords = self._extract_keywords(text)
        
        if not content_keywords:
            return 0.0
        
        # Calculate weighted similarity
        # Higher weight for title and heading matches
        score = 0.0
        weight_total = 0.0
        
        # Title similarity (weight: 3)
        if soup.title:
            title_keywords = self._extract_keywords(soup.title.string or "")
            title_similarity = len(title_keywords & self.seed_keywords) / max(len(self.seed_keywords), 1)
            score += title_similarity * 3
            weight_total += 3
        
        # Heading similarity (weight: 2)
        heading_keywords = set()
        for heading in soup.find_all(['h1', 'h2', 'h3']):
            heading_keywords.update(self._extract_keywords(heading.get_text()))
        
        if heading_keywords:
            heading_similarity = len(heading_keywords & self.seed_keywords) / max(len(self.seed_keywords), 1)
            score += heading_similarity * 2
            weight_total += 2
        
        # Body text similarity (weight: 1)
        body_similarity = len(content_keywords & self.seed_keywords) / max(len(self.seed_keywords), 1)
        score += body_similarity * 1
        weight_total += 1
        
        return score / weight_total if weight_total > 0 else 0.0
    
    def _is_unrelated_url(self, url: str) -> bool:
        """Check if URL matches known unrelated patterns"""
        url_lower = url.lower()
        for pattern in self.unrelated_patterns:
            if re.search(pattern, url_lower):
                return True
        return False
    
    def _is_navigation_link(self, text: str) -> bool:
        """Check if link text suggests navigation"""
        text_lower = text.lower()
        text_words = set(text_lower.split())
        return bool(text_words & self.navigation_keywords)
    
    def is_relevant(self, url: str, 
                   link_text: Optional[str] = None,
                   link_context: Optional[str] = None,
                   page_content: Optional[str] = None) -> bool:
        """
        Determine if a URL is relevant enough to follow
        
        Args:
            url: The URL to check
            link_text: The anchor text
            link_context: Surrounding context
            page_content: Full page content if available
            
        Returns:
            True if relevant, False otherwise
        """
        score = self.calculate_relevance_score(url, link_text, link_context, page_content)
        return score >= self.similarity_threshold
    
    def get_link_context(self, link_element, context_size: int = 100) -> str:
        """
        Extract context around a link element
        
        Args:
            link_element: BeautifulSoup link element
            context_size: Number of characters of context to extract
            
        Returns:
            Context string
        """
        # Get parent element
        parent = link_element.parent
        if not parent:
            return ""
        
        # Get text from parent
        parent_text = parent.get_text()
        link_text = link_element.get_text()
        
        # Find link position in parent text
        link_pos = parent_text.find(link_text)
        if link_pos == -1:
            return parent_text[:context_size]
        
        # Extract context before and after
        start = max(0, link_pos - context_size // 2)
        end = min(len(parent_text), link_pos + len(link_text) + context_size // 2)
        
        return parent_text[start:end]
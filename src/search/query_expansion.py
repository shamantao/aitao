"""
Query Expansion Module for AItao.

This module provides query enrichment capabilities to improve search quality,
especially for short or ambiguous queries. It expands user queries with 
synonyms, translations, and related terms to increase recall.

Key Features:
- Synonym expansion for common terms (CV → curriculum vitae, resume)
- Multilingual expansion (CV → 履歷, résumé)
- Acronym expansion (PDF → Portable Document Format)
- Query normalization and cleaning
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
import re

from src.core.logger import get_logger

logger = get_logger("search.query_expansion")


@dataclass
class ExpandedQuery:
    """
    Result of query expansion.
    
    Attributes:
        original: Original user query
        expanded: Expanded query with synonyms
        terms: List of individual expanded terms
        expansion_applied: Whether any expansion was applied
    """
    original: str
    expanded: str
    terms: List[str]
    expansion_applied: bool


# Synonym dictionary: term -> list of synonyms/expansions
# Includes French, English, and Chinese equivalents
SYNONYMS: Dict[str, List[str]] = {
    # CV / Resume related
    "cv": ["curriculum vitae", "resume", "résumé", "履歷", "履歷表", "简历"],
    "curriculum vitae": ["cv", "resume", "résumé", "履歷"],
    "resume": ["cv", "curriculum vitae", "résumé", "履歷"],
    "履歷": ["cv", "curriculum vitae", "resume"],
    
    # Document types
    "facture": ["invoice", "發票", "bill", "receipt", "reçu"],
    "invoice": ["facture", "發票", "bill"],
    "發票": ["invoice", "facture"],
    "contrat": ["contract", "合約", "agreement"],
    "contract": ["contrat", "合約", "agreement"],
    "合約": ["contract", "contrat"],
    
    # Travel related
    "voyage": ["travel", "trip", "旅行", "旅遊"],
    "travel": ["voyage", "trip", "旅行"],
    "旅行": ["voyage", "travel", "trip"],
    
    # Work/Job related
    "travail": ["work", "job", "emploi", "工作"],
    "work": ["travail", "job", "emploi", "工作"],
    "emploi": ["job", "work", "travail", "工作"],
    "工作": ["work", "job", "travail", "emploi"],
    
    # Meeting/Schedule
    "réunion": ["meeting", "會議", "rendez-vous"],
    "meeting": ["réunion", "會議"],
    "會議": ["meeting", "réunion"],
    
    # Email related
    "email": ["courriel", "mail", "電子郵件", "e-mail"],
    "courriel": ["email", "mail", "電子郵件"],
    "mail": ["email", "courriel", "電子郵件"],
    
    # Report/Document
    "rapport": ["report", "報告", "compte-rendu"],
    "report": ["rapport", "報告"],
    "報告": ["report", "rapport"],
    
    # Photo/Image
    "photo": ["image", "picture", "照片", "圖片"],
    "image": ["photo", "picture", "照片"],
    "照片": ["photo", "image", "picture"],
    
    # Personal/Name related
    "mon": ["my", "mes", "我的"],
    "my": ["mon", "ma", "mes", "我的"],
    
    # Time related
    "hier": ["yesterday", "昨天"],
    "yesterday": ["hier", "昨天"],
    "今天": ["today", "aujourd'hui"],
    "today": ["aujourd'hui", "今天"],
    
    # Find/Search verbs
    "trouver": ["find", "search", "chercher", "找", "搜尋"],
    "find": ["trouver", "chercher", "找"],
    "où": ["where", "哪裡", "location"],
    "where": ["où", "哪裡"],
}

# Short terms that ALWAYS need expansion (too ambiguous alone)
ALWAYS_EXPAND: Set[str] = {
    "cv", "doc", "pdf", "img", "pic",
}

# Stop words to skip during expansion
STOP_WORDS: Set[str] = {
    "le", "la", "les", "un", "une", "des", "de", "du", "d'",
    "the", "a", "an", "of", "to", "in", "for", "on", "with",
    "est", "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses",
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "是", "的", "了", "在", "有",
}

# Query words to ignore (not content-bearing)
QUERY_WORDS: Set[str] = {
    "où", "where", "quel", "quelle", "quels", "quelles", "what", "which",
    "comment", "how", "pourquoi", "why", "quand", "when",
    "trouve", "trouver", "cherche", "chercher", "find", "search", "locate",
    "est", "se", "qui", "que",
}


def normalize_query(query: str) -> str:
    """
    Normalize query: lowercase, remove punctuation, normalize whitespace.
    
    Args:
        query: Raw user query
        
    Returns:
        Normalized query string
    """
    # Lowercase
    normalized = query.lower().strip()
    
    # Remove punctuation except hyphens
    normalized = re.sub(r"[^\w\s\-]", " ", normalized)
    
    # Normalize whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    
    return normalized


def extract_content_terms(query: str) -> List[str]:
    """
    Extract content-bearing terms from query.
    
    Removes stop words and query words, keeping only meaningful terms.
    
    Args:
        query: Normalized query
        
    Returns:
        List of content-bearing terms
    """
    terms = query.split()
    
    content_terms = []
    for term in terms:
        if term not in STOP_WORDS and term not in QUERY_WORDS:
            content_terms.append(term)
    
    return content_terms


def expand_term(term: str) -> List[str]:
    """
    Expand a single term with its synonyms.
    
    Args:
        term: Single term to expand
        
    Returns:
        List containing original term plus synonyms
    """
    expanded = [term]
    
    # Check if term has synonyms
    term_lower = term.lower()
    if term_lower in SYNONYMS:
        for synonym in SYNONYMS[term_lower]:
            if synonym not in expanded:
                expanded.append(synonym)
    
    return expanded


def expand_query(query: str, max_synonyms_per_term: int = 3) -> ExpandedQuery:
    """
    Expand query with synonyms and related terms.
    
    This is the main function for query expansion. It:
    1. Normalizes the query
    2. Extracts content-bearing terms
    3. Expands each term with synonyms
    4. Builds an expanded query string
    
    Args:
        query: Original user query
        max_synonyms_per_term: Maximum synonyms to add per term
        
    Returns:
        ExpandedQuery with original and expanded versions
    
    Example:
        >>> result = expand_query("Où est mon CV ?")
        >>> print(result.expanded)
        "cv curriculum vitae resume 履歷"
    """
    original = query
    normalized = normalize_query(query)
    
    # Extract meaningful terms
    content_terms = extract_content_terms(normalized)
    
    if not content_terms:
        # Query has no content terms (e.g., "où est ?")
        return ExpandedQuery(
            original=original,
            expanded=normalized,
            terms=[],
            expansion_applied=False,
        )
    
    # Expand each term
    all_expanded: List[str] = []
    expansion_applied = False
    
    for term in content_terms:
        term_expansions = expand_term(term)
        
        # Check if expansion was applied
        if len(term_expansions) > 1:
            expansion_applied = True
        
        # Add original term first
        if term not in all_expanded:
            all_expanded.append(term)
        
        # Add synonyms (limited)
        for syn in term_expansions[1:max_synonyms_per_term + 1]:
            if syn not in all_expanded:
                all_expanded.append(syn)
    
    # Build expanded query string
    expanded_str = " ".join(all_expanded)
    
    logger.debug(
        "Query expanded",
        metadata={
            "original": original,
            "expanded": expanded_str,
            "terms_count": len(all_expanded),
            "expansion_applied": expansion_applied,
        }
    )
    
    return ExpandedQuery(
        original=original,
        expanded=expanded_str,
        terms=all_expanded,
        expansion_applied=expansion_applied,
    )


def should_expand(query: str) -> bool:
    """
    Determine if query should be expanded.
    
    Returns True if:
    - Query is short (< 4 words)
    - Query contains always-expand terms
    - Query appears to be a simple lookup
    
    Args:
        query: User query
        
    Returns:
        True if query should be expanded
    """
    normalized = normalize_query(query)
    terms = normalized.split()
    
    # Short queries always benefit from expansion
    if len(terms) <= 4:
        return True
    
    # Check for always-expand terms
    for term in terms:
        if term.lower() in ALWAYS_EXPAND:
            return True
    
    return False


def get_search_queries(query: str) -> List[str]:
    """
    Get multiple query variations for comprehensive search.
    
    Returns a list of queries to search, including:
    1. Original query
    2. Expanded query (if applicable)
    3. Key terms only
    
    Args:
        query: User query
        
    Returns:
        List of query strings to search
    """
    queries = [query]
    
    if should_expand(query):
        expanded = expand_query(query)
        if expanded.expansion_applied and expanded.expanded != query:
            queries.append(expanded.expanded)
    
    return queries

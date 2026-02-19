"""
BAEL Search Engine
==================

Comprehensive full-text search with:
- Inverted index
- Multiple tokenizers
- BM25, TF-IDF scoring
- Fuzzy matching
- Faceted search
- Autocomplete

"Ba'el locates all knowledge in the infinite library." — Ba'el
"""

import asyncio
import logging
import re
import math
import string
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict, Counter
import threading
import uuid
import heapq
from difflib import SequenceMatcher

logger = logging.getLogger("BAEL.Search")


# ============================================================================
# ENUMS
# ============================================================================

class IndexType(Enum):
    """Types of indexes."""
    INVERTED = "inverted"     # Standard inverted index
    FORWARD = "forward"       # Document to terms
    POSITIONAL = "positional" # With term positions


class TokenizerType(Enum):
    """Types of tokenizers."""
    STANDARD = "standard"     # Whitespace + punctuation
    WHITESPACE = "whitespace" # Whitespace only
    NGRAM = "ngram"           # N-gram tokenizer
    EDGE_NGRAM = "edge_ngram" # Edge n-grams (for autocomplete)
    KEYWORD = "keyword"       # Treat as single token


class ScoringAlgorithm(Enum):
    """Scoring algorithms."""
    BM25 = "bm25"
    TFIDF = "tfidf"
    BOOLEAN = "boolean"


class QueryType(Enum):
    """Query types."""
    MATCH = "match"           # Standard full-text
    TERM = "term"             # Exact term match
    PHRASE = "phrase"         # Phrase match
    PREFIX = "prefix"         # Prefix match
    FUZZY = "fuzzy"           # Fuzzy match
    WILDCARD = "wildcard"     # Wildcard patterns
    BOOLEAN = "boolean"       # Boolean operators


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Document:
    """A searchable document."""
    id: str
    content: Dict[str, Any]  # Field name -> value

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    indexed_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def get_field(self, field: str) -> Optional[str]:
        """Get a field value as string."""
        value = self.content.get(field)
        if value is None:
            return None
        return str(value)


@dataclass
class SearchResult:
    """A search result."""
    document: Document
    score: float
    highlights: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.document.id,
            'score': self.score,
            'content': self.document.content,
            'highlights': self.highlights
        }


@dataclass
class SearchQuery:
    """A search query."""
    query: str
    query_type: QueryType = QueryType.MATCH

    # Fields to search
    fields: List[str] = field(default_factory=lambda: ['*'])

    # Pagination
    offset: int = 0
    limit: int = 10

    # Filtering
    filters: Dict[str, Any] = field(default_factory=dict)

    # Fuzzy options
    fuzziness: int = 2  # Max edit distance

    # Highlighting
    highlight: bool = True
    highlight_pre_tag: str = "<b>"
    highlight_post_tag: str = "</b>"


@dataclass
class IndexConfig:
    """Index configuration."""
    index_type: IndexType = IndexType.INVERTED
    tokenizer: TokenizerType = TokenizerType.STANDARD

    # N-gram settings
    min_ngram: int = 2
    max_ngram: int = 3

    # Text processing
    lowercase: bool = True
    remove_stopwords: bool = True
    stemming: bool = False

    # Field-specific settings
    field_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class SearchConfig:
    """Search engine configuration."""
    default_scoring: ScoringAlgorithm = ScoringAlgorithm.BM25

    # BM25 parameters
    bm25_k1: float = 1.2
    bm25_b: float = 0.75

    # Limits
    max_results: int = 10000

    # Caching
    cache_queries: bool = True
    cache_size: int = 1000


# ============================================================================
# TOKENIZER
# ============================================================================

class Tokenizer:
    """
    Text tokenizer with multiple strategies.
    """

    # English stopwords
    STOPWORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'were', 'will', 'with', 'the', 'this', 'but', 'they',
        'have', 'had', 'what', 'when', 'where', 'who', 'which', 'why', 'how'
    }

    def __init__(self, config: Optional[IndexConfig] = None):
        """Initialize tokenizer."""
        self.config = config or IndexConfig()

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text."""
        if not text:
            return []

        # Lowercase
        if self.config.lowercase:
            text = text.lower()

        # Tokenize based on type
        if self.config.tokenizer == TokenizerType.KEYWORD:
            tokens = [text]
        elif self.config.tokenizer == TokenizerType.WHITESPACE:
            tokens = text.split()
        elif self.config.tokenizer == TokenizerType.NGRAM:
            tokens = self._ngram_tokenize(text)
        elif self.config.tokenizer == TokenizerType.EDGE_NGRAM:
            tokens = self._edge_ngram_tokenize(text)
        else:  # STANDARD
            tokens = self._standard_tokenize(text)

        # Remove stopwords
        if self.config.remove_stopwords:
            tokens = [t for t in tokens if t not in self.STOPWORDS]

        return tokens

    def _standard_tokenize(self, text: str) -> List[str]:
        """Standard tokenization."""
        # Remove punctuation and split
        translator = str.maketrans('', '', string.punctuation)
        text = text.translate(translator)
        return [t.strip() for t in text.split() if t.strip()]

    def _ngram_tokenize(self, text: str) -> List[str]:
        """N-gram tokenization."""
        words = self._standard_tokenize(text)
        ngrams = []

        for word in words:
            for n in range(self.config.min_ngram, self.config.max_ngram + 1):
                for i in range(len(word) - n + 1):
                    ngrams.append(word[i:i+n])

        return ngrams

    def _edge_ngram_tokenize(self, text: str) -> List[str]:
        """Edge n-gram tokenization (for autocomplete)."""
        words = self._standard_tokenize(text)
        ngrams = []

        for word in words:
            for n in range(self.config.min_ngram, min(len(word), self.config.max_ngram) + 1):
                ngrams.append(word[:n])

        return ngrams


# ============================================================================
# INVERTED INDEX
# ============================================================================

class InvertedIndex:
    """
    Inverted index for fast text search.
    """

    def __init__(self, config: Optional[IndexConfig] = None):
        """Initialize inverted index."""
        self.config = config or IndexConfig()
        self.tokenizer = Tokenizer(config)

        # term -> {doc_id: term_frequency}
        self._index: Dict[str, Dict[str, int]] = defaultdict(dict)

        # term -> {doc_id: [positions]}
        self._positions: Dict[str, Dict[str, List[int]]] = defaultdict(dict)

        # doc_id -> field -> [terms]
        self._forward: Dict[str, Dict[str, List[str]]] = {}

        # Term document frequency
        self._doc_freq: Dict[str, int] = defaultdict(int)

        # Document lengths
        self._doc_lengths: Dict[str, int] = {}

        # Total documents
        self._total_docs = 0

        self._lock = threading.RLock()

    def index_document(
        self,
        doc_id: str,
        field: str,
        text: str
    ) -> None:
        """Index a document field."""
        tokens = self.tokenizer.tokenize(text)

        with self._lock:
            # Clear old index for this doc/field
            self._remove_from_index(doc_id, field)

            # Forward index
            if doc_id not in self._forward:
                self._forward[doc_id] = {}
            self._forward[doc_id][field] = tokens

            # Inverted index
            seen_terms = set()
            for pos, term in enumerate(tokens):
                key = f"{field}:{term}"

                # Term frequency
                if doc_id not in self._index[key]:
                    self._index[key][doc_id] = 0
                self._index[key][doc_id] += 1

                # Positions
                if doc_id not in self._positions[key]:
                    self._positions[key][doc_id] = []
                self._positions[key][doc_id].append(pos)

                # Document frequency (count once per doc)
                if key not in seen_terms:
                    self._doc_freq[key] += 1
                    seen_terms.add(key)

            # Document length
            self._doc_lengths[doc_id] = len(tokens)

    def _remove_from_index(self, doc_id: str, field: str) -> None:
        """Remove a document from the index."""
        if doc_id in self._forward:
            if field in self._forward[doc_id]:
                old_tokens = set(self._forward[doc_id][field])
                for term in old_tokens:
                    key = f"{field}:{term}"

                    if doc_id in self._index[key]:
                        del self._index[key][doc_id]
                        if not self._index[key]:
                            del self._index[key]

                    if doc_id in self._positions[key]:
                        del self._positions[key][doc_id]

                    self._doc_freq[key] = max(0, self._doc_freq[key] - 1)

    def remove_document(self, doc_id: str) -> None:
        """Remove a document entirely."""
        with self._lock:
            if doc_id in self._forward:
                for field in list(self._forward[doc_id].keys()):
                    self._remove_from_index(doc_id, field)
                del self._forward[doc_id]

            if doc_id in self._doc_lengths:
                del self._doc_lengths[doc_id]

    def search_term(
        self,
        field: str,
        term: str
    ) -> Dict[str, int]:
        """Search for a single term."""
        key = f"{field}:{term.lower()}"
        return dict(self._index.get(key, {}))

    def search_prefix(
        self,
        field: str,
        prefix: str
    ) -> Dict[str, int]:
        """Search for terms with a prefix."""
        prefix = prefix.lower()
        prefix_key = f"{field}:{prefix}"

        results: Dict[str, int] = defaultdict(int)

        with self._lock:
            for key, postings in self._index.items():
                if key.startswith(prefix_key):
                    for doc_id, freq in postings.items():
                        results[doc_id] += freq

        return dict(results)

    def get_document_frequency(self, field: str, term: str) -> int:
        """Get document frequency for a term."""
        key = f"{field}:{term.lower()}"
        return self._doc_freq.get(key, 0)

    def get_term_positions(
        self,
        field: str,
        term: str,
        doc_id: str
    ) -> List[int]:
        """Get term positions in a document."""
        key = f"{field}:{term.lower()}"
        return self._positions.get(key, {}).get(doc_id, [])

    @property
    def total_documents(self) -> int:
        """Get total indexed documents."""
        return len(self._doc_lengths)

    @property
    def average_doc_length(self) -> float:
        """Get average document length."""
        if not self._doc_lengths:
            return 0.0
        return sum(self._doc_lengths.values()) / len(self._doc_lengths)


# ============================================================================
# DOCUMENT STORE
# ============================================================================

class DocumentStore:
    """
    Stores and retrieves documents.
    """

    def __init__(self):
        """Initialize document store."""
        self._documents: Dict[str, Document] = {}
        self._lock = threading.RLock()

    def store(self, document: Document) -> None:
        """Store a document."""
        with self._lock:
            self._documents[document.id] = document

    def get(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self._documents.get(doc_id)

    def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        with self._lock:
            if doc_id in self._documents:
                del self._documents[doc_id]
                return True
            return False

    def get_all(self, doc_ids: List[str]) -> List[Document]:
        """Get multiple documents."""
        return [self._documents[id] for id in doc_ids if id in self._documents]

    def count(self) -> int:
        """Count documents."""
        return len(self._documents)


# ============================================================================
# QUERY PARSER
# ============================================================================

class QueryParser:
    """
    Parses search queries.
    """

    def __init__(self, tokenizer: Tokenizer):
        """Initialize query parser."""
        self._tokenizer = tokenizer

    def parse(self, query: SearchQuery) -> Dict[str, Any]:
        """Parse a search query."""
        text = query.query

        if query.query_type == QueryType.BOOLEAN:
            return self._parse_boolean(text)
        elif query.query_type == QueryType.PHRASE:
            return {'type': 'phrase', 'terms': self._tokenizer.tokenize(text)}
        elif query.query_type == QueryType.PREFIX:
            return {'type': 'prefix', 'prefix': text.lower().strip()}
        elif query.query_type == QueryType.WILDCARD:
            return {'type': 'wildcard', 'pattern': text}
        elif query.query_type == QueryType.FUZZY:
            return {
                'type': 'fuzzy',
                'terms': self._tokenizer.tokenize(text),
                'fuzziness': query.fuzziness
            }
        else:  # MATCH or TERM
            return {'type': 'match', 'terms': self._tokenizer.tokenize(text)}

    def _parse_boolean(self, text: str) -> Dict[str, Any]:
        """Parse boolean query."""
        # Simple boolean parsing: AND, OR, NOT, parentheses
        result = {
            'type': 'boolean',
            'must': [],
            'should': [],
            'must_not': []
        }

        # Split by AND/OR (simplified)
        parts = re.split(r'\s+(AND|OR)\s+', text)

        for part in parts:
            part = part.strip()
            if not part or part in ('AND', 'OR'):
                continue

            if part.startswith('NOT '):
                term = part[4:].strip()
                result['must_not'].extend(self._tokenizer.tokenize(term))
            elif part.startswith('-'):
                term = part[1:].strip()
                result['must_not'].extend(self._tokenizer.tokenize(term))
            elif part.startswith('+'):
                term = part[1:].strip()
                result['must'].extend(self._tokenizer.tokenize(term))
            else:
                result['should'].extend(self._tokenizer.tokenize(part))

        return result


# ============================================================================
# SCORER
# ============================================================================

class Scorer:
    """
    Scores search results.
    """

    def __init__(
        self,
        index: InvertedIndex,
        config: Optional[SearchConfig] = None
    ):
        """Initialize scorer."""
        self._index = index
        self.config = config or SearchConfig()

    def score_bm25(
        self,
        doc_id: str,
        field: str,
        terms: List[str]
    ) -> float:
        """BM25 scoring."""
        score = 0.0

        N = self._index.total_documents
        avgdl = self._index.average_doc_length
        doc_length = self._index._doc_lengths.get(doc_id, 0)

        if avgdl == 0:
            return 0.0

        k1 = self.config.bm25_k1
        b = self.config.bm25_b

        for term in terms:
            # Term frequency in document
            key = f"{field}:{term}"
            tf = self._index._index.get(key, {}).get(doc_id, 0)

            if tf == 0:
                continue

            # Document frequency
            df = self._index.get_document_frequency(field, term)

            # IDF
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1)

            # BM25 formula
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_length / avgdl))

            score += idf * (numerator / denominator)

        return score

    def score_tfidf(
        self,
        doc_id: str,
        field: str,
        terms: List[str]
    ) -> float:
        """TF-IDF scoring."""
        score = 0.0

        N = self._index.total_documents

        for term in terms:
            key = f"{field}:{term}"
            tf = self._index._index.get(key, {}).get(doc_id, 0)

            if tf == 0:
                continue

            df = self._index.get_document_frequency(field, term)

            # Log-normalized TF
            tf_log = 1 + math.log(tf) if tf > 0 else 0

            # IDF
            idf = math.log(N / (df + 1)) + 1 if df > 0 else 0

            score += tf_log * idf

        return score

    def score(
        self,
        doc_id: str,
        field: str,
        terms: List[str],
        algorithm: Optional[ScoringAlgorithm] = None
    ) -> float:
        """Score a document."""
        algorithm = algorithm or self.config.default_scoring

        if algorithm == ScoringAlgorithm.BM25:
            return self.score_bm25(doc_id, field, terms)
        elif algorithm == ScoringAlgorithm.TFIDF:
            return self.score_tfidf(doc_id, field, terms)
        else:  # BOOLEAN
            # Simple match count
            score = 0.0
            for term in terms:
                key = f"{field}:{term}"
                if doc_id in self._index._index.get(key, {}):
                    score += 1
            return score


# ============================================================================
# MAIN SEARCH ENGINE
# ============================================================================

class SearchEngine:
    """
    Main search engine.

    Features:
    - Full-text indexing
    - BM25/TF-IDF scoring
    - Multiple query types
    - Fuzzy matching
    - Highlighting

    "Ba'el's search spans all knowledge." — Ba'el
    """

    def __init__(
        self,
        index_config: Optional[IndexConfig] = None,
        search_config: Optional[SearchConfig] = None
    ):
        """Initialize search engine."""
        self.index_config = index_config or IndexConfig()
        self.search_config = search_config or SearchConfig()

        # Components
        self._index = InvertedIndex(self.index_config)
        self._store = DocumentStore()
        self._tokenizer = Tokenizer(self.index_config)
        self._parser = QueryParser(self._tokenizer)
        self._scorer = Scorer(self._index, self.search_config)

        # Query cache
        self._cache: Dict[str, List[SearchResult]] = {}

        logger.info("SearchEngine initialized")

    # ========================================================================
    # INDEXING
    # ========================================================================

    def index(
        self,
        id: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """Index a document."""
        document = Document(
            id=id,
            content=content,
            metadata=metadata or {}
        )

        self._store.store(document)

        # Index each field
        for field, value in content.items():
            if isinstance(value, str):
                self._index.index_document(id, field, value)

        # Invalidate cache
        self._cache.clear()

        return document

    def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        self._index.remove_document(doc_id)
        result = self._store.delete(doc_id)
        self._cache.clear()
        return result

    def update(
        self,
        id: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Document]:
        """Update a document."""
        existing = self._store.get(id)
        if not existing:
            return None

        self.delete(id)
        return self.index(id, content, metadata)

    # ========================================================================
    # SEARCHING
    # ========================================================================

    def search(self, query: Union[str, SearchQuery]) -> List[SearchResult]:
        """Search for documents."""
        if isinstance(query, str):
            query = SearchQuery(query=query)

        # Check cache
        cache_key = f"{query.query}:{query.query_type.value}:{query.fields}"
        if self.search_config.cache_queries and cache_key in self._cache:
            cached = self._cache[cache_key]
            return cached[query.offset:query.offset + query.limit]

        # Parse query
        parsed = self._parser.parse(query)

        # Get matching documents
        if parsed['type'] == 'match':
            results = self._search_match(query, parsed['terms'])
        elif parsed['type'] == 'prefix':
            results = self._search_prefix(query, parsed['prefix'])
        elif parsed['type'] == 'fuzzy':
            results = self._search_fuzzy(query, parsed['terms'], parsed['fuzziness'])
        elif parsed['type'] == 'phrase':
            results = self._search_phrase(query, parsed['terms'])
        elif parsed['type'] == 'boolean':
            results = self._search_boolean(query, parsed)
        else:
            results = self._search_match(query, parsed.get('terms', []))

        # Apply filters
        if query.filters:
            results = self._apply_filters(results, query.filters)

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)

        # Cache
        if self.search_config.cache_queries:
            if len(self._cache) >= self.search_config.cache_size:
                # Simple cache eviction
                self._cache.pop(next(iter(self._cache)))
            self._cache[cache_key] = results

        # Pagination
        return results[query.offset:query.offset + query.limit]

    def _search_match(
        self,
        query: SearchQuery,
        terms: List[str]
    ) -> List[SearchResult]:
        """Standard match search."""
        doc_scores: Dict[str, float] = defaultdict(float)

        fields = self._get_search_fields(query.fields)

        for field in fields:
            weight = self.index_config.field_weights.get(field, 1.0)

            for term in terms:
                postings = self._index.search_term(field, term)

                for doc_id in postings:
                    score = self._scorer.score(doc_id, field, [term])
                    doc_scores[doc_id] += score * weight

        return self._build_results(doc_scores, query, terms)

    def _search_prefix(
        self,
        query: SearchQuery,
        prefix: str
    ) -> List[SearchResult]:
        """Prefix search."""
        doc_scores: Dict[str, float] = defaultdict(float)

        fields = self._get_search_fields(query.fields)

        for field in fields:
            postings = self._index.search_prefix(field, prefix)

            for doc_id, freq in postings.items():
                doc_scores[doc_id] += float(freq)

        return self._build_results(doc_scores, query, [prefix])

    def _search_fuzzy(
        self,
        query: SearchQuery,
        terms: List[str],
        fuzziness: int
    ) -> List[SearchResult]:
        """Fuzzy search with edit distance."""
        doc_scores: Dict[str, float] = defaultdict(float)

        fields = self._get_search_fields(query.fields)

        # Get all indexed terms
        all_terms = set()
        for key in self._index._index.keys():
            field_term = key.split(':', 1)
            if len(field_term) == 2:
                all_terms.add(field_term[1])

        for field in fields:
            for term in terms:
                # Find fuzzy matches
                for indexed_term in all_terms:
                    distance = self._levenshtein_distance(term, indexed_term)
                    if distance <= fuzziness:
                        postings = self._index.search_term(field, indexed_term)

                        for doc_id in postings:
                            # Reduce score based on edit distance
                            score = self._scorer.score(doc_id, field, [indexed_term])
                            score *= (1.0 / (1 + distance))
                            doc_scores[doc_id] += score

        return self._build_results(doc_scores, query, terms)

    def _search_phrase(
        self,
        query: SearchQuery,
        terms: List[str]
    ) -> List[SearchResult]:
        """Phrase search with position matching."""
        if not terms:
            return []

        doc_scores: Dict[str, float] = defaultdict(float)

        fields = self._get_search_fields(query.fields)

        for field in fields:
            # Find documents containing all terms
            first_term_docs = set(self._index.search_term(field, terms[0]).keys())

            for term in terms[1:]:
                term_docs = set(self._index.search_term(field, term).keys())
                first_term_docs &= term_docs

            # Check phrase positions
            for doc_id in first_term_docs:
                if self._check_phrase_positions(doc_id, field, terms):
                    score = self._scorer.score(doc_id, field, terms)
                    doc_scores[doc_id] += score * 2  # Boost phrase matches

        return self._build_results(doc_scores, query, terms)

    def _search_boolean(
        self,
        query: SearchQuery,
        parsed: Dict[str, Any]
    ) -> List[SearchResult]:
        """Boolean search."""
        must_docs: Optional[Set[str]] = None
        should_docs: Set[str] = set()
        must_not_docs: Set[str] = set()

        fields = self._get_search_fields(query.fields)

        for field in fields:
            # MUST
            for term in parsed['must']:
                term_docs = set(self._index.search_term(field, term).keys())
                if must_docs is None:
                    must_docs = term_docs
                else:
                    must_docs &= term_docs

            # SHOULD
            for term in parsed['should']:
                term_docs = set(self._index.search_term(field, term).keys())
                should_docs |= term_docs

            # MUST NOT
            for term in parsed['must_not']:
                term_docs = set(self._index.search_term(field, term).keys())
                must_not_docs |= term_docs

        # Combine results
        if must_docs is not None:
            result_docs = must_docs
        else:
            result_docs = should_docs

        result_docs -= must_not_docs

        # Score
        all_terms = parsed['must'] + parsed['should']
        doc_scores = {}
        for doc_id in result_docs:
            total_score = 0.0
            for field in fields:
                total_score += self._scorer.score(doc_id, field, all_terms)
            doc_scores[doc_id] = total_score

        return self._build_results(doc_scores, query, all_terms)

    def _check_phrase_positions(
        self,
        doc_id: str,
        field: str,
        terms: List[str]
    ) -> bool:
        """Check if terms appear as a phrase."""
        if not terms:
            return True

        first_positions = self._index.get_term_positions(field, terms[0], doc_id)

        for start_pos in first_positions:
            is_phrase = True
            for i, term in enumerate(terms[1:], 1):
                positions = self._index.get_term_positions(field, term, doc_id)
                if (start_pos + i) not in positions:
                    is_phrase = False
                    break

            if is_phrase:
                return True

        return False

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)

        for i, c1 in enumerate(s1):
            current_row = [i + 1]

            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)

                current_row.append(min(insertions, deletions, substitutions))

            previous_row = current_row

        return previous_row[-1]

    def _get_search_fields(self, fields: List[str]) -> List[str]:
        """Get fields to search."""
        if '*' in fields:
            # All fields from indexed documents
            all_fields = set()
            for doc in self._store._documents.values():
                all_fields.update(doc.content.keys())
            return list(all_fields)
        return fields

    def _apply_filters(
        self,
        results: List[SearchResult],
        filters: Dict[str, Any]
    ) -> List[SearchResult]:
        """Apply filters to results."""
        filtered = []

        for result in results:
            matches = True

            for field, value in filters.items():
                doc_value = result.document.content.get(field)

                if isinstance(value, dict):
                    # Range filters
                    if 'gte' in value and doc_value < value['gte']:
                        matches = False
                    if 'lte' in value and doc_value > value['lte']:
                        matches = False
                    if 'gt' in value and doc_value <= value['gt']:
                        matches = False
                    if 'lt' in value and doc_value >= value['lt']:
                        matches = False
                elif isinstance(value, list):
                    # In filter
                    if doc_value not in value:
                        matches = False
                else:
                    # Exact match
                    if doc_value != value:
                        matches = False

            if matches:
                filtered.append(result)

        return filtered

    def _build_results(
        self,
        doc_scores: Dict[str, float],
        query: SearchQuery,
        terms: List[str]
    ) -> List[SearchResult]:
        """Build search results."""
        results = []

        for doc_id, score in doc_scores.items():
            document = self._store.get(doc_id)
            if not document:
                continue

            # Highlighting
            highlights = {}
            if query.highlight:
                highlights = self._highlight(document, terms, query)

            results.append(SearchResult(
                document=document,
                score=score,
                highlights=highlights
            ))

        return results

    def _highlight(
        self,
        document: Document,
        terms: List[str],
        query: SearchQuery
    ) -> Dict[str, List[str]]:
        """Generate highlights."""
        highlights = {}

        for field, value in document.content.items():
            if not isinstance(value, str):
                continue

            field_highlights = []
            text = value

            for term in terms:
                pattern = re.compile(re.escape(term), re.IGNORECASE)

                for match in pattern.finditer(text):
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)

                    snippet = text[start:end]
                    highlighted = pattern.sub(
                        f"{query.highlight_pre_tag}{match.group()}{query.highlight_post_tag}",
                        snippet
                    )

                    if start > 0:
                        highlighted = "..." + highlighted
                    if end < len(text):
                        highlighted = highlighted + "..."

                    field_highlights.append(highlighted)

            if field_highlights:
                highlights[field] = field_highlights[:3]  # Max 3 highlights

        return highlights

    # ========================================================================
    # AUTOCOMPLETE
    # ========================================================================

    def autocomplete(
        self,
        prefix: str,
        field: str = "title",
        limit: int = 10
    ) -> List[str]:
        """Get autocomplete suggestions."""
        suggestions = set()

        # Find all documents matching prefix
        postings = self._index.search_prefix(field, prefix.lower())

        for doc_id in postings:
            doc = self._store.get(doc_id)
            if doc:
                value = doc.get_field(field)
                if value:
                    suggestions.add(value)

        # Sort and limit
        return sorted(suggestions)[:limit]

    # ========================================================================
    # FACETS
    # ========================================================================

    def get_facets(
        self,
        field: str,
        query: Optional[SearchQuery] = None
    ) -> Dict[str, int]:
        """Get facet counts."""
        facets: Dict[str, int] = defaultdict(int)

        if query:
            results = self.search(query)
            docs = [r.document for r in results]
        else:
            docs = list(self._store._documents.values())

        for doc in docs:
            value = doc.content.get(field)
            if value:
                if isinstance(value, list):
                    for v in value:
                        facets[str(v)] += 1
                else:
                    facets[str(value)] += 1

        return dict(sorted(facets.items(), key=lambda x: -x[1]))

    # ========================================================================
    # STATS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'total_documents': self._store.count(),
            'total_terms': len(self._index._index),
            'average_doc_length': self._index.average_doc_length,
            'cache_size': len(self._cache)
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

search_engine = SearchEngine()

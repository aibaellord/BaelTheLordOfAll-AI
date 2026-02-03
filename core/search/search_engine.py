#!/usr/bin/env python3
"""
BAEL - Search Engine System
Comprehensive full-text search and indexing.

Features:
- Full-text search
- Inverted index
- TF-IDF scoring
- Fuzzy matching
- Faceted search
- Highlighting
- Suggestions
- Multi-field search
- Boolean queries
- Pagination
"""

import asyncio
import hashlib
import json
import logging
import math
import re
import string
import time
import unicodedata
import uuid
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class QueryType(Enum):
    """Query types."""
    MATCH = "match"
    MATCH_PHRASE = "match_phrase"
    TERM = "term"
    PREFIX = "prefix"
    WILDCARD = "wildcard"
    FUZZY = "fuzzy"
    RANGE = "range"
    BOOL = "bool"


class SortOrder(Enum):
    """Sort order."""
    ASC = "asc"
    DESC = "desc"


class TokenType(Enum):
    """Token types."""
    WORD = "word"
    NUMBER = "number"
    EMAIL = "email"
    URL = "url"
    HASHTAG = "hashtag"
    MENTION = "mention"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Token:
    """Search token."""
    text: str
    position: int
    token_type: TokenType = TokenType.WORD
    start_offset: int = 0
    end_offset: int = 0

    @property
    def normalized(self) -> str:
        """Get normalized token text."""
        return self.text.lower()


@dataclass
class Document:
    """Searchable document."""
    id: str
    fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    indexed_at: datetime = field(default_factory=datetime.utcnow)

    def get(self, field_name: str, default: Any = None) -> Any:
        """Get field value."""
        return self.fields.get(field_name, default)

    def set(self, field_name: str, value: Any) -> 'Document':
        """Set field value."""
        self.fields[field_name] = value
        return self


@dataclass
class SearchHit:
    """Search result hit."""
    document: Document
    score: float
    highlights: Dict[str, List[str]] = field(default_factory=dict)
    matched_fields: List[str] = field(default_factory=list)
    explanation: Optional[str] = None


@dataclass
class SearchResult:
    """Search results container."""
    hits: List[SearchHit]
    total: int
    took_ms: float
    query: str = ""
    facets: Dict[str, Dict[str, int]] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    page: int = 1
    page_size: int = 10

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page * self.page_size < self.total

    @property
    def pages(self) -> int:
        """Get total pages."""
        return math.ceil(self.total / self.page_size)


@dataclass
class FieldMapping:
    """Field mapping configuration."""
    name: str
    field_type: str = "text"
    indexed: bool = True
    stored: bool = True
    analyzed: bool = True
    boost: float = 1.0
    analyzer: str = "standard"


# =============================================================================
# ANALYZERS
# =============================================================================

class Analyzer(ABC):
    """Text analyzer."""

    @abstractmethod
    def analyze(self, text: str) -> List[Token]:
        """Analyze text into tokens."""
        pass


class StandardAnalyzer(Analyzer):
    """Standard text analyzer."""

    STOPWORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
        'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
        'that', 'the', 'to', 'was', 'were', 'will', 'with'
    }

    def __init__(
        self,
        lowercase: bool = True,
        remove_stopwords: bool = True,
        min_token_length: int = 2
    ):
        self.lowercase = lowercase
        self.remove_stopwords = remove_stopwords
        self.min_token_length = min_token_length

    def analyze(self, text: str) -> List[Token]:
        """Analyze text into tokens."""
        if not text:
            return []

        tokens = []
        position = 0

        # Normalize unicode
        text = unicodedata.normalize('NFKD', text)

        # Tokenize by whitespace and punctuation
        pattern = r'\b[\w]+\b'

        for match in re.finditer(pattern, text):
            word = match.group()

            if self.lowercase:
                word = word.lower()

            if len(word) < self.min_token_length:
                continue

            if self.remove_stopwords and word in self.STOPWORDS:
                continue

            tokens.append(Token(
                text=word,
                position=position,
                start_offset=match.start(),
                end_offset=match.end()
            ))

            position += 1

        return tokens


class WhitespaceAnalyzer(Analyzer):
    """Simple whitespace analyzer."""

    def analyze(self, text: str) -> List[Token]:
        """Split by whitespace."""
        if not text:
            return []

        tokens = []
        offset = 0

        for i, word in enumerate(text.split()):
            tokens.append(Token(
                text=word,
                position=i,
                start_offset=offset,
                end_offset=offset + len(word)
            ))
            offset += len(word) + 1

        return tokens


class KeywordAnalyzer(Analyzer):
    """Keyword analyzer (no tokenization)."""

    def analyze(self, text: str) -> List[Token]:
        """Return text as single token."""
        if not text:
            return []

        return [Token(
            text=text,
            position=0,
            start_offset=0,
            end_offset=len(text)
        )]


# =============================================================================
# INDEX
# =============================================================================

class InvertedIndex:
    """Inverted index for full-text search."""

    def __init__(self, analyzer: Analyzer = None):
        self.analyzer = analyzer or StandardAnalyzer()

        # term -> {doc_id -> [positions]}
        self._index: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))

        # doc_id -> term_frequency
        self._doc_terms: Dict[str, Counter] = {}

        # term -> document_frequency
        self._term_docs: Dict[str, int] = defaultdict(int)

        # Total documents
        self._doc_count = 0

        # Document lengths (for normalization)
        self._doc_lengths: Dict[str, int] = {}

        # Average document length
        self._avg_doc_length = 0.0

    def index(self, doc_id: str, text: str) -> int:
        """Index document text."""
        tokens = self.analyzer.analyze(text)

        if not tokens:
            return 0

        # Remove old document if exists
        if doc_id in self._doc_terms:
            self._remove(doc_id)

        # Add document
        self._doc_count += 1
        self._doc_terms[doc_id] = Counter()
        self._doc_lengths[doc_id] = len(tokens)

        # Update average
        total_length = sum(self._doc_lengths.values())
        self._avg_doc_length = total_length / self._doc_count if self._doc_count > 0 else 0

        for token in tokens:
            term = token.normalized

            self._index[term][doc_id].append(token.position)
            self._doc_terms[doc_id][term] += 1

        # Update document frequencies
        for term in set(t.normalized for t in tokens):
            self._term_docs[term] += 1

        return len(tokens)

    def _remove(self, doc_id: str) -> None:
        """Remove document from index."""
        if doc_id not in self._doc_terms:
            return

        for term in self._doc_terms[doc_id]:
            if doc_id in self._index[term]:
                del self._index[term][doc_id]

            self._term_docs[term] -= 1

            if self._term_docs[term] <= 0:
                del self._term_docs[term]

        del self._doc_terms[doc_id]
        del self._doc_lengths[doc_id]
        self._doc_count -= 1

    def search(self, query: str) -> Dict[str, float]:
        """Search index using BM25 scoring."""
        tokens = self.analyzer.analyze(query)

        if not tokens:
            return {}

        scores: Dict[str, float] = defaultdict(float)

        k1 = 1.2
        b = 0.75

        for token in tokens:
            term = token.normalized

            if term not in self._index:
                continue

            # IDF
            df = self._term_docs.get(term, 0)

            if df == 0:
                continue

            idf = math.log((self._doc_count - df + 0.5) / (df + 0.5) + 1)

            for doc_id, positions in self._index[term].items():
                tf = len(positions)
                doc_len = self._doc_lengths.get(doc_id, 1)

                # BM25 scoring
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_len / max(self._avg_doc_length, 1)))

                scores[doc_id] += idf * (numerator / denominator)

        return dict(scores)

    def get_term_positions(self, term: str, doc_id: str) -> List[int]:
        """Get positions of term in document."""
        term = term.lower()
        return self._index.get(term, {}).get(doc_id, [])

    def get_documents_with_term(self, term: str) -> Set[str]:
        """Get documents containing term."""
        term = term.lower()
        return set(self._index.get(term, {}).keys())

    @property
    def document_count(self) -> int:
        """Get number of indexed documents."""
        return self._doc_count

    @property
    def term_count(self) -> int:
        """Get number of unique terms."""
        return len(self._index)


# =============================================================================
# QUERY BUILDER
# =============================================================================

@dataclass
class Query:
    """Search query."""
    query_type: QueryType
    field: Optional[str] = None
    value: Any = None
    boost: float = 1.0
    fuzziness: int = 0
    children: List['Query'] = field(default_factory=list)
    operator: str = "AND"  # For bool queries


class QueryBuilder:
    """Fluent query builder."""

    @staticmethod
    def match(field: str, value: str, boost: float = 1.0) -> Query:
        """Match query."""
        return Query(
            query_type=QueryType.MATCH,
            field=field,
            value=value,
            boost=boost
        )

    @staticmethod
    def match_phrase(field: str, value: str, boost: float = 1.0) -> Query:
        """Match phrase query."""
        return Query(
            query_type=QueryType.MATCH_PHRASE,
            field=field,
            value=value,
            boost=boost
        )

    @staticmethod
    def term(field: str, value: Any, boost: float = 1.0) -> Query:
        """Term query."""
        return Query(
            query_type=QueryType.TERM,
            field=field,
            value=value,
            boost=boost
        )

    @staticmethod
    def prefix(field: str, value: str, boost: float = 1.0) -> Query:
        """Prefix query."""
        return Query(
            query_type=QueryType.PREFIX,
            field=field,
            value=value,
            boost=boost
        )

    @staticmethod
    def fuzzy(field: str, value: str, fuzziness: int = 1, boost: float = 1.0) -> Query:
        """Fuzzy query."""
        return Query(
            query_type=QueryType.FUZZY,
            field=field,
            value=value,
            fuzziness=fuzziness,
            boost=boost
        )

    @staticmethod
    def range(
        field: str,
        gte: Any = None,
        lte: Any = None,
        gt: Any = None,
        lt: Any = None,
        boost: float = 1.0
    ) -> Query:
        """Range query."""
        return Query(
            query_type=QueryType.RANGE,
            field=field,
            value={"gte": gte, "lte": lte, "gt": gt, "lt": lt},
            boost=boost
        )

    @staticmethod
    def bool() -> 'BoolQueryBuilder':
        """Boolean query builder."""
        return BoolQueryBuilder()


class BoolQueryBuilder:
    """Boolean query builder."""

    def __init__(self):
        self._must: List[Query] = []
        self._should: List[Query] = []
        self._must_not: List[Query] = []
        self._filter: List[Query] = []

    def must(self, query: Query) -> 'BoolQueryBuilder':
        """Add must clause."""
        self._must.append(query)
        return self

    def should(self, query: Query) -> 'BoolQueryBuilder':
        """Add should clause."""
        self._should.append(query)
        return self

    def must_not(self, query: Query) -> 'BoolQueryBuilder':
        """Add must not clause."""
        self._must_not.append(query)
        return self

    def filter(self, query: Query) -> 'BoolQueryBuilder':
        """Add filter clause."""
        self._filter.append(query)
        return self

    def build(self) -> Query:
        """Build query."""
        query = Query(query_type=QueryType.BOOL)
        query.children = self._must + self._should + self._filter
        query.value = {
            "must": self._must,
            "should": self._should,
            "must_not": self._must_not,
            "filter": self._filter
        }

        return query


# =============================================================================
# SEARCH ENGINE
# =============================================================================

class SearchEngine:
    """
    Comprehensive Search Engine for BAEL.

    Provides full-text search with advanced features.
    """

    def __init__(self, analyzer: Analyzer = None):
        self._analyzer = analyzer or StandardAnalyzer()
        self._documents: Dict[str, Document] = {}
        self._field_indices: Dict[str, InvertedIndex] = {}
        self._field_mappings: Dict[str, FieldMapping] = {}
        self._facet_fields: Set[str] = set()

    # -------------------------------------------------------------------------
    # SCHEMA
    # -------------------------------------------------------------------------

    def define_field(self, mapping: FieldMapping) -> 'SearchEngine':
        """Define field mapping."""
        self._field_mappings[mapping.name] = mapping

        if mapping.indexed and mapping.analyzed:
            self._field_indices[mapping.name] = InvertedIndex(self._analyzer)

        return self

    def add_facet_field(self, field: str) -> 'SearchEngine':
        """Add facet field."""
        self._facet_fields.add(field)
        return self

    # -------------------------------------------------------------------------
    # INDEXING
    # -------------------------------------------------------------------------

    async def index(self, document: Document) -> None:
        """Index document."""
        self._documents[document.id] = document

        for field_name, value in document.fields.items():
            if field_name in self._field_indices:
                if isinstance(value, str):
                    self._field_indices[field_name].index(document.id, value)

    async def index_many(self, documents: List[Document]) -> int:
        """Index multiple documents."""
        for doc in documents:
            await self.index(doc)

        return len(documents)

    async def delete(self, doc_id: str) -> bool:
        """Delete document."""
        if doc_id not in self._documents:
            return False

        del self._documents[doc_id]

        for index in self._field_indices.values():
            index._remove(doc_id)

        return True

    async def get(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self._documents.get(doc_id)

    # -------------------------------------------------------------------------
    # SEARCH
    # -------------------------------------------------------------------------

    async def search(
        self,
        query: str,
        fields: List[str] = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = None,
        sort_order: SortOrder = SortOrder.DESC,
        filters: Dict[str, Any] = None,
        facets: bool = True,
        highlight: bool = True
    ) -> SearchResult:
        """Search documents."""
        start_time = time.time()

        # Determine search fields
        search_fields = fields or list(self._field_indices.keys())

        # Collect scores from each field
        all_scores: Dict[str, float] = defaultdict(float)
        field_matches: Dict[str, List[str]] = defaultdict(list)

        for field in search_fields:
            if field not in self._field_indices:
                continue

            index = self._field_indices[field]
            mapping = self._field_mappings.get(field)
            boost = mapping.boost if mapping else 1.0

            field_scores = index.search(query)

            for doc_id, score in field_scores.items():
                all_scores[doc_id] += score * boost
                field_matches[doc_id].append(field)

        # Apply filters
        if filters:
            all_scores = self._apply_filters(all_scores, filters)

        # Sort results
        if sort_by and sort_by in self._field_mappings:
            sorted_docs = self._sort_by_field(all_scores, sort_by, sort_order)
        else:
            sorted_docs = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)

        total = len(sorted_docs)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        page_docs = sorted_docs[start:end]

        # Build hits
        hits = []

        for doc_id, score in page_docs:
            doc = self._documents.get(doc_id)

            if not doc:
                continue

            hit = SearchHit(
                document=doc,
                score=score,
                matched_fields=field_matches.get(doc_id, [])
            )

            if highlight:
                hit.highlights = self._highlight(doc, query, search_fields)

            hits.append(hit)

        # Calculate facets
        facet_results = {}

        if facets:
            for facet_field in self._facet_fields:
                facet_results[facet_field] = self._calculate_facet(
                    [doc_id for doc_id, _ in sorted_docs],
                    facet_field
                )

        # Get suggestions
        suggestions = self._get_suggestions(query)

        elapsed = (time.time() - start_time) * 1000

        return SearchResult(
            hits=hits,
            total=total,
            took_ms=elapsed,
            query=query,
            facets=facet_results,
            suggestions=suggestions,
            page=page,
            page_size=page_size
        )

    async def search_query(
        self,
        query: Query,
        page: int = 1,
        page_size: int = 10
    ) -> SearchResult:
        """Search using query object."""
        start_time = time.time()

        scores = self._execute_query(query)
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        total = len(sorted_docs)
        start = (page - 1) * page_size
        end = start + page_size
        page_docs = sorted_docs[start:end]

        hits = []

        for doc_id, score in page_docs:
            doc = self._documents.get(doc_id)

            if doc:
                hits.append(SearchHit(document=doc, score=score))

        elapsed = (time.time() - start_time) * 1000

        return SearchResult(
            hits=hits,
            total=total,
            took_ms=elapsed,
            page=page,
            page_size=page_size
        )

    def _execute_query(self, query: Query) -> Dict[str, float]:
        """Execute query recursively."""
        if query.query_type == QueryType.MATCH:
            return self._execute_match(query)

        elif query.query_type == QueryType.TERM:
            return self._execute_term(query)

        elif query.query_type == QueryType.PREFIX:
            return self._execute_prefix(query)

        elif query.query_type == QueryType.FUZZY:
            return self._execute_fuzzy(query)

        elif query.query_type == QueryType.BOOL:
            return self._execute_bool(query)

        return {}

    def _execute_match(self, query: Query) -> Dict[str, float]:
        """Execute match query."""
        if query.field and query.field in self._field_indices:
            scores = self._field_indices[query.field].search(str(query.value))
            return {doc_id: score * query.boost for doc_id, score in scores.items()}

        return {}

    def _execute_term(self, query: Query) -> Dict[str, float]:
        """Execute term query."""
        if query.field and query.field in self._field_indices:
            index = self._field_indices[query.field]
            docs = index.get_documents_with_term(str(query.value))
            return {doc_id: query.boost for doc_id in docs}

        return {}

    def _execute_prefix(self, query: Query) -> Dict[str, float]:
        """Execute prefix query."""
        if not query.field or query.field not in self._field_indices:
            return {}

        index = self._field_indices[query.field]
        prefix = str(query.value).lower()

        scores: Dict[str, float] = {}

        for term in index._index:
            if term.startswith(prefix):
                for doc_id in index._index[term]:
                    scores[doc_id] = scores.get(doc_id, 0) + query.boost

        return scores

    def _execute_fuzzy(self, query: Query) -> Dict[str, float]:
        """Execute fuzzy query."""
        if not query.field or query.field not in self._field_indices:
            return {}

        index = self._field_indices[query.field]
        target = str(query.value).lower()
        fuzziness = query.fuzziness

        scores: Dict[str, float] = {}

        for term in index._index:
            distance = self._levenshtein_distance(target, term)

            if distance <= fuzziness:
                for doc_id in index._index[term]:
                    # Score inversely proportional to distance
                    score = query.boost * (1 / (distance + 1))
                    scores[doc_id] = max(scores.get(doc_id, 0), score)

        return scores

    def _execute_bool(self, query: Query) -> Dict[str, float]:
        """Execute boolean query."""
        value = query.value or {}
        must = value.get("must", [])
        should = value.get("should", [])
        must_not = value.get("must_not", [])

        # Start with all documents if no must clauses
        if must:
            scores: Dict[str, float] = None

            for q in must:
                q_scores = self._execute_query(q)

                if scores is None:
                    scores = q_scores
                else:
                    # Intersect
                    scores = {
                        doc_id: scores[doc_id] + q_scores.get(doc_id, 0)
                        for doc_id in scores
                        if doc_id in q_scores
                    }

            scores = scores or {}

        else:
            scores = {doc_id: 0.0 for doc_id in self._documents}

        # Add should scores
        for q in should:
            q_scores = self._execute_query(q)

            for doc_id, score in q_scores.items():
                if doc_id in scores:
                    scores[doc_id] += score

        # Remove must_not
        for q in must_not:
            q_scores = self._execute_query(q)

            for doc_id in q_scores:
                scores.pop(doc_id, None)

        return scores

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance."""
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

    def _apply_filters(
        self,
        scores: Dict[str, float],
        filters: Dict[str, Any]
    ) -> Dict[str, float]:
        """Apply filters to scores."""
        result = {}

        for doc_id, score in scores.items():
            doc = self._documents.get(doc_id)

            if not doc:
                continue

            match = True

            for field, value in filters.items():
                doc_value = doc.get(field)

                if isinstance(value, list):
                    if doc_value not in value:
                        match = False
                        break

                elif doc_value != value:
                    match = False
                    break

            if match:
                result[doc_id] = score

        return result

    def _sort_by_field(
        self,
        scores: Dict[str, float],
        field: str,
        order: SortOrder
    ) -> List[Tuple[str, float]]:
        """Sort by field value."""
        docs_with_values = []

        for doc_id, score in scores.items():
            doc = self._documents.get(doc_id)

            if doc:
                value = doc.get(field)
                docs_with_values.append((doc_id, score, value))

        reverse = order == SortOrder.DESC
        docs_with_values.sort(key=lambda x: (x[2] or "", x[1]), reverse=reverse)

        return [(d[0], d[1]) for d in docs_with_values]

    def _highlight(
        self,
        doc: Document,
        query: str,
        fields: List[str]
    ) -> Dict[str, List[str]]:
        """Generate highlights."""
        highlights = {}
        tokens = self._analyzer.analyze(query)
        terms = {t.normalized for t in tokens}

        for field in fields:
            value = doc.get(field)

            if not isinstance(value, str):
                continue

            field_highlights = []

            for term in terms:
                pattern = re.compile(f'({re.escape(term)})', re.IGNORECASE)

                if pattern.search(value):
                    # Create snippet with highlight
                    highlighted = pattern.sub(r'<em>\1</em>', value)

                    # Truncate to snippet
                    if len(highlighted) > 200:
                        match = pattern.search(value)

                        if match:
                            start = max(0, match.start() - 50)
                            end = min(len(value), match.end() + 50)
                            snippet = value[start:end]
                            highlighted = pattern.sub(r'<em>\1</em>', snippet)

                            if start > 0:
                                highlighted = "..." + highlighted

                            if end < len(value):
                                highlighted += "..."

                    field_highlights.append(highlighted)

            if field_highlights:
                highlights[field] = field_highlights

        return highlights

    def _calculate_facet(
        self,
        doc_ids: List[str],
        field: str
    ) -> Dict[str, int]:
        """Calculate facet counts."""
        counts: Dict[str, int] = defaultdict(int)

        for doc_id in doc_ids:
            doc = self._documents.get(doc_id)

            if doc:
                value = doc.get(field)

                if value:
                    if isinstance(value, list):
                        for v in value:
                            counts[str(v)] += 1
                    else:
                        counts[str(value)] += 1

        return dict(counts)

    def _get_suggestions(self, query: str) -> List[str]:
        """Get query suggestions."""
        suggestions = []
        tokens = self._analyzer.analyze(query)

        for token in tokens:
            term = token.normalized

            # Find similar terms
            for field_index in self._field_indices.values():
                for indexed_term in field_index._index:
                    if indexed_term.startswith(term[:2]):
                        distance = self._levenshtein_distance(term, indexed_term)

                        if 0 < distance <= 2:
                            suggestions.append(indexed_term)

        return list(set(suggestions))[:5]

    # -------------------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "document_count": len(self._documents),
            "fields": list(self._field_indices.keys()),
            "facet_fields": list(self._facet_fields),
            "term_counts": {
                field: index.term_count
                for field, index in self._field_indices.items()
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Search Engine System."""
    print("=" * 70)
    print("BAEL - SEARCH ENGINE SYSTEM DEMO")
    print("Comprehensive Full-Text Search")
    print("=" * 70)
    print()

    # Create search engine
    engine = SearchEngine()

    # Define schema
    engine.define_field(FieldMapping(name="title", boost=2.0))
    engine.define_field(FieldMapping(name="content", boost=1.0))
    engine.define_field(FieldMapping(name="author", boost=1.5))
    engine.define_field(FieldMapping(name="category", analyzed=False))
    engine.add_facet_field("category")
    engine.add_facet_field("author")

    # 1. Index Documents
    print("1. INDEXING DOCUMENTS:")
    print("-" * 40)

    documents = [
        Document(
            id="1",
            fields={
                "title": "Introduction to Machine Learning",
                "content": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                "author": "Alice",
                "category": "AI"
            }
        ),
        Document(
            id="2",
            fields={
                "title": "Deep Learning Fundamentals",
                "content": "Deep learning uses neural networks with multiple layers to learn complex patterns.",
                "author": "Bob",
                "category": "AI"
            }
        ),
        Document(
            id="3",
            fields={
                "title": "Natural Language Processing",
                "content": "NLP enables computers to understand and process human language using machine learning.",
                "author": "Alice",
                "category": "AI"
            }
        ),
        Document(
            id="4",
            fields={
                "title": "Web Development Best Practices",
                "content": "Building modern web applications requires understanding of HTML, CSS, and JavaScript.",
                "author": "Carol",
                "category": "Web"
            }
        ),
        Document(
            id="5",
            fields={
                "title": "Database Optimization Techniques",
                "content": "Learn how to optimize database queries for better performance and scalability.",
                "author": "Bob",
                "category": "Database"
            }
        )
    ]

    count = await engine.index_many(documents)
    print(f"   Indexed: {count} documents")

    stats = engine.get_stats()
    print(f"   Term counts: {stats['term_counts']}")
    print()

    # 2. Basic Search
    print("2. BASIC SEARCH:")
    print("-" * 40)

    result = await engine.search("machine learning")

    print(f"   Query: 'machine learning'")
    print(f"   Results: {result.total}")
    print(f"   Time: {result.took_ms:.2f}ms")

    for hit in result.hits:
        print(f"      - {hit.document.get('title')} (score: {hit.score:.2f})")
    print()

    # 3. Multi-field Search
    print("3. MULTI-FIELD SEARCH:")
    print("-" * 40)

    result = await engine.search("Alice", fields=["author"])

    print(f"   Query: 'Alice' in author field")
    print(f"   Results: {result.total}")

    for hit in result.hits:
        print(f"      - {hit.document.get('title')} by {hit.document.get('author')}")
    print()

    # 4. Filtered Search
    print("4. FILTERED SEARCH:")
    print("-" * 40)

    result = await engine.search(
        "learning",
        filters={"category": "AI"}
    )

    print(f"   Query: 'learning' filtered by category=AI")
    print(f"   Results: {result.total}")

    for hit in result.hits:
        print(f"      - {hit.document.get('title')} [{hit.document.get('category')}]")
    print()

    # 5. Faceted Search
    print("5. FACETED SEARCH:")
    print("-" * 40)

    result = await engine.search("learning", facets=True)

    print(f"   Query: 'learning'")
    print(f"   Facets:")

    for facet_name, facet_values in result.facets.items():
        print(f"      {facet_name}:")

        for value, count in facet_values.items():
            print(f"         {value}: {count}")
    print()

    # 6. Query Builder
    print("6. QUERY BUILDER:")
    print("-" * 40)

    query = (QueryBuilder.bool()
        .must(QueryBuilder.match("content", "learning"))
        .should(QueryBuilder.match("title", "machine", boost=2.0))
        .build())

    result = await engine.search_query(query)

    print(f"   Bool query: must(content:learning) should(title:machine^2)")
    print(f"   Results: {result.total}")

    for hit in result.hits:
        print(f"      - {hit.document.get('title')} (score: {hit.score:.2f})")
    print()

    # 7. Prefix Search
    print("7. PREFIX SEARCH:")
    print("-" * 40)

    query = QueryBuilder.prefix("title", "Deep")
    result = await engine.search_query(query)

    print(f"   Prefix query: title starts with 'Deep'")
    print(f"   Results: {result.total}")

    for hit in result.hits:
        print(f"      - {hit.document.get('title')}")
    print()

    # 8. Fuzzy Search
    print("8. FUZZY SEARCH:")
    print("-" * 40)

    query = QueryBuilder.fuzzy("title", "Machien", fuzziness=2)
    result = await engine.search_query(query)

    print(f"   Fuzzy query: 'Machien' (fuzziness=2)")
    print(f"   Results: {result.total}")

    for hit in result.hits:
        print(f"      - {hit.document.get('title')}")
    print()

    # 9. Highlighting
    print("9. HIGHLIGHTING:")
    print("-" * 40)

    result = await engine.search("neural networks", highlight=True)

    print(f"   Query: 'neural networks'")

    for hit in result.hits:
        print(f"      - {hit.document.get('title')}")

        for field, highlights in hit.highlights.items():
            for h in highlights:
                print(f"        {field}: {h[:60]}...")
    print()

    # 10. Pagination
    print("10. PAGINATION:")
    print("-" * 40)

    result = await engine.search("", page=1, page_size=2)

    print(f"   Page 1 of {result.pages}")
    print(f"   Has next: {result.has_next}")
    print(f"   Results on page: {len(result.hits)}")
    print()

    # 11. Analyzer Demo
    print("11. ANALYZER:")
    print("-" * 40)

    analyzer = StandardAnalyzer()
    text = "The quick brown fox jumps over the lazy dog!"
    tokens = analyzer.analyze(text)

    print(f"   Text: '{text}'")
    print(f"   Tokens: {[t.text for t in tokens]}")
    print()

    # 12. Index Stats
    print("12. INDEX STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()

    print(f"   Documents: {stats['document_count']}")
    print(f"   Fields: {stats['fields']}")
    print(f"   Facet fields: {stats['facet_fields']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Search Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

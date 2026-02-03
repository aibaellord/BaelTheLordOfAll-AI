#!/usr/bin/env python3
"""
BAEL - Indexing Engine
Search indexing for agents.

Features:
- Full-text indexing
- Inverted index
- Fuzzy search
- Ranking algorithms
- Index persistence
"""

import asyncio
import json
import math
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class IndexType(Enum):
    """Index types."""
    INVERTED = "inverted"
    FORWARD = "forward"
    POSITIONAL = "positional"
    NGRAM = "ngram"


class TokenizerType(Enum):
    """Tokenizer types."""
    WHITESPACE = "whitespace"
    WORD = "word"
    NGRAM = "ngram"
    CHARACTER = "character"


class ScoringMethod(Enum):
    """Scoring methods."""
    TF_IDF = "tf_idf"
    BM25 = "bm25"
    BOOLEAN = "boolean"
    FREQUENCY = "frequency"


class MatchType(Enum):
    """Match types."""
    EXACT = "exact"
    PREFIX = "prefix"
    FUZZY = "fuzzy"
    WILDCARD = "wildcard"
    REGEX = "regex"


class FieldType(Enum):
    """Field types."""
    TEXT = "text"
    KEYWORD = "keyword"
    NUMERIC = "numeric"
    DATE = "date"
    BOOLEAN = "boolean"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Document:
    """A searchable document."""
    doc_id: str = ""
    content: str = ""
    fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    indexed_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.doc_id:
            self.doc_id = str(uuid.uuid4())[:8]


@dataclass
class SearchResult:
    """A search result."""
    doc_id: str = ""
    score: float = 0.0
    document: Optional[Document] = None
    highlights: List[str] = field(default_factory=list)
    matched_terms: List[str] = field(default_factory=list)


@dataclass
class SearchQuery:
    """A search query."""
    query_id: str = ""
    text: str = ""
    fields: List[str] = field(default_factory=list)
    match_type: MatchType = MatchType.EXACT
    limit: int = 10
    offset: int = 0
    min_score: float = 0.0

    def __post_init__(self):
        if not self.query_id:
            self.query_id = str(uuid.uuid4())[:8]


@dataclass
class IndexStats:
    """Index statistics."""
    document_count: int = 0
    term_count: int = 0
    total_tokens: int = 0
    avg_doc_length: float = 0.0
    index_size_bytes: int = 0


@dataclass
class IndexConfig:
    """Index configuration."""
    index_type: IndexType = IndexType.INVERTED
    tokenizer: TokenizerType = TokenizerType.WORD
    scoring: ScoringMethod = ScoringMethod.TF_IDF
    lowercase: bool = True
    remove_stopwords: bool = True
    min_token_length: int = 2
    ngram_min: int = 2
    ngram_max: int = 4


# =============================================================================
# TOKENIZER
# =============================================================================

class Tokenizer:
    """Text tokenizer."""

    STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
        "to", "was", "were", "will", "with", "the", "this", "but", "they",
        "have", "had", "what", "when", "where", "who", "which", "why", "how"
    }

    def __init__(self, config: IndexConfig):
        self._config = config

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text."""
        if self._config.tokenizer == TokenizerType.WHITESPACE:
            tokens = text.split()
        elif self._config.tokenizer == TokenizerType.WORD:
            tokens = re.findall(r'\b\w+\b', text)
        elif self._config.tokenizer == TokenizerType.NGRAM:
            tokens = self._generate_ngrams(text)
        elif self._config.tokenizer == TokenizerType.CHARACTER:
            tokens = list(text)
        else:
            tokens = re.findall(r'\b\w+\b', text)

        if self._config.lowercase:
            tokens = [t.lower() for t in tokens]

        tokens = [t for t in tokens if len(t) >= self._config.min_token_length]

        if self._config.remove_stopwords:
            tokens = [t for t in tokens if t.lower() not in self.STOPWORDS]

        return tokens

    def _generate_ngrams(self, text: str) -> List[str]:
        """Generate n-grams."""
        if self._config.lowercase:
            text = text.lower()

        text = re.sub(r'\s+', ' ', text)

        ngrams = []
        for n in range(self._config.ngram_min, self._config.ngram_max + 1):
            for i in range(len(text) - n + 1):
                ngram = text[i:i+n]
                if ' ' not in ngram:
                    ngrams.append(ngram)

        return ngrams


# =============================================================================
# INVERTED INDEX
# =============================================================================

class InvertedIndex:
    """Inverted index for full-text search."""

    def __init__(self):
        self._index: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))
        self._doc_lengths: Dict[str, int] = {}
        self._term_freq: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._doc_freq: Dict[str, int] = defaultdict(int)
        self._total_docs: int = 0
        self._avg_doc_length: float = 0.0

    def add(self, doc_id: str, tokens: List[str]) -> None:
        """Add document to index."""
        self._doc_lengths[doc_id] = len(tokens)
        self._total_docs += 1

        self._update_avg_doc_length()

        seen_terms = set()

        for position, token in enumerate(tokens):
            self._index[token][doc_id].append(position)
            self._term_freq[doc_id][token] += 1

            if token not in seen_terms:
                self._doc_freq[token] += 1
                seen_terms.add(token)

    def remove(self, doc_id: str) -> bool:
        """Remove document from index."""
        if doc_id not in self._doc_lengths:
            return False

        for term in list(self._index.keys()):
            if doc_id in self._index[term]:
                del self._index[term][doc_id]
                self._doc_freq[term] -= 1

                if not self._index[term]:
                    del self._index[term]
                    del self._doc_freq[term]

        if doc_id in self._term_freq:
            del self._term_freq[doc_id]

        del self._doc_lengths[doc_id]
        self._total_docs -= 1

        self._update_avg_doc_length()

        return True

    def _update_avg_doc_length(self) -> None:
        """Update average document length."""
        if self._total_docs > 0:
            self._avg_doc_length = sum(self._doc_lengths.values()) / self._total_docs
        else:
            self._avg_doc_length = 0.0

    def search(self, terms: List[str]) -> Dict[str, Set[int]]:
        """Search for terms, return matching docs with positions."""
        results: Dict[str, Set[int]] = defaultdict(set)

        for term in terms:
            if term in self._index:
                for doc_id, positions in self._index[term].items():
                    results[doc_id].update(positions)

        return dict(results)

    def get_doc_frequency(self, term: str) -> int:
        """Get document frequency for term."""
        return self._doc_freq.get(term, 0)

    def get_term_frequency(self, doc_id: str, term: str) -> int:
        """Get term frequency in document."""
        return self._term_freq.get(doc_id, {}).get(term, 0)

    def get_doc_length(self, doc_id: str) -> int:
        """Get document length."""
        return self._doc_lengths.get(doc_id, 0)

    @property
    def total_docs(self) -> int:
        return self._total_docs

    @property
    def avg_doc_length(self) -> float:
        return self._avg_doc_length

    @property
    def term_count(self) -> int:
        return len(self._index)


# =============================================================================
# SCORER
# =============================================================================

class Scorer:
    """Score search results."""

    def __init__(self, index: InvertedIndex, method: ScoringMethod):
        self._index = index
        self._method = method
        self._k1 = 1.2
        self._b = 0.75

    def score(self, doc_id: str, terms: List[str]) -> float:
        """Score a document."""
        if self._method == ScoringMethod.TF_IDF:
            return self._tf_idf_score(doc_id, terms)
        elif self._method == ScoringMethod.BM25:
            return self._bm25_score(doc_id, terms)
        elif self._method == ScoringMethod.BOOLEAN:
            return self._boolean_score(doc_id, terms)
        elif self._method == ScoringMethod.FREQUENCY:
            return self._frequency_score(doc_id, terms)
        else:
            return self._tf_idf_score(doc_id, terms)

    def _tf_idf_score(self, doc_id: str, terms: List[str]) -> float:
        """Calculate TF-IDF score."""
        score = 0.0
        total_docs = self._index.total_docs

        for term in terms:
            tf = self._index.get_term_frequency(doc_id, term)
            df = self._index.get_doc_frequency(term)

            if tf > 0 and df > 0:
                tf_norm = 1 + math.log10(tf)
                idf = math.log10(total_docs / df)
                score += tf_norm * idf

        return score

    def _bm25_score(self, doc_id: str, terms: List[str]) -> float:
        """Calculate BM25 score."""
        score = 0.0
        total_docs = self._index.total_docs
        avg_dl = self._index.avg_doc_length
        doc_length = self._index.get_doc_length(doc_id)

        if avg_dl == 0:
            return 0.0

        for term in terms:
            tf = self._index.get_term_frequency(doc_id, term)
            df = self._index.get_doc_frequency(term)

            if tf > 0 and df > 0:
                idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1)
                tf_component = (tf * (self._k1 + 1)) / (tf + self._k1 * (1 - self._b + self._b * (doc_length / avg_dl)))
                score += idf * tf_component

        return score

    def _boolean_score(self, doc_id: str, terms: List[str]) -> float:
        """Boolean score (presence-based)."""
        matches = 0

        for term in terms:
            if self._index.get_term_frequency(doc_id, term) > 0:
                matches += 1

        return matches / len(terms) if terms else 0.0

    def _frequency_score(self, doc_id: str, terms: List[str]) -> float:
        """Simple frequency score."""
        total = 0

        for term in terms:
            total += self._index.get_term_frequency(doc_id, term)

        return float(total)


# =============================================================================
# FUZZY MATCHER
# =============================================================================

class FuzzyMatcher:
    """Fuzzy string matching."""

    def __init__(self, max_distance: int = 2):
        self._max_distance = max_distance

    def levenshtein(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance."""
        if len(s1) < len(s2):
            return self.levenshtein(s2, s1)

        if len(s2) == 0:
            return len(s1)

        prev_row = range(len(s2) + 1)

        for i, c1 in enumerate(s1):
            curr_row = [i + 1]

            for j, c2 in enumerate(s2):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))

            prev_row = curr_row

        return prev_row[-1]

    def find_similar(
        self,
        query: str,
        candidates: List[str],
        threshold: Optional[int] = None
    ) -> List[Tuple[str, int]]:
        """Find similar strings."""
        max_dist = threshold if threshold is not None else self._max_distance
        results = []

        for candidate in candidates:
            distance = self.levenshtein(query.lower(), candidate.lower())
            if distance <= max_dist:
                results.append((candidate, distance))

        results.sort(key=lambda x: x[1])
        return results

    def is_similar(
        self,
        s1: str,
        s2: str,
        threshold: Optional[int] = None
    ) -> bool:
        """Check if strings are similar."""
        max_dist = threshold if threshold is not None else self._max_distance
        return self.levenshtein(s1.lower(), s2.lower()) <= max_dist


# =============================================================================
# DOCUMENT STORE
# =============================================================================

class DocumentStore:
    """Store documents."""

    def __init__(self):
        self._documents: Dict[str, Document] = {}

    def add(self, document: Document) -> str:
        """Add document."""
        self._documents[document.doc_id] = document
        return document.doc_id

    def get(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self._documents.get(doc_id)

    def remove(self, doc_id: str) -> bool:
        """Remove document."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False

    def exists(self, doc_id: str) -> bool:
        """Check if document exists."""
        return doc_id in self._documents

    def count(self) -> int:
        """Count documents."""
        return len(self._documents)

    def list_ids(self) -> List[str]:
        """List document IDs."""
        return list(self._documents.keys())

    def all(self) -> List[Document]:
        """Get all documents."""
        return list(self._documents.values())


# =============================================================================
# HIGHLIGHTER
# =============================================================================

class Highlighter:
    """Highlight search matches."""

    def __init__(self, pre_tag: str = "<b>", post_tag: str = "</b>"):
        self._pre_tag = pre_tag
        self._post_tag = post_tag

    def highlight(
        self,
        text: str,
        terms: List[str],
        context_words: int = 5
    ) -> List[str]:
        """Generate highlights for matching terms."""
        highlights = []
        words = text.split()

        for i, word in enumerate(words):
            clean_word = re.sub(r'\W+', '', word.lower())

            for term in terms:
                if term.lower() in clean_word or clean_word in term.lower():
                    start = max(0, i - context_words)
                    end = min(len(words), i + context_words + 1)

                    context = words[start:end]

                    highlighted = []
                    for w in context:
                        clean = re.sub(r'\W+', '', w.lower())
                        if any(t.lower() in clean or clean in t.lower() for t in terms):
                            highlighted.append(f"{self._pre_tag}{w}{self._post_tag}")
                        else:
                            highlighted.append(w)

                    highlights.append(" ".join(highlighted))
                    break

        return highlights[:3]


# =============================================================================
# INDEXING ENGINE
# =============================================================================

class IndexingEngine:
    """
    Indexing Engine for BAEL.

    Full-text search indexing.
    """

    def __init__(self, config: Optional[IndexConfig] = None):
        self._config = config or IndexConfig()

        self._tokenizer = Tokenizer(self._config)
        self._index = InvertedIndex()
        self._store = DocumentStore()
        self._scorer = Scorer(self._index, self._config.scoring)
        self._fuzzy = FuzzyMatcher()
        self._highlighter = Highlighter()

    # ----- Indexing -----

    def index(
        self,
        content: str,
        fields: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> Document:
        """Index a document."""
        document = Document(
            doc_id=doc_id or "",
            content=content,
            fields=fields or {}
        )

        self._store.add(document)

        tokens = self._tokenizer.tokenize(content)

        for field_name, field_value in document.fields.items():
            if isinstance(field_value, str):
                field_tokens = self._tokenizer.tokenize(field_value)
                tokens.extend(field_tokens)

        self._index.add(document.doc_id, tokens)

        return document

    def index_many(self, documents: List[Tuple[str, Optional[Dict]]]) -> List[Document]:
        """Index multiple documents."""
        indexed = []

        for content, fields in documents:
            doc = self.index(content, fields)
            indexed.append(doc)

        return indexed

    def remove(self, doc_id: str) -> bool:
        """Remove document from index."""
        self._index.remove(doc_id)
        return self._store.remove(doc_id)

    def update(
        self,
        doc_id: str,
        content: str,
        fields: Optional[Dict[str, Any]] = None
    ) -> Optional[Document]:
        """Update an indexed document."""
        if not self._store.exists(doc_id):
            return None

        self.remove(doc_id)

        return self.index(content, fields, doc_id)

    def clear(self) -> int:
        """Clear all indexed documents."""
        count = self._store.count()

        for doc_id in self._store.list_ids():
            self.remove(doc_id)

        return count

    # ----- Searching -----

    def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        match_type: MatchType = MatchType.EXACT,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """Search the index."""
        tokens = self._tokenizer.tokenize(query)

        if not tokens:
            return []

        if match_type == MatchType.FUZZY:
            tokens = self._expand_fuzzy(tokens)
        elif match_type == MatchType.PREFIX:
            tokens = self._expand_prefix(tokens)

        matching_docs = self._index.search(tokens)

        results = []
        for doc_id in matching_docs:
            score = self._scorer.score(doc_id, tokens)

            if score >= min_score:
                document = self._store.get(doc_id)

                highlights = []
                if document:
                    highlights = self._highlighter.highlight(document.content, tokens)

                results.append(SearchResult(
                    doc_id=doc_id,
                    score=score,
                    document=document,
                    highlights=highlights,
                    matched_terms=tokens
                ))

        results.sort(key=lambda x: x.score, reverse=True)

        return results[offset:offset + limit]

    def _expand_fuzzy(self, tokens: List[str]) -> List[str]:
        """Expand tokens with fuzzy matches."""
        expanded = set(tokens)
        all_terms = list(self._index._index.keys())

        for token in tokens:
            similar = self._fuzzy.find_similar(token, all_terms)
            for term, _ in similar:
                expanded.add(term)

        return list(expanded)

    def _expand_prefix(self, tokens: List[str]) -> List[str]:
        """Expand tokens with prefix matches."""
        expanded = set(tokens)
        all_terms = list(self._index._index.keys())

        for token in tokens:
            for term in all_terms:
                if term.startswith(token):
                    expanded.add(term)

        return list(expanded)

    def search_query(self, query: SearchQuery) -> List[SearchResult]:
        """Search with query object."""
        return self.search(
            query=query.text,
            limit=query.limit,
            offset=query.offset,
            match_type=query.match_type,
            min_score=query.min_score
        )

    def suggest(self, prefix: str, limit: int = 10) -> List[str]:
        """Suggest terms based on prefix."""
        suggestions = []
        all_terms = list(self._index._index.keys())

        for term in all_terms:
            if term.startswith(prefix.lower()):
                suggestions.append(term)

        suggestions.sort()
        return suggestions[:limit]

    def similar_terms(self, term: str, limit: int = 10) -> List[Tuple[str, int]]:
        """Find similar terms."""
        all_terms = list(self._index._index.keys())
        similar = self._fuzzy.find_similar(term, all_terms)
        return similar[:limit]

    # ----- Document Access -----

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self._store.get(doc_id)

    def document_exists(self, doc_id: str) -> bool:
        """Check if document exists."""
        return self._store.exists(doc_id)

    def list_documents(self) -> List[Document]:
        """List all documents."""
        return self._store.all()

    # ----- Stats -----

    def stats(self) -> IndexStats:
        """Get index statistics."""
        doc_count = self._store.count()

        total_tokens = 0
        for doc_id in self._store.list_ids():
            total_tokens += self._index.get_doc_length(doc_id)

        return IndexStats(
            document_count=doc_count,
            term_count=self._index.term_count,
            total_tokens=total_tokens,
            avg_doc_length=self._index.avg_doc_length,
            index_size_bytes=0
        )

    def term_stats(self, term: str) -> Dict[str, Any]:
        """Get stats for a term."""
        return {
            "term": term,
            "document_frequency": self._index.get_doc_frequency(term),
            "exists": term in self._index._index
        }

    # ----- Persistence -----

    def export_index(self) -> Dict[str, Any]:
        """Export index to dictionary."""
        documents = []
        for doc in self._store.all():
            documents.append({
                "doc_id": doc.doc_id,
                "content": doc.content,
                "fields": doc.fields,
                "metadata": doc.metadata
            })

        return {
            "config": {
                "index_type": self._config.index_type.value,
                "tokenizer": self._config.tokenizer.value,
                "scoring": self._config.scoring.value,
                "lowercase": self._config.lowercase,
                "remove_stopwords": self._config.remove_stopwords
            },
            "documents": documents
        }

    def import_index(self, data: Dict[str, Any]) -> int:
        """Import index from dictionary."""
        self.clear()

        count = 0
        for doc_data in data.get("documents", []):
            self.index(
                content=doc_data["content"],
                fields=doc_data.get("fields"),
                doc_id=doc_data.get("doc_id")
            )
            count += 1

        return count

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        stats = self.stats()

        return {
            "document_count": stats.document_count,
            "term_count": stats.term_count,
            "total_tokens": stats.total_tokens,
            "avg_doc_length": round(stats.avg_doc_length, 2),
            "index_type": self._config.index_type.value,
            "tokenizer": self._config.tokenizer.value,
            "scoring": self._config.scoring.value
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Indexing Engine."""
    print("=" * 70)
    print("BAEL - INDEXING ENGINE DEMO")
    print("Full-Text Search Indexing")
    print("=" * 70)
    print()

    engine = IndexingEngine()

    # 1. Index Documents
    print("1. INDEX DOCUMENTS:")
    print("-" * 40)

    docs = [
        ("Python is a versatile programming language used for web development, data science, and artificial intelligence.", {"title": "Python Overview", "category": "programming"}),
        ("JavaScript is the language of the web, powering interactive websites and modern web applications.", {"title": "JavaScript Basics", "category": "programming"}),
        ("Machine learning algorithms can learn patterns from data and make predictions.", {"title": "ML Introduction", "category": "ai"}),
        ("Artificial intelligence is transforming industries from healthcare to finance.", {"title": "AI Impact", "category": "ai"}),
        ("Web development frameworks like Django and Flask make building web apps easier.", {"title": "Web Frameworks", "category": "web"}),
        ("Data science combines statistics, programming, and domain expertise.", {"title": "Data Science", "category": "data"}),
    ]

    for content, fields in docs:
        doc = engine.index(content, fields)
        print(f"   Indexed: {doc.doc_id} - {fields.get('title')}")
    print()

    # 2. Basic Search
    print("2. BASIC SEARCH:")
    print("-" * 40)

    results = engine.search("programming language")
    print(f"   Query: 'programming language'")
    print(f"   Found: {len(results)} results")
    for r in results[:3]:
        print(f"   - {r.doc_id}: score={r.score:.3f}")
        if r.document:
            print(f"     Title: {r.document.fields.get('title')}")
    print()

    # 3. Search for AI Topics
    print("3. AI TOPIC SEARCH:")
    print("-" * 40)

    results = engine.search("artificial intelligence machine learning")
    print(f"   Query: 'artificial intelligence machine learning'")
    print(f"   Found: {len(results)} results")
    for r in results:
        print(f"   - Score: {r.score:.3f} - {r.document.fields.get('title') if r.document else 'N/A'}")
    print()

    # 4. Fuzzy Search
    print("4. FUZZY SEARCH:")
    print("-" * 40)

    results = engine.search("programing", match_type=MatchType.FUZZY)
    print(f"   Query: 'programing' (misspelled)")
    print(f"   Found: {len(results)} results with fuzzy matching")
    for r in results[:2]:
        print(f"   - {r.score:.3f}: {r.document.fields.get('title') if r.document else 'N/A'}")
    print()

    # 5. Prefix Search
    print("5. PREFIX SEARCH:")
    print("-" * 40)

    results = engine.search("web", match_type=MatchType.PREFIX)
    print(f"   Query: 'web' (prefix)")
    print(f"   Found: {len(results)} results")
    for r in results[:3]:
        print(f"   - {r.score:.3f}: {r.document.content[:50] if r.document else 'N/A'}...")
    print()

    # 6. Highlights
    print("6. SEARCH HIGHLIGHTS:")
    print("-" * 40)

    results = engine.search("data science")
    print(f"   Query: 'data science'")
    for r in results[:2]:
        print(f"   Doc: {r.doc_id}")
        for h in r.highlights[:2]:
            print(f"   -> {h}")
    print()

    # 7. Term Suggestions
    print("7. TERM SUGGESTIONS:")
    print("-" * 40)

    suggestions = engine.suggest("pro")
    print(f"   Prefix: 'pro'")
    print(f"   Suggestions: {suggestions}")

    suggestions = engine.suggest("web")
    print(f"   Prefix: 'web'")
    print(f"   Suggestions: {suggestions}")
    print()

    # 8. Similar Terms
    print("8. SIMILAR TERMS:")
    print("-" * 40)

    similar = engine.similar_terms("learning")
    print(f"   Term: 'learning'")
    print(f"   Similar: {similar}")
    print()

    # 9. Term Stats
    print("9. TERM STATISTICS:")
    print("-" * 40)

    for term in ["python", "web", "data", "programming"]:
        stats = engine.term_stats(term)
        print(f"   '{term}': df={stats['document_frequency']}")
    print()

    # 10. Index Stats
    print("10. INDEX STATISTICS:")
    print("-" * 40)

    stats = engine.stats()
    print(f"   Documents: {stats.document_count}")
    print(f"   Terms: {stats.term_count}")
    print(f"   Total tokens: {stats.total_tokens}")
    print(f"   Avg doc length: {stats.avg_doc_length:.2f}")
    print()

    # 11. Search with Limit/Offset
    print("11. PAGINATION:")
    print("-" * 40)

    results = engine.search("web", limit=2, offset=0)
    print(f"   First page (limit=2, offset=0): {len(results)} results")

    results = engine.search("web", limit=2, offset=2)
    print(f"   Second page (limit=2, offset=2): {len(results)} results")
    print()

    # 12. Search Query Object
    print("12. SEARCH QUERY OBJECT:")
    print("-" * 40)

    query = SearchQuery(
        text="python programming",
        limit=5,
        match_type=MatchType.EXACT,
        min_score=0.1
    )

    results = engine.search_query(query)
    print(f"   Query: {query.text}")
    print(f"   Found: {len(results)} results (min_score={query.min_score})")
    print()

    # 13. Update Document
    print("13. UPDATE DOCUMENT:")
    print("-" * 40)

    first_doc = engine.list_documents()[0]
    print(f"   Original: {first_doc.content[:50]}...")

    updated = engine.update(
        first_doc.doc_id,
        "Python is an amazing programming language for AI, ML, and automation.",
        {"title": "Python Updated"}
    )
    print(f"   Updated: {updated.content[:50]}...")
    print()

    # 14. Export/Import
    print("14. EXPORT/IMPORT:")
    print("-" * 40)

    exported = engine.export_index()
    print(f"   Exported {len(exported['documents'])} documents")

    engine.clear()
    print(f"   Cleared index: {engine.stats().document_count} documents")

    count = engine.import_index(exported)
    print(f"   Imported {count} documents")
    print(f"   Index now has: {engine.stats().document_count} documents")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Indexing Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())

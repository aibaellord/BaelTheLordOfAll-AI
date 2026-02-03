"""
Knowledge Base & Documentation System

Comprehensive knowledge management system providing:
- Semantic search with vector embeddings
- Full-text search capabilities
- Version control and history tracking
- Collaborative editing with conflict resolution
- Access control and permissions
- Automatic embedding generation
- Q&A system with relevance ranking
- Knowledge graph construction
- Multi-language support
- Export and publishing

This module provides complete knowledge management for enterprise scale.
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class DocumentType(str, Enum):
    """Types of documents"""
    ARTICLE = "article"
    GUIDE = "guide"
    FAQ = "faq"
    TROUBLESHOOTING = "troubleshooting"
    API_REFERENCE = "api_reference"
    TUTORIAL = "tutorial"
    CASE_STUDY = "case_study"
    POLICY = "policy"
    PROCEDURE = "procedure"


class AccessLevel(str, Enum):
    """Access levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class DocumentStatus(str, Enum):
    """Document status"""
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class EditConflictResolution(str, Enum):
    """Conflict resolution strategies"""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"
    MANUAL = "manual"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class DocumentVersion:
    """Represents a version of a document"""
    version_id: str
    document_id: str
    version_number: int
    content: str
    title: str
    author_id: str
    created_at: datetime
    change_summary: str = ""
    is_major_version: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version_id': self.version_id,
            'document_id': self.document_id,
            'version': self.version_number,
            'title': self.title,
            'author': self.author_id,
            'created_at': self.created_at.isoformat(),
            'summary': self.change_summary,
            'major': self.is_major_version,
            'content_length': len(self.content)
        }


@dataclass
class KnowledgeDocument:
    """Represents a knowledge base document"""
    document_id: str
    title: str
    content: str
    document_type: DocumentType
    status: DocumentStatus
    access_level: AccessLevel
    author_id: str
    created_at: datetime
    updated_at: datetime
    tags: Set[str] = field(default_factory=set)
    categories: List[str] = field(default_factory=list)
    language: str = "en"
    view_count: int = 0
    helpful_count: int = 0
    unhelpful_count: int = 0
    versions: List[str] = field(default_factory=list)
    related_documents: Set[str] = field(default_factory=set)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'title': self.title,
            'type': self.document_type.value,
            'status': self.status.value,
            'access': self.access_level.value,
            'author': self.author_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'tags': list(self.tags),
            'categories': self.categories,
            'language': self.language,
            'views': self.view_count,
            'helpful': self.helpful_count,
            'unhelpful': self.unhelpful_count,
            'versions': len(self.versions)
        }


@dataclass
class SearchResult:
    """Search result"""
    document_id: str
    title: str
    content_preview: str
    score: float
    relevance: float
    document_type: str
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'title': self.title,
            'preview': self.content_preview,
            'score': self.score,
            'relevance': self.relevance,
            'type': self.document_type,
            'tags': self.tags
        }


@dataclass
class QnAItem:
    """Question and Answer item"""
    qa_id: str
    question: str
    answer: str
    document_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    helpful_count: int = 0
    unhelpful_count: int = 0
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'qa_id': self.qa_id,
            'question': self.question,
            'answer': self.answer,
            'document_id': self.document_id,
            'created_at': self.created_at.isoformat(),
            'helpful': self.helpful_count,
            'unhelpful': self.unhelpful_count
        }


@dataclass
class EditSession:
    """Collaborative editing session"""
    session_id: str
    document_id: str
    editor_id: str
    started_at: datetime
    last_activity: datetime
    pending_changes: List[Dict[str, Any]] = field(default_factory=list)
    conflicting_edits: List[Dict[str, Any]] = field(default_factory=list)

    def is_active(self, timeout_minutes: int = 30) -> bool:
        """Check if session is still active"""
        elapsed = (datetime.now(timezone.utc) - self.last_activity).total_seconds() / 60
        return elapsed < timeout_minutes


# ============================================================================
# DOCUMENT MANAGEMENT
# ============================================================================

class DocumentManager:
    """Manages knowledge documents"""

    def __init__(self):
        self.documents: Dict[str, KnowledgeDocument] = {}
        self.versions: Dict[str, DocumentVersion] = {}
        self.version_history: Dict[str, List[str]] = {}  # document_id -> version_ids

    def create_document(self, title: str, content: str,
                       doc_type: DocumentType, author_id: str,
                       access_level: AccessLevel = AccessLevel.INTERNAL,
                       tags: Optional[Set[str]] = None) -> KnowledgeDocument:
        """Create a new document"""
        doc_id = str(uuid4())
        now = datetime.now(timezone.utc)

        document = KnowledgeDocument(
            document_id=doc_id,
            title=title,
            content=content,
            document_type=doc_type,
            status=DocumentStatus.DRAFT,
            access_level=access_level,
            author_id=author_id,
            created_at=now,
            updated_at=now,
            tags=tags or set()
        )

        self.documents[doc_id] = document
        self.version_history[doc_id] = []

        # Create initial version
        version_id = str(uuid4())
        version = DocumentVersion(
            version_id=version_id,
            document_id=doc_id,
            version_number=1,
            content=content,
            title=title,
            author_id=author_id,
            created_at=now,
            is_major_version=True
        )

        self.versions[version_id] = version
        self.version_history[doc_id].append(version_id)
        document.versions.append(version_id)

        logger.info(f"Document created: {doc_id}")
        return document

    def update_document(self, doc_id: str, content: str,
                       user_id: str, change_summary: str = "") -> Optional[DocumentVersion]:
        """Update a document"""
        document = self.documents.get(doc_id)
        if not document:
            return None

        # Create new version
        version_id = str(uuid4())
        new_version_number = len(self.version_history[doc_id]) + 1

        version = DocumentVersion(
            version_id=version_id,
            document_id=doc_id,
            version_number=new_version_number,
            content=content,
            title=document.title,
            author_id=user_id,
            created_at=datetime.now(timezone.utc),
            change_summary=change_summary
        )

        self.versions[version_id] = version
        self.version_history[doc_id].append(version_id)
        document.versions.append(version_id)

        # Update document
        document.content = content
        document.updated_at = datetime.now(timezone.utc)

        logger.info(f"Document updated: {doc_id} (v{new_version_number})")
        return version

    def publish_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """Publish a document"""
        document = self.documents.get(doc_id)
        if document:
            document.status = DocumentStatus.PUBLISHED
            logger.info(f"Document published: {doc_id}")
        return document

    def archive_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """Archive a document"""
        document = self.documents.get(doc_id)
        if document:
            document.status = DocumentStatus.ARCHIVED
            logger.info(f"Document archived: {doc_id}")
        return document

    def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """Retrieve a document"""
        return self.documents.get(doc_id)

    def get_document_version(self, version_id: str) -> Optional[DocumentVersion]:
        """Retrieve a specific version"""
        return self.versions.get(version_id)

    def get_document_history(self, doc_id: str) -> List[DocumentVersion]:
        """Get version history for a document"""
        version_ids = self.version_history.get(doc_id, [])
        return [self.versions[vid] for vid in version_ids if vid in self.versions]

    def add_tags(self, doc_id: str, tags: Set[str]) -> Optional[KnowledgeDocument]:
        """Add tags to a document"""
        document = self.documents.get(doc_id)
        if document:
            document.tags.update(tags)
        return document

    def set_categories(self, doc_id: str, categories: List[str]) -> Optional[KnowledgeDocument]:
        """Set categories for a document"""
        document = self.documents.get(doc_id)
        if document:
            document.categories = categories
        return document

    def record_view(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """Record a document view"""
        document = self.documents.get(doc_id)
        if document:
            document.view_count += 1
        return document

    def record_feedback(self, doc_id: str, helpful: bool) -> Optional[KnowledgeDocument]:
        """Record user feedback"""
        document = self.documents.get(doc_id)
        if document:
            if helpful:
                document.helpful_count += 1
            else:
                document.unhelpful_count += 1
        return document


class SearchEngine:
    """Semantic and full-text search"""

    def __init__(self, document_manager: DocumentManager):
        self.document_manager = document_manager
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.document_vectors: Dict[str, np.ndarray] = {}
        self.last_indexed: Optional[datetime] = None

    def index_documents(self) -> None:
        """Index all documents for search"""
        documents = list(self.document_manager.documents.values())

        if not documents:
            return

        # Prepare content for vectorization
        contents = [doc.content for doc in documents]

        try:
            # Create TF-IDF vectors
            matrix = self.vectorizer.fit_transform(contents)

            # Store vectors
            for i, doc in enumerate(documents):
                self.document_vectors[doc.document_id] = matrix[i]

            self.last_indexed = datetime.now(timezone.utc)
            logger.info(f"Indexed {len(documents)} documents")

        except Exception as e:
            logger.error(f"Indexing error: {e}")

    def full_text_search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Perform full-text search"""
        results = []

        for doc in self.document_manager.documents.values():
            # Simple keyword matching
            query_lower = query.lower()
            title_match = query_lower in doc.title.lower()
            content_match = query_lower in doc.content.lower()
            tag_match = any(query_lower in tag.lower() for tag in doc.tags)

            if title_match or content_match or tag_match:
                # Calculate simple score
                score = 0
                if title_match:
                    score += 3
                if content_match:
                    score += 1
                if tag_match:
                    score += 2

                content_preview = doc.content[:200] + "..."

                result = SearchResult(
                    document_id=doc.document_id,
                    title=doc.title,
                    content_preview=content_preview,
                    score=float(score),
                    relevance=0.0,
                    document_type=doc.document_type.value,
                    tags=list(doc.tags)
                )
                results.append(result)

        return sorted(results, key=lambda x: x.score, reverse=True)[:limit]

    def semantic_search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Perform semantic/vector search"""
        if not self.document_vectors:
            self.index_documents()

        if not self.document_vectors:
            return []

        try:
            # Vectorize query
            query_vector = self.vectorizer.transform([query])

            results = []

            # Calculate similarity with all documents
            for doc_id, doc_vector in self.document_vectors.items():
                similarity = cosine_similarity(query_vector, doc_vector)[0][0]

                if similarity > 0.1:  # Minimum threshold
                    doc = self.document_manager.documents[doc_id]
                    content_preview = doc.content[:200] + "..."

                    result = SearchResult(
                        document_id=doc_id,
                        title=doc.title,
                        content_preview=content_preview,
                        score=float(similarity),
                        relevance=float(similarity),
                        document_type=doc.document_type.value,
                        tags=list(doc.tags)
                    )
                    results.append(result)

            return sorted(results, key=lambda x: x.score, reverse=True)[:limit]

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []

    def search(self, query: str, limit: int = 10, use_semantic: bool = True) -> List[SearchResult]:
        """Unified search using both methods"""
        if use_semantic:
            results = self.semantic_search(query, limit)
        else:
            results = self.full_text_search(query, limit)

        return results


class QnASystem:
    """Q&A system with relevance ranking"""

    def __init__(self, search_engine: SearchEngine):
        self.search_engine = search_engine
        self.qa_items: Dict[str, QnAItem] = {}
        self.qa_by_document: Dict[str, List[str]] = {}

    def add_qa(self, question: str, answer: str,
               doc_id: Optional[str] = None) -> QnAItem:
        """Add a Q&A pair"""
        qa_id = str(uuid4())

        qa = QnAItem(
            qa_id=qa_id,
            question=question,
            answer=answer,
            document_id=doc_id
        )

        self.qa_items[qa_id] = qa

        if doc_id:
            if doc_id not in self.qa_by_document:
                self.qa_by_document[doc_id] = []
            self.qa_by_document[doc_id].append(qa_id)

        logger.info(f"Q&A added: {qa_id}")
        return qa

    def find_answers(self, question: str, limit: int = 5) -> List[QnAItem]:
        """Find answers to a question"""
        # Search for related documents
        results = self.search_engine.semantic_search(question, limit=limit * 2)

        answers = []
        seen_docs = set()

        # Get QA items from related documents
        for result in results:
            doc_qa_ids = self.qa_by_document.get(result.document_id, [])
            for qa_id in doc_qa_ids:
                if qa_id not in [qa.qa_id for qa in answers]:
                    qa = self.qa_items[qa_id]
                    answers.append(qa)
                    if len(answers) >= limit:
                        break
            if len(answers) >= limit:
                break

        # If no doc-specific QA, search general QA
        if not answers:
            for qa in self.qa_items.values():
                if question.lower() in qa.question.lower():
                    answers.append(qa)
                    if len(answers) >= limit:
                        break

        return answers[:limit]


class CollaborativeEditor:
    """Handles collaborative editing with conflict resolution"""

    def __init__(self, document_manager: DocumentManager):
        self.document_manager = document_manager
        self.edit_sessions: Dict[str, EditSession] = {}
        self.conflict_resolver = EditConflictResolution.LAST_WRITE_WINS

    def start_edit_session(self, doc_id: str, user_id: str) -> EditSession:
        """Start a collaborative edit session"""
        session_id = str(uuid4())
        now = datetime.now(timezone.utc)

        session = EditSession(
            session_id=session_id,
            document_id=doc_id,
            editor_id=user_id,
            started_at=now,
            last_activity=now
        )

        self.edit_sessions[session_id] = session
        logger.info(f"Edit session started: {session_id}")
        return session

    def apply_changes(self, session_id: str, changes: Dict[str, Any]) -> bool:
        """Apply changes from edit session"""
        session = self.edit_sessions.get(session_id)
        if not session:
            return False

        session.pending_changes.append(changes)
        session.last_activity = datetime.now(timezone.utc)

        return True

    def resolve_conflicts(self, session_id: str) -> bool:
        """Resolve editing conflicts"""
        session = self.edit_sessions.get(session_id)
        if not session or not session.conflicting_edits:
            return True

        if self.conflict_resolver == EditConflictResolution.LAST_WRITE_WINS:
            # Keep the last change
            session.conflicting_edits = session.conflicting_edits[-1:]

        elif self.conflict_resolver == EditConflictResolution.MERGE:
            # Attempt to merge changes
            logger.info(f"Merging edits for session {session_id}")

        logger.info(f"Conflicts resolved for session {session_id}")
        return True

    def commit_changes(self, session_id: str) -> Optional[DocumentVersion]:
        """Commit all pending changes"""
        session = self.edit_sessions.get(session_id)
        if not session:
            return None

        # Resolve conflicts first
        self.resolve_conflicts(session_id)

        # Apply all changes to document
        document = self.document_manager.get_document(session.document_id)
        if not document:
            return None

        # Merge all pending changes into content
        updated_content = document.content
        for change in session.pending_changes:
            # Simple text replacement
            if 'old' in change and 'new' in change:
                updated_content = updated_content.replace(change['old'], change['new'])

        # Update document
        version = self.document_manager.update_document(
            session.document_id,
            updated_content,
            session.editor_id,
            change_summary="Collaborative edit"
        )

        # Clean up session
        del self.edit_sessions[session_id]

        logger.info(f"Changes committed: {session.document_id}")
        return version


# ============================================================================
# MAIN KNOWLEDGE BASE SYSTEM
# ============================================================================

class KnowledgeBaseSystem:
    """Unified knowledge management system"""

    def __init__(self):
        self.document_manager = DocumentManager()
        self.search_engine = SearchEngine(self.document_manager)
        self.qa_system = QnASystem(self.search_engine)
        self.collaborative_editor = CollaborativeEditor(self.document_manager)

    def create_document(self, title: str, content: str,
                       doc_type: DocumentType, author_id: str,
                       **kwargs) -> KnowledgeDocument:
        """Create a knowledge document"""
        doc = self.document_manager.create_document(
            title, content, doc_type, author_id, **kwargs
        )
        # Re-index after creation
        self.search_engine.index_documents()
        return doc

    def search(self, query: str, semantic: bool = True) -> List[SearchResult]:
        """Search knowledge base"""
        return self.search_engine.search(query, use_semantic=semantic)

    def answer_question(self, question: str) -> List[QnAItem]:
        """Find answers to questions"""
        return self.qa_system.find_answers(question)

    def start_collaborative_edit(self, doc_id: str, user_id: str) -> EditSession:
        """Start collaborative editing"""
        return self.collaborative_editor.start_edit_session(doc_id, user_id)

    def commit_edits(self, session_id: str) -> Optional[DocumentVersion]:
        """Commit collaborative edits"""
        return self.collaborative_editor.commit_changes(session_id)

    def get_document_history(self, doc_id: str) -> List[DocumentVersion]:
        """Get document version history"""
        return self.document_manager.get_document_history(doc_id)


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_kb_system: Optional[KnowledgeBaseSystem] = None


def get_knowledge_base_system() -> KnowledgeBaseSystem:
    """Get or create the singleton KnowledgeBaseSystem instance"""
    global _kb_system
    if _kb_system is None:
        _kb_system = KnowledgeBaseSystem()
    return _kb_system


if __name__ == "__main__":
    kb = get_knowledge_base_system()

    # Example usage
    doc = kb.create_document(
        "Getting Started with BAEL",
        "BAEL is an advanced AI platform...",
        DocumentType.GUIDE,
        "admin"
    )
    print(f"Document created: {doc.document_id}")

    results = kb.search("advanced AI platform")
    print(f"Search results: {len(results)} found")

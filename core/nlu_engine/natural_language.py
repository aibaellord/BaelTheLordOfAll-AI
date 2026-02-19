"""
BAEL Natural Language Understanding Engine
==========================================

Advanced NLU capabilities for deep language comprehension.

"Language is the gateway to understanding reality." — Ba'el
"""

import asyncio
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union
)


class IntentType(Enum):
    """Types of user intents."""
    COMMAND = "command"
    QUESTION = "question"
    STATEMENT = "statement"
    REQUEST = "request"
    GREETING = "greeting"
    FAREWELL = "farewell"
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"
    NEGATION = "negation"
    UNKNOWN = "unknown"


class EntityType(Enum):
    """Types of named entities."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    TIME = "time"
    DURATION = "duration"
    NUMBER = "number"
    MONEY = "money"
    PERCENTAGE = "percentage"
    EMAIL = "email"
    URL = "url"
    PHONE = "phone"
    CODE = "code"
    FILE_PATH = "file_path"
    TECHNOLOGY = "technology"
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    ACTION = "action"


class SentimentType(Enum):
    """Sentiment classifications."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class QuestionType(Enum):
    """Types of questions."""
    WHAT = "what"
    WHO = "who"
    WHERE = "where"
    WHEN = "when"
    WHY = "why"
    HOW = "how"
    WHICH = "which"
    YES_NO = "yes_no"
    CHOICE = "choice"
    OPEN = "open"


class DiscourseRelation(Enum):
    """Discourse relations between sentences."""
    ELABORATION = "elaboration"
    CONTRAST = "contrast"
    CAUSE = "cause"
    RESULT = "result"
    CONDITION = "condition"
    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    EXAMPLE = "example"
    SUMMARY = "summary"


@dataclass
class Entity:
    """Extracted named entity."""
    text: str
    entity_type: EntityType
    start: int
    end: int
    confidence: float = 0.8
    normalized: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Intent:
    """Detected intent."""
    intent_type: IntentType
    confidence: float
    action: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Sentiment:
    """Sentiment analysis result."""
    sentiment: SentimentType
    score: float  # -1 to 1
    confidence: float
    aspects: Dict[str, float] = field(default_factory=dict)


@dataclass
class Token:
    """Tokenized word."""
    text: str
    lemma: str
    pos: str  # Part of speech
    index: int
    is_stop: bool = False
    is_punct: bool = False


@dataclass
class Phrase:
    """Extracted phrase."""
    text: str
    phrase_type: str  # noun_phrase, verb_phrase, etc.
    tokens: List[Token] = field(default_factory=list)
    head: Optional[str] = None


@dataclass
class Sentence:
    """Parsed sentence."""
    text: str
    tokens: List[Token]
    entities: List[Entity]
    intent: Optional[Intent]
    sentiment: Optional[Sentiment]
    question_type: Optional[QuestionType]
    phrases: List[Phrase] = field(default_factory=list)


@dataclass
class Document:
    """Analyzed document."""
    text: str
    sentences: List[Sentence]
    entities: List[Entity]
    overall_sentiment: Optional[Sentiment]
    keywords: List[Tuple[str, float]]  # (keyword, score)
    summary: Optional[str] = None
    topics: List[str] = field(default_factory=list)


class Tokenizer:
    """Text tokenization."""

    # Stop words (minimal set)
    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall",
        "can", "to", "of", "in", "for", "on", "with", "at", "by",
        "from", "as", "into", "through", "during", "before", "after",
        "above", "below", "between", "under", "again", "further",
        "then", "once", "here", "there", "when", "where", "why",
        "how", "all", "each", "few", "more", "most", "other", "some",
        "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "just", "and", "but", "if", "or",
        "because", "until", "while", "although", "though", "it",
        "its", "itself", "this", "that", "these", "those", "i", "you",
        "he", "she", "we", "they", "my", "your", "his", "her", "our"
    }

    # Simple POS patterns
    POS_PATTERNS = {
        "verb": re.compile(r"^(is|are|was|were|have|has|had|do|does|did|can|could|will|would|should|may|might|must)$|.*ing$|.*ed$", re.I),
        "noun": re.compile(r".*tion$|.*ness$|.*ment$|.*ity$|.*er$|.*or$|.*ism$|.*ist$", re.I),
        "adj": re.compile(r".*ful$|.*less$|.*ive$|.*ous$|.*able$|.*ible$|.*al$|.*ic$", re.I),
        "adv": re.compile(r".*ly$", re.I),
    }

    def tokenize(self, text: str) -> List[Token]:
        """Tokenize text into tokens."""
        # Simple word tokenization
        words = re.findall(r"\b\w+\b|[^\w\s]", text)

        tokens = []
        for i, word in enumerate(words):
            is_punct = bool(re.match(r"[^\w\s]", word))
            is_stop = word.lower() in self.STOP_WORDS

            # Simple POS tagging
            pos = self._get_pos(word)

            # Simple lemmatization
            lemma = self._lemmatize(word)

            tokens.append(Token(
                text=word,
                lemma=lemma,
                pos=pos,
                index=i,
                is_stop=is_stop,
                is_punct=is_punct
            ))

        return tokens

    def _get_pos(self, word: str) -> str:
        """Get part of speech."""
        for pos, pattern in self.POS_PATTERNS.items():
            if pattern.match(word):
                return pos.upper()
        return "NOUN"  # Default

    def _lemmatize(self, word: str) -> str:
        """Simple lemmatization."""
        word_lower = word.lower()

        # Common suffix removal
        if word_lower.endswith("ing") and len(word_lower) > 5:
            return word_lower[:-3]
        if word_lower.endswith("ed") and len(word_lower) > 4:
            return word_lower[:-2]
        if word_lower.endswith("ly") and len(word_lower) > 4:
            return word_lower[:-2]
        if word_lower.endswith("ies"):
            return word_lower[:-3] + "y"
        if word_lower.endswith("es") and len(word_lower) > 4:
            return word_lower[:-2]
        if word_lower.endswith("s") and len(word_lower) > 3:
            return word_lower[:-1]

        return word_lower


class EntityExtractor:
    """Named entity recognition."""

    # Entity patterns
    PATTERNS = {
        EntityType.EMAIL: re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b"),
        EntityType.URL: re.compile(r"https?://\S+|www\.\S+"),
        EntityType.PHONE: re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        EntityType.FILE_PATH: re.compile(r"(?:[a-zA-Z]:)?(?:/[\w\.-]+)+/?|\./[\w\.-/]+|~/[\w\.-/]+"),
        EntityType.PERCENTAGE: re.compile(r"\b\d+(?:\.\d+)?%\b"),
        EntityType.MONEY: re.compile(r"\$\d+(?:,\d{3})*(?:\.\d{2})?|\b\d+(?:\.\d+)?\s*(?:dollars?|USD|EUR|GBP)\b", re.I),
        EntityType.DATE: re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,?\s+\d{4})?\b", re.I),
        EntityType.TIME: re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b"),
        EntityType.NUMBER: re.compile(r"\b\d+(?:\.\d+)?(?:\s*(?:million|billion|thousand|K|M|B))?\b", re.I),
    }

    # Technology keywords
    TECH_KEYWORDS = {
        EntityType.PROGRAMMING_LANGUAGE: {
            "python", "javascript", "typescript", "java", "go", "rust",
            "c++", "c#", "ruby", "php", "swift", "kotlin", "scala",
            "r", "matlab", "julia", "perl", "bash", "shell", "sql"
        },
        EntityType.FRAMEWORK: {
            "react", "angular", "vue", "django", "flask", "fastapi",
            "spring", "express", "next.js", "nuxt", "svelte", "rails",
            "laravel", "tensorflow", "pytorch", "keras", "scikit-learn"
        },
        EntityType.TECHNOLOGY: {
            "docker", "kubernetes", "aws", "azure", "gcp", "terraform",
            "ansible", "jenkins", "gitlab", "github", "git", "redis",
            "mongodb", "postgresql", "mysql", "elasticsearch", "kafka",
            "graphql", "rest", "api", "microservices", "ai", "ml"
        }
    }

    def extract(self, text: str) -> List[Entity]:
        """Extract entities from text."""
        entities = []

        # Pattern-based extraction
        for entity_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                entities.append(Entity(
                    text=match.group(),
                    entity_type=entity_type,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9
                ))

        # Keyword-based extraction
        text_lower = text.lower()
        for entity_type, keywords in self.TECH_KEYWORDS.items():
            for keyword in keywords:
                pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.I)
                for match in pattern.finditer(text):
                    # Check for overlap with existing entities
                    if not any(
                        e.start <= match.start() < e.end or
                        e.start < match.end() <= e.end
                        for e in entities
                    ):
                        entities.append(Entity(
                            text=match.group(),
                            entity_type=entity_type,
                            start=match.start(),
                            end=match.end(),
                            confidence=0.85
                        ))

        return sorted(entities, key=lambda e: e.start)


class IntentClassifier:
    """Intent classification."""

    # Intent patterns
    PATTERNS = {
        IntentType.QUESTION: [
            re.compile(r"^(what|who|where|when|why|how|which|can|could|would|will|is|are|do|does|did)\b", re.I),
            re.compile(r"\?$"),
        ],
        IntentType.COMMAND: [
            re.compile(r"^(please\s+)?(create|make|build|run|execute|delete|remove|update|install|deploy|start|stop)", re.I),
            re.compile(r"^(please\s+)?(show|display|list|get|fetch|find|search|analyze|check)", re.I),
        ],
        IntentType.REQUEST: [
            re.compile(r"^(i\s+)?(?:would\s+like|want|need)\s+", re.I),
            re.compile(r"^(can|could)\s+you\s+(?:please\s+)?", re.I),
            re.compile(r"^please\s+", re.I),
        ],
        IntentType.GREETING: [
            re.compile(r"^(hi|hello|hey|greetings|good\s+(?:morning|afternoon|evening))\b", re.I),
        ],
        IntentType.FAREWELL: [
            re.compile(r"^(bye|goodbye|see\s+you|farewell|take\s+care)\b", re.I),
        ],
        IntentType.CONFIRMATION: [
            re.compile(r"^(yes|yeah|yep|sure|okay|ok|correct|right|exactly|absolutely)\b", re.I),
        ],
        IntentType.NEGATION: [
            re.compile(r"^(no|nope|never|not|don't|won't|can't)\b", re.I),
        ],
    }

    # Action extraction
    ACTION_PATTERNS = [
        re.compile(r"\b(create|make|build|generate)\b", re.I),
        re.compile(r"\b(run|execute|start|launch|deploy)\b", re.I),
        re.compile(r"\b(update|modify|change|edit)\b", re.I),
        re.compile(r"\b(delete|remove|destroy)\b", re.I),
        re.compile(r"\b(find|search|look|get|fetch|retrieve)\b", re.I),
        re.compile(r"\b(analyze|check|verify|validate|test)\b", re.I),
        re.compile(r"\b(explain|describe|tell|show)\b", re.I),
        re.compile(r"\b(help|assist|support)\b", re.I),
    ]

    def classify(self, text: str) -> Intent:
        """Classify intent."""
        best_intent = IntentType.STATEMENT
        best_confidence = 0.3

        for intent_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if pattern.search(text):
                    confidence = 0.8
                    if confidence > best_confidence:
                        best_intent = intent_type
                        best_confidence = confidence

        # Extract action
        action = None
        for pattern in self.ACTION_PATTERNS:
            match = pattern.search(text)
            if match:
                action = match.group().lower()
                break

        return Intent(
            intent_type=best_intent,
            confidence=best_confidence,
            action=action
        )

    def get_question_type(self, text: str) -> Optional[QuestionType]:
        """Determine question type."""
        text_lower = text.lower().strip()

        if text_lower.startswith("what"):
            return QuestionType.WHAT
        elif text_lower.startswith("who"):
            return QuestionType.WHO
        elif text_lower.startswith("where"):
            return QuestionType.WHERE
        elif text_lower.startswith("when"):
            return QuestionType.WHEN
        elif text_lower.startswith("why"):
            return QuestionType.WHY
        elif text_lower.startswith("how"):
            return QuestionType.HOW
        elif text_lower.startswith("which"):
            return QuestionType.WHICH
        elif re.match(r"^(is|are|do|does|did|can|could|will|would|should)\b", text_lower):
            return QuestionType.YES_NO
        elif "or" in text_lower and text.endswith("?"):
            return QuestionType.CHOICE
        elif text.endswith("?"):
            return QuestionType.OPEN

        return None


class SentimentAnalyzer:
    """Sentiment analysis."""

    # Sentiment word lists
    POSITIVE_WORDS = {
        "good", "great", "excellent", "amazing", "wonderful", "fantastic",
        "awesome", "brilliant", "superb", "outstanding", "perfect", "love",
        "like", "enjoy", "happy", "pleased", "delighted", "satisfied",
        "beautiful", "best", "better", "nice", "helpful", "useful",
        "effective", "efficient", "fast", "easy", "simple", "clear",
        "success", "successful", "improved", "innovative", "impressive"
    }

    NEGATIVE_WORDS = {
        "bad", "terrible", "horrible", "awful", "poor", "worst", "hate",
        "dislike", "annoying", "frustrating", "disappointed", "unsatisfied",
        "ugly", "slow", "difficult", "hard", "confusing", "complicated",
        "broken", "failed", "failure", "error", "problem", "issue",
        "bug", "wrong", "incorrect", "useless", "ineffective", "waste"
    }

    INTENSIFIERS = {
        "very": 1.5, "really": 1.5, "extremely": 2.0, "incredibly": 2.0,
        "absolutely": 2.0, "totally": 1.8, "completely": 1.8, "quite": 1.3,
        "somewhat": 0.7, "slightly": 0.5, "a bit": 0.5
    }

    NEGATORS = {"not", "no", "never", "neither", "nobody", "nothing", "nowhere"}

    def analyze(self, text: str) -> Sentiment:
        """Analyze sentiment."""
        words = re.findall(r"\b\w+\b", text.lower())

        positive_score = 0
        negative_score = 0
        intensifier = 1.0
        negated = False

        for i, word in enumerate(words):
            # Check for intensifiers
            if word in self.INTENSIFIERS:
                intensifier = self.INTENSIFIERS[word]
                continue

            # Check for negators
            if word in self.NEGATORS:
                negated = True
                continue

            # Score words
            if word in self.POSITIVE_WORDS:
                score = 1.0 * intensifier
                if negated:
                    negative_score += score
                else:
                    positive_score += score
                negated = False
                intensifier = 1.0

            elif word in self.NEGATIVE_WORDS:
                score = 1.0 * intensifier
                if negated:
                    positive_score += score
                else:
                    negative_score += score
                negated = False
                intensifier = 1.0

            # Reset after other words
            elif len(word) > 3:
                negated = False
                intensifier = 1.0

        # Calculate final score
        total = positive_score + negative_score
        if total == 0:
            final_score = 0
            sentiment = SentimentType.NEUTRAL
            confidence = 0.5
        else:
            final_score = (positive_score - negative_score) / total
            confidence = min(0.9, 0.5 + total * 0.1)

            if final_score > 0.5:
                sentiment = SentimentType.VERY_POSITIVE
            elif final_score > 0.1:
                sentiment = SentimentType.POSITIVE
            elif final_score < -0.5:
                sentiment = SentimentType.VERY_NEGATIVE
            elif final_score < -0.1:
                sentiment = SentimentType.NEGATIVE
            else:
                sentiment = SentimentType.NEUTRAL

        return Sentiment(
            sentiment=sentiment,
            score=final_score,
            confidence=confidence
        )


class KeywordExtractor:
    """Keyword and keyphrase extraction."""

    def __init__(self, top_n: int = 10):
        self.top_n = top_n
        self.tokenizer = Tokenizer()

    def extract(self, text: str) -> List[Tuple[str, float]]:
        """Extract keywords with scores."""
        tokens = self.tokenizer.tokenize(text)

        # Filter to content words
        content_words = [
            t.lemma for t in tokens
            if not t.is_stop and not t.is_punct and len(t.text) > 2
        ]

        # Calculate TF scores
        word_freq = defaultdict(int)
        for word in content_words:
            word_freq[word] += 1

        total = len(content_words)
        if total == 0:
            return []

        # Score by frequency and position
        word_scores = {}
        for word, freq in word_freq.items():
            tf_score = freq / total
            # Boost words that appear early
            first_pos = next((i for i, w in enumerate(content_words) if w == word), 0)
            position_score = 1 - (first_pos / total) * 0.5
            word_scores[word] = tf_score * position_score

        # Sort by score
        sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_words[:self.top_n]


class NLUEngine:
    """
    Main Natural Language Understanding Engine

    Combines:
    - Tokenization
    - Entity extraction
    - Intent classification
    - Sentiment analysis
    - Keyword extraction
    """

    def __init__(self):
        self.tokenizer = Tokenizer()
        self.entity_extractor = EntityExtractor()
        self.intent_classifier = IntentClassifier()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.keyword_extractor = KeywordExtractor()

        self.processing_history: List[Document] = []

        self.data_dir = Path("data/nlu")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def process(self, text: str) -> Document:
        """Process text and return analyzed document."""
        # Split into sentences
        sentence_texts = re.split(r'(?<=[.!?])\s+', text.strip())

        sentences = []
        all_entities = []

        for sent_text in sentence_texts:
            if not sent_text.strip():
                continue

            # Tokenize
            tokens = self.tokenizer.tokenize(sent_text)

            # Extract entities
            entities = self.entity_extractor.extract(sent_text)
            all_entities.extend(entities)

            # Classify intent
            intent = self.intent_classifier.classify(sent_text)

            # Analyze sentiment
            sentiment = self.sentiment_analyzer.analyze(sent_text)

            # Get question type
            question_type = None
            if intent.intent_type == IntentType.QUESTION:
                question_type = self.intent_classifier.get_question_type(sent_text)

            sentences.append(Sentence(
                text=sent_text,
                tokens=tokens,
                entities=entities,
                intent=intent,
                sentiment=sentiment,
                question_type=question_type
            ))

        # Overall sentiment
        if sentences:
            scores = [s.sentiment.score for s in sentences if s.sentiment]
            avg_score = sum(scores) / len(scores) if scores else 0
            overall_sentiment = self.sentiment_analyzer.analyze(text)
        else:
            overall_sentiment = None

        # Extract keywords
        keywords = self.keyword_extractor.extract(text)

        # Create document
        doc = Document(
            text=text,
            sentences=sentences,
            entities=list(all_entities),
            overall_sentiment=overall_sentiment,
            keywords=keywords
        )

        self.processing_history.append(doc)

        return doc

    async def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities only."""
        return self.entity_extractor.extract(text)

    async def classify_intent(self, text: str) -> Intent:
        """Classify intent only."""
        return self.intent_classifier.classify(text)

    async def analyze_sentiment(self, text: str) -> Sentiment:
        """Analyze sentiment only."""
        return self.sentiment_analyzer.analyze(text)

    async def extract_keywords(self, text: str) -> List[Tuple[str, float]]:
        """Extract keywords only."""
        return self.keyword_extractor.extract(text)

    async def summarize(self, text: str, max_sentences: int = 3) -> str:
        """Create extractive summary."""
        doc = await self.process(text)

        # Score sentences by keyword overlap
        keywords = set(kw[0] for kw in doc.keywords[:10])

        sentence_scores = []
        for sent in doc.sentences:
            words = set(t.lemma for t in sent.tokens if not t.is_stop)
            overlap = len(words & keywords)
            sentence_scores.append((sent, overlap))

        # Sort by score, keep order for ties
        sorted_sents = sorted(
            enumerate(sentence_scores),
            key=lambda x: (x[1][1], -x[0]),
            reverse=True
        )

        # Take top sentences, maintain order
        top_indices = sorted([x[0] for x in sorted_sents[:max_sentences]])
        summary = " ".join(doc.sentences[i].text for i in top_indices)

        return summary

    async def answer_question(
        self,
        question: str,
        context: str
    ) -> Dict[str, Any]:
        """Answer a question given context."""
        # Process question
        q_doc = await self.process(question)
        q_intent = q_doc.sentences[0].intent if q_doc.sentences else None
        q_type = q_doc.sentences[0].question_type if q_doc.sentences else None

        # Process context
        c_doc = await self.process(context)

        # Find relevant sentences
        q_keywords = set(kw[0] for kw in q_doc.keywords[:5])

        scored_sents = []
        for sent in c_doc.sentences:
            words = set(t.lemma for t in sent.tokens if not t.is_stop)
            score = len(words & q_keywords) / max(len(q_keywords), 1)
            scored_sents.append((sent, score))

        # Get best matching sentence
        scored_sents.sort(key=lambda x: x[1], reverse=True)

        if scored_sents and scored_sents[0][1] > 0:
            answer_sent = scored_sents[0][0]
            return {
                "answer": answer_sent.text,
                "confidence": scored_sents[0][1],
                "question_type": q_type.value if q_type else "unknown",
                "relevant_entities": [e.text for e in answer_sent.entities]
            }

        return {
            "answer": None,
            "confidence": 0,
            "question_type": q_type.value if q_type else "unknown",
            "reason": "No relevant answer found in context"
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        total_entities = sum(len(d.entities) for d in self.processing_history)

        return {
            "documents_processed": len(self.processing_history),
            "total_entities_extracted": total_entities,
            "capabilities": [
                "tokenization",
                "entity_extraction",
                "intent_classification",
                "sentiment_analysis",
                "keyword_extraction",
                "summarization",
                "question_answering"
            ],
            "entity_types": [e.value for e in EntityType],
            "intent_types": [i.value for i in IntentType]
        }


# Convenience instance
nlu_engine = NLUEngine()

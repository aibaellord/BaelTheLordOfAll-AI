#!/usr/bin/env python3
"""
BAEL - Database Initialization Script
Initializes all database schemas and seed data.
"""

import logging
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BAEL.Init")


def init_episodic_db(db_path: str) -> None:
    """Initialize episodic memory database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            content TEXT NOT NULL,
            context TEXT,
            participants TEXT,
            location TEXT,
            duration_seconds REAL,
            outcome TEXT,
            emotional_valence INTEGER,
            importance REAL,
            tags TEXT,
            linked_episodes TEXT,
            embedding BLOB,
            access_count INTEGER DEFAULT 0,
            last_accessed TEXT,
            decay_rate REAL DEFAULT 0.01
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON episodes(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON episodes(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON episodes(importance)")

    conn.commit()
    conn.close()
    logger.info(f"✅ Episodic database initialized: {db_path}")


def init_semantic_db(db_path: str) -> None:
    """Initialize semantic memory database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            concept_type TEXT NOT NULL,
            definition TEXT NOT NULL,
            domain TEXT,
            properties TEXT,
            confidence REAL,
            source TEXT,
            created_at TEXT,
            updated_at TEXT,
            access_count INTEGER DEFAULT 0,
            embedding BLOB,
            aliases TEXT,
            examples TEXT,
            counter_examples TEXT,
            tags TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relations (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            strength REAL,
            properties TEXT,
            bidirectional INTEGER,
            confidence REAL,
            FOREIGN KEY (source_id) REFERENCES concepts(id),
            FOREIGN KEY (target_id) REFERENCES concepts(id)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_concept_name ON concepts(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_concept_domain ON concepts(domain)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_source ON relations(source_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_target ON relations(target_id)")

    conn.commit()
    conn.close()
    logger.info(f"✅ Semantic database initialized: {db_path}")


def init_procedural_db(db_path: str) -> None:
    """Initialize procedural memory database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS procedures (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            procedure_type TEXT NOT NULL,
            description TEXT,
            domain TEXT,
            steps TEXT,
            prerequisites TEXT,
            proficiency INTEGER,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            last_executed TEXT,
            average_duration REAL,
            context_requirements TEXT,
            output_schema TEXT,
            created_at TEXT,
            updated_at TEXT,
            tags TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS execution_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            procedure_id TEXT NOT NULL,
            success INTEGER,
            start_time TEXT,
            end_time TEXT,
            steps_completed INTEGER,
            output TEXT,
            error TEXT,
            step_results TEXT,
            FOREIGN KEY (procedure_id) REFERENCES procedures(id)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_procedure_name ON procedures(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_procedure_type ON procedures(procedure_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_procedure ON execution_history(procedure_id)")

    conn.commit()
    conn.close()
    logger.info(f"✅ Procedural database initialized: {db_path}")


def init_vector_db(db_path: str) -> None:
    """Initialize vector memory database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vectors (
            id TEXT PRIMARY KEY,
            vector BLOB NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT,
            source TEXT,
            namespace TEXT DEFAULT 'default'
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_namespace ON vectors(namespace)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON vectors(source)")

    conn.commit()
    conn.close()
    logger.info(f"✅ Vector database initialized: {db_path}")


def seed_knowledge(semantic_db_path: str) -> None:
    """Seed initial knowledge into semantic database."""
    conn = sqlite3.connect(semantic_db_path)
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM concepts")
    if cursor.fetchone()[0] > 0:
        logger.info("Database already seeded, skipping...")
        conn.close()
        return

    # Seed some basic concepts
    import json
    now = datetime.now().isoformat()

    concepts = [
        {
            "id": "bael_self",
            "name": "BAEL",
            "concept_type": "entity",
            "definition": "The All-Knowing AI Assistant - a multi-persona, multi-capability AI system",
            "domain": "self",
            "properties": {"version": "1.0.0"},
            "confidence": 1.0,
            "source": "system"
        },
        {
            "id": "persona_architect",
            "name": "Architect Persona",
            "concept_type": "entity",
            "definition": "A specialized persona for system design and architectural decisions",
            "domain": "personas",
            "properties": {"specialty": "architecture"},
            "confidence": 1.0,
            "source": "system"
        },
        {
            "id": "persona_coder",
            "name": "Coder Persona",
            "concept_type": "entity",
            "definition": "A specialized persona for code implementation and development",
            "domain": "personas",
            "properties": {"specialty": "coding"},
            "confidence": 1.0,
            "source": "system"
        }
    ]

    for concept in concepts:
        cursor.execute("""
            INSERT INTO concepts
            (id, name, concept_type, definition, domain, properties, confidence,
             source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            concept["id"],
            concept["name"],
            concept["concept_type"],
            concept["definition"],
            concept["domain"],
            json.dumps(concept["properties"]),
            concept["confidence"],
            concept["source"],
            now,
            now
        ))

    conn.commit()
    conn.close()
    logger.info("✅ Knowledge base seeded with initial concepts")


def main():
    """Main initialization routine."""
    logger.info("=" * 60)
    logger.info("BAEL Database Initialization")
    logger.info("=" * 60)

    # Base paths
    memory_base = project_root / "memory"

    # Initialize all databases
    init_episodic_db(str(memory_base / "episodic" / "episodes.db"))
    init_semantic_db(str(memory_base / "semantic" / "concepts.db"))
    init_procedural_db(str(memory_base / "procedural" / "procedures.db"))
    init_vector_db(str(memory_base / "vector" / "vectors.db"))

    # Seed initial knowledge
    seed_knowledge(str(memory_base / "semantic" / "concepts.db"))

    logger.info("=" * 60)
    logger.info("Database initialization complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

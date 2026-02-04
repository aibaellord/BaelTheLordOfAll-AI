"""
BAEL - Identity Fabrication System
====================================

CREATE. FORGE. ASSUME. DOMINATE.

Complete identity control:
- Digital identity creation
- Document forgery
- Credential generation
- Persona management
- Background fabrication
- Biometric spoofing
- Social profile generation
- History fabrication
- Identity theft
- Deep cover creation

"Ba'el wears a thousand faces."
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.IDENTITY")


class IdentityType(Enum):
    """Types of identities."""
    PERSON = "person"
    BUSINESS = "business"
    GOVERNMENT_OFFICIAL = "government_official"
    MILITARY = "military"
    JOURNALIST = "journalist"
    ACADEMIC = "academic"
    ACTIVIST = "activist"
    CRIMINAL = "criminal"
    INTELLIGENCE = "intelligence"
    TECHNICAL = "technical"


class DocumentType(Enum):
    """Types of documents."""
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"
    BIRTH_CERTIFICATE = "birth_certificate"
    SOCIAL_SECURITY = "social_security"
    CREDIT_CARD = "credit_card"
    BANK_STATEMENT = "bank_statement"
    UTILITY_BILL = "utility_bill"
    DIPLOMA = "diploma"
    EMPLOYMENT_RECORD = "employment_record"


class CredentialType(Enum):
    """Types of credentials."""
    EMAIL = "email"
    SOCIAL_MEDIA = "social_media"
    BANKING = "banking"
    GOVERNMENT = "government"
    CORPORATE = "corporate"
    MEDICAL = "medical"
    EDUCATIONAL = "educational"
    PROFESSIONAL = "professional"


class QualityLevel(Enum):
    """Quality levels of fabrications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROFESSIONAL = "professional"
    STATE_LEVEL = "state_level"


class VerificationStatus(Enum):
    """Verification status."""
    UNVERIFIED = "unverified"
    PARTIAL = "partial"
    VERIFIED = "verified"
    BACKSTOPPED = "backstopped"


@dataclass
class Identity:
    """A fabricated identity."""
    id: str
    identity_type: IdentityType
    name: str
    date_of_birth: datetime
    nationality: str
    documents: List[str]
    credentials: List[str]
    backstory: str
    quality: QualityLevel
    verification: VerificationStatus = VerificationStatus.UNVERIFIED


@dataclass
class Document:
    """A fabricated document."""
    id: str
    document_type: DocumentType
    holder_name: str
    document_number: str
    issue_date: datetime
    expiry_date: Optional[datetime]
    issuing_authority: str
    quality: QualityLevel


@dataclass
class Credential:
    """A fabricated credential."""
    id: str
    credential_type: CredentialType
    username: str
    password: str
    associated_identity: str
    platform: str
    created: datetime
    active: bool = True


@dataclass
class SocialProfile:
    """A fabricated social profile."""
    id: str
    platform: str
    username: str
    display_name: str
    followers: int
    posts: int
    created_date: datetime
    history_depth_days: int


@dataclass
class Backstory:
    """A complete backstory."""
    id: str
    identity_id: str
    biography: str
    education: List[Dict[str, Any]]
    employment: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    locations: List[Dict[str, Any]]
    depth_score: float


class IdentityFabricationSystem:
    """
    The identity fabrication system.

    Complete identity control:
    - Identity creation
    - Document forgery
    - Credential generation
    - Deep cover establishment
    """

    def __init__(self):
        self.identities: Dict[str, Identity] = {}
        self.documents: Dict[str, Document] = {}
        self.credentials: Dict[str, Credential] = {}
        self.social_profiles: Dict[str, SocialProfile] = {}
        self.backstories: Dict[str, Backstory] = {}

        self.identities_created = 0
        self.documents_forged = 0
        self.credentials_generated = 0
        self.profiles_fabricated = 0

        self._init_generation_data()

        logger.info("IdentityFabricationSystem initialized - BA'EL WEARS A THOUSAND FACES")

    def _gen_id(self) -> str:
        """Generate unique ID."""
        return f"idn_{int(time.time() * 1000) % 100000}_{random.randint(1000, 9999)}"

    def _init_generation_data(self):
        """Initialize data for identity generation."""
        self.first_names = [
            "James", "John", "Michael", "David", "Richard",
            "Sarah", "Emily", "Jessica", "Emma", "Jennifer",
            "Wei", "Mohammed", "Carlos", "Ivan", "Hans"
        ]

        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones",
            "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
            "Chen", "Ali", "Mueller", "Petrov", "Tanaka"
        ]

        self.nationalities = [
            "United States", "United Kingdom", "Canada", "Australia",
            "Germany", "France", "Japan", "China", "Brazil", "Russia"
        ]

        self.platforms = [
            "facebook", "twitter", "instagram", "linkedin",
            "reddit", "github", "medium", "youtube"
        ]

        self.document_authorities = {
            DocumentType.PASSPORT: ["Department of State", "Home Office", "Foreign Affairs"],
            DocumentType.DRIVERS_LICENSE: ["DMV", "DVLA", "Transport Authority"],
            DocumentType.NATIONAL_ID: ["National Registry", "Civil Registry"],
            DocumentType.BIRTH_CERTIFICATE: ["Vital Records", "Civil Registry"],
            DocumentType.SOCIAL_SECURITY: ["SSA", "Social Security Office"],
            DocumentType.CREDIT_CARD: ["Visa", "Mastercard", "Amex"],
            DocumentType.BANK_STATEMENT: ["Bank of America", "Chase", "HSBC"],
            DocumentType.UTILITY_BILL: ["Electric Company", "Water Authority"],
            DocumentType.DIPLOMA: ["University", "College", "Institute"],
            DocumentType.EMPLOYMENT_RECORD: ["HR Department", "Company Registry"]
        }

    # =========================================================================
    # IDENTITY GENERATION
    # =========================================================================

    async def generate_identity(
        self,
        identity_type: IdentityType,
        quality: QualityLevel = QualityLevel.MEDIUM,
        nationality: Optional[str] = None
    ) -> Identity:
        """Generate a new identity."""
        first_name = random.choice(self.first_names)
        last_name = random.choice(self.last_names)
        name = f"{first_name} {last_name}"

        if nationality is None:
            nationality = random.choice(self.nationalities)

        # Generate age appropriate to identity type
        age_range = {
            IdentityType.PERSON: (18, 65),
            IdentityType.BUSINESS: (25, 55),
            IdentityType.GOVERNMENT_OFFICIAL: (30, 60),
            IdentityType.MILITARY: (20, 45),
            IdentityType.JOURNALIST: (22, 50),
            IdentityType.ACADEMIC: (25, 70),
            IdentityType.ACTIVIST: (18, 45),
            IdentityType.CRIMINAL: (18, 50),
            IdentityType.INTELLIGENCE: (25, 55),
            IdentityType.TECHNICAL: (20, 45)
        }.get(identity_type, (18, 65))

        age = random.randint(*age_range)
        dob = datetime.now() - timedelta(days=age * 365)

        # Generate backstory
        backstory = await self._generate_backstory_text(identity_type, name, nationality)

        identity = Identity(
            id=self._gen_id(),
            identity_type=identity_type,
            name=name,
            date_of_birth=dob,
            nationality=nationality,
            documents=[],
            credentials=[],
            backstory=backstory,
            quality=quality
        )

        self.identities[identity.id] = identity
        self.identities_created += 1

        return identity

    async def _generate_backstory_text(
        self,
        identity_type: IdentityType,
        name: str,
        nationality: str
    ) -> str:
        """Generate backstory text."""
        templates = {
            IdentityType.PERSON: f"{name} is a citizen of {nationality} with a background in business.",
            IdentityType.BUSINESS: f"{name} is an entrepreneur from {nationality} running multiple ventures.",
            IdentityType.GOVERNMENT_OFFICIAL: f"{name} is a mid-level government official from {nationality}.",
            IdentityType.MILITARY: f"{name} served in the {nationality} armed forces with distinction.",
            IdentityType.JOURNALIST: f"{name} is a freelance journalist based in {nationality}.",
            IdentityType.ACADEMIC: f"{name} is a professor at a university in {nationality}.",
            IdentityType.ACTIVIST: f"{name} is a human rights activist from {nationality}.",
            IdentityType.CRIMINAL: f"{name} has ties to organized crime networks in {nationality}.",
            IdentityType.INTELLIGENCE: f"{name} works for a security consultancy, formerly of {nationality} intelligence.",
            IdentityType.TECHNICAL: f"{name} is a software engineer from {nationality}."
        }

        return templates.get(identity_type, f"{name} is from {nationality}.")

    # =========================================================================
    # DOCUMENT FORGERY
    # =========================================================================

    async def forge_document(
        self,
        identity_id: str,
        document_type: DocumentType,
        quality: Optional[QualityLevel] = None
    ) -> Document:
        """Forge a document for an identity."""
        identity = self.identities.get(identity_id)
        if not identity:
            raise ValueError("Identity not found")

        if quality is None:
            quality = identity.quality

        # Generate document number
        number_format = {
            DocumentType.PASSPORT: f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))}{random.randint(1000000, 9999999)}",
            DocumentType.DRIVERS_LICENSE: f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=12))}",
            DocumentType.NATIONAL_ID: f"{random.randint(100000000, 999999999)}",
            DocumentType.SOCIAL_SECURITY: f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}",
            DocumentType.CREDIT_CARD: f"{random.randint(4000, 5999)}-{''.join([str(random.randint(1000, 9999)) for _ in range(3)])}",
            DocumentType.BIRTH_CERTIFICATE: f"BC{random.randint(100000, 999999)}",
            DocumentType.BANK_STATEMENT: f"ACC{random.randint(10000000, 99999999)}",
            DocumentType.UTILITY_BILL: f"UTIL{random.randint(100000, 999999)}",
            DocumentType.DIPLOMA: f"DIP{random.randint(1000, 9999)}/{random.randint(2000, 2023)}",
            DocumentType.EMPLOYMENT_RECORD: f"EMP{random.randint(10000, 99999)}"
        }.get(document_type, f"DOC{random.randint(100000, 999999)}")

        # Issue and expiry dates
        issue_date = datetime.now() - timedelta(days=random.randint(30, 1825))
        expiry_date = None
        if document_type in [DocumentType.PASSPORT, DocumentType.DRIVERS_LICENSE, DocumentType.NATIONAL_ID]:
            expiry_date = issue_date + timedelta(days=random.randint(1825, 3650))

        authority = random.choice(self.document_authorities.get(document_type, ["Authority"]))

        document = Document(
            id=self._gen_id(),
            document_type=document_type,
            holder_name=identity.name,
            document_number=number_format,
            issue_date=issue_date,
            expiry_date=expiry_date,
            issuing_authority=authority,
            quality=quality
        )

        self.documents[document.id] = document
        identity.documents.append(document.id)
        self.documents_forged += 1

        return document

    async def create_document_package(
        self,
        identity_id: str,
        package_type: str = "standard"
    ) -> Dict[str, Any]:
        """Create a package of documents."""
        packages = {
            "basic": [DocumentType.DRIVERS_LICENSE, DocumentType.UTILITY_BILL],
            "standard": [DocumentType.PASSPORT, DocumentType.DRIVERS_LICENSE, DocumentType.UTILITY_BILL, DocumentType.BANK_STATEMENT],
            "full": list(DocumentType),
            "travel": [DocumentType.PASSPORT, DocumentType.DRIVERS_LICENSE, DocumentType.CREDIT_CARD],
            "financial": [DocumentType.BANK_STATEMENT, DocumentType.CREDIT_CARD, DocumentType.UTILITY_BILL, DocumentType.EMPLOYMENT_RECORD]
        }

        doc_types = packages.get(package_type, packages["standard"])
        documents = []

        for doc_type in doc_types:
            doc = await self.forge_document(identity_id, doc_type)
            documents.append(doc.id)

        return {
            "identity_id": identity_id,
            "package_type": package_type,
            "documents_created": len(documents),
            "document_ids": documents
        }

    # =========================================================================
    # CREDENTIAL GENERATION
    # =========================================================================

    async def generate_credential(
        self,
        identity_id: str,
        credential_type: CredentialType,
        platform: str
    ) -> Credential:
        """Generate a credential for an identity."""
        identity = self.identities.get(identity_id)
        if not identity:
            raise ValueError("Identity not found")

        # Generate username
        name_parts = identity.name.lower().split()
        username_formats = [
            f"{name_parts[0]}.{name_parts[-1]}",
            f"{name_parts[0]}{name_parts[-1][0]}",
            f"{name_parts[0]}{random.randint(10, 99)}",
            f"{name_parts[0]}_{name_parts[-1]}_{random.randint(100, 999)}"
        ]
        username = random.choice(username_formats)

        # Generate password
        password = ''.join(random.choices(
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%',
            k=16
        ))

        credential = Credential(
            id=self._gen_id(),
            credential_type=credential_type,
            username=username,
            password=password,
            associated_identity=identity_id,
            platform=platform,
            created=datetime.now()
        )

        self.credentials[credential.id] = credential
        identity.credentials.append(credential.id)
        self.credentials_generated += 1

        return credential

    async def create_credential_set(
        self,
        identity_id: str
    ) -> Dict[str, Any]:
        """Create a full set of credentials."""
        credential_platforms = {
            CredentialType.EMAIL: ["gmail", "outlook", "protonmail"],
            CredentialType.SOCIAL_MEDIA: ["twitter", "facebook", "instagram", "linkedin"],
            CredentialType.BANKING: ["chase", "bofa", "wells_fargo"],
            CredentialType.CORPORATE: ["slack", "office365", "gsuite"],
            CredentialType.PROFESSIONAL: ["linkedin", "github", "stackoverflow"]
        }

        credentials = []
        for cred_type, platforms in credential_platforms.items():
            platform = random.choice(platforms)
            cred = await self.generate_credential(identity_id, cred_type, platform)
            credentials.append(cred.id)

        return {
            "identity_id": identity_id,
            "credentials_created": len(credentials),
            "credential_ids": credentials
        }

    # =========================================================================
    # SOCIAL PROFILE FABRICATION
    # =========================================================================

    async def fabricate_social_profile(
        self,
        identity_id: str,
        platform: str,
        history_days: int = 365
    ) -> SocialProfile:
        """Fabricate a social media profile."""
        identity = self.identities.get(identity_id)
        if not identity:
            raise ValueError("Identity not found")

        name_parts = identity.name.split()
        username = f"{name_parts[0].lower()}{name_parts[-1][0].lower()}{random.randint(10, 99)}"

        profile = SocialProfile(
            id=self._gen_id(),
            platform=platform,
            username=username,
            display_name=identity.name,
            followers=random.randint(50, 5000),
            posts=random.randint(20, 500),
            created_date=datetime.now() - timedelta(days=history_days + random.randint(0, 365)),
            history_depth_days=history_days
        )

        self.social_profiles[profile.id] = profile
        self.profiles_fabricated += 1

        return profile

    async def establish_social_presence(
        self,
        identity_id: str
    ) -> Dict[str, Any]:
        """Establish social media presence across platforms."""
        profiles = []

        for platform in self.platforms[:5]:
            history = random.randint(180, 730)
            profile = await self.fabricate_social_profile(identity_id, platform, history)
            profiles.append({
                "platform": profile.platform,
                "username": profile.username,
                "followers": profile.followers,
                "history_days": profile.history_depth_days
            })

        return {
            "identity_id": identity_id,
            "profiles_created": len(profiles),
            "profiles": profiles
        }

    # =========================================================================
    # BACKSTORY CREATION
    # =========================================================================

    async def create_backstory(
        self,
        identity_id: str
    ) -> Backstory:
        """Create detailed backstory for an identity."""
        identity = self.identities.get(identity_id)
        if not identity:
            raise ValueError("Identity not found")

        age = (datetime.now() - identity.date_of_birth).days // 365

        # Generate education
        education = []
        if age >= 22:
            education.append({
                "institution": f"University of {random.choice(['Cambridge', 'Oxford', 'Stanford', 'MIT', 'Berkeley'])}",
                "degree": random.choice(["BA", "BS", "MA", "MS", "PhD"]),
                "field": random.choice(["Computer Science", "Business", "Engineering", "Law", "Medicine"]),
                "year": 2023 - (age - 22) - random.randint(0, 5)
            })
        if age >= 18:
            education.append({
                "institution": f"{random.choice(['Central', 'Northern', 'Western'])} High School",
                "type": "High School Diploma",
                "year": 2023 - (age - 18)
            })

        # Generate employment
        employment = []
        years_worked = min(age - 22, 20) if age > 22 else 0
        for i in range(min(3, years_worked // 3)):
            employment.append({
                "company": f"{random.choice(['Global', 'Premier', 'Advanced', 'Innovative'])} {random.choice(['Tech', 'Solutions', 'Industries', 'Corp'])}",
                "position": random.choice(["Manager", "Director", "Analyst", "Engineer", "Consultant"]),
                "start_year": 2023 - years_worked + i * 3,
                "end_year": 2023 - years_worked + (i + 1) * 3 if i < 2 else None
            })

        # Generate relationships
        relationships = []
        if random.random() > 0.3:
            relationships.append({
                "type": random.choice(["spouse", "partner"]),
                "name": f"{random.choice(self.first_names)} {random.choice(self.last_names)}",
                "since": 2023 - random.randint(1, 15)
            })
        for _ in range(random.randint(1, 3)):
            relationships.append({
                "type": "friend",
                "name": f"{random.choice(self.first_names)} {random.choice(self.last_names)}",
                "context": random.choice(["work", "school", "neighborhood"])
            })

        # Generate locations
        locations = []
        locations.append({
            "type": "birth",
            "city": random.choice(["New York", "London", "Paris", "Tokyo", "Sydney"]),
            "country": identity.nationality
        })
        locations.append({
            "type": "current",
            "city": random.choice(["San Francisco", "Berlin", "Singapore", "Toronto", "Dubai"]),
            "address": f"{random.randint(100, 9999)} {random.choice(['Oak', 'Maple', 'Pine', 'Main'])} Street"
        })

        depth_score = len(education) * 0.1 + len(employment) * 0.15 + len(relationships) * 0.1 + len(locations) * 0.1

        backstory = Backstory(
            id=self._gen_id(),
            identity_id=identity_id,
            biography=identity.backstory,
            education=education,
            employment=employment,
            relationships=relationships,
            locations=locations,
            depth_score=min(1.0, depth_score)
        )

        self.backstories[backstory.id] = backstory

        return backstory

    # =========================================================================
    # FULL IDENTITY PACKAGE
    # =========================================================================

    async def create_complete_identity(
        self,
        identity_type: IdentityType,
        quality: QualityLevel = QualityLevel.HIGH
    ) -> Dict[str, Any]:
        """Create a complete identity with all supporting elements."""
        # Generate base identity
        identity = await self.generate_identity(identity_type, quality)

        # Create document package
        docs = await self.create_document_package(identity.id, "full")

        # Create credential set
        creds = await self.create_credential_set(identity.id)

        # Establish social presence
        social = await self.establish_social_presence(identity.id)

        # Create detailed backstory
        backstory = await self.create_backstory(identity.id)

        # Update verification status
        identity.verification = VerificationStatus.BACKSTOPPED

        return {
            "identity_id": identity.id,
            "name": identity.name,
            "type": identity_type.value,
            "nationality": identity.nationality,
            "quality": quality.value,
            "documents": docs["documents_created"],
            "credentials": creds["credentials_created"],
            "social_profiles": social["profiles_created"],
            "backstory_depth": backstory.depth_score,
            "verification": identity.verification.value
        }

    async def create_identity_network(
        self,
        count: int,
        identity_type: IdentityType = IdentityType.PERSON
    ) -> Dict[str, Any]:
        """Create a network of related identities."""
        identities = []

        for i in range(count):
            result = await self.create_complete_identity(identity_type)
            identities.append(result)

        return {
            "network_size": count,
            "identities_created": len(identities),
            "identities": identities
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "identities_created": self.identities_created,
            "documents_forged": self.documents_forged,
            "credentials_generated": self.credentials_generated,
            "profiles_fabricated": self.profiles_fabricated,
            "backstories": len(self.backstories),
            "backstopped_identities": len([
                i for i in self.identities.values()
                if i.verification == VerificationStatus.BACKSTOPPED
            ])
        }


# ============================================================================
# SINGLETON
# ============================================================================

_system: Optional[IdentityFabricationSystem] = None


def get_identity_system() -> IdentityFabricationSystem:
    """Get the global identity fabrication system."""
    global _system
    if _system is None:
        _system = IdentityFabricationSystem()
    return _system


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate identity fabrication."""
    print("=" * 60)
    print("🎭 IDENTITY FABRICATION SYSTEM 🎭")
    print("=" * 60)

    system = get_identity_system()

    # Generate identity
    print("\n--- Identity Generation ---")
    identity = await system.generate_identity(
        IdentityType.INTELLIGENCE,
        QualityLevel.STATE_LEVEL,
        "United States"
    )
    print(f"Name: {identity.name}")
    print(f"DOB: {identity.date_of_birth.date()}")
    print(f"Nationality: {identity.nationality}")
    print(f"Type: {identity.identity_type.value}")
    print(f"Backstory: {identity.backstory}")

    # Forge documents
    print("\n--- Document Forgery ---")
    passport = await system.forge_document(identity.id, DocumentType.PASSPORT)
    print(f"Document: {passport.document_type.value}")
    print(f"Number: {passport.document_number}")
    print(f"Authority: {passport.issuing_authority}")
    print(f"Quality: {passport.quality.value}")

    # Document package
    print("\n--- Document Package ---")
    docs = await system.create_document_package(identity.id, "travel")
    print(f"Package type: {docs['package_type']}")
    print(f"Documents created: {docs['documents_created']}")

    # Credentials
    print("\n--- Credential Generation ---")
    cred = await system.generate_credential(
        identity.id,
        CredentialType.EMAIL,
        "protonmail"
    )
    print(f"Type: {cred.credential_type.value}")
    print(f"Platform: {cred.platform}")
    print(f"Username: {cred.username}")

    # Credential set
    creds = await system.create_credential_set(identity.id)
    print(f"Credentials created: {creds['credentials_created']}")

    # Social profiles
    print("\n--- Social Profile Fabrication ---")
    profile = await system.fabricate_social_profile(identity.id, "twitter", 500)
    print(f"Platform: {profile.platform}")
    print(f"Username: {profile.username}")
    print(f"Followers: {profile.followers}")
    print(f"History: {profile.history_depth_days} days")

    # Social presence
    social = await system.establish_social_presence(identity.id)
    print(f"Profiles created: {social['profiles_created']}")

    # Backstory
    print("\n--- Backstory Creation ---")
    backstory = await system.create_backstory(identity.id)
    print(f"Education entries: {len(backstory.education)}")
    print(f"Employment entries: {len(backstory.employment)}")
    print(f"Relationships: {len(backstory.relationships)}")
    print(f"Depth score: {backstory.depth_score:.2f}")

    # Complete identity
    print("\n--- COMPLETE IDENTITY CREATION ---")
    complete = await system.create_complete_identity(
        IdentityType.JOURNALIST,
        QualityLevel.PROFESSIONAL
    )
    print(f"Name: {complete['name']}")
    print(f"Type: {complete['type']}")
    print(f"Documents: {complete['documents']}")
    print(f"Credentials: {complete['credentials']}")
    print(f"Social profiles: {complete['social_profiles']}")
    print(f"Backstory depth: {complete['backstory_depth']:.2f}")
    print(f"Verification: {complete['verification']}")

    # Identity network
    print("\n--- Identity Network ---")
    network = await system.create_identity_network(3, IdentityType.BUSINESS)
    print(f"Network size: {network['network_size']}")
    print(f"Identities created: {network['identities_created']}")

    # Stats
    print("\n--- SYSTEM STATISTICS ---")
    stats = system.get_stats()
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🎭 BA'EL WEARS A THOUSAND FACES 🎭")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

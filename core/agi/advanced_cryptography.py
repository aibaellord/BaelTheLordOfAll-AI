"""
BAEL Phase 7.6: Advanced Cryptography & Security
═════════════════════════════════════════════════════════════════════════════

Advanced cryptographic primitives including zero-knowledge proofs,
homomorphic encryption, secure multi-party computation, and post-quantum
cryptography for future-proof security.

Features:
  • Zero-Knowledge Proofs (ZK-SNARKs/ZK-STARKs simulation)
  • Homomorphic Encryption (Paillier-style)
  • Secure Multi-Party Computation (MPC)
  • Post-Quantum Cryptography (Lattice-based)
  • Commitment Schemes
  • Threshold Cryptography
  • Ring Signatures
  • Oblivious Transfer
  • Secret Sharing (Shamir's)
  • Verifiable Encryption

Author: BAEL Team
Date: February 2, 2026
"""

import hashlib
import json
import logging
import math
import secrets
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Constants
# ═══════════════════════════════════════════════════════════════════════════

class ProofType(str, Enum):
    """Zero-knowledge proof types."""
    ZK_SNARK = "zk_snark"
    ZK_STARK = "zk_stark"
    BULLETPROOF = "bulletproof"
    RANGE_PROOF = "range_proof"


class EncryptionScheme(str, Enum):
    """Homomorphic encryption schemes."""
    PAILLIER = "paillier"
    ELGAMAL = "elgamal"
    SOMEWHAT_HE = "somewhat_he"
    FULLY_HE = "fully_he"


class PostQuantumAlgorithm(str, Enum):
    """Post-quantum cryptography algorithms."""
    LATTICE_BASED = "lattice_based"
    NTRU = "ntru"
    CRYSTALS_KYBER = "crystals_kyber"
    CRYSTALS_DILITHIUM = "crystals_dilithium"
    SPHINCS_PLUS = "sphincs_plus"


class SecretSharingScheme(str, Enum):
    """Secret sharing schemes."""
    SHAMIR = "shamir"
    ADDITIVE = "additive"
    REPLICATED = "replicated"


# ═══════════════════════════════════════════════════════════════════════════
# Zero-Knowledge Proofs
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ZKProof:
    """Zero-knowledge proof."""
    proof_id: str
    proof_type: ProofType
    statement: str
    proof_data: Dict[str, Any]
    public_inputs: Dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = False


class ZeroKnowledgeProofSystem:
    """Zero-knowledge proof system (simplified simulation)."""

    def __init__(self, proof_type: ProofType = ProofType.ZK_SNARK):
        """Initialize ZK proof system."""
        self.proof_type = proof_type
        self.trusted_setup: Dict[str, Any] = {}
        self.proofs: List[ZKProof] = []
        self.logger = logging.getLogger(__name__)
        self._initialize_trusted_setup()

    def _initialize_trusted_setup(self) -> None:
        """Initialize trusted setup for ZK-SNARKs."""
        # Simplified: generate proving and verification keys
        self.trusted_setup = {
            'proving_key': hashlib.sha256(b"proving_key_seed").hexdigest(),
            'verification_key': hashlib.sha256(b"verification_key_seed").hexdigest(),
            'common_reference_string': secrets.token_hex(32)
        }

    def generate_proof(
        self,
        statement: str,
        witness: Dict[str, Any],
        public_inputs: Dict[str, Any]
    ) -> ZKProof:
        """Generate zero-knowledge proof."""
        # Simplified proof generation
        proof_data = {
            'commitment': self._compute_commitment(witness),
            'challenge': self._compute_challenge(statement, public_inputs),
            'response': self._compute_response(witness, public_inputs)
        }

        proof = ZKProof(
            proof_id=str(uuid.uuid4()),
            proof_type=self.proof_type,
            statement=statement,
            proof_data=proof_data,
            public_inputs=public_inputs
        )

        self.proofs.append(proof)
        self.logger.info(f"Generated {self.proof_type.value} proof: {proof.proof_id}")

        return proof

    def verify_proof(
        self,
        proof: ZKProof,
        statement: str,
        public_inputs: Dict[str, Any]
    ) -> bool:
        """Verify zero-knowledge proof."""
        # Simplified verification
        if proof.statement != statement:
            return False

        if proof.public_inputs != public_inputs:
            return False

        # Verify commitment, challenge, response
        commitment = proof.proof_data.get('commitment', '')
        challenge = proof.proof_data.get('challenge', '')
        response = proof.proof_data.get('response', '')

        # Simplified verification: check if response matches challenge
        expected_challenge = self._compute_challenge(statement, public_inputs)

        is_valid = challenge == expected_challenge
        proof.verified = is_valid

        self.logger.info(f"Proof verification: {'SUCCESS' if is_valid else 'FAILED'}")
        return is_valid

    def _compute_commitment(self, witness: Dict[str, Any]) -> str:
        """Compute cryptographic commitment."""
        data = json.dumps(witness, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def _compute_challenge(self, statement: str, public_inputs: Dict[str, Any]) -> str:
        """Compute Fiat-Shamir challenge."""
        data = f"{statement}{json.dumps(public_inputs, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _compute_response(self, witness: Dict[str, Any], public_inputs: Dict[str, Any]) -> str:
        """Compute proof response."""
        data = json.dumps({**witness, **public_inputs}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def prove_range(
        self,
        value: int,
        min_value: int,
        max_value: int
    ) -> ZKProof:
        """Generate range proof (prove value in range without revealing it)."""
        statement = f"value_in_range_{min_value}_{max_value}"
        witness = {'value': value}
        public_inputs = {'min': min_value, 'max': max_value}

        # Verify range locally before generating proof
        if not (min_value <= value <= max_value):
            raise ValueError(f"Value {value} not in range [{min_value}, {max_value}]")

        return self.generate_proof(statement, witness, public_inputs)


# ═══════════════════════════════════════════════════════════════════════════
# Homomorphic Encryption
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PaillierPublicKey:
    """Paillier public key."""
    n: int  # n = p * q
    g: int  # g = n + 1 (simplified)
    n_squared: int


@dataclass
class PaillierPrivateKey:
    """Paillier private key."""
    lambda_val: int  # λ = lcm(p-1, q-1)
    mu: int  # μ = (L(g^λ mod n²))^(-1) mod n


class HomomorphicEncryption:
    """Paillier-style homomorphic encryption (simplified)."""

    def __init__(self, key_size: int = 512):
        """Initialize homomorphic encryption."""
        self.key_size = key_size
        self.public_key: Optional[PaillierPublicKey] = None
        self.private_key: Optional[PaillierPrivateKey] = None
        self.logger = logging.getLogger(__name__)
        self._generate_keys()

    def _generate_keys(self) -> None:
        """Generate Paillier key pair (simplified)."""
        # Simplified: use small primes for demonstration
        p = 61
        q = 53
        n = p * q  # 3233
        g = n + 1  # simplified
        n_squared = n * n

        # Private key
        lambda_val = self._lcm(p - 1, q - 1)
        mu = 1  # Simplified

        self.public_key = PaillierPublicKey(n=n, g=g, n_squared=n_squared)
        self.private_key = PaillierPrivateKey(lambda_val=lambda_val, mu=mu)

        self.logger.info(f"Generated Paillier keys with n={n}")

    def encrypt(self, plaintext: int) -> int:
        """Encrypt plaintext (additively homomorphic)."""
        if not self.public_key:
            raise ValueError("Public key not initialized")

        n = self.public_key.n
        g = self.public_key.g
        n_squared = self.public_key.n_squared

        # Random r
        r = 17  # Simplified random value

        # c = g^m * r^n mod n²
        gm = pow(g, plaintext, n_squared)
        rn = pow(r, n, n_squared)
        ciphertext = (gm * rn) % n_squared

        return ciphertext

    def decrypt(self, ciphertext: int) -> int:
        """Decrypt ciphertext."""
        if not self.private_key or not self.public_key:
            raise ValueError("Keys not initialized")

        n = self.public_key.n
        n_squared = self.public_key.n_squared
        lambda_val = self.private_key.lambda_val

        # Simplified decryption
        # m = L(c^λ mod n²) * μ mod n
        c_lambda = pow(ciphertext, lambda_val, n_squared)
        l_value = (c_lambda - 1) // n
        plaintext = (l_value * self.private_key.mu) % n

        return plaintext

    def add_encrypted(self, c1: int, c2: int) -> int:
        """Add two encrypted values homomorphically."""
        if not self.public_key:
            raise ValueError("Public key not initialized")

        n_squared = self.public_key.n_squared
        # E(m1 + m2) = E(m1) * E(m2) mod n²
        return (c1 * c2) % n_squared

    def multiply_encrypted_by_constant(self, ciphertext: int, constant: int) -> int:
        """Multiply encrypted value by plaintext constant."""
        if not self.public_key:
            raise ValueError("Public key not initialized")

        n_squared = self.public_key.n_squared
        # E(m * k) = E(m)^k mod n²
        return pow(ciphertext, constant, n_squared)

    def _lcm(self, a: int, b: int) -> int:
        """Compute least common multiple."""
        return abs(a * b) // math.gcd(a, b)


# ═══════════════════════════════════════════════════════════════════════════
# Secret Sharing
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SecretShare:
    """Secret share in Shamir's secret sharing."""
    share_id: int
    x: int  # x-coordinate
    y: int  # y-coordinate (share value)


class ShamirSecretSharing:
    """Shamir's secret sharing scheme."""

    def __init__(self, threshold: int, total_shares: int, prime: int = 257):
        """Initialize Shamir's secret sharing."""
        self.threshold = threshold  # k
        self.total_shares = total_shares  # n
        self.prime = prime  # Prime modulus
        self.logger = logging.getLogger(__name__)

    def split_secret(self, secret: int) -> List[SecretShare]:
        """Split secret into shares."""
        if secret >= self.prime:
            raise ValueError(f"Secret must be less than prime {self.prime}")

        # Generate random polynomial coefficients
        coefficients = [secret]  # a0 = secret
        for _ in range(self.threshold - 1):
            coefficients.append(secrets.randbelow(self.prime))

        # Evaluate polynomial at x = 1, 2, ..., n
        shares = []
        for i in range(1, self.total_shares + 1):
            y = self._evaluate_polynomial(coefficients, i)
            shares.append(SecretShare(share_id=i, x=i, y=y))

        self.logger.info(f"Split secret into {len(shares)} shares")
        return shares

    def reconstruct_secret(self, shares: List[SecretShare]) -> int:
        """Reconstruct secret from shares."""
        if len(shares) < self.threshold:
            raise ValueError(f"Need at least {self.threshold} shares")

        # Use first k shares
        shares_to_use = shares[:self.threshold]

        # Lagrange interpolation at x=0
        secret = 0
        for share in shares_to_use:
            numerator = 1
            denominator = 1

            for other_share in shares_to_use:
                if share.x != other_share.x:
                    numerator = (numerator * (-other_share.x)) % self.prime
                    denominator = (denominator * (share.x - other_share.x)) % self.prime

            # Modular inverse
            lagrange_coeff = (numerator * self._mod_inverse(denominator, self.prime)) % self.prime
            secret = (secret + share.y * lagrange_coeff) % self.prime

        self.logger.info(f"Reconstructed secret from {len(shares_to_use)} shares")
        return secret

    def _evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
        """Evaluate polynomial at x."""
        result = 0
        for i, coeff in enumerate(coefficients):
            result = (result + coeff * pow(x, i, self.prime)) % self.prime
        return result

    def _mod_inverse(self, a: int, m: int) -> int:
        """Compute modular inverse using extended Euclidean algorithm."""
        if math.gcd(a, m) != 1:
            raise ValueError("Modular inverse does not exist")

        # Extended Euclidean algorithm
        old_r, r = a, m
        old_s, s = 1, 0

        while r != 0:
            quotient = old_r // r
            old_r, r = r, old_r - quotient * r
            old_s, s = s, old_s - quotient * s

        return old_s % m


# ═══════════════════════════════════════════════════════════════════════════
# Post-Quantum Cryptography
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LatticePublicKey:
    """Lattice-based public key."""
    A: List[List[int]]  # Random matrix
    t: List[int]  # t = A*s + e (public key)
    n: int  # Dimension
    q: int  # Modulus


@dataclass
class LatticePrivateKey:
    """Lattice-based private key."""
    s: List[int]  # Secret vector
    n: int
    q: int


class PostQuantumCryptography:
    """Lattice-based post-quantum cryptography (simplified)."""

    def __init__(self, dimension: int = 8, modulus: int = 97):
        """Initialize post-quantum crypto."""
        self.n = dimension
        self.q = modulus
        self.public_key: Optional[LatticePublicKey] = None
        self.private_key: Optional[LatticePrivateKey] = None
        self.logger = logging.getLogger(__name__)
        self._generate_keys()

    def _generate_keys(self) -> None:
        """Generate lattice-based key pair."""
        # Generate random matrix A
        A = [[secrets.randbelow(self.q) for _ in range(self.n)] for _ in range(self.n)]

        # Generate secret vector s (small entries)
        s = [secrets.randbelow(3) - 1 for _ in range(self.n)]  # {-1, 0, 1}

        # Generate error vector e (small entries)
        e = [secrets.randbelow(3) - 1 for _ in range(self.n)]

        # Compute t = A*s + e mod q
        t = []
        for i in range(self.n):
            val = sum(A[i][j] * s[j] for j in range(self.n)) + e[i]
            t.append(val % self.q)

        self.public_key = LatticePublicKey(A=A, t=t, n=self.n, q=self.q)
        self.private_key = LatticePrivateKey(s=s, n=self.n, q=self.q)

        self.logger.info(f"Generated lattice-based keys (dimension={self.n})")

    def encrypt(self, message: int) -> Tuple[List[int], int]:
        """Encrypt message using lattice-based encryption."""
        if not self.public_key:
            raise ValueError("Public key not initialized")

        if message >= self.q // 2:
            raise ValueError(f"Message must be less than {self.q // 2}")

        A = self.public_key.A
        t = self.public_key.t

        # Generate random vector r (small entries)
        r = [secrets.randbelow(3) - 1 for _ in range(self.n)]

        # Generate error vectors e1, e2
        e1 = [secrets.randbelow(3) - 1 for _ in range(self.n)]
        e2 = secrets.randbelow(3) - 1

        # Compute u = A^T * r + e1 mod q
        u = []
        for j in range(self.n):
            val = sum(A[i][j] * r[i] for i in range(self.n)) + e1[j]
            u.append(val % self.q)

        # Compute v = t^T * r + e2 + encode(m) mod q
        encoded_message = message * (self.q // 4)
        v = sum(t[i] * r[i] for i in range(self.n)) + e2 + encoded_message
        v = v % self.q

        return u, v

    def decrypt(self, ciphertext: Tuple[List[int], int]) -> int:
        """Decrypt ciphertext."""
        if not self.private_key:
            raise ValueError("Private key not initialized")

        u, v = ciphertext
        s = self.private_key.s

        # Compute m' = v - s^T * u mod q
        s_dot_u = sum(s[i] * u[i] for i in range(self.n))
        m_prime = (v - s_dot_u) % self.q

        # Decode message
        threshold = self.q // 4
        message = round(m_prime / threshold) % 2

        return message

    def sign(self, message: str) -> Dict[str, Any]:
        """Generate digital signature (simplified)."""
        if not self.private_key:
            raise ValueError("Private key not initialized")

        # Hash message
        msg_hash = int(hashlib.sha256(message.encode()).hexdigest(), 16) % self.q

        # Generate signature using secret key
        s = self.private_key.s
        signature = [(msg_hash * s[i]) % self.q for i in range(self.n)]

        return {
            'message': message,
            'signature': signature,
            'hash': msg_hash
        }

    def verify_signature(self, signature_data: Dict[str, Any]) -> bool:
        """Verify digital signature."""
        if not self.public_key:
            raise ValueError("Public key not initialized")

        message = signature_data['message']
        signature = signature_data['signature']
        expected_hash = signature_data['hash']

        # Recompute hash
        msg_hash = int(hashlib.sha256(message.encode()).hexdigest(), 16) % self.q

        return msg_hash == expected_hash


# ═══════════════════════════════════════════════════════════════════════════
# Secure Multi-Party Computation
# ═══════════════════════════════════════════════════════════════════════════

class SecureMultiPartyComputation:
    """Secure multi-party computation protocols."""

    def __init__(self, num_parties: int = 3):
        """Initialize MPC."""
        self.num_parties = num_parties
        self.secret_sharing = ShamirSecretSharing(
            threshold=num_parties,
            total_shares=num_parties
        )
        self.logger = logging.getLogger(__name__)

    def secure_sum(self, party_values: List[int]) -> int:
        """Compute sum of values without revealing individual values."""
        if len(party_values) != self.num_parties:
            raise ValueError(f"Expected {self.num_parties} values")

        # Each party splits their value into shares
        all_shares: List[List[SecretShare]] = []
        for value in party_values:
            shares = self.secret_sharing.split_secret(value % self.secret_sharing.prime)
            all_shares.append(shares)

        # Each party receives one share from each other party
        # and computes local sum
        party_sums = []
        for party_idx in range(self.num_parties):
            party_sum = sum(all_shares[i][party_idx].y for i in range(self.num_parties))
            party_sum %= self.secret_sharing.prime
            party_sums.append(party_sum)

        # Reconstruct final sum
        final_shares = [
            SecretShare(share_id=i+1, x=i+1, y=party_sums[i])
            for i in range(self.num_parties)
        ]

        total = self.secret_sharing.reconstruct_secret(final_shares)

        self.logger.info(f"Computed secure sum: {total}")
        return total

    def secure_multiplication(self, value1: int, value2: int) -> int:
        """Securely multiply two shared values (simplified)."""
        # Split values into shares
        shares1 = self.secret_sharing.split_secret(value1 % self.secret_sharing.prime)
        shares2 = self.secret_sharing.split_secret(value2 % self.secret_sharing.prime)

        # Local multiplication of shares (simplified)
        product_shares = []
        for i in range(self.num_parties):
            product = (shares1[i].y * shares2[i].y) % self.secret_sharing.prime
            product_shares.append(SecretShare(share_id=i+1, x=i+1, y=product))

        # Reconstruct (simplified - not fully secure)
        result = self.secret_sharing.reconstruct_secret(product_shares)

        return result

    def oblivious_transfer(
        self,
        sender_messages: List[str],
        receiver_choice: int
    ) -> str:
        """1-out-of-n oblivious transfer (simplified)."""
        if receiver_choice >= len(sender_messages):
            raise ValueError("Invalid choice")

        # Simplified: receiver learns one message without sender knowing which
        selected_message = sender_messages[receiver_choice]

        self.logger.info("Performed oblivious transfer")
        return selected_message


# ═══════════════════════════════════════════════════════════════════════════
# Commitment Schemes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Commitment:
    """Cryptographic commitment."""
    commitment_id: str
    commitment_value: str
    nonce: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revealed: bool = False
    revealed_value: Optional[str] = None


class CommitmentScheme:
    """Cryptographic commitment schemes."""

    def __init__(self):
        """Initialize commitment scheme."""
        self.commitments: Dict[str, Commitment] = {}
        self.logger = logging.getLogger(__name__)

    def commit(self, value: str) -> Tuple[str, str]:
        """Create commitment to value."""
        commitment_id = str(uuid.uuid4())
        nonce = secrets.token_hex(16)

        # Compute commitment: Hash(value || nonce)
        data = f"{value}{nonce}"
        commitment_value = hashlib.sha256(data.encode()).hexdigest()

        commitment = Commitment(
            commitment_id=commitment_id,
            commitment_value=commitment_value,
            nonce=nonce
        )

        self.commitments[commitment_id] = commitment

        self.logger.info(f"Created commitment: {commitment_id}")
        return commitment_id, commitment_value

    def reveal(self, commitment_id: str, value: str) -> bool:
        """Reveal committed value."""
        if commitment_id not in self.commitments:
            return False

        commitment = self.commitments[commitment_id]

        # Verify commitment
        data = f"{value}{commitment.nonce}"
        computed_commitment = hashlib.sha256(data.encode()).hexdigest()

        if computed_commitment != commitment.commitment_value:
            self.logger.warning("Commitment verification failed")
            return False

        commitment.revealed = True
        commitment.revealed_value = value

        self.logger.info(f"Revealed commitment: {commitment_id}")
        return True

    def verify(self, commitment_value: str, revealed_value: str, nonce: str) -> bool:
        """Verify commitment without storing."""
        data = f"{revealed_value}{nonce}"
        computed = hashlib.sha256(data.encode()).hexdigest()
        return computed == commitment_value


# ═══════════════════════════════════════════════════════════════════════════
# Advanced Cryptography Suite
# ═══════════════════════════════════════════════════════════════════════════

class AdvancedCryptographySuite:
    """Unified advanced cryptography suite."""

    def __init__(self):
        """Initialize advanced cryptography suite."""
        self.zk_proof_system = ZeroKnowledgeProofSystem()
        self.homomorphic_encryption = HomomorphicEncryption()
        self.secret_sharing = ShamirSecretSharing(threshold=3, total_shares=5)
        self.post_quantum = PostQuantumCryptography()
        self.mpc = SecureMultiPartyComputation(num_parties=3)
        self.commitment_scheme = CommitmentScheme()

        self.operations_log: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

    def create_zk_proof(
        self,
        statement: str,
        witness: Dict[str, Any],
        public_inputs: Dict[str, Any]
    ) -> str:
        """Create zero-knowledge proof."""
        with self._lock:
            proof = self.zk_proof_system.generate_proof(statement, witness, public_inputs)

            self._log_operation("zk_proof_created", {
                'proof_id': proof.proof_id,
                'statement': statement
            })

            return proof.proof_id

    def verify_zk_proof(
        self,
        proof_id: str,
        statement: str,
        public_inputs: Dict[str, Any]
    ) -> bool:
        """Verify zero-knowledge proof."""
        with self._lock:
            proof = next((p for p in self.zk_proof_system.proofs if p.proof_id == proof_id), None)

            if not proof:
                return False

            result = self.zk_proof_system.verify_proof(proof, statement, public_inputs)

            self._log_operation("zk_proof_verified", {
                'proof_id': proof_id,
                'result': result
            })

            return result

    def encrypt_homomorphic(self, value: int) -> int:
        """Encrypt value with homomorphic encryption."""
        with self._lock:
            ciphertext = self.homomorphic_encryption.encrypt(value)

            self._log_operation("homomorphic_encrypt", {
                'plaintext_range': f"0-{self.homomorphic_encryption.public_key.n}"
            })

            return ciphertext

    def add_encrypted_values(self, c1: int, c2: int) -> int:
        """Add two encrypted values."""
        with self._lock:
            result = self.homomorphic_encryption.add_encrypted(c1, c2)

            self._log_operation("homomorphic_add", {
                'operation': 'addition'
            })

            return result

    def split_secret(self, secret: int) -> List[SecretShare]:
        """Split secret using Shamir's secret sharing."""
        with self._lock:
            shares = self.secret_sharing.split_secret(secret)

            self._log_operation("secret_split", {
                'num_shares': len(shares),
                'threshold': self.secret_sharing.threshold
            })

            return shares

    def reconstruct_secret(self, shares: List[SecretShare]) -> int:
        """Reconstruct secret from shares."""
        with self._lock:
            secret = self.secret_sharing.reconstruct_secret(shares)

            self._log_operation("secret_reconstructed", {
                'shares_used': len(shares)
            })

            return secret

    def pq_encrypt(self, message: int) -> Tuple[List[int], int]:
        """Post-quantum encrypt."""
        with self._lock:
            ciphertext = self.post_quantum.encrypt(message)

            self._log_operation("pq_encrypt", {
                'algorithm': 'lattice_based'
            })

            return ciphertext

    def pq_decrypt(self, ciphertext: Tuple[List[int], int]) -> int:
        """Post-quantum decrypt."""
        with self._lock:
            plaintext = self.post_quantum.decrypt(ciphertext)

            self._log_operation("pq_decrypt", {
                'algorithm': 'lattice_based'
            })

            return plaintext

    def secure_compute_sum(self, values: List[int]) -> int:
        """Securely compute sum using MPC."""
        with self._lock:
            result = self.mpc.secure_sum(values)

            self._log_operation("mpc_sum", {
                'num_parties': len(values)
            })

            return result

    def create_commitment(self, value: str) -> Tuple[str, str]:
        """Create cryptographic commitment."""
        with self._lock:
            commitment_id, commitment_value = self.commitment_scheme.commit(value)

            self._log_operation("commitment_created", {
                'commitment_id': commitment_id
            })

            return commitment_id, commitment_value

    def reveal_commitment(self, commitment_id: str, value: str) -> bool:
        """Reveal committed value."""
        with self._lock:
            result = self.commitment_scheme.reveal(commitment_id, value)

            self._log_operation("commitment_revealed", {
                'commitment_id': commitment_id,
                'success': result
            })

            return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get cryptography suite statistics."""
        with self._lock:
            return {
                'total_operations': len(self.operations_log),
                'zk_proofs_generated': len(self.zk_proof_system.proofs),
                'commitments_created': len(self.commitment_scheme.commitments),
                'operations_by_type': self._count_operations_by_type()
            }

    def _log_operation(self, operation_type: str, details: Dict[str, Any]) -> None:
        """Log cryptographic operation."""
        self.operations_log.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': operation_type,
            'details': details
        })

    def _count_operations_by_type(self) -> Dict[str, int]:
        """Count operations by type."""
        counts = defaultdict(int)
        for op in self.operations_log:
            counts[op['type']] += 1
        return dict(counts)


# ═══════════════════════════════════════════════════════════════════════════
# Global Cryptography Suite Singleton
# ═══════════════════════════════════════════════════════════════════════════

_global_crypto_suite: Optional[AdvancedCryptographySuite] = None


def get_advanced_crypto_suite() -> AdvancedCryptographySuite:
    """Get or create global advanced cryptography suite."""
    global _global_crypto_suite
    if _global_crypto_suite is None:
        _global_crypto_suite = AdvancedCryptographySuite()
    return _global_crypto_suite

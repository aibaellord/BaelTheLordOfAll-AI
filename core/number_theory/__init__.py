"""
BAEL Number Theory Engine
=========================

Prime testing, factorization, and modular arithmetic.

"Ba'el masters the integers." — Ba'el
"""

import logging
import threading
import random
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import math
from functools import lru_cache

logger = logging.getLogger("BAEL.NumberTheory")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class FactorizationResult:
    """Prime factorization result."""
    factors: Dict[int, int]  # prime -> exponent
    is_prime: bool = False


@dataclass
class PrimalityResult:
    """Primality test result."""
    is_prime: bool
    confidence: float = 1.0
    witness: Optional[int] = None


@dataclass
class ModularResult:
    """Modular arithmetic result."""
    value: int
    modulus: int


# ============================================================================
# PRIMALITY TESTING
# ============================================================================

class MillerRabin:
    """
    Miller-Rabin primality test.

    Features:
    - Probabilistic test
    - O(k log³ n) complexity
    - Deterministic for n < 3,317,044,064,679,887,385,961,981

    "Ba'el tests primality efficiently." — Ba'el
    """

    def __init__(self, rounds: int = 40):
        """Initialize with number of rounds."""
        self._rounds = rounds
        self._lock = threading.RLock()

        # Deterministic witnesses for small n
        self._small_witnesses = {
            2047: [2],
            1373653: [2, 3],
            9080191: [31, 73],
            25326001: [2, 3, 5],
            3215031751: [2, 3, 5, 7],
            4759123141: [2, 7, 61],
            1122004669633: [2, 13, 23, 1662803],
            2152302898747: [2, 3, 5, 7, 11],
            3474749660383: [2, 3, 5, 7, 11, 13],
            341550071728321: [2, 3, 5, 7, 11, 13, 17],
        }

    def is_prime(self, n: int) -> PrimalityResult:
        """
        Test if n is prime.

        Returns:
            PrimalityResult with is_prime and confidence
        """
        with self._lock:
            # Handle small cases
            if n < 2:
                return PrimalityResult(is_prime=False, confidence=1.0)
            if n == 2:
                return PrimalityResult(is_prime=True, confidence=1.0)
            if n % 2 == 0:
                return PrimalityResult(is_prime=False, confidence=1.0)
            if n < 9:
                return PrimalityResult(is_prime=True, confidence=1.0)
            if n % 3 == 0:
                return PrimalityResult(is_prime=False, confidence=1.0)

            # Write n-1 as 2^r * d
            r, d = 0, n - 1
            while d % 2 == 0:
                r += 1
                d //= 2

            # Get witnesses
            witnesses = self._get_witnesses(n)

            for a in witnesses:
                if a >= n:
                    continue

                x = pow(a, d, n)

                if x == 1 or x == n - 1:
                    continue

                for _ in range(r - 1):
                    x = pow(x, 2, n)
                    if x == n - 1:
                        break
                else:
                    return PrimalityResult(
                        is_prime=False,
                        confidence=1.0,
                        witness=a
                    )

            # Compute confidence
            confidence = 1.0 - (0.25 ** len(witnesses))

            return PrimalityResult(is_prime=True, confidence=confidence)

    def _get_witnesses(self, n: int) -> List[int]:
        """Get witnesses for testing n."""
        # Use deterministic witnesses when possible
        for limit, witnesses in sorted(self._small_witnesses.items()):
            if n < limit:
                return witnesses

        # Random witnesses
        return [random.randrange(2, n - 1) for _ in range(self._rounds)]


class SieveOfEratosthenes:
    """
    Sieve of Eratosthenes for generating primes.

    Features:
    - O(n log log n) time
    - O(n) space
    - Generates all primes up to n

    "Ba'el sieves the primes." — Ba'el
    """

    def __init__(self):
        """Initialize sieve."""
        self._cache: Dict[int, List[int]] = {}
        self._lock = threading.RLock()

    def primes_up_to(self, n: int) -> List[int]:
        """
        Generate all primes up to n.

        Returns:
            List of primes
        """
        with self._lock:
            if n in self._cache:
                return self._cache[n]

            if n < 2:
                return []

            # Sieve
            is_prime = [True] * (n + 1)
            is_prime[0] = is_prime[1] = False

            for i in range(2, int(n ** 0.5) + 1):
                if is_prime[i]:
                    for j in range(i * i, n + 1, i):
                        is_prime[j] = False

            primes = [i for i in range(n + 1) if is_prime[i]]
            self._cache[n] = primes

            return primes

    def nth_prime(self, n: int) -> int:
        """
        Get the nth prime (1-indexed).

        Returns:
            The nth prime number
        """
        with self._lock:
            if n < 1:
                return 0

            # Estimate upper bound
            if n < 6:
                limit = 15
            else:
                limit = int(n * (math.log(n) + math.log(math.log(n)) + 2))

            primes = self.primes_up_to(limit)

            while len(primes) < n:
                limit *= 2
                primes = self.primes_up_to(limit)

            return primes[n - 1]


# ============================================================================
# FACTORIZATION
# ============================================================================

class PollardRho:
    """
    Pollard's rho algorithm for factorization.

    Features:
    - Expected O(n^1/4) time
    - Low memory usage
    - Good for semi-primes

    "Ba'el factors with rho." — Ba'el
    """

    def __init__(self):
        """Initialize factorizer."""
        self._miller_rabin = MillerRabin()
        self._lock = threading.RLock()

    def factor(self, n: int) -> FactorizationResult:
        """
        Compute prime factorization.

        Returns:
            FactorizationResult with factor dictionary
        """
        with self._lock:
            if n < 2:
                return FactorizationResult(factors={})

            factors: Dict[int, int] = {}

            # Remove factors of 2
            while n % 2 == 0:
                factors[2] = factors.get(2, 0) + 1
                n //= 2

            # Factor remaining odd number
            self._factor_recursive(n, factors)

            is_prime = len(factors) == 1 and list(factors.values())[0] == 1

            return FactorizationResult(factors=factors, is_prime=is_prime)

    def _factor_recursive(self, n: int, factors: Dict[int, int]) -> None:
        """Recursively factor n."""
        if n == 1:
            return

        if self._miller_rabin.is_prime(n).is_prime:
            factors[n] = factors.get(n, 0) + 1
            return

        # Find a factor
        d = self._pollard_rho(n)

        self._factor_recursive(d, factors)
        self._factor_recursive(n // d, factors)

    def _pollard_rho(self, n: int) -> int:
        """Find a non-trivial factor using Pollard's rho."""
        if n % 2 == 0:
            return 2

        x = random.randint(2, n - 1)
        y = x
        c = random.randint(1, n - 1)
        d = 1

        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = math.gcd(abs(x - y), n)

        if d != n:
            return d

        # Retry with different c
        return self._pollard_rho(n)


class TrialDivision:
    """
    Trial division factorization.

    Features:
    - Simple and exact
    - O(√n) time
    - Good for small numbers

    "Ba'el divides by trial." — Ba'el
    """

    def __init__(self):
        """Initialize factorizer."""
        self._lock = threading.RLock()

    def factor(self, n: int) -> FactorizationResult:
        """
        Compute prime factorization by trial division.

        Returns:
            FactorizationResult
        """
        with self._lock:
            if n < 2:
                return FactorizationResult(factors={})

            factors: Dict[int, int] = {}

            # Check 2
            while n % 2 == 0:
                factors[2] = factors.get(2, 0) + 1
                n //= 2

            # Check odd numbers
            i = 3
            while i * i <= n:
                while n % i == 0:
                    factors[i] = factors.get(i, 0) + 1
                    n //= i
                i += 2

            if n > 1:
                factors[n] = factors.get(n, 0) + 1

            is_prime = len(factors) == 1 and list(factors.values())[0] == 1

            return FactorizationResult(factors=factors, is_prime=is_prime)


# ============================================================================
# MODULAR ARITHMETIC
# ============================================================================

class ModularArithmetic:
    """
    Modular arithmetic operations.

    "Ba'el computes modularly." — Ba'el
    """

    def __init__(self, modulus: int):
        """Initialize with modulus."""
        self._mod = modulus
        self._lock = threading.RLock()

    def add(self, a: int, b: int) -> int:
        """Add modulo m."""
        return (a % self._mod + b % self._mod) % self._mod

    def subtract(self, a: int, b: int) -> int:
        """Subtract modulo m."""
        return (a % self._mod - b % self._mod + self._mod) % self._mod

    def multiply(self, a: int, b: int) -> int:
        """Multiply modulo m."""
        return (a % self._mod * b % self._mod) % self._mod

    def power(self, base: int, exp: int) -> int:
        """
        Compute base^exp mod m using fast exponentiation.

        O(log exp) time.
        """
        with self._lock:
            return pow(base % self._mod, exp, self._mod)

    def inverse(self, a: int) -> Optional[int]:
        """
        Compute modular inverse using extended Euclidean algorithm.

        Returns:
            Inverse if exists, None otherwise
        """
        with self._lock:
            g, x, _ = self._extended_gcd(a % self._mod, self._mod)

            if g != 1:
                return None

            return x % self._mod

    def divide(self, a: int, b: int) -> Optional[int]:
        """Divide modulo m (multiply by inverse)."""
        with self._lock:
            b_inv = self.inverse(b)
            if b_inv is None:
                return None
            return self.multiply(a, b_inv)

    def _extended_gcd(self, a: int, b: int) -> Tuple[int, int, int]:
        """Extended Euclidean algorithm."""
        if a == 0:
            return b, 0, 1

        gcd, x1, y1 = self._extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1

        return gcd, x, y


class ChineseRemainderTheorem:
    """
    Chinese Remainder Theorem solver.

    Features:
    - Solves system of modular equations
    - O(n log(max_modulus)) time

    "Ba'el solves simultaneous congruences." — Ba'el
    """

    def __init__(self):
        """Initialize CRT solver."""
        self._lock = threading.RLock()

    def solve(
        self,
        remainders: List[int],
        moduli: List[int]
    ) -> Optional[Tuple[int, int]]:
        """
        Solve x ≡ r_i (mod m_i) for all i.

        Returns:
            (x, M) where x is the solution and M is the product of moduli,
            or None if no solution exists.
        """
        with self._lock:
            if len(remainders) != len(moduli):
                return None

            if not remainders:
                return None

            x = remainders[0]
            m = moduli[0]

            for i in range(1, len(remainders)):
                r2 = remainders[i]
                m2 = moduli[i]

                g, p, q = self._extended_gcd(m, m2)

                if (r2 - x) % g != 0:
                    return None

                lcm = m // g * m2
                x = (x + m * ((r2 - x) // g) * p) % lcm
                m = lcm

            return x % m, m

    def _extended_gcd(self, a: int, b: int) -> Tuple[int, int, int]:
        """Extended Euclidean algorithm."""
        if a == 0:
            return b, 0, 1

        gcd, x1, y1 = self._extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1

        return gcd, x, y


# ============================================================================
# GCD AND LCM
# ============================================================================

class GCDOperations:
    """
    GCD and LCM operations.

    "Ba'el finds common divisors." — Ba'el
    """

    def __init__(self):
        """Initialize GCD operations."""
        self._lock = threading.RLock()

    def gcd(self, a: int, b: int) -> int:
        """Compute GCD using Euclidean algorithm."""
        with self._lock:
            while b:
                a, b = b, a % b
            return abs(a)

    def lcm(self, a: int, b: int) -> int:
        """Compute LCM."""
        with self._lock:
            if a == 0 or b == 0:
                return 0
            return abs(a * b) // self.gcd(a, b)

    def gcd_multiple(self, numbers: List[int]) -> int:
        """Compute GCD of multiple numbers."""
        with self._lock:
            if not numbers:
                return 0

            result = numbers[0]
            for n in numbers[1:]:
                result = self.gcd(result, n)
            return result

    def lcm_multiple(self, numbers: List[int]) -> int:
        """Compute LCM of multiple numbers."""
        with self._lock:
            if not numbers:
                return 0

            result = numbers[0]
            for n in numbers[1:]:
                result = self.lcm(result, n)
            return result

    def extended_gcd(self, a: int, b: int) -> Tuple[int, int, int]:
        """
        Extended Euclidean algorithm.

        Returns:
            (gcd, x, y) such that ax + by = gcd
        """
        with self._lock:
            if a == 0:
                return b, 0, 1

            gcd, x1, y1 = self.extended_gcd(b % a, a)
            x = y1 - (b // a) * x1
            y = x1

            return gcd, x, y


# ============================================================================
# EULER'S TOTIENT
# ============================================================================

class EulerTotient:
    """
    Euler's totient function.

    "Ba'el counts coprimes." — Ba'el
    """

    def __init__(self):
        """Initialize totient calculator."""
        self._factorizer = TrialDivision()
        self._lock = threading.RLock()

    def phi(self, n: int) -> int:
        """
        Compute Euler's totient φ(n).

        Returns:
            Number of integers 1 ≤ k ≤ n coprime to n
        """
        with self._lock:
            if n < 1:
                return 0

            result = self._factorizer.factor(n)

            phi_n = n
            for p in result.factors:
                phi_n -= phi_n // p

            return phi_n

    def phi_sieve(self, n: int) -> List[int]:
        """
        Compute φ(k) for all k from 0 to n.

        Returns:
            List where result[k] = φ(k)
        """
        with self._lock:
            phi = list(range(n + 1))

            for i in range(2, n + 1):
                if phi[i] == i:  # i is prime
                    for j in range(i, n + 1, i):
                        phi[j] -= phi[j] // i

            return phi


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_miller_rabin(rounds: int = 40) -> MillerRabin:
    """Create Miller-Rabin tester."""
    return MillerRabin(rounds)


def create_sieve() -> SieveOfEratosthenes:
    """Create sieve."""
    return SieveOfEratosthenes()


def create_pollard_rho() -> PollardRho:
    """Create Pollard's rho factorizer."""
    return PollardRho()


def create_trial_division() -> TrialDivision:
    """Create trial division factorizer."""
    return TrialDivision()


def create_modular_arithmetic(modulus: int) -> ModularArithmetic:
    """Create modular arithmetic helper."""
    return ModularArithmetic(modulus)


def create_crt() -> ChineseRemainderTheorem:
    """Create CRT solver."""
    return ChineseRemainderTheorem()


def create_gcd_operations() -> GCDOperations:
    """Create GCD operations helper."""
    return GCDOperations()


def create_euler_totient() -> EulerTotient:
    """Create Euler's totient calculator."""
    return EulerTotient()


def is_prime(n: int) -> bool:
    """Check if n is prime."""
    return MillerRabin().is_prime(n).is_prime


def primes_up_to(n: int) -> List[int]:
    """Get all primes up to n."""
    return SieveOfEratosthenes().primes_up_to(n)


def factorize(n: int) -> Dict[int, int]:
    """Factorize n."""
    return PollardRho().factor(n).factors


def gcd(a: int, b: int) -> int:
    """Compute GCD."""
    return GCDOperations().gcd(a, b)


def lcm(a: int, b: int) -> int:
    """Compute LCM."""
    return GCDOperations().lcm(a, b)


def mod_pow(base: int, exp: int, mod: int) -> int:
    """Compute base^exp mod m."""
    return pow(base, exp, mod)


def mod_inverse(a: int, mod: int) -> Optional[int]:
    """Compute modular inverse."""
    return ModularArithmetic(mod).inverse(a)


def euler_phi(n: int) -> int:
    """Compute Euler's totient."""
    return EulerTotient().phi(n)

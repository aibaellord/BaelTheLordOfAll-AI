"""
BAEL Fast Fourier Transform Engine
==================================

FFT and related transforms.

"Ba'el transforms between domains." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import math
import cmath
from enum import Enum, auto

logger = logging.getLogger("BAEL.FFT")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class FFTResult:
    """Result of FFT computation."""
    coefficients: List[complex]
    size: int
    is_inverse: bool = False


@dataclass
class FFTStats:
    """FFT statistics."""
    input_size: int = 0
    padded_size: int = 0
    operations: int = 0
    time_ms: float = 0.0


# ============================================================================
# COOLEY-TUKEY FFT
# ============================================================================

class CooleyTukeyFFT:
    """
    Cooley-Tukey FFT algorithm.

    Features:
    - O(n log n) complexity
    - Radix-2 implementation
    - In-place butterfly operations

    "Ba'el computes the FFT efficiently." — Ba'el
    """

    def __init__(self):
        """Initialize FFT."""
        self._lock = threading.RLock()

        logger.debug("Cooley-Tukey FFT initialized")

    def fft(self, signal: List[complex]) -> List[complex]:
        """
        Compute FFT of signal.

        Args:
            signal: Input signal (complex or real values)

        Returns:
            FFT coefficients
        """
        with self._lock:
            n = len(signal)

            if n == 0:
                return []

            # Pad to power of 2
            n_padded = 1
            while n_padded < n:
                n_padded *= 2

            # Pad with zeros
            x = list(signal) + [0] * (n_padded - n)

            return self._fft_recursive(x)

    def _fft_recursive(self, x: List[complex]) -> List[complex]:
        """Recursive FFT implementation."""
        n = len(x)

        if n <= 1:
            return x

        # Divide
        even = self._fft_recursive(x[0::2])
        odd = self._fft_recursive(x[1::2])

        # Combine
        result = [0] * n

        for k in range(n // 2):
            t = cmath.exp(-2j * cmath.pi * k / n) * odd[k]
            result[k] = even[k] + t
            result[k + n // 2] = even[k] - t

        return result

    def ifft(self, coefficients: List[complex]) -> List[complex]:
        """
        Compute inverse FFT.

        Args:
            coefficients: FFT coefficients

        Returns:
            Original signal
        """
        with self._lock:
            n = len(coefficients)

            if n == 0:
                return []

            # Conjugate, apply FFT, conjugate again, and scale
            conjugated = [c.conjugate() for c in coefficients]
            transformed = self._fft_recursive(conjugated)

            return [c.conjugate() / n for c in transformed]


# ============================================================================
# ITERATIVE FFT
# ============================================================================

class IterativeFFT:
    """
    Iterative (in-place) FFT using bit reversal.

    Features:
    - O(n log n) complexity
    - O(1) extra space
    - Cache-friendly

    "Ba'el iterates through butterflies." — Ba'el
    """

    def __init__(self):
        """Initialize iterative FFT."""
        self._lock = threading.RLock()

    def fft(self, signal: List[complex]) -> List[complex]:
        """Compute FFT."""
        with self._lock:
            n = len(signal)

            if n == 0:
                return []

            # Pad to power of 2
            n_padded = 1
            while n_padded < n:
                n_padded *= 2

            x = list(signal) + [0] * (n_padded - n)
            n = n_padded

            # Bit reversal permutation
            j = 0
            for i in range(1, n):
                bit = n >> 1
                while j & bit:
                    j ^= bit
                    bit >>= 1
                j ^= bit

                if i < j:
                    x[i], x[j] = x[j], x[i]

            # Butterfly operations
            length = 2
            while length <= n:
                angle = -2 * cmath.pi / length
                wn = cmath.exp(1j * angle)

                for start in range(0, n, length):
                    w = 1
                    for k in range(length // 2):
                        t = w * x[start + k + length // 2]
                        u = x[start + k]
                        x[start + k] = u + t
                        x[start + k + length // 2] = u - t
                        w *= wn

                length *= 2

            return x

    def ifft(self, coefficients: List[complex]) -> List[complex]:
        """Compute inverse FFT."""
        with self._lock:
            n = len(coefficients)

            conjugated = [c.conjugate() for c in coefficients]
            transformed = self.fft(conjugated)

            return [c.conjugate() / n for c in transformed]


# ============================================================================
# NUMBER THEORETIC TRANSFORM (NTT)
# ============================================================================

class NTT:
    """
    Number Theoretic Transform.

    Features:
    - Exact integer arithmetic
    - No floating point errors
    - Useful for polynomial multiplication

    "Ba'el transforms in finite fields." — Ba'el
    """

    def __init__(self, mod: int = 998244353, root: int = 3):
        """
        Initialize NTT.

        Args:
            mod: Prime modulus (default: 998244353 = 119 * 2^23 + 1)
            root: Primitive root of mod
        """
        self._mod = mod
        self._root = root
        self._root_inv = pow(root, mod - 2, mod)
        self._lock = threading.RLock()

    def ntt(self, a: List[int], invert: bool = False) -> List[int]:
        """
        Compute NTT.

        Args:
            a: Input array
            invert: If True, compute inverse NTT

        Returns:
            Transformed array
        """
        with self._lock:
            n = len(a)

            if n == 0:
                return []

            # Ensure power of 2
            n_padded = 1
            while n_padded < n:
                n_padded *= 2

            a = list(a) + [0] * (n_padded - n)
            n = n_padded

            # Bit reversal
            j = 0
            for i in range(1, n):
                bit = n >> 1
                while j & bit:
                    j ^= bit
                    bit >>= 1
                j ^= bit

                if i < j:
                    a[i], a[j] = a[j], a[i]

            # Butterfly
            length = 2
            while length <= n:
                w = self._root_inv if invert else self._root

                # Compute w^(2^23 / length)
                for i in range(23):
                    if (1 << i) >= length:
                        break
                    w = (w * w) % self._mod

                for start in range(0, n, length):
                    wn = 1
                    for k in range(length // 2):
                        t = (wn * a[start + k + length // 2]) % self._mod
                        u = a[start + k]
                        a[start + k] = (u + t) % self._mod
                        a[start + k + length // 2] = (u - t + self._mod) % self._mod
                        wn = (wn * w) % self._mod

                length *= 2

            if invert:
                n_inv = pow(n, self._mod - 2, self._mod)
                a = [(x * n_inv) % self._mod for x in a]

            return a

    def multiply_polynomials(
        self,
        poly1: List[int],
        poly2: List[int]
    ) -> List[int]:
        """
        Multiply two polynomials using NTT.

        Args:
            poly1, poly2: Polynomial coefficients

        Returns:
            Product polynomial coefficients
        """
        with self._lock:
            n = len(poly1) + len(poly2)

            n_padded = 1
            while n_padded < n:
                n_padded *= 2

            a = list(poly1) + [0] * (n_padded - len(poly1))
            b = list(poly2) + [0] * (n_padded - len(poly2))

            fa = self.ntt(a)
            fb = self.ntt(b)

            fc = [(fa[i] * fb[i]) % self._mod for i in range(n_padded)]

            c = self.ntt(fc, invert=True)

            return c[:len(poly1) + len(poly2) - 1]


# ============================================================================
# DISCRETE COSINE TRANSFORM (DCT)
# ============================================================================

class DCT:
    """
    Discrete Cosine Transform.

    Features:
    - Type-II DCT (most common)
    - Used in JPEG, MP3
    - Real-valued transform

    "Ba'el transforms with cosines." — Ba'el
    """

    def __init__(self):
        """Initialize DCT."""
        self._lock = threading.RLock()

    def dct(self, signal: List[float]) -> List[float]:
        """
        Compute DCT-II.

        Args:
            signal: Input signal

        Returns:
            DCT coefficients
        """
        with self._lock:
            n = len(signal)

            if n == 0:
                return []

            result = []

            for k in range(n):
                total = 0.0
                for i in range(n):
                    total += signal[i] * math.cos(math.pi * k * (2 * i + 1) / (2 * n))

                if k == 0:
                    total *= math.sqrt(1 / n)
                else:
                    total *= math.sqrt(2 / n)

                result.append(total)

            return result

    def idct(self, coefficients: List[float]) -> List[float]:
        """
        Compute inverse DCT (DCT-III).

        Args:
            coefficients: DCT coefficients

        Returns:
            Original signal
        """
        with self._lock:
            n = len(coefficients)

            if n == 0:
                return []

            result = []

            for i in range(n):
                total = coefficients[0] / math.sqrt(n)

                for k in range(1, n):
                    total += math.sqrt(2 / n) * coefficients[k] * \
                            math.cos(math.pi * k * (2 * i + 1) / (2 * n))

                result.append(total)

            return result


# ============================================================================
# CONVOLUTION
# ============================================================================

class FFTConvolution:
    """
    Fast convolution using FFT.

    Features:
    - O(n log n) convolution
    - Works for any signals

    "Ba'el convolves efficiently." — Ba'el
    """

    def __init__(self):
        """Initialize convolution."""
        self._fft = CooleyTukeyFFT()
        self._lock = threading.RLock()

    def convolve(
        self,
        signal1: List[float],
        signal2: List[float]
    ) -> List[float]:
        """
        Compute convolution of two signals.

        Args:
            signal1, signal2: Input signals

        Returns:
            Convolution result
        """
        with self._lock:
            n = len(signal1) + len(signal2) - 1

            # Pad to power of 2
            n_padded = 1
            while n_padded < n:
                n_padded *= 2

            # Pad signals
            s1 = [complex(x, 0) for x in signal1] + [0] * (n_padded - len(signal1))
            s2 = [complex(x, 0) for x in signal2] + [0] * (n_padded - len(signal2))

            # FFT
            f1 = self._fft.fft(s1)
            f2 = self._fft.fft(s2)

            # Multiply in frequency domain
            f_result = [f1[i] * f2[i] for i in range(n_padded)]

            # Inverse FFT
            result = self._fft.ifft(f_result)

            return [r.real for r in result[:n]]

    def cross_correlation(
        self,
        signal1: List[float],
        signal2: List[float]
    ) -> List[float]:
        """
        Compute cross-correlation.

        Args:
            signal1, signal2: Input signals

        Returns:
            Cross-correlation result
        """
        with self._lock:
            # Cross-correlation is convolution with reversed signal
            return self.convolve(signal1, list(reversed(signal2)))


# ============================================================================
# POWER SPECTRUM
# ============================================================================

class PowerSpectrum:
    """
    Power spectrum analysis.

    "Ba'el analyzes frequency content." — Ba'el
    """

    def __init__(self):
        """Initialize power spectrum analyzer."""
        self._fft = CooleyTukeyFFT()
        self._lock = threading.RLock()

    def compute(self, signal: List[float]) -> List[float]:
        """
        Compute power spectrum.

        Args:
            signal: Input signal

        Returns:
            Power spectrum (magnitude squared)
        """
        with self._lock:
            x = [complex(s, 0) for s in signal]
            fft_result = self._fft.fft(x)

            return [abs(c) ** 2 for c in fft_result]

    def magnitude_spectrum(self, signal: List[float]) -> List[float]:
        """
        Compute magnitude spectrum.

        Args:
            signal: Input signal

        Returns:
            Magnitude spectrum
        """
        with self._lock:
            x = [complex(s, 0) for s in signal]
            fft_result = self._fft.fft(x)

            return [abs(c) for c in fft_result]

    def phase_spectrum(self, signal: List[float]) -> List[float]:
        """
        Compute phase spectrum.

        Args:
            signal: Input signal

        Returns:
            Phase spectrum (radians)
        """
        with self._lock:
            x = [complex(s, 0) for s in signal]
            fft_result = self._fft.fft(x)

            return [cmath.phase(c) for c in fft_result]


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_cooley_tukey_fft() -> CooleyTukeyFFT:
    """Create Cooley-Tukey FFT."""
    return CooleyTukeyFFT()


def create_iterative_fft() -> IterativeFFT:
    """Create iterative FFT."""
    return IterativeFFT()


def create_ntt(mod: int = 998244353, root: int = 3) -> NTT:
    """Create NTT."""
    return NTT(mod, root)


def create_dct() -> DCT:
    """Create DCT."""
    return DCT()


def create_fft_convolution() -> FFTConvolution:
    """Create FFT convolution."""
    return FFTConvolution()


def create_power_spectrum() -> PowerSpectrum:
    """Create power spectrum analyzer."""
    return PowerSpectrum()


def fft(signal: List[complex]) -> List[complex]:
    """Compute FFT."""
    return CooleyTukeyFFT().fft(signal)


def ifft(coefficients: List[complex]) -> List[complex]:
    """Compute inverse FFT."""
    return CooleyTukeyFFT().ifft(coefficients)


def convolve(signal1: List[float], signal2: List[float]) -> List[float]:
    """Convolve two signals."""
    return FFTConvolution().convolve(signal1, signal2)


def polynomial_multiply(poly1: List[int], poly2: List[int]) -> List[int]:
    """Multiply polynomials using NTT."""
    return NTT().multiply_polynomials(poly1, poly2)


def power_spectrum(signal: List[float]) -> List[float]:
    """Compute power spectrum."""
    return PowerSpectrum().compute(signal)

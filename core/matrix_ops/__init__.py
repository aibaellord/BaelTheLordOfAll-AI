"""
BAEL Matrix Operations Engine
=============================

Advanced matrix algorithms.

"Ba'el manipulates matrices." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import math
from copy import deepcopy

logger = logging.getLogger("BAEL.Matrix")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class LUDecomposition:
    """LU decomposition result."""
    L: List[List[float]]
    U: List[List[float]]
    P: List[int]  # Permutation


@dataclass
class QRDecomposition:
    """QR decomposition result."""
    Q: List[List[float]]
    R: List[List[float]]


@dataclass
class EigenResult:
    """Eigenvalue decomposition result."""
    eigenvalues: List[float]
    eigenvectors: List[List[float]]


@dataclass
class SVDResult:
    """Singular Value Decomposition result."""
    U: List[List[float]]
    S: List[float]  # Singular values
    V: List[List[float]]


@dataclass
class MatrixStats:
    """Matrix statistics."""
    rows: int = 0
    cols: int = 0
    rank: int = 0
    determinant: float = 0.0
    condition_number: float = 0.0


# ============================================================================
# BASIC MATRIX OPERATIONS
# ============================================================================

class Matrix:
    """
    Matrix class with basic operations.

    "Ba'el operates on matrices." — Ba'el
    """

    def __init__(self, data: List[List[float]]):
        """Initialize matrix."""
        self._data = [row[:] for row in data]
        self._rows = len(data)
        self._cols = len(data[0]) if data else 0
        self._lock = threading.RLock()

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def cols(self) -> int:
        return self._cols

    @property
    def data(self) -> List[List[float]]:
        return [row[:] for row in self._data]

    def __getitem__(self, key: Tuple[int, int]) -> float:
        return self._data[key[0]][key[1]]

    def __setitem__(self, key: Tuple[int, int], value: float) -> None:
        self._data[key[0]][key[1]] = value

    def copy(self) -> 'Matrix':
        return Matrix(self._data)

    @staticmethod
    def zeros(rows: int, cols: int) -> 'Matrix':
        """Create zero matrix."""
        return Matrix([[0.0] * cols for _ in range(rows)])

    @staticmethod
    def identity(n: int) -> 'Matrix':
        """Create identity matrix."""
        data = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        return Matrix(data)

    def add(self, other: 'Matrix') -> 'Matrix':
        """Add matrices."""
        with self._lock:
            result = [[self._data[i][j] + other._data[i][j]
                      for j in range(self._cols)]
                     for i in range(self._rows)]
            return Matrix(result)

    def subtract(self, other: 'Matrix') -> 'Matrix':
        """Subtract matrices."""
        with self._lock:
            result = [[self._data[i][j] - other._data[i][j]
                      for j in range(self._cols)]
                     for i in range(self._rows)]
            return Matrix(result)

    def multiply(self, other: 'Matrix') -> 'Matrix':
        """Multiply matrices."""
        with self._lock:
            result = [[sum(self._data[i][k] * other._data[k][j]
                          for k in range(self._cols))
                      for j in range(other._cols)]
                     for i in range(self._rows)]
            return Matrix(result)

    def scale(self, scalar: float) -> 'Matrix':
        """Scale matrix."""
        with self._lock:
            result = [[self._data[i][j] * scalar
                      for j in range(self._cols)]
                     for i in range(self._rows)]
            return Matrix(result)

    def transpose(self) -> 'Matrix':
        """Transpose matrix."""
        with self._lock:
            result = [[self._data[j][i] for j in range(self._rows)]
                     for i in range(self._cols)]
            return Matrix(result)

    def trace(self) -> float:
        """Compute trace."""
        with self._lock:
            return sum(self._data[i][i] for i in range(min(self._rows, self._cols)))


# ============================================================================
# LU DECOMPOSITION
# ============================================================================

class LUDecomposer:
    """
    LU decomposition with partial pivoting.

    Features:
    - PA = LU decomposition
    - O(n³) complexity
    - Numerical stability via pivoting

    "Ba'el decomposes into L and U." — Ba'el
    """

    def __init__(self):
        """Initialize decomposer."""
        self._lock = threading.RLock()

    def decompose(self, matrix: List[List[float]]) -> LUDecomposition:
        """
        Compute LU decomposition.

        Returns:
            LUDecomposition with L, U, and P
        """
        with self._lock:
            n = len(matrix)

            # Copy matrix
            U = [row[:] for row in matrix]
            L = [[0.0] * n for _ in range(n)]
            P = list(range(n))

            for k in range(n):
                # Find pivot
                max_val = abs(U[k][k])
                max_row = k

                for i in range(k + 1, n):
                    if abs(U[i][k]) > max_val:
                        max_val = abs(U[i][k])
                        max_row = i

                # Swap rows
                if max_row != k:
                    U[k], U[max_row] = U[max_row], U[k]
                    P[k], P[max_row] = P[max_row], P[k]

                    # Swap L rows (only up to k)
                    for j in range(k):
                        L[k][j], L[max_row][j] = L[max_row][j], L[k][j]

                # Eliminate
                L[k][k] = 1.0

                if abs(U[k][k]) > 1e-10:
                    for i in range(k + 1, n):
                        L[i][k] = U[i][k] / U[k][k]

                        for j in range(k, n):
                            U[i][j] -= L[i][k] * U[k][j]

            return LUDecomposition(L=L, U=U, P=P)

    def solve(self, matrix: List[List[float]], b: List[float]) -> List[float]:
        """
        Solve Ax = b using LU decomposition.

        Returns:
            Solution vector x
        """
        with self._lock:
            decomp = self.decompose(matrix)
            n = len(b)

            # Apply permutation to b
            pb = [b[decomp.P[i]] for i in range(n)]

            # Forward substitution (Ly = Pb)
            y = [0.0] * n
            for i in range(n):
                y[i] = pb[i] - sum(decomp.L[i][j] * y[j] for j in range(i))

            # Back substitution (Ux = y)
            x = [0.0] * n
            for i in range(n - 1, -1, -1):
                if abs(decomp.U[i][i]) < 1e-10:
                    x[i] = 0.0
                else:
                    x[i] = (y[i] - sum(decomp.U[i][j] * x[j]
                           for j in range(i + 1, n))) / decomp.U[i][i]

            return x

    def determinant(self, matrix: List[List[float]]) -> float:
        """Compute determinant using LU decomposition."""
        with self._lock:
            decomp = self.decompose(matrix)

            det = 1.0
            for i in range(len(matrix)):
                det *= decomp.U[i][i]

            # Count permutation swaps
            swaps = 0
            P = decomp.P[:]
            for i in range(len(P)):
                while P[i] != i:
                    j = P[i]
                    P[i], P[j] = P[j], P[i]
                    swaps += 1

            return det * ((-1) ** swaps)


# ============================================================================
# QR DECOMPOSITION
# ============================================================================

class QRDecomposer:
    """
    QR decomposition using Gram-Schmidt.

    Features:
    - A = QR decomposition
    - Q is orthogonal
    - R is upper triangular

    "Ba'el orthogonalizes columns." — Ba'el
    """

    def __init__(self):
        """Initialize decomposer."""
        self._lock = threading.RLock()

    def decompose(self, matrix: List[List[float]]) -> QRDecomposition:
        """
        Compute QR decomposition using modified Gram-Schmidt.

        Returns:
            QRDecomposition with Q and R
        """
        with self._lock:
            m = len(matrix)
            n = len(matrix[0])

            Q = [[0.0] * n for _ in range(m)]
            R = [[0.0] * n for _ in range(n)]

            # Copy columns
            V = [[matrix[i][j] for i in range(m)] for j in range(n)]

            for j in range(n):
                # Compute R[j][j] and Q[:, j]
                r_jj = math.sqrt(sum(V[j][i] ** 2 for i in range(m)))
                R[j][j] = r_jj

                if r_jj > 1e-10:
                    for i in range(m):
                        Q[i][j] = V[j][i] / r_jj

                # Orthogonalize remaining columns
                for k in range(j + 1, n):
                    R[j][k] = sum(Q[i][j] * V[k][i] for i in range(m))

                    for i in range(m):
                        V[k][i] -= R[j][k] * Q[i][j]

            return QRDecomposition(Q=Q, R=R)

    def solve_least_squares(
        self,
        matrix: List[List[float]],
        b: List[float]
    ) -> List[float]:
        """
        Solve least squares problem min ||Ax - b||.

        Returns:
            Solution vector x
        """
        with self._lock:
            decomp = self.decompose(matrix)
            m = len(decomp.Q)
            n = len(decomp.R)

            # Compute Q^T * b
            qtb = [sum(decomp.Q[i][j] * b[i] for i in range(m)) for j in range(n)]

            # Back substitution
            x = [0.0] * n
            for i in range(n - 1, -1, -1):
                if abs(decomp.R[i][i]) < 1e-10:
                    x[i] = 0.0
                else:
                    x[i] = (qtb[i] - sum(decomp.R[i][j] * x[j]
                           for j in range(i + 1, n))) / decomp.R[i][i]

            return x


# ============================================================================
# EIGENVALUE DECOMPOSITION (POWER ITERATION)
# ============================================================================

class EigenDecomposer:
    """
    Eigenvalue decomposition.

    Features:
    - Power iteration for dominant eigenvalue
    - QR algorithm for all eigenvalues

    "Ba'el finds eigenvalues." — Ba'el
    """

    def __init__(self, max_iterations: int = 1000, tolerance: float = 1e-10):
        """Initialize decomposer."""
        self._max_iter = max_iterations
        self._tol = tolerance
        self._lock = threading.RLock()

    def power_iteration(
        self,
        matrix: List[List[float]]
    ) -> Tuple[float, List[float]]:
        """
        Find dominant eigenvalue and eigenvector.

        Returns:
            (eigenvalue, eigenvector)
        """
        with self._lock:
            n = len(matrix)

            # Initial vector
            v = [1.0 / math.sqrt(n)] * n
            eigenvalue = 0.0

            for _ in range(self._max_iter):
                # Matrix-vector multiply
                new_v = [sum(matrix[i][j] * v[j] for j in range(n))
                        for i in range(n)]

                # Compute norm
                norm = math.sqrt(sum(x ** 2 for x in new_v))

                if norm < 1e-10:
                    break

                # Normalize
                new_v = [x / norm for x in new_v]

                # Compute eigenvalue (Rayleigh quotient)
                new_eigenvalue = sum(
                    new_v[i] * sum(matrix[i][j] * new_v[j] for j in range(n))
                    for i in range(n)
                )

                if abs(new_eigenvalue - eigenvalue) < self._tol:
                    return new_eigenvalue, new_v

                eigenvalue = new_eigenvalue
                v = new_v

            return eigenvalue, v

    def qr_algorithm(
        self,
        matrix: List[List[float]]
    ) -> List[float]:
        """
        Find all eigenvalues using QR algorithm.

        Returns:
            List of eigenvalues
        """
        with self._lock:
            n = len(matrix)
            A = [row[:] for row in matrix]
            qr = QRDecomposer()

            for _ in range(self._max_iter):
                decomp = qr.decompose(A)

                # A = RQ
                A = [[sum(decomp.R[i][k] * decomp.Q[k][j] for k in range(n))
                     for j in range(n)] for i in range(n)]

                # Check convergence (off-diagonal elements)
                off_diag = sum(abs(A[i][j]) for i in range(n)
                              for j in range(n) if i != j)

                if off_diag < self._tol:
                    break

            return [A[i][i] for i in range(n)]


# ============================================================================
# MATRIX INVERSION
# ============================================================================

class MatrixInverter:
    """
    Matrix inversion.

    "Ba'el inverts matrices." — Ba'el
    """

    def __init__(self):
        """Initialize inverter."""
        self._lu = LUDecomposer()
        self._lock = threading.RLock()

    def invert(self, matrix: List[List[float]]) -> Optional[List[List[float]]]:
        """
        Compute matrix inverse.

        Returns:
            Inverse matrix or None if singular
        """
        with self._lock:
            n = len(matrix)

            # Solve for each column of identity
            inverse = [[0.0] * n for _ in range(n)]

            for j in range(n):
                # Create unit vector
                e = [1.0 if i == j else 0.0 for i in range(n)]

                try:
                    col = self._lu.solve(matrix, e)
                    for i in range(n):
                        inverse[i][j] = col[i]
                except:
                    return None

            return inverse

    def pseudo_inverse(
        self,
        matrix: List[List[float]]
    ) -> List[List[float]]:
        """
        Compute Moore-Penrose pseudo-inverse.

        Returns:
            Pseudo-inverse matrix
        """
        with self._lock:
            m = len(matrix)
            n = len(matrix[0])

            # A+ = (A^T A)^-1 A^T for full column rank
            # A+ = A^T (A A^T)^-1 for full row rank

            # Compute A^T
            at = [[matrix[j][i] for j in range(m)] for i in range(n)]

            if m >= n:
                # A^T A
                ata = [[sum(at[i][k] * matrix[k][j] for k in range(m))
                       for j in range(n)] for i in range(n)]

                ata_inv = self.invert(ata)
                if ata_inv is None:
                    return [[0.0] * m for _ in range(n)]

                # (A^T A)^-1 A^T
                result = [[sum(ata_inv[i][k] * at[k][j] for k in range(n))
                          for j in range(m)] for i in range(n)]
            else:
                # A A^T
                aat = [[sum(matrix[i][k] * at[k][j] for k in range(n))
                       for j in range(m)] for i in range(m)]

                aat_inv = self.invert(aat)
                if aat_inv is None:
                    return [[0.0] * m for _ in range(n)]

                # A^T (A A^T)^-1
                result = [[sum(at[i][k] * aat_inv[k][j] for k in range(m))
                          for j in range(m)] for i in range(n)]

            return result


# ============================================================================
# STRASSEN MULTIPLICATION
# ============================================================================

class StrassenMultiplier:
    """
    Strassen's matrix multiplication.

    Features:
    - O(n^2.807) complexity
    - Better than naive O(n³) for large matrices

    "Ba'el multiplies sub-cubically." — Ba'el
    """

    def __init__(self, threshold: int = 64):
        """Initialize with threshold for fallback to naive."""
        self._threshold = threshold
        self._lock = threading.RLock()

    def multiply(
        self,
        A: List[List[float]],
        B: List[List[float]]
    ) -> List[List[float]]:
        """
        Multiply matrices using Strassen's algorithm.

        Returns:
            Product matrix
        """
        with self._lock:
            n = len(A)

            if n <= self._threshold:
                return self._naive_multiply(A, B)

            # Pad to power of 2
            m = 1
            while m < n:
                m *= 2

            A_pad = self._pad(A, m)
            B_pad = self._pad(B, m)

            result = self._strassen(A_pad, B_pad)

            # Remove padding
            return [row[:n] for row in result[:n]]

    def _strassen(
        self,
        A: List[List[float]],
        B: List[List[float]]
    ) -> List[List[float]]:
        """Recursive Strassen's algorithm."""
        n = len(A)

        if n <= self._threshold:
            return self._naive_multiply(A, B)

        mid = n // 2

        # Split matrices
        A11, A12, A21, A22 = self._split(A)
        B11, B12, B21, B22 = self._split(B)

        # Compute 7 products
        M1 = self._strassen(self._add(A11, A22), self._add(B11, B22))
        M2 = self._strassen(self._add(A21, A22), B11)
        M3 = self._strassen(A11, self._sub(B12, B22))
        M4 = self._strassen(A22, self._sub(B21, B11))
        M5 = self._strassen(self._add(A11, A12), B22)
        M6 = self._strassen(self._sub(A21, A11), self._add(B11, B12))
        M7 = self._strassen(self._sub(A12, A22), self._add(B21, B22))

        # Combine
        C11 = self._add(self._sub(self._add(M1, M4), M5), M7)
        C12 = self._add(M3, M5)
        C21 = self._add(M2, M4)
        C22 = self._add(self._sub(self._add(M1, M3), M2), M6)

        return self._combine(C11, C12, C21, C22)

    def _pad(self, M: List[List[float]], n: int) -> List[List[float]]:
        """Pad matrix to size n x n."""
        m = len(M)
        result = [[0.0] * n for _ in range(n)]
        for i in range(m):
            for j in range(len(M[i])):
                result[i][j] = M[i][j]
        return result

    def _split(
        self,
        M: List[List[float]]
    ) -> Tuple[List[List[float]], ...]:
        """Split matrix into 4 quadrants."""
        n = len(M)
        mid = n // 2

        M11 = [row[:mid] for row in M[:mid]]
        M12 = [row[mid:] for row in M[:mid]]
        M21 = [row[:mid] for row in M[mid:]]
        M22 = [row[mid:] for row in M[mid:]]

        return M11, M12, M21, M22

    def _combine(
        self,
        C11: List[List[float]],
        C12: List[List[float]],
        C21: List[List[float]],
        C22: List[List[float]]
    ) -> List[List[float]]:
        """Combine 4 quadrants into one matrix."""
        n = len(C11) * 2
        result = [[0.0] * n for _ in range(n)]
        mid = n // 2

        for i in range(mid):
            for j in range(mid):
                result[i][j] = C11[i][j]
                result[i][j + mid] = C12[i][j]
                result[i + mid][j] = C21[i][j]
                result[i + mid][j + mid] = C22[i][j]

        return result

    def _add(
        self,
        A: List[List[float]],
        B: List[List[float]]
    ) -> List[List[float]]:
        """Add matrices."""
        n = len(A)
        return [[A[i][j] + B[i][j] for j in range(n)] for i in range(n)]

    def _sub(
        self,
        A: List[List[float]],
        B: List[List[float]]
    ) -> List[List[float]]:
        """Subtract matrices."""
        n = len(A)
        return [[A[i][j] - B[i][j] for j in range(n)] for i in range(n)]

    def _naive_multiply(
        self,
        A: List[List[float]],
        B: List[List[float]]
    ) -> List[List[float]]:
        """Naive O(n³) multiplication."""
        n = len(A)
        m = len(B[0]) if B else 0
        k = len(B)

        return [[sum(A[i][l] * B[l][j] for l in range(k))
                for j in range(m)] for i in range(n)]


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_matrix(data: List[List[float]]) -> Matrix:
    """Create matrix."""
    return Matrix(data)


def create_lu_decomposer() -> LUDecomposer:
    """Create LU decomposer."""
    return LUDecomposer()


def create_qr_decomposer() -> QRDecomposer:
    """Create QR decomposer."""
    return QRDecomposer()


def create_eigen_decomposer() -> EigenDecomposer:
    """Create eigenvalue decomposer."""
    return EigenDecomposer()


def create_matrix_inverter() -> MatrixInverter:
    """Create matrix inverter."""
    return MatrixInverter()


def create_strassen_multiplier() -> StrassenMultiplier:
    """Create Strassen multiplier."""
    return StrassenMultiplier()


def lu_decomposition(matrix: List[List[float]]) -> LUDecomposition:
    """Compute LU decomposition."""
    return LUDecomposer().decompose(matrix)


def qr_decomposition(matrix: List[List[float]]) -> QRDecomposition:
    """Compute QR decomposition."""
    return QRDecomposer().decompose(matrix)


def solve_linear_system(A: List[List[float]], b: List[float]) -> List[float]:
    """Solve Ax = b."""
    return LUDecomposer().solve(A, b)


def matrix_determinant(matrix: List[List[float]]) -> float:
    """Compute determinant."""
    return LUDecomposer().determinant(matrix)


def matrix_inverse(matrix: List[List[float]]) -> Optional[List[List[float]]]:
    """Compute matrix inverse."""
    return MatrixInverter().invert(matrix)


def eigenvalues(matrix: List[List[float]]) -> List[float]:
    """Compute eigenvalues."""
    return EigenDecomposer().qr_algorithm(matrix)


def dominant_eigenvalue(matrix: List[List[float]]) -> Tuple[float, List[float]]:
    """Find dominant eigenvalue and eigenvector."""
    return EigenDecomposer().power_iteration(matrix)


def matrix_multiply_strassen(
    A: List[List[float]],
    B: List[List[float]]
) -> List[List[float]]:
    """Multiply matrices using Strassen's algorithm."""
    return StrassenMultiplier().multiply(A, B)

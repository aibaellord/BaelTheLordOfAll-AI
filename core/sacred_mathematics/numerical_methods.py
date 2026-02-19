"""
⚡ NUMERICAL METHODS ⚡
======================
Advanced numerical computation.

Features:
- Root finding
- Integration
- Differentiation
- Linear algebra
- Optimization
- ODE solving
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class NumericalResult:
    """Result of numerical computation"""
    value: Any
    error: float = 0.0
    iterations: int = 0
    converged: bool = True
    message: str = ""


class NumericalSolver:
    """Base class for numerical solvers"""

    def __init__(self, tolerance: float = 1e-10, max_iterations: int = 1000):
        self.tolerance = tolerance
        self.max_iterations = max_iterations


class RootFinder(NumericalSolver):
    """
    Root finding algorithms.
    """

    def bisection(
        self,
        f: Callable[[float], float],
        a: float,
        b: float
    ) -> NumericalResult:
        """Bisection method"""
        if f(a) * f(b) >= 0:
            return NumericalResult(
                value=None,
                converged=False,
                message="Function must have different signs at endpoints"
            )

        for i in range(self.max_iterations):
            c = (a + b) / 2
            fc = f(c)

            if abs(fc) < self.tolerance or (b - a) / 2 < self.tolerance:
                return NumericalResult(
                    value=c,
                    error=(b - a) / 2,
                    iterations=i + 1
                )

            if f(a) * fc < 0:
                b = c
            else:
                a = c

        return NumericalResult(
            value=(a + b) / 2,
            error=(b - a) / 2,
            iterations=self.max_iterations,
            converged=False,
            message="Did not converge"
        )

    def newton(
        self,
        f: Callable[[float], float],
        df: Callable[[float], float],
        x0: float
    ) -> NumericalResult:
        """Newton-Raphson method"""
        x = x0

        for i in range(self.max_iterations):
            fx = f(x)
            dfx = df(x)

            if abs(dfx) < 1e-15:
                return NumericalResult(
                    value=x,
                    converged=False,
                    message="Derivative near zero"
                )

            x_new = x - fx / dfx

            if abs(x_new - x) < self.tolerance:
                return NumericalResult(
                    value=x_new,
                    error=abs(x_new - x),
                    iterations=i + 1
                )

            x = x_new

        return NumericalResult(
            value=x,
            iterations=self.max_iterations,
            converged=False
        )

    def secant(
        self,
        f: Callable[[float], float],
        x0: float,
        x1: float
    ) -> NumericalResult:
        """Secant method"""
        for i in range(self.max_iterations):
            f0, f1 = f(x0), f(x1)

            if abs(f1 - f0) < 1e-15:
                return NumericalResult(
                    value=x1,
                    converged=False,
                    message="Division by zero"
                )

            x2 = x1 - f1 * (x1 - x0) / (f1 - f0)

            if abs(x2 - x1) < self.tolerance:
                return NumericalResult(
                    value=x2,
                    error=abs(x2 - x1),
                    iterations=i + 1
                )

            x0, x1 = x1, x2

        return NumericalResult(
            value=x1,
            iterations=self.max_iterations,
            converged=False
        )

    def brent(
        self,
        f: Callable[[float], float],
        a: float,
        b: float
    ) -> NumericalResult:
        """Brent's method - combination of bisection, secant, and inverse quadratic"""
        fa, fb = f(a), f(b)

        if fa * fb >= 0:
            return NumericalResult(
                value=None,
                converged=False,
                message="Root not bracketed"
            )

        if abs(fa) < abs(fb):
            a, b = b, a
            fa, fb = fb, fa

        c, fc = a, fa
        mflag = True

        for i in range(self.max_iterations):
            if abs(fb) < self.tolerance:
                return NumericalResult(value=b, iterations=i + 1)

            if fa != fc and fb != fc:
                # Inverse quadratic interpolation
                s = (a * fb * fc / ((fa - fb) * (fa - fc)) +
                     b * fa * fc / ((fb - fa) * (fb - fc)) +
                     c * fa * fb / ((fc - fa) * (fc - fb)))
            else:
                # Secant
                s = b - fb * (b - a) / (fb - fa)

            # Conditions for bisection
            use_bisection = (
                not ((3 * a + b) / 4 < s < b or b < s < (3 * a + b) / 4) or
                (mflag and abs(s - b) >= abs(b - c) / 2) or
                (not mflag and abs(s - b) >= abs(c - d) / 2) or
                (mflag and abs(b - c) < self.tolerance) or
                (not mflag and abs(c - d) < self.tolerance)
            )

            if use_bisection:
                s = (a + b) / 2
                mflag = True
            else:
                mflag = False

            fs = f(s)
            d, c = c, b
            fc = fb

            if fa * fs < 0:
                b, fb = s, fs
            else:
                a, fa = s, fs

            if abs(fa) < abs(fb):
                a, b = b, a
                fa, fb = fb, fa

        return NumericalResult(value=b, iterations=self.max_iterations, converged=False)


class Integrator(NumericalSolver):
    """
    Numerical integration.
    """

    def trapezoidal(
        self,
        f: Callable[[float], float],
        a: float,
        b: float,
        n: int = 100
    ) -> NumericalResult:
        """Trapezoidal rule"""
        h = (b - a) / n
        s = 0.5 * (f(a) + f(b))

        for i in range(1, n):
            s += f(a + i * h)

        result = h * s

        # Error estimate
        error = abs(b - a) ** 3 / (12 * n ** 2)

        return NumericalResult(value=result, error=error)

    def simpson(
        self,
        f: Callable[[float], float],
        a: float,
        b: float,
        n: int = 100
    ) -> NumericalResult:
        """Simpson's rule"""
        if n % 2 == 1:
            n += 1

        h = (b - a) / n
        s = f(a) + f(b)

        for i in range(1, n, 2):
            s += 4 * f(a + i * h)
        for i in range(2, n - 1, 2):
            s += 2 * f(a + i * h)

        result = h * s / 3
        error = abs(b - a) ** 5 / (180 * n ** 4)

        return NumericalResult(value=result, error=error)

    def romberg(
        self,
        f: Callable[[float], float],
        a: float,
        b: float,
        max_order: int = 10
    ) -> NumericalResult:
        """Romberg integration"""
        R = np.zeros((max_order, max_order))

        h = b - a
        R[0, 0] = 0.5 * h * (f(a) + f(b))

        for i in range(1, max_order):
            h /= 2

            # Trapezoidal
            s = 0
            for k in range(1, 2 ** i, 2):
                s += f(a + k * h)
            R[i, 0] = 0.5 * R[i - 1, 0] + h * s

            # Richardson extrapolation
            for j in range(1, i + 1):
                R[i, j] = R[i, j - 1] + (R[i, j - 1] - R[i - 1, j - 1]) / (4 ** j - 1)

            # Check convergence
            if i > 0 and abs(R[i, i] - R[i - 1, i - 1]) < self.tolerance:
                return NumericalResult(
                    value=R[i, i],
                    error=abs(R[i, i] - R[i - 1, i - 1]),
                    iterations=i
                )

        return NumericalResult(
            value=R[-1, -1],
            iterations=max_order
        )

    def gauss_legendre(
        self,
        f: Callable[[float], float],
        a: float,
        b: float,
        n: int = 5
    ) -> NumericalResult:
        """Gauss-Legendre quadrature"""
        # Nodes and weights for n-point rule
        nodes, weights = np.polynomial.legendre.leggauss(n)

        # Transform to [a, b]
        c1 = (b - a) / 2
        c2 = (a + b) / 2

        result = c1 * sum(w * f(c1 * x + c2) for x, w in zip(nodes, weights))

        return NumericalResult(value=result)


class Differentiator(NumericalSolver):
    """
    Numerical differentiation.
    """

    def forward_difference(
        self,
        f: Callable[[float], float],
        x: float,
        h: float = 1e-8
    ) -> float:
        """Forward difference approximation"""
        return (f(x + h) - f(x)) / h

    def central_difference(
        self,
        f: Callable[[float], float],
        x: float,
        h: float = 1e-8
    ) -> float:
        """Central difference approximation"""
        return (f(x + h) - f(x - h)) / (2 * h)

    def richardson_extrapolation(
        self,
        f: Callable[[float], float],
        x: float,
        h: float = 0.1,
        order: int = 4
    ) -> NumericalResult:
        """Richardson extrapolation for derivatives"""
        D = np.zeros((order, order))

        for i in range(order):
            hi = h / (2 ** i)
            D[i, 0] = (f(x + hi) - f(x - hi)) / (2 * hi)

        for j in range(1, order):
            for i in range(j, order):
                D[i, j] = D[i, j - 1] + (D[i, j - 1] - D[i - 1, j - 1]) / (4 ** j - 1)

        return NumericalResult(
            value=D[-1, -1],
            error=abs(D[-1, -1] - D[-2, -2]) if order > 1 else 0
        )

    def second_derivative(
        self,
        f: Callable[[float], float],
        x: float,
        h: float = 1e-5
    ) -> float:
        """Second derivative approximation"""
        return (f(x + h) - 2 * f(x) + f(x - h)) / (h ** 2)


class LinearAlgebraSolver:
    """
    Linear algebra operations.
    """

    def solve(
        self,
        A: np.ndarray,
        b: np.ndarray
    ) -> NumericalResult:
        """Solve linear system Ax = b"""
        try:
            x = np.linalg.solve(A, b)
            residual = np.linalg.norm(A @ x - b)
            return NumericalResult(value=x, error=residual)
        except np.linalg.LinAlgError as e:
            return NumericalResult(value=None, converged=False, message=str(e))

    def lu_decomposition(
        self,
        A: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """LU decomposition with partial pivoting"""
        n = A.shape[0]
        L = np.eye(n)
        U = A.copy().astype(float)
        P = np.eye(n)

        for k in range(n - 1):
            # Pivot
            max_idx = k + np.argmax(np.abs(U[k:, k]))
            U[[k, max_idx]] = U[[max_idx, k]]
            P[[k, max_idx]] = P[[max_idx, k]]
            L[[k, max_idx], :k] = L[[max_idx, k], :k]

            for i in range(k + 1, n):
                L[i, k] = U[i, k] / U[k, k]
                U[i, k:] -= L[i, k] * U[k, k:]

        return P, L, U

    def qr_decomposition(
        self,
        A: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """QR decomposition using Gram-Schmidt"""
        m, n = A.shape
        Q = np.zeros((m, n))
        R = np.zeros((n, n))

        for j in range(n):
            v = A[:, j].copy()

            for i in range(j):
                R[i, j] = np.dot(Q[:, i], A[:, j])
                v -= R[i, j] * Q[:, i]

            R[j, j] = np.linalg.norm(v)
            Q[:, j] = v / R[j, j] if R[j, j] > 1e-10 else v

        return Q, R

    def eigenvalues(
        self,
        A: np.ndarray,
        max_iter: int = 100
    ) -> NumericalResult:
        """Compute eigenvalues using QR iteration"""
        n = A.shape[0]
        Ak = A.copy().astype(float)

        for i in range(max_iter):
            Q, R = self.qr_decomposition(Ak)
            Ak = R @ Q

            # Check convergence (off-diagonal elements)
            off_diag = sum(abs(Ak[i, j]) for i in range(n) for j in range(i))
            if off_diag < 1e-10:
                break

        eigenvalues = np.diag(Ak)
        return NumericalResult(value=eigenvalues, iterations=i + 1)


class OptimizationSolver(NumericalSolver):
    """
    Optimization algorithms.
    """

    def golden_section(
        self,
        f: Callable[[float], float],
        a: float,
        b: float
    ) -> NumericalResult:
        """Golden section search for minimum"""
        phi = (1 + math.sqrt(5)) / 2
        resphi = 2 - phi

        x1 = a + resphi * (b - a)
        x2 = b - resphi * (b - a)
        f1, f2 = f(x1), f(x2)

        for i in range(self.max_iterations):
            if abs(b - a) < self.tolerance:
                x_min = (a + b) / 2
                return NumericalResult(value=x_min, iterations=i + 1)

            if f1 < f2:
                b, x2, f2 = x2, x1, f1
                x1 = a + resphi * (b - a)
                f1 = f(x1)
            else:
                a, x1, f1 = x1, x2, f2
                x2 = b - resphi * (b - a)
                f2 = f(x2)

        return NumericalResult(value=(a + b) / 2, iterations=self.max_iterations)

    def gradient_descent(
        self,
        f: Callable[[np.ndarray], float],
        grad_f: Callable[[np.ndarray], np.ndarray],
        x0: np.ndarray,
        learning_rate: float = 0.01
    ) -> NumericalResult:
        """Gradient descent optimization"""
        x = x0.copy()

        for i in range(self.max_iterations):
            grad = grad_f(x)
            x_new = x - learning_rate * grad

            if np.linalg.norm(x_new - x) < self.tolerance:
                return NumericalResult(value=x_new, iterations=i + 1)

            x = x_new

        return NumericalResult(value=x, iterations=self.max_iterations, converged=False)


class ODESolver(NumericalSolver):
    """
    Ordinary differential equation solvers.
    """

    def euler(
        self,
        f: Callable[[float, float], float],
        y0: float,
        t_span: Tuple[float, float],
        n: int = 100
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Euler's method"""
        t0, tf = t_span
        h = (tf - t0) / n

        t = np.linspace(t0, tf, n + 1)
        y = np.zeros(n + 1)
        y[0] = y0

        for i in range(n):
            y[i + 1] = y[i] + h * f(t[i], y[i])

        return t, y

    def rk4(
        self,
        f: Callable[[float, float], float],
        y0: float,
        t_span: Tuple[float, float],
        n: int = 100
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Fourth-order Runge-Kutta"""
        t0, tf = t_span
        h = (tf - t0) / n

        t = np.linspace(t0, tf, n + 1)
        y = np.zeros(n + 1)
        y[0] = y0

        for i in range(n):
            k1 = h * f(t[i], y[i])
            k2 = h * f(t[i] + h / 2, y[i] + k1 / 2)
            k3 = h * f(t[i] + h / 2, y[i] + k2 / 2)
            k4 = h * f(t[i] + h, y[i] + k3)

            y[i + 1] = y[i] + (k1 + 2 * k2 + 2 * k3 + k4) / 6

        return t, y

    def rkf45(
        self,
        f: Callable[[float, float], float],
        y0: float,
        t_span: Tuple[float, float],
        h_init: float = 0.1
    ) -> Tuple[List[float], List[float]]:
        """Runge-Kutta-Fehlberg adaptive step"""
        t0, tf = t_span
        t = [t0]
        y = [y0]
        h = h_init

        # RKF45 coefficients
        while t[-1] < tf:
            ti, yi = t[-1], y[-1]

            k1 = h * f(ti, yi)
            k2 = h * f(ti + h / 4, yi + k1 / 4)
            k3 = h * f(ti + 3 * h / 8, yi + 3 * k1 / 32 + 9 * k2 / 32)
            k4 = h * f(ti + 12 * h / 13, yi + 1932 * k1 / 2197 - 7200 * k2 / 2197 + 7296 * k3 / 2197)
            k5 = h * f(ti + h, yi + 439 * k1 / 216 - 8 * k2 + 3680 * k3 / 513 - 845 * k4 / 4104)
            k6 = h * f(ti + h / 2, yi - 8 * k1 / 27 + 2 * k2 - 3544 * k3 / 2565 + 1859 * k4 / 4104 - 11 * k5 / 40)

            # 4th and 5th order solutions
            y4 = yi + 25 * k1 / 216 + 1408 * k3 / 2565 + 2197 * k4 / 4104 - k5 / 5
            y5 = yi + 16 * k1 / 135 + 6656 * k3 / 12825 + 28561 * k4 / 56430 - 9 * k5 / 50 + 2 * k6 / 55

            # Error estimate
            error = abs(y5 - y4)

            if error < self.tolerance:
                t.append(ti + h)
                y.append(y5)

            # Adjust step size
            if error > 0:
                h = 0.9 * h * (self.tolerance / error) ** 0.2

            h = min(h, tf - t[-1])

        return t, y


# Export all
__all__ = [
    'NumericalResult',
    'NumericalSolver',
    'RootFinder',
    'Integrator',
    'Differentiator',
    'LinearAlgebraSolver',
    'OptimizationSolver',
    'ODESolver',
]

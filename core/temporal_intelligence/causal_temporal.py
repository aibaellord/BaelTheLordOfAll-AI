"""
⚡ CAUSAL TEMPORAL ⚡
====================
Temporal causal analysis.

Features:
- Granger causality
- Temporal causal graphs
- Intervention analysis
- Counterfactual reasoning
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


@dataclass
class TemporalCause:
    """A temporal causal relationship"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    cause_variable: str = ""
    effect_variable: str = ""

    # Temporal properties
    lag: int = 1  # Time steps between cause and effect
    lag_distribution: List[float] = None  # Probability over different lags

    # Strength
    strength: float = 1.0
    confidence: float = 1.0

    # Type
    is_direct: bool = True
    is_contemporaneous: bool = False  # Same time step

    # Statistical evidence
    p_value: float = 0.0
    test_statistic: float = 0.0


@dataclass
class CausalChain:
    """A chain of temporal causes"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Chain of causes
    causes: List[TemporalCause] = field(default_factory=list)

    # Properties
    total_lag: int = 0
    total_strength: float = 1.0

    def add_cause(self, cause: TemporalCause):
        """Add cause to chain"""
        self.causes.append(cause)
        self.total_lag += cause.lag
        self.total_strength *= cause.strength

    def get_path(self) -> List[str]:
        """Get path of variables"""
        if not self.causes:
            return []

        path = [self.causes[0].cause_variable]
        for cause in self.causes:
            path.append(cause.effect_variable)

        return path


class TemporalCausalGraph:
    """
    Graph of temporal causal relationships.
    """

    def __init__(self):
        self.variables: Set[str] = set()
        self.causes: Dict[str, TemporalCause] = {}

        # Adjacency (with lags)
        self.adjacency: Dict[str, Dict[str, List[TemporalCause]]] = defaultdict(lambda: defaultdict(list))

    def add_variable(self, name: str):
        """Add variable to graph"""
        self.variables.add(name)

    def add_cause(self, cause: TemporalCause):
        """Add causal relationship"""
        self.variables.add(cause.cause_variable)
        self.variables.add(cause.effect_variable)

        self.causes[cause.id] = cause
        self.adjacency[cause.cause_variable][cause.effect_variable].append(cause)

    def get_causes_of(self, variable: str) -> List[TemporalCause]:
        """Get all causes of a variable"""
        causes = []
        for var in self.variables:
            causes.extend(self.adjacency[var][variable])
        return causes

    def get_effects_of(self, variable: str) -> List[TemporalCause]:
        """Get all effects of a variable"""
        effects = []
        for target in self.adjacency[variable]:
            effects.extend(self.adjacency[variable][target])
        return effects

    def find_causal_paths(
        self,
        source: str,
        target: str,
        max_length: int = 5
    ) -> List[CausalChain]:
        """Find all causal paths from source to target"""
        paths = []

        def dfs(current: str, chain: CausalChain, visited: Set[str]):
            if current == target and chain.causes:
                paths.append(chain)
                return

            if len(chain.causes) >= max_length:
                return

            for effect_var in self.adjacency[current]:
                if effect_var in visited:
                    continue

                for cause in self.adjacency[current][effect_var]:
                    new_chain = CausalChain(causes=chain.causes.copy())
                    new_chain.add_cause(cause)

                    new_visited = visited.copy()
                    new_visited.add(effect_var)

                    dfs(effect_var, new_chain, new_visited)

        dfs(source, CausalChain(), {source})
        return paths

    def get_total_effect(
        self,
        source: str,
        target: str
    ) -> float:
        """Get total causal effect (sum over all paths)"""
        paths = self.find_causal_paths(source, target)

        if not paths:
            return 0.0

        return sum(chain.total_strength for chain in paths)

    def check_confounding(
        self,
        cause: str,
        effect: str
    ) -> List[str]:
        """Check for confounding variables"""
        confounders = []

        for var in self.variables:
            if var == cause or var == effect:
                continue

            # Check if var causes both cause and effect
            causes_cause = bool(self.adjacency[var][cause])
            causes_effect = bool(self.adjacency[var][effect])

            if causes_cause and causes_effect:
                confounders.append(var)

        return confounders


class GrangerCausality:
    """
    Granger causality testing.
    """

    def __init__(self, max_lag: int = 5, significance: float = 0.05):
        self.max_lag = max_lag
        self.significance = significance

    def test(
        self,
        x: np.ndarray,
        y: np.ndarray,
        lag: int = None
    ) -> Dict[str, Any]:
        """
        Test if X Granger-causes Y.

        X Granger-causes Y if past values of X help predict Y
        beyond what past values of Y alone can predict.
        """
        lag = lag or self.max_lag

        n = len(y)
        if n <= lag * 2:
            return {'granger_causes': False, 'p_value': 1.0}

        # Restricted model: Y predicted by its own lags
        y_lags = np.column_stack([y[lag-i-1:n-i-1] for i in range(lag)])
        y_target = y[lag:]

        # Fit restricted model
        try:
            beta_r = np.linalg.lstsq(y_lags, y_target, rcond=None)[0]
            y_pred_r = y_lags @ beta_r
            rss_r = np.sum((y_target - y_pred_r) ** 2)
        except np.linalg.LinAlgError:
            return {'granger_causes': False, 'p_value': 1.0}

        # Unrestricted model: Y predicted by lags of Y and X
        x_lags = np.column_stack([x[lag-i-1:n-i-1] for i in range(lag)])
        xy_lags = np.column_stack([y_lags, x_lags])

        try:
            beta_u = np.linalg.lstsq(xy_lags, y_target, rcond=None)[0]
            y_pred_u = xy_lags @ beta_u
            rss_u = np.sum((y_target - y_pred_u) ** 2)
        except np.linalg.LinAlgError:
            return {'granger_causes': False, 'p_value': 1.0}

        # F-test
        n_obs = len(y_target)
        df1 = lag
        df2 = n_obs - 2 * lag

        if df2 <= 0 or rss_u <= 0:
            return {'granger_causes': False, 'p_value': 1.0}

        f_stat = ((rss_r - rss_u) / df1) / (rss_u / df2)

        # Approximate p-value using F distribution approximation
        # Using the fact that F(df1, df2) ≈ χ²(df1)/df1 for large df2
        from scipy import stats if False else None  # Would use scipy if available

        # Simple approximation
        p_value = math.exp(-f_stat * 0.5) if f_stat > 0 else 1.0

        granger_causes = p_value < self.significance

        return {
            'granger_causes': granger_causes,
            'f_statistic': f_stat,
            'p_value': p_value,
            'lag': lag,
            'rss_restricted': rss_r,
            'rss_unrestricted': rss_u
        }

    def find_optimal_lag(
        self,
        x: np.ndarray,
        y: np.ndarray
    ) -> int:
        """Find optimal lag using BIC"""
        best_lag = 1
        best_bic = float('inf')

        for lag in range(1, self.max_lag + 1):
            result = self.test(x, y, lag)

            n = len(y) - lag
            k = 2 * lag
            rss = result.get('rss_unrestricted', float('inf'))

            if n > k:
                bic = n * np.log(rss / n + 1e-10) + k * np.log(n)

                if bic < best_bic:
                    best_bic = bic
                    best_lag = lag

        return best_lag

    def test_all_pairs(
        self,
        data: Dict[str, np.ndarray]
    ) -> TemporalCausalGraph:
        """Test Granger causality between all variable pairs"""
        graph = TemporalCausalGraph()

        variables = list(data.keys())

        for x_name in variables:
            graph.add_variable(x_name)

        for x_name in variables:
            for y_name in variables:
                if x_name == y_name:
                    continue

                x = data[x_name]
                y = data[y_name]

                optimal_lag = self.find_optimal_lag(x, y)
                result = self.test(x, y, optimal_lag)

                if result['granger_causes']:
                    cause = TemporalCause(
                        cause_variable=x_name,
                        effect_variable=y_name,
                        lag=optimal_lag,
                        strength=result['f_statistic'] / (result['f_statistic'] + 1),
                        confidence=1 - result['p_value'],
                        p_value=result['p_value'],
                        test_statistic=result['f_statistic']
                    )
                    graph.add_cause(cause)

        return graph


class TemporalIntervention:
    """
    Temporal intervention analysis.
    """

    def __init__(self, causal_graph: TemporalCausalGraph = None):
        self.graph = causal_graph or TemporalCausalGraph()

    def do(
        self,
        variable: str,
        value: float,
        time_step: int,
        data: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """
        Perform do-intervention: do(X = value) at time step.

        Returns modified time series for all variables.
        """
        result = {var: series.copy() for var, series in data.items()}

        # Set intervention
        if variable in result and time_step < len(result[variable]):
            result[variable][time_step] = value

        # Propagate effects forward in time
        for t in range(time_step + 1, max(len(s) for s in result.values())):
            for effect_var in self.graph.variables:
                if effect_var == variable:
                    continue

                causes = self.graph.get_causes_of(effect_var)

                for cause in causes:
                    if cause.lag <= 0 or t - cause.lag < 0:
                        continue

                    cause_var = cause.cause_variable
                    if cause_var not in result:
                        continue

                    # Apply causal effect
                    if t < len(result[effect_var]) and t - cause.lag < len(result[cause_var]):
                        effect = cause.strength * (
                            result[cause_var][t - cause.lag] -
                            data[cause_var][t - cause.lag]
                        )
                        result[effect_var][t] += effect

        return result

    def counterfactual(
        self,
        variable: str,
        actual_value: float,
        counterfactual_value: float,
        time_step: int,
        data: Dict[str, np.ndarray]
    ) -> Dict[str, Any]:
        """
        Compute counterfactual: What if X had been different?
        """
        # Get actual outcome
        actual_outcome = {var: series.copy() for var, series in data.items()}

        # Get counterfactual outcome
        cf_outcome = self.do(variable, counterfactual_value, time_step, data)

        # Compute differences
        differences = {}
        for var in data:
            diff = cf_outcome[var] - actual_outcome[var]
            differences[var] = {
                'max_diff': float(np.max(np.abs(diff))),
                'mean_diff': float(np.mean(diff)),
                'affected_steps': int(np.sum(np.abs(diff) > 1e-10))
            }

        return {
            'counterfactual_variable': variable,
            'actual_value': actual_value,
            'counterfactual_value': counterfactual_value,
            'time_step': time_step,
            'effects': differences,
            'counterfactual_data': cf_outcome
        }

    def estimate_causal_effect(
        self,
        cause_var: str,
        effect_var: str,
        data: Dict[str, np.ndarray],
        intervention_size: float = 1.0
    ) -> Dict[str, float]:
        """
        Estimate causal effect of cause on effect.
        """
        if cause_var not in data or effect_var not in data:
            return {'effect': 0.0, 'method': 'missing_data'}

        n = len(data[cause_var])
        effects = []

        # Estimate effect at multiple time points
        for t in range(min(10, n // 2)):
            baseline = data[effect_var][t+1:].mean() if t+1 < n else 0

            # Intervene
            modified = self.do(cause_var,
                             data[cause_var][t] + intervention_size,
                             t, data)

            intervened = modified[effect_var][t+1:].mean() if t+1 < n else 0

            effects.append(intervened - baseline)

        return {
            'average_causal_effect': np.mean(effects) if effects else 0.0,
            'std_causal_effect': np.std(effects) if effects else 0.0,
            'n_estimates': len(effects),
            'intervention_size': intervention_size
        }


# Export all
__all__ = [
    'TemporalCause',
    'CausalChain',
    'TemporalCausalGraph',
    'GrangerCausality',
    'TemporalIntervention',
]

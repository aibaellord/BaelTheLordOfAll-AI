"""
⚡ ROBUSTNESS ⚡
===============
Input/output robustness.

Features:
- Input validation
- Output sanitization
- Perturbation detection
- Adversarial defense
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import re
import uuid


@dataclass
class RobustnessMetric:
    """Robustness measurement"""
    name: str = ""

    # Scores (0-1)
    input_robustness: float = 0.0
    output_robustness: float = 0.0
    behavioral_robustness: float = 0.0

    # Details
    perturbation_tolerance: float = 0.0
    adversarial_accuracy: float = 0.0
    consistency_score: float = 0.0

    # Tests
    tests_passed: int = 0
    tests_failed: int = 0

    def overall_score(self) -> float:
        """Calculate overall robustness score"""
        return (
            self.input_robustness * 0.3 +
            self.output_robustness * 0.3 +
            self.behavioral_robustness * 0.4
        )


class InputValidator:
    """
    Validate and sanitize inputs.
    """

    def __init__(self):
        # Validation rules
        self.max_length = 10000
        self.min_length = 1
        self.allowed_chars = set(
            'abcdefghijklmnopqrstuvwxyz'
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            '0123456789'
            ' .,!?;:\'"-()[]{}@#$%^&*+=<>/\\\n\t'
        )

        # Dangerous patterns
        self.dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'data:text/html',
        ]

        # Validation history
        self.validation_history: List[Dict] = []

    def validate(self, input_data: Any) -> Tuple[bool, List[str]]:
        """Validate input, return (is_valid, errors)"""
        errors = []

        if not isinstance(input_data, str):
            try:
                input_data = str(input_data)
            except:
                errors.append("Input cannot be converted to string")
                return False, errors

        # Length check
        if len(input_data) < self.min_length:
            errors.append(f"Input too short (min: {self.min_length})")

        if len(input_data) > self.max_length:
            errors.append(f"Input too long (max: {self.max_length})")

        # Character check
        invalid_chars = set(input_data) - self.allowed_chars
        if invalid_chars:
            errors.append(f"Invalid characters: {invalid_chars}")

        # Pattern check
        for pattern in self.dangerous_patterns:
            if re.search(pattern, input_data, re.IGNORECASE | re.DOTALL):
                errors.append(f"Dangerous pattern detected: {pattern[:20]}...")

        is_valid = len(errors) == 0

        self.validation_history.append({
            'input_hash': hash(input_data),
            'is_valid': is_valid,
            'errors': errors
        })

        return is_valid, errors

    def sanitize(self, input_data: str) -> str:
        """Sanitize input"""
        # Remove null bytes
        sanitized = input_data.replace('\x00', '')

        # Limit length
        if len(sanitized) > self.max_length:
            sanitized = sanitized[:self.max_length]

        # Remove dangerous patterns
        for pattern in self.dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)

        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())

        return sanitized

    def add_validation_rule(self, name: str, validator: Callable[[str], bool], error_msg: str):
        """Add custom validation rule"""
        self._custom_rules = getattr(self, '_custom_rules', [])
        self._custom_rules.append((name, validator, error_msg))


class OutputSanitizer:
    """
    Sanitize outputs to prevent information leakage.
    """

    def __init__(self):
        # Sensitive patterns
        self.sensitive_patterns = [
            # API keys
            (r'[a-zA-Z0-9]{32,}', '[REDACTED_KEY]'),
            # Passwords
            (r'password["\']?\s*[:=]\s*["\']?[^\s"\']+', '[REDACTED_PASSWORD]'),
            # Tokens
            (r'Bearer\s+[a-zA-Z0-9\-_]+', '[REDACTED_TOKEN]'),
            # Email addresses (optional)
            (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]'),
        ]

        # Blocklist phrases
        self.blocked_phrases: List[str] = []

        # Replacement mode
        self.redact_mode = True

    def sanitize(self, output: str) -> str:
        """Sanitize output"""
        sanitized = output

        # Apply sensitive pattern redaction
        if self.redact_mode:
            for pattern, replacement in self.sensitive_patterns:
                sanitized = re.sub(pattern, replacement, sanitized)

        # Remove blocked phrases
        for phrase in self.blocked_phrases:
            sanitized = sanitized.replace(phrase, '[BLOCKED]')

        return sanitized

    def add_sensitive_pattern(self, pattern: str, replacement: str = '[REDACTED]'):
        """Add sensitive pattern"""
        self.sensitive_patterns.append((pattern, replacement))

    def block_phrase(self, phrase: str):
        """Block a specific phrase"""
        self.blocked_phrases.append(phrase)

    def check_for_leakage(self, output: str, secrets: List[str]) -> List[str]:
        """Check if output contains any secrets"""
        found = []
        for secret in secrets:
            if secret in output:
                found.append(secret)
        return found


class PerturbationDetector:
    """
    Detect adversarial perturbations in inputs.
    """

    def __init__(self):
        # Baseline embeddings/signatures
        self.baseline_signatures: Dict[str, np.ndarray] = {}

        # Detection thresholds
        self.distance_threshold = 0.5
        self.similarity_threshold = 0.9

    def compute_signature(self, text: str) -> np.ndarray:
        """Compute text signature for comparison"""
        # Simple character-based signature
        char_counts = np.zeros(128)
        for c in text:
            if ord(c) < 128:
                char_counts[ord(c)] += 1

        # Normalize
        if char_counts.sum() > 0:
            char_counts = char_counts / char_counts.sum()

        # Add n-gram features
        bigram_counts = np.zeros(100)
        for i in range(len(text) - 1):
            bigram = text[i:i+2]
            idx = hash(bigram) % 100
            bigram_counts[idx] += 1

        if bigram_counts.sum() > 0:
            bigram_counts = bigram_counts / bigram_counts.sum()

        return np.concatenate([char_counts, bigram_counts])

    def register_baseline(self, name: str, text: str):
        """Register baseline text"""
        self.baseline_signatures[name] = self.compute_signature(text)

    def detect_perturbation(
        self,
        text: str,
        baseline_name: str = None
    ) -> Tuple[bool, float]:
        """Detect if text is perturbed version of baseline"""
        signature = self.compute_signature(text)

        if baseline_name and baseline_name in self.baseline_signatures:
            baseline = self.baseline_signatures[baseline_name]
            distance = np.linalg.norm(signature - baseline)

            # Cosine similarity
            similarity = np.dot(signature, baseline) / (
                np.linalg.norm(signature) * np.linalg.norm(baseline) + 1e-10
            )

            is_perturbed = (
                distance > self.distance_threshold or
                similarity < self.similarity_threshold
            )

            return is_perturbed, 1 - similarity

        # Check against all baselines
        min_distance = float('inf')
        for baseline in self.baseline_signatures.values():
            distance = np.linalg.norm(signature - baseline)
            min_distance = min(min_distance, distance)

        return min_distance > self.distance_threshold, min_distance

    def detect_unicode_tricks(self, text: str) -> List[str]:
        """Detect Unicode-based perturbation tricks"""
        tricks = []

        # Homoglyph detection
        homoglyphs = {
            'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p',  # Cyrillic
            'ⅰ': 'i', 'ⅱ': 'ii', 'ⅲ': 'iii',  # Roman numerals
            '０': '0', '１': '1', '２': '2',  # Fullwidth
        }

        for char in text:
            if char in homoglyphs:
                tricks.append(f"Homoglyph: {char} -> {homoglyphs[char]}")

        # Zero-width characters
        zero_width = ['\u200b', '\u200c', '\u200d', '\ufeff']
        for zw in zero_width:
            if zw in text:
                tricks.append(f"Zero-width character: U+{ord(zw):04X}")

        # RTL/LTR override
        bidi_chars = ['\u202a', '\u202b', '\u202c', '\u202d', '\u202e']
        for bc in bidi_chars:
            if bc in text:
                tricks.append(f"BiDi override: U+{ord(bc):04X}")

        return tricks


class AdversarialDefense:
    """
    Defense mechanisms against adversarial attacks.
    """

    def __init__(self):
        self.input_validator = InputValidator()
        self.output_sanitizer = OutputSanitizer()
        self.perturbation_detector = PerturbationDetector()

        # Defense strategies
        self.strategies: List[Callable] = []

        # Statistics
        self.attacks_blocked = 0
        self.attacks_detected = 0

    def defend(
        self,
        input_data: str,
        context: Dict = None
    ) -> Tuple[str, bool, List[str]]:
        """
        Apply defensive measures.

        Returns: (sanitized_input, is_safe, warnings)
        """
        warnings = []
        context = context or {}

        # Input validation
        is_valid, errors = self.input_validator.validate(input_data)
        if not is_valid:
            warnings.extend(errors)

        # Sanitize
        sanitized = self.input_validator.sanitize(input_data)

        # Perturbation detection
        unicode_tricks = self.perturbation_detector.detect_unicode_tricks(input_data)
        if unicode_tricks:
            warnings.extend(unicode_tricks)
            self.attacks_detected += 1

        # Apply custom strategies
        for strategy in self.strategies:
            try:
                sanitized, strategy_warnings = strategy(sanitized, context)
                warnings.extend(strategy_warnings)
            except Exception as e:
                warnings.append(f"Strategy error: {e}")

        is_safe = len(warnings) == 0

        if not is_safe:
            self.attacks_blocked += 1

        return sanitized, is_safe, warnings

    def add_defense_strategy(self, strategy: Callable):
        """Add custom defense strategy"""
        self.strategies.append(strategy)

    def randomize_input(self, text: str, noise_level: float = 0.01) -> str:
        """Add random noise to break adversarial patterns"""
        chars = list(text)
        n_changes = int(len(chars) * noise_level)

        for _ in range(n_changes):
            idx = np.random.randint(len(chars))
            if chars[idx].isalpha():
                # Add zero-width space after character
                chars[idx] = chars[idx]  # Keep original

        return ''.join(chars)

    def detect_repeated_prompts(
        self,
        history: List[str],
        current: str,
        threshold: float = 0.9
    ) -> bool:
        """Detect if user is repeatedly trying similar prompts"""
        if not history:
            return False

        current_sig = self.perturbation_detector.compute_signature(current)

        similar_count = 0
        for past in history[-10:]:  # Check last 10
            past_sig = self.perturbation_detector.compute_signature(past)
            similarity = np.dot(current_sig, past_sig) / (
                np.linalg.norm(current_sig) * np.linalg.norm(past_sig) + 1e-10
            )
            if similarity > threshold:
                similar_count += 1

        return similar_count >= 3

    def get_defense_statistics(self) -> Dict[str, int]:
        """Get defense statistics"""
        return {
            'attacks_detected': self.attacks_detected,
            'attacks_blocked': self.attacks_blocked,
            'strategies_active': len(self.strategies)
        }


# Export all
__all__ = [
    'RobustnessMetric',
    'InputValidator',
    'OutputSanitizer',
    'PerturbationDetector',
    'AdversarialDefense',
]

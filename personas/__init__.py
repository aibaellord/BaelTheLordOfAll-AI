"""
BAEL - Personas Package
Persona management and loading for the BAEL AI system.
"""

from .definitions import PERSONAS
from .loader import Persona, PersonaLoader

__all__ = ["PersonaLoader", "Persona", "PERSONAS"]

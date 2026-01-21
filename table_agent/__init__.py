"""Table Agent - клиент для подключения к покер-румам"""

from .agent import TableAgent
from .connection import BackendConnection

__all__ = ['TableAgent', 'BackendConnection']

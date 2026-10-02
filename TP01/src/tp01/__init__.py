"""Pacote TP01 - Sistema Agente com OpenAI Agents SDK."""

import asyncio
from .main import main as run_agente_principal


def main() -> None:
    """Ponto de entrada padrão do pacote executando todos os agentes do TP01."""
    asyncio.run(run_agente_principal())

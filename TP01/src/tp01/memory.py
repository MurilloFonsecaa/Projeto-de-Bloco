"""
memory.py
---------
Camada de memória persistente do agente em duas partes:

  1. SQLiteSession  – implementação do protocolo Session do SDK que persiste
                      o histórico de conversação em um arquivo SQLite local,
                      mantendo contexto entre runs distintos.

  2. RAGMemory      – pipeline de busca semântica via embeddings (OpenAI API)
                      com armazenamento no mesmo banco SQLite. Permite recuperar
                      interações anteriores relevantes para o contexto atual.
"""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from agents import SessionABC
from agents.items import TResponseInputItem


# ---------------------------------------------------------------------------
# Configuração do banco de dados
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent / "memoria.db"


def _get_connection() -> sqlite3.Connection:
    """Retorna uma conexão SQLite com as tabelas criadas se não existirem."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_items (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            item_json  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rag_entries (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            texto      TEXT NOT NULL,
            embedding  TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


# ===========================================================================
# PARTE 1 – SQLiteSession
# Implementa o protocolo Session do SDK usando SQLite local para persistência.
# ===========================================================================

class SQLiteSession(SessionABC):
    """
    Implementação do protocolo Session que persiste o histórico de conversação
    em um banco SQLite local. Permite retomar contextos entre execuções distintas
    sem depender de APIs externas.
    """

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self.session_settings = None

    @property
    def session_id(self) -> str:
        return self._session_id

    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        """Recupera o histórico de mensagens da sessão persistida no SQLite."""
        conn = _get_connection()
        try:
            if limit is None:
                rows = conn.execute(
                    "SELECT item_json FROM session_items WHERE session_id = ? ORDER BY id ASC",
                    (self._session_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT item_json FROM session_items WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                    (self._session_id, limit),
                ).fetchall()
                rows = list(reversed(rows))
            return [json.loads(row[0]) for row in rows]
        finally:
            conn.close()

    async def add_items(self, items: list[TResponseInputItem]) -> None:
        """Persiste novos itens de conversação no SQLite."""
        conn = _get_connection()
        try:
            conn.executemany(
                "INSERT INTO session_items (session_id, item_json) VALUES (?, ?)",
                [(self._session_id, json.dumps(item)) for item in items],
            )
            conn.commit()
        finally:
            conn.close()

    async def pop_item(self) -> TResponseInputItem | None:
        """Remove e retorna o item mais recente da sessão."""
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT id, item_json FROM session_items WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                (self._session_id,),
            ).fetchone()
            if row is None:
                return None
            conn.execute("DELETE FROM session_items WHERE id = ?", (row[0],))
            conn.commit()
            return json.loads(row[1])
        finally:
            conn.close()

    async def clear_session(self) -> None:
        """Remove todo o histórico da sessão do banco de dados."""
        conn = _get_connection()
        try:
            conn.execute(
                "DELETE FROM session_items WHERE session_id = ?",
                (self._session_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def contar_mensagens(self) -> int:
        """Retorna quantas mensagens estão salvas para esta sessão."""
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM session_items WHERE session_id = ?",
                (self._session_id,),
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()


# ===========================================================================
# PARTE 2 – RAGMemory (pipeline de busca semântica com embeddings)
# Armazena interações com seus embeddings e permite recuperação por similaridade.
# ===========================================================================

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calcula similaridade por cosseno entre dois vetores."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x ** 2 for x in a))
    norm_b = math.sqrt(sum(x ** 2 for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class RAGMemory:
    """
    Pipeline de memória semântica com embeddings e busca por similaridade.
    Cada interação é convertida em embedding via OpenAI API e armazenada
    no SQLite. Na busca, o query também é embedado e comparado com todos
    os registros usando similaridade por cosseno.
    """

    def __init__(self, session_id: str, client: AsyncOpenAI, modelo_embedding: str = "text-embedding-3-small") -> None:
        self._session_id = session_id
        self._client = client
        self._modelo = modelo_embedding

    async def _embed(self, texto: str) -> list[float]:
        """Gera embedding de um texto via OpenAI Embeddings API."""
        response = await self._client.embeddings.create(
            input=texto,
            model=self._modelo,
        )
        return response.data[0].embedding

    async def adicionar(self, texto: str) -> None:
        """Salva um texto com seu embedding no banco de dados."""
        embedding = await self._embed(texto)
        conn = _get_connection()
        try:
            conn.execute(
                "INSERT INTO rag_entries (session_id, texto, embedding) VALUES (?, ?, ?)",
                (self._session_id, texto, json.dumps(embedding)),
            )
            conn.commit()
        finally:
            conn.close()

    async def buscar(self, query: str, top_k: int = 3) -> list[str]:
        """
        Recupera os textos mais semanticamente próximos ao query.

        Args:
            query: Texto de consulta para busca semântica.
            top_k: Número máximo de resultados a retornar.

        Returns:
            Lista dos textos mais relevantes em ordem decrescente de similaridade.
        """
        query_embedding = await self._embed(query)

        conn = _get_connection()
        try:
            rows = conn.execute(
                "SELECT texto, embedding FROM rag_entries WHERE session_id = ?",
                (self._session_id,),
            ).fetchall()
        finally:
            conn.close()

        if not rows:
            return []

        # Calcula similaridade e ordena
        scored: list[tuple[float, str]] = []
        for texto, emb_json in rows:
            emb = json.loads(emb_json)
            sim = _cosine_similarity(query_embedding, emb)
            scored.append((sim, texto))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [texto for _, texto in scored[:top_k]]

    def listar_entradas(self) -> list[str]:
        """Retorna todos os textos armazenados na memória RAG desta sessão."""
        conn = _get_connection()
        try:
            rows = conn.execute(
                "SELECT texto FROM rag_entries WHERE session_id = ? ORDER BY id ASC",
                (self._session_id,),
            ).fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

    def limpar(self) -> None:
        """Remove todos os registros RAG desta sessão."""
        conn = _get_connection()
        try:
            conn.execute(
                "DELETE FROM rag_entries WHERE session_id = ?",
                (self._session_id,),
            )
            conn.commit()
        finally:
            conn.close()

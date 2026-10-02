"""
schemas.py
----------
Modelos Pydantic que definem a estrutura de saída tipada do agente de atendimento.
"""

from typing import List
from pydantic import BaseModel, Field


class ItemSolicitado(BaseModel):
    """Item extraído diretamente do texto do cliente, sem preço ainda."""

    produto: str = Field(
        ...,
        description="Nome do produto como mencionado pelo cliente",
        examples=["coxinha", "kibe"],
    )
    quantidade: int = Field(
        ...,
        description="Quantidade solicitada (inteiro >= 1)",
        examples=[10, 5],
        ge=1,
    )


class ExtracaoPedido(BaseModel):
    """Saída estruturada da extração de dados brutos."""

    nome_cliente: str = Field(..., description="Nome completo do cliente", examples=["João Silva"])
    endereco: str = Field(..., description="Endereço de entrega informado", examples=["Rua das Flores, 123"])
    forma_pagamento: str = Field(..., description="Forma de pagamento informada", examples=["Pix"])
    itens_solicitados: List[ItemSolicitado] = Field(
        ...,
        description="Lista de itens e quantidades extraídos da mensagem do cliente",
    )


class ItemPedido(BaseModel):
    """Representa um item individual solicitado pelo cliente no pedido e validado via tool."""

    produto: str = Field(
        ...,
        description="Nome do produto solicitado (ex: Coxinha, Kibe, Bolinha de Queijo)",
        examples=["Coxinha", "Kibe"],
    )
    quantidade: int = Field(
        ...,
        description="Quantidade de unidades do produto (deve ser um inteiro >= 1)",
        examples=[10, 5],
        ge=1,
    )
    preco_unitario: float = Field(
        ...,
        description="Preço unitário tabelado do produto em Reais (R$)",
        examples=[3.50, 4.00],
        ge=0.0,
    )
    disponivel: bool = Field(
        True,
        description="Indica se o item possui estoque suficiente confirmado via ferramenta",
        examples=[True, False],
    )


class PedidoSchema(BaseModel):
    """
    Schema principal de resposta estruturada em JSON para o agente de atendimento.
    Todos os campos são obrigatórios e validados tipadamente via Pydantic.
    """

    nome_cliente: str = Field(
        ...,
        description="Nome completo do cliente informado no atendimento",
        examples=["João Silva"],
    )
    endereco: str = Field(
        ...,
        description="Endereço de entrega completo informado pelo cliente",
        examples=["Rua das Flores, nº 123, Bairro Centro"],
    )
    forma_pagamento: str = Field(
        ...,
        description="Forma de pagamento escolhida (ex: Cartão de Crédito, Pix, Dinheiro)",
        examples=["Pix", "Cartão de Crédito"],
    )
    itens: List[ItemPedido] = Field(
        ...,
        description="Lista de itens solicitados no pedido com quantidades e preços unitários",
    )
    subtotal: float = Field(
        ...,
        description="Soma do valor de todos os itens disponíveis do pedido em Reais (R$)",
        examples=[55.00],
        ge=0.0,
    )
    taxa_entrega: float = Field(
        ...,
        description="Valor fixo da taxa de entrega em Reais (R$)",
        examples=[5.00],
        ge=0.0,
    )
    total: float = Field(
        ...,
        description="Valor total do pedido (subtotal + taxa_entrega) em Reais (R$)",
        examples=[60.00],
        ge=0.0,
    )
    mensagem_confirmacao: str = Field(
        ...,
        description="Mensagem educada de confirmação informando status do estoque e estimativa de entrega",
        examples=["Olá João! Seu pedido foi registrado com sucesso e chegará em até 40 minutos."],
    )
"""
tools.py
--------
Ferramentas Python registradas com @function_tool para uso pelo agente.
Cada tool acessa dados externos ao modelo (simulando BD ou API) e retorna
uma string que o agente integra diretamente na resposta final.
"""

from agents import function_tool

# ---------------------------------------------------------------------------
# Dados simulados – representam uma fonte de dados externa (BD, API, etc.)
# ---------------------------------------------------------------------------

_ESTOQUE: dict[str, int] = {
    "coxinha": 30,
    "bolinha de queijo": 20,
    "enroladinho de salsicha": 15,
    "kibe": 10,
    "presunto e queijo": 12,
    "refrigerante": 25,
    "suco": 18,
}

_PEDIDOS: dict[str, str] = {
    "PED-001": "Em preparo",
    "PED-002": "Saiu para entrega",
    "PED-003": "Entregue",
    "PED-004": "Cancelado",
}

# ---------------------------------------------------------------------------
# Ferramentas registradas com @function_tool
# ---------------------------------------------------------------------------

@function_tool
def consultar_estoque(produto: str) -> str:
    """
    Consulta a disponibilidade em estoque de um produto da lanchonete.

    Args:
        produto: Nome do produto a consultar (ex: 'coxinha', 'kibe').

    Returns:
        Mensagem informando a quantidade disponível em estoque ou
        indicando que o produto não foi encontrado.
    """
    chave = produto.strip().lower()
    if chave in _ESTOQUE:
        quantidade = _ESTOQUE[chave]
        if quantidade == 0:
            return f"'{produto}' está ESGOTADO no momento."
        return f"'{produto}' está disponível. Estoque atual: {quantidade} unidades."
    return f"Produto '{produto}' não encontrado no cardápio."

@function_tool
def consultar_status_pedido(numero_pedido: str) -> str:
    """
    Consulta o status atual de um pedido pelo seu número de identificação.

    Args:
        numero_pedido: Código do pedido a rastrear (ex: 'PED-001').

    Returns:
        Status atual do pedido ou mensagem de pedido não encontrado.
    """
    chave = numero_pedido.strip().upper()
    if chave in _PEDIDOS:
        return f"Pedido {chave}: {_PEDIDOS[chave]}."
    return f"Pedido '{numero_pedido}' não encontrado. Verifique o número informado."

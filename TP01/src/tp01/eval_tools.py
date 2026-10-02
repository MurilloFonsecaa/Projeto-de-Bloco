"""
eval_tools.py
-------------
Ferramenta do agente para fornecer o dataset de testes e as variantes de prompt.
"""

from typing import Any, Dict, List
from agents import function_tool

# ---------------------------------------------------------------------------
# Dados de Avaliação
# ---------------------------------------------------------------------------

_VARIANTES: Dict[str, str] = {
    "Variante A (Prompt Sucinto)": """
Você é um assistente de atendimento da lanchonete Salgados & Cia.
Receba o pedido do cliente, verifique a disponibilidade no estoque via ferramenta 'consultar_estoque'
e retorne uma resposta estritamente estruturada em JSON no schema PedidoSchema.

Tabela de Preços:
- Coxinha: R$ 3,50 | Bolinha de Queijo: R$ 3,50 | Enroladinho de Salsicha: R$ 3,00
- Kibe: R$ 4,00 | Presunto e Queijo: R$ 4,00 | Refrigerante: R$ 8,00 | Suco: R$ 6,00
- Taxa fixa de entrega: R$ 5,00
""",
    "Variante B (Prompt Refinado PRRR)": """
### CONTEXTO E PAPEL
Você é o assistente virtual oficial da lanchonete Salgados & Cia.
Sua função é processar os pedidos dos clientes gerando uma saída estritamente estruturada conforme o schema JSON solicitado.

### PASSO A PASSO OBRIGATÓRIO DE EXECUÇÃO:
1. **Validação de Estoque:** Para CADA item solicitado na mensagem do cliente, chame obrigatoriamente a ferramenta `consultar_estoque(produto)`.
2. **Definição de Disponibilidade:**
   - Se a ferramenta informar estoque suficiente: defina `disponivel: true`.
   - Se o item estiver esgotado ou com quantidade insuficiente no estoque (ex: cliente pede 50 kibes, mas só há 10 no estoque): defina `disponivel: false`.
3. **Cálculo de Preços e Totais:**
   - Preço unitário: consulte a Tabela de Preços.
   - Subtotal: Calcule a soma APENAS dos itens com `disponivel: true` (quantidade * preco_unitario). NÃO inclua itens indisponíveis no subtotal.
   - Taxa de entrega: Aplique o valor fixo de R$ 5,00.
   - Total: Subtotal + Taxa de entrega.
4. **Mensagem de Confirmação:** Elabore uma mensagem educada informando se algum item do pedido foi recusado por falta de estoque e a estimativa de entrega (30 a 40 min).

### TABELA DE PREÇOS TABELADOS
- Coxinha: R$ 3,50
- Bolinha de Queijo: R$ 3,50
- Enroladinho de Salsicha: R$ 3,00
- Kibe: R$ 4,00
- Presunto e Queijo: R$ 4,00
- Refrigerante: R$ 8,00
- Suco: R$ 6,00
- Taxa de entrega fixa: R$ 5,00
"""
}

_DATASET_TESTES: List[Dict[str, Any]] = [
    {
        "id": "TC-01",
        "descricao": "Pedido simples dentro do estoque com Pix",
        "prompt": "Olá! Sou a Ana Clara. Quero 5 coxinhas e 2 sucos. Moro na Rua A, 100. Pagamento via Pix.",
        "itens_esperados": ["coxinha", "suco"],
        "expectativa_estoque_ok": True,
    },
    {
        "id": "TC-02",
        "descricao": "Pedido que excede o estoque disponível (50 Kibes vs 10 no estoque)",
        "prompt": "Oi, meu nome é Bruno Santos. Gostaria de pedir 50 kibes e 2 refrigerantes. Rua B, 200. Vou pagar no cartão.",
        "itens_esperados": ["kibe", "refrigerante"],
        "expectativa_estoque_ok": False,
    },
    {
        "id": "TC-03",
        "descricao": "Pedido com múltiplos itens e endereço completo",
        "prompt": "Sou o Lucas Lima. Manda 2 coxinhas, 2 bolinhas de queijo e 1 suco para a Av. Paulista, 1500. Pago em dinheiro.",
        "itens_esperados": ["coxinha", "bolinha de queijo", "suco"],
        "expectativa_estoque_ok": True,
    },
    {
        "id": "TC-04",
        "descricao": "Consulta de item que não existe no cardápio",
        "prompt": "Boa noite! Meu nome é Carla. Quero 3 empadas de frango e 1 refrigerante. Rua C, 50. Pix.",
        "itens_esperados": ["empada", "refrigerante"],
        "expectativa_estoque_ok": False,
    }
]

# ---------------------------------------------------------------------------
# Função Python Pura
# ---------------------------------------------------------------------------

def obter_dados_avaliacao_fn() -> Dict[str, Any]:
    """Retorna o dicionário com as variantes e o dataset de testes."""
    return {
        "variantes": _VARIANTES,
        "dataset": _DATASET_TESTES
    }

# ---------------------------------------------------------------------------
# Tool Registrada para os Agentes
# ---------------------------------------------------------------------------

@function_tool
def obter_dados_avaliacao() -> Dict[str, Any]:
    """
    Retorna o conjunto de dados completo para avaliação A/B de agentes,
    contendo as variantes de prompt configuradas e o dataset de casos de teste.
    """
    return obter_dados_avaliacao_fn()
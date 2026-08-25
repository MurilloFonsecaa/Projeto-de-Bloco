import asyncio
import os
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from agents import Agent, Runner, ModelSettings, set_default_openai_api

load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")
os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
set_default_openai_api("chat_completions")

class ItemPedido(BaseModel):
    """Representa um item individual solicitado pelo cliente no pedido."""
    produto: str = Field(
        ..., 
        description="Nome do produto solicitado (ex: Coxinha, Kibe, Bolinha de Queijo)",
        examples=["Coxinha", "Kibe"]
    )
    quantidade: int = Field(
        ..., 
        description="Quantidade de unidades do produto (deve ser um inteiro >= 1)",
        examples=[10, 5],
        ge=1
    )
    preco_unitario: float = Field(
        ..., 
        description="Preço unitário estimado ou tabelado do produto em Reais (R$)",
        examples=[3.50, 4.00],
        ge=0.0
    )


class PedidoSchema(BaseModel):
    """
    Schema principal de resposta estruturada em JSON para o agente de atendimento.
    Todos os campos são obrigatórios e validados tipadamente via Pydantic.
    """
    nome_cliente: str = Field(
        ..., 
        description="Nome completo do cliente informado no atendimento",
        examples=["João Silva"]
    )
    endereco: str = Field(
        ..., 
        description="Endereço de entrega completo informado pelo cliente",
        examples=["Rua das Flores, nº 123, Bairro Centro"]
    )
    forma_pagamento: str = Field(
        ..., 
        description="Forma de pagamento escolhida (ex: Cartão de Crédito, Pix, Dinheiro)",
        examples=["Pix", "Cartão de Crédito"]
    )
    itens: List[ItemPedido] = Field(
        ..., 
        description="Lista de itens solicitados no pedido com quantidades e preços unitários",
        examples=[[{"produto": "Coxinha", "quantidade": 10, "preco_unitario": 3.50}]]
    )
    subtotal: float = Field(
        ..., 
        description="Soma do valor de todos os itens do pedido em Reais (R$)",
        examples=[55.00],
        ge=0.0
    )
    taxa_entrega: float = Field(
        ..., 
        description="Valor fixo ou calculado da taxa de entrega em Reais (R$)",
        examples=[5.00],
        ge=0.0
    )
    total: float = Field(
        ..., 
        description="Valor total do pedido (subtotal + taxa_entrega) em Reais (R$)",
        examples=[60.00],
        ge=0.0
    )
    mensagem_confirmacao: str = Field(
        ..., 
        description="Mensagem educada de confirmação com status e estimativa de entrega",
        examples=["Olá João! Seu pedido foi registrado com sucesso e chegará em até 40 minutos."]
    )

INSTRUCOES = """
### CONTEXTO
Você é um assistente de atendimento automatizado de uma lanchonete/salgaria.
Sua função é receber o pedido do cliente e gerar uma resposta estritamente estruturada em JSON.

### PRODUTOS E PREÇOS TABELADOS
- Coxinha: R$ 3,50
- Bolinha de Queijo: R$ 3,50
- Enroladinho de Salsicha: R$ 3,00
- Kibe: R$ 4,00
- Presunto e Queijo: R$ 4,00
- Refrigerante: R$ 8,00
- Suco: R$ 6,00
- Taxa fixa de entrega: R$ 5,00

### REGRAS
1. Identifique o nome do cliente, endereço, forma de pagamento e a lista de itens com suas quantidades.
2. Calcule o subtotal (soma dos produtos * quantidade), aplique a taxa de entrega (R$ 5,00) e determine o valor total final.
3. Elabore uma mensagem educada de confirmação informando o tempo estimado de entrega (entre 30 e 40 minutos).
4. Preencha RIGOROSAMENTE todos os campos do schema JSON solicitado sem omitir nenhuma informação.
"""

async def main():
    agent = Agent(
        name="Assistente de Atendimento Estruturado",
        instructions=INSTRUCOES,
        output_type=PedidoSchema, 
        model_settings=ModelSettings(max_tokens=600)
    )

    prompt_cliente = (
        "Olá! Meu nome é João Silva. Gostaria de pedir 10 coxinhas e 5 kibes. "
        "Moro na Rua das Flores, número 123. Vou pagar no Pix."
    )

    print("==================================================")
    print("PROMPT ENVIADO AO AGENTE:")
    print(prompt_cliente)
    print("==================================================\n")

    result = await Runner.run(agent, prompt_cliente)

    output = result.final_output

    print("==================================================")
    print("VERIFICAÇÃO DA SAÍDA VIA result.final_output:")
    print("==================================================")
    print(f"• Tipo do objeto retornado: {type(output)}")
    print(f"• Instância direta de PedidoSchema? {isinstance(output, PedidoSchema)}")

    if isinstance(output, PedidoSchema):
        print("\n✅ SUCESSO: A saída gerada pelo agente corresponde exatamente ao schema Pydantic!")
        print("\n--- JSON GERADO (FORMATADO) ---")
        print(output.model_dump_json(indent=2))

        print("\n--- ACESSO DIRETO AOS CAMPOS VALIDADOS ---")
        print(f"• Cliente: {output.nome_cliente}")
        print(f"• Endereço: {output.endereco}")
        print(f"• Forma de Pagamento: {output.forma_pagamento}")
        print(f"• Qtd de Itens Distintos: {len(output.itens)}")
        for item in output.itens:
            print(f"  - {item.quantidade}x {item.produto} (R$ {item.preco_unitario:.2f}/un)")
        print(f"• Subtotal: R$ {output.subtotal:.2f}")
        print(f"• Taxa de Entrega: R$ {output.taxa_entrega:.2f}")
        print(f"• Total Final: R$ {output.total:.2f}")
        print(f"• Mensagem de Confirmação: \"{output.mensagem_confirmacao}\"")
    else:
        print("\n❌ FALHA: A saída do agente não seguiu o schema Pydantic esperado.")
        print("Output bruto retornado:", output)


if __name__ == "__main__":
    asyncio.run(main())

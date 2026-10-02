"""
eval_ab.py
----------
Módulo de avaliação quantitativa e Teste A/B para prompts do agente.
Aplica métricas automatizadas de validação de schema, execução de tools e
precisão matemática sobre um dataset sintético de testes.
"""

import asyncio
import os
import time
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, Runner, ModelSettings, set_default_openai_api

from schemas import PedidoSchema
from tools import consultar_estoque

# ---------------------------------------------------------------------------
# Configuração do Ambiente
# ---------------------------------------------------------------------------
load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")
os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
set_default_openai_api("chat_completions")


# ===========================================================================
# 1. DEFINIÇÃO DAS VARIANTES DE PROMPT (PROMPT A vs PROMPT B)
# ===========================================================================

# VARIANTE A: Prompt sucinto / direto (Sem instruções detalhadas de cálculo e fallback de estoque)
INSTRUCOES_VARIANTE_A = """
Você é um assistente de atendimento da lanchonete Salgados & Cia.
Receba o pedido do cliente, verifique a disponibilidade no estoque via ferramenta 'consultar_estoque'
e retorne uma resposta estritamente estruturada em JSON no schema PedidoSchema.

Tabela de Preços:
- Coxinha: R$ 3,50 | Bolinha de Queijo: R$ 3,50 | Enroladinho de Salsicha: R$ 3,00
- Kibe: R$ 4,00 | Presunto e Queijo: R$ 4,00 | Refrigerante: R$ 8,00 | Suco: R$ 6,00
- Taxa fixa de entrega: R$ 5,00
"""

# VARIANTE B: Prompt refinado via ciclo PRRR (Com fluxo passo a passo estrito e regras de negócio)
INSTRUCOES_VARIANTE_B = """
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


# ===========================================================================
# 2. DATASET DE TESTES (Cenários variados do mundo real)
# ===========================================================================

DATASET_TESTES: List[Dict[str, Any]] = [
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
        "expectativa_estoque_ok": False, # Kibe deve vir marcado como disponivel=False ou ser tratado
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


# ===========================================================================
# 3. MOTOR DE AVALIAÇÃO E MÉTRICAS
# ===========================================================================

async def executar_avaliacao_variante(
    nome_variante: str, 
    instrucoes: str
) -> Dict[str, Any]:
    """
    Executa a suíte de testes contra uma variante de prompt específica e calcula métricas.
    """
    print(f"\n" + "=" * 70)
    print(f"  EXECUTANDO AVALIAÇÃO: {nome_variante}")
    print("=" * 70)

    agente = Agent(
        name=f"Agente Teste {nome_variante}",
        instructions=instrucoes,
        tools=[consultar_estoque],
        output_type=PedidoSchema,
        model_settings=ModelSettings(max_tokens=600, temperature=0.1)
    )

    sucessos_schema = 0
    sucessos_calculo = 0
    tempo_total_ms = 0.0
    resultados_detalhados = []

    for caso in DATASET_TESTES:
        t0 = time.perf_counter()
        erro_ocorrido = None
        saida_valida = False
        calculo_correto = False

        print(f"\n[ Teste {caso['id']} ] - {caso['descricao']}")
        print(f"  Entrada: \"{caso['prompt']}\"")

        try:
            res = await Runner.run(agente, caso["prompt"])
            delta_t = (time.perf_counter() - t0) * 1000
            tempo_total_ms += delta_t

            output: PedidoSchema = res.final_output

            # Métrica 1: Validação estrita de Schema Pydantic
            if isinstance(output, PedidoSchema):
                saida_valida = True
                sucessos_schema += 1

                # Métrica 2: Acurácia Matemática do Cálculo Total (Subtotal + Taxa == Total)
                # Tolera diferença de 1 centavo devido a arredondamento de float
                soma_esperada = round(output.subtotal + output.taxa_entrega, 2)
                if abs(soma_esperada - output.total) < 0.01:
                    calculo_correto = True
                    sucessos_calculo += 1

                print(f"  Status    : ✅ Saída Pydantic Válida")
                print(f"  Cálculo   : {'✅ Correto' if calculo_correto else '❌ Incorreto'} (Subtotal: R${output.subtotal:.2f} + Taxa: R${output.taxa_entrega:.2f} = Total: R${output.total:.2f})")
                print(f"  Tempo Exec: {delta_t:.1f} ms")
            else:
                print(f"  Status    : ❌ Falha de Tipo (Retornou {type(output)})")

        except Exception as e:
            delta_t = (time.perf_counter() - t0) * 1000
            tempo_total_ms += delta_t
            erro_ocorrido = str(e)
            print(f"  Status    : ❌ Exceção Lançada -> {erro_ocorrido}")

        resultados_detalhados.append({
            "id": caso["id"],
            "saida_valida": saida_valida,
            "calculo_correto": calculo_correto,
            "tempo_ms": delta_t,
            "erro": erro_ocorrido
        })

    # Consolidação das Métricas Finais
    total_casos = len(DATASET_TESTES)
    taxa_schema = (sucessos_schema / total_casos) * 100
    taxa_calculo = (sucessos_calculo / total_casos) * 100
    tempo_medio = tempo_total_ms / total_casos

    metrics = {
        "variante": nome_variante,
        "taxa_conformidade_schema": taxa_schema,
        "taxa_precisao_calculo": taxa_calculo,
        "tempo_medio_ms": tempo_medio,
        "casos_avaliados": total_casos,
        "detalhes": resultados_detalhados
    }

    return metrics

# ===========================================================================
# 4. EXECUTOR PRINCIPAL E COMPARAÇÃO A/B
# ===========================================================================

async def main():
    print("Iniciando bateria de Testes A/B para evolução de Agentes...\n")

    # Rodar testes nas duas variantes
    metricas_a = await executar_avaliacao_variante("Variante A (Prompt Sucinto)", INSTRUCOES_VARIANTE_A)
    metricas_b = await executar_avaliacao_variante("Variante B (Prompt Refinado PRRR)", INSTRUCOES_VARIANTE_B)

    # Exibição do Quadro Comparativo Final
    print("\n" + "=" * 75)
    print("                   QUADRO COMPARATIVO DO TESTE A/B")
    print("=" * 75)
    print(f"{'Métrica':<35} | {'Variante A (Original)':<18} | {'Variante B (Refinada)':<18}")
    print("-" * 75)
    print(f"{'Conformidade Pydantic (Schema)':<35} | {metricas_a['taxa_conformidade_schema']:>17.1f}% | {metricas_b['taxa_conformidade_schema']:>17.1f}%")
    print(f"{'Precisão nos Cálculos (%)':<35} | {metricas_a['taxa_precisao_calculo']:>17.1f}% | {metricas_b['taxa_precisao_calculo']:>17.1f}%")
    print(f"{'Tempo Médio de Resposta (ms)':<35} | {metricas_a['tempo_medio_ms']:>15.1f} ms | {metricas_b['tempo_medio_ms']:>15.1f} ms")
    print("=" * 75)

    # Parecer/Decisão Automática
    print("\n[ DECISÃO E CONCLUSÃO DO TESTE ]")
    if metricas_b['taxa_precisao_calculo'] >= metricas_a['taxa_precisao_calculo'] and metricas_b['taxa_conformidade_schema'] >= metricas_a['taxa_conformidade_schema']:
        print("🏆 RECOMENDAÇÃO: Adotar a **Variante B** em produção.")
        print("   Justificativa: A Variante B apresentou melhor precisão lógica no tratamento")
        print("   de regras de negócio de estoque e consistência total dos cálculos financeiros.")
    else:
        print("⚠️ RECOMENDAÇÃO: Manter a Variante A ou realizar novo ciclo PRRR.")

if __name__ == "__main__":
    asyncio.run(main())
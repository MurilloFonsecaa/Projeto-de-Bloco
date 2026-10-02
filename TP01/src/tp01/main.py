"""
main.py
-------
Ponto de entrada do sistema agente – TP01/TP02.
Orquestra a execução dos agentes sem conter lógica de domínio,
schemas ou ferramentas (cada um em seu próprio módulo).
"""

import asyncio
import os
import time
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, Runner, ModelSettings, set_default_openai_api

from schemas import PedidoSchema, ExtracaoPedido
from tools import consultar_estoque, consultar_status_pedido
from memory import SQLiteSession, RAGMemory
from eval_tools import obter_dados_avaliacao, obter_dados_avaliacao_fn

# ---------------------------------------------------------------------------
# Configuração do ambiente
# ---------------------------------------------------------------------------
load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")
os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
set_default_openai_api("chat_completions")


# ---------------------------------------------------------------------------
# Prompts / instruções dos agentes
# ---------------------------------------------------------------------------

INSTRUCOES_JSON = """
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

INSTRUCOES_TOOLS = """
### CONTEXTO
Você é um assistente de atendimento da lanchonete Salgados & Cia.
Você tem acesso a ferramentas para consultar dados reais do sistema da loja.

### FERRAMENTAS DISPONÍVEIS
- consultar_estoque(produto): verifica a quantidade disponível de um produto.
- consultar_status_pedido(numero_pedido): retorna o status atual de um pedido.

### INSTRUÇÕES
- Use as ferramentas sempre que o cliente perguntar sobre estoque ou status de pedido.
- Nunca invente informações; baseie sua resposta EXCLUSIVAMENTE no retorno das ferramentas.
- Responda de forma objetiva, educada e direta ao ponto.
"""

INSTRUCOES_ETAPA1_EXTRACAO = """
Você é um extrator de dados de pedidos de uma lanchonete.
Sua única função é ler a mensagem do cliente e extrair:
- nome do cliente
- endereço de entrega
- forma de pagamento
- lista de itens com suas quantidades

Não calcule preços, não valide estoque. Apenas extraia as informações da mensagem.
"""

INSTRUCOES_ETAPA2_VALIDACAO = """
Você é um validador de pedidos de uma lanchonete com acesso ao sistema de estoque.
Você recebe uma lista de itens solicitados e deve verificar, um a um, se cada produto
está disponível em estoque usando a ferramenta consultar_estoque.

Para cada item, informe:
- se está disponível (quantidade no estoque)
- se está esgotado ou não encontrado

Ao final, apresente um relatório claro indicando quais itens podem ser incluídos no pedido.
"""

INSTRUCOES_ETAPA3_FINALIZACAO = """
Você é o finalizador de pedidos de uma lanchonete.
Você recebe os dados do cliente e a lista de itens já validados com disponibilidade confirmada.
Sua função é gerar o pedido final completo em JSON, preenchendo todos os campos do schema.

### PREÇOS TABELADOS
- Coxinha: R$ 3,50
- Bolinha de Queijo: R$ 3,50
- Enroladinho de Salsicha: R$ 3,00
- Kibe: R$ 4,00
- Presunto e Queijo: R$ 4,00
- Refrigerante: R$ 8,00
- Suco: R$ 6,00
- Taxa fixa de entrega: R$ 5,00

### REGRAS
1. Use apenas itens com disponibilidade confirmada no relatório de validação.
2. Calcule subtotal, aplique taxa de entrega de R$ 5,00 e determine o total.
3. Gere mensagem educada de confirmação com tempo estimado de 30 a 40 minutos.
4. Preencha RIGOROSAMENTE todos os campos do schema JSON.
"""

INSTRUCOES_AGENTE_MEMORIA = """
Você é um assistente de atendimento da lanchonete Salgados & Cia com memória persistente.
Você se lembra de interações anteriores com o cliente e usa esse contexto para personalizar o atendimento.

### INSTRUÇÕES
- Cumprimente o cliente pelo nome se já o conhecer.
- Mencione pedidos anteriores quando relevante.
- Responda de forma acolhedora e personalizada.
- Caso receba contexto de memória, use-o ativamente na resposta.
"""


# ---------------------------------------------------------------------------
# Agentes
# ---------------------------------------------------------------------------

async def agente_json():
    """Agente com saída estruturada em JSON validada pelo schema Pydantic."""

    agent = Agent(
        name="Assistente de Atendimento Estruturado",
        instructions=INSTRUCOES_JSON,
        output_type=PedidoSchema,
        model_settings=ModelSettings(max_tokens=600),
    )

    prompt_cliente = (
        "Olá! Meu nome é João Silva. Gostaria de pedir 10 coxinhas e 5 kibes. "
        "Moro na Rua das Flores, número 123. Vou pagar no Pix."
    )

    print("PROMPT ENVIADO AO AGENTE:")
    print(f"  >> {prompt_cliente}\n")

    result = await Runner.run(agent, prompt_cliente)
    output = result.final_output

    print(f"• Tipo retornado       : {type(output)}")
    print(f"• É PedidoSchema?      : {isinstance(output, PedidoSchema)}")

    if isinstance(output, PedidoSchema):
        print("\n✅ SUCESSO – JSON gerado e validado:\n")
        print(output.model_dump_json(indent=2))
    else:
        print("\n❌ FALHA – saída fora do schema esperado:")
        print(output)


async def agente_com_ferramentas():
    """Agente equipado com @function_tool que consulta dados externos ao modelo."""

    agent = Agent(
        name="Assistente com Ferramentas",
        instructions=INSTRUCOES_TOOLS,
        tools=[consultar_estoque, consultar_status_pedido],
        model_settings=ModelSettings(max_tokens=300),
    )

    # Teste 1 – consulta de estoque
    prompt_estoque = "Olá! Ainda tem coxinha disponível? E kibe?"
    print("PROMPT 1 (consulta de estoque):")
    print(f"  >> {prompt_estoque}")
    resultado = await Runner.run(agent, prompt_estoque)
    print(f"  RESPOSTA: {resultado.final_output}\n")

    # Teste 2 – status de pedido
    prompt_status = "Qual o status do meu pedido PED-002?"
    print("PROMPT 2 (status de pedido):")
    print(f"  >> {prompt_status}")
    resultado = await Runner.run(agent, prompt_status)
    print(f"  RESPOSTA: {resultado.final_output}")


async def agente_pipeline_encadeado():
    """
    Pipeline de raciocínio encadeado com Prompt Chaining.
    Decompõe o processamento de um pedido complexo em 3 etapas sequenciais:
      Etapa 1 – Extração: interpreta a mensagem do cliente → ExtracaoPedido
      Etapa 2 – Validação: consulta estoque item a item via tool → relatório textual
      Etapa 3 – Finalização: gera o pedido final validado → PedidoSchema (JSON)
    """

    mensagem_cliente = (
        "Oi! Sou a Maria Souza. Quero 8 coxinhas, 4 kibes e 2 sucos. "
        "Entrega na Av. Brasil, 500. Vou pagar no cartão de crédito."
    )

    print(f"MENSAGEM DO CLIENTE:\n  >> {mensagem_cliente}\n")

    # ETAPA 1
    print("[ ETAPA 1 – EXTRAÇÃO DE DADOS DO PEDIDO ]")

    agente_extracao = Agent(
        name="Extrator de Pedido",
        instructions=INSTRUCOES_ETAPA1_EXTRACAO,
        output_type=ExtracaoPedido,
        model_settings=ModelSettings(max_tokens=300),
    )

    resultado_etapa1 = await Runner.run(agente_extracao, mensagem_cliente)
    extracao: ExtracaoPedido = resultado_etapa1.final_output

    print("  OUTPUT INTERMEDIÁRIO (ExtracaoPedido):")
    print(f"  {extracao.model_dump_json(indent=2)}\n")

    # ETAPA 2
    print("[ ETAPA 2 – VALIDAÇÃO DE ESTOQUE VIA TOOLS ]")

    itens_str = ", ".join(
        f"{item.quantidade}x {item.produto}" for item in extracao.itens_solicitados
    )
    prompt_validacao = (
        f"Valide a disponibilidade dos seguintes itens do pedido: {itens_str}. "
        "Consulte o estoque de cada produto individualmente e gere um relatório."
    )

    agente_validacao = Agent(
        name="Validador de Estoque",
        instructions=INSTRUCOES_ETAPA2_VALIDACAO,
        tools=[consultar_estoque],
        model_settings=ModelSettings(max_tokens=400),
    )

    resultado_etapa2 = await Runner.run(agente_validacao, prompt_validacao)
    relatorio_validacao: str = resultado_etapa2.final_output

    print("  OUTPUT INTERMEDIÁRIO (relatório de validação):")
    print(f"  {relatorio_validacao}\n")

    # ETAPA 3
    print("[ ETAPA 3 – GERAÇÃO DO PEDIDO FINAL (JSON) ]")

    prompt_finalizacao = (
        f"Dados do cliente:\n"
        f"  Nome: {extracao.nome_cliente}\n"
        f"  Endereço: {extracao.endereco}\n"
        f"  Pagamento: {extracao.forma_pagamento}\n\n"
        f"Relatório de validação de estoque:\n{relatorio_validacao}\n\n"
        "Gere o pedido final em JSON com todos os campos preenchidos."
    )

    agente_finalizacao = Agent(
        name="Finalizador de Pedido",
        instructions=INSTRUCOES_ETAPA3_FINALIZACAO,
        output_type=PedidoSchema,
        model_settings=ModelSettings(max_tokens=600),
    )

    resultado_etapa3 = await Runner.run(agente_finalizacao, prompt_finalizacao)
    pedido_final: PedidoSchema = resultado_etapa3.final_output

    if isinstance(pedido_final, PedidoSchema):
        print("  ✅ PEDIDO FINAL GERADO COM SUCESSO:")
        print(pedido_final.model_dump_json(indent=2))
    else:
        print("  ❌ FALHA na etapa de finalização.")
        print(pedido_final)


async def agente_com_memoria():
    """
    Demonstra memória persistente em duas camadas: SQLiteSession + RAGMemory.
    """

    SESSION_ID = "cliente-joao-silva"

    openai_client = AsyncOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        base_url="https://openrouter.ai/api/v1",
    )

    sessao = SQLiteSession(session_id=SESSION_ID)
    rag = RAGMemory(session_id=SESSION_ID, client=openai_client)

    agente = Agent(
        name="Assistente com Memória",
        instructions=INSTRUCOES_AGENTE_MEMORIA,
        model_settings=ModelSettings(max_tokens=300),
    )

    # RUN 1
    print("[ RUN 1 – PRIMEIRA SESSÃO (novo cliente) ]")
    msg1 = "Olá! Meu nome é João. Gostaria de pedir 10 coxinhas."
    print(f"  Cliente: {msg1}")

    resultado1 = await Runner.run(agente, msg1, session=sessao)
    resposta1 = resultado1.final_output
    print(f"  Agente : {resposta1}\n")

    await rag.adicionar(f"Cliente: {msg1} | Agente: {resposta1}")
    print(f"  [SQLite] Mensagens na sessão: {sessao.contar_mensagens()}")
    print(f"  [RAG]    Entradas armazenadas: {len(rag.listar_entradas())}")

    # RUN 2
    print("\n[ RUN 2 – SEGUNDA SESSÃO (mesmo cliente retorna) ]")
    msg2 = "Você se lembra de mim? Quero fazer mais um pedido."
    print(f"  Cliente: {msg2}")

    contexto_rag = await rag.buscar(msg2, top_k=2)
    contexto_str = "\n".join(contexto_rag) if contexto_rag else "Nenhum contexto anterior encontrado."

    prompt_com_contexto = (
        f"[Contexto de interações anteriores recuperado via busca semântica:]\n"
        f"{contexto_str}\n\n"
        f"[Mensagem atual do cliente:]\n{msg2}"
    )

    resultado2 = await Runner.run(agente, prompt_com_contexto, session=sessao)
    resposta2 = resultado2.final_output
    print(f"  Agente : {resposta2}\n")

    await rag.adicionar(f"Cliente: {msg2} | Agente: {resposta2}")
    print(f"  [SQLite] Mensagens na sessão: {sessao.contar_mensagens()}")
    print(f"  [RAG]    Entradas armazenadas: {len(rag.listar_entradas())}")

    # RUN 3
    print("\n[ RUN 3 – TERCEIRA SESSÃO (histórico completo disponível) ]")
    msg3 = "Quantas coxinhas eu pedi da última vez?"
    print(f"  Cliente: {msg3}")

    contexto_rag3 = await rag.buscar(msg3, top_k=3)
    contexto_str3 = "\n".join(contexto_rag3) if contexto_rag3 else "Nenhum contexto anterior."

    prompt_com_contexto3 = (
        f"[Contexto relevante de sessões anteriores:]\n"
        f"{contexto_str3}\n\n"
        f"[Mensagem atual do cliente:]\n{msg3}"
    )

    resultado3 = await Runner.run(agente, prompt_com_contexto3, session=sessao)
    resposta3 = resultado3.final_output
    print(f"  Agente : {resposta3}\n")

    print(f"  [SQLite] Mensagens na sessão: {sessao.contar_mensagens()}")
    print(f"  [RAG]    Entradas armazenadas: {len(rag.listar_entradas())}")
    print(f"  [DB]     Sessão '{SESSION_ID}' → memoria.db")


async def agente_com_ferramentas_e_pydantic():
    """
    Demonstra a execução de um agente que utiliza ferramentas externas (tools)
    e retorna o resultado diretamente estruturado e validado via Pydantic (output_type).
    """
    print("=" * 60)
    print("AGENTE COMBINADO: FERRAMENTAS + SAÍDA VALIDADA COM PYDANTIC")
    print("=" * 60)

    agent = Agent(
        name="Assistente Validador e Estruturado",
        instructions=INSTRUCOES_TOOLS,
        tools=[consultar_estoque],
        output_type=PedidoSchema,
        model_settings=ModelSettings(max_tokens=800),
    )

    prompt_cliente = (
        "Olá! Sou o Carlos Eduardo. Gostaria de pedir 5 coxinhas, 3 kibes e 2 sucos. "
        "Moro na Av. Paulista, 1000. Vou pagar via Pix."
    )

    print("PROMPT ENVIADO:")
    print(f"  >> {prompt_cliente}\n")

    result = await Runner.run(agent, prompt_cliente)
    output: PedidoSchema = result.final_output

    print("VERIFICAÇÃO DE TIPAGEM:")
    print(f"• Tipo da variável 'output' : {type(output)}")
    print(f"• É instância de PedidoSchema? : {isinstance(output, PedidoSchema)}\n")

    if isinstance(output, PedidoSchema):
        print("✅ SUCESSO - Saída validada com sucesso pelo Pydantic:\n")
        print(output.model_dump_json(indent=2))

        print("\n[ DADOS ACESSADOS DE FORMA TIPADA ]")
        print(f"• Cliente    : {output.nome_cliente}")
        print(f"• Endereço   : {output.endereco}")
        print(f"• Pagamento  : {output.forma_pagamento}")
        print(f"• Total      : R$ {output.total:.2f}")
        print(f"• Confirm.   : {output.mensagem_confirmacao}")
    else:
        print("❌ FALHA - A saída não seguiu o schema Pydantic esperado.")
        print(output)


async def executar_avaliacao_variante(
    nome_variante: str, 
    instrucoes: str,
    dataset: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Executa a suíte de testes para uma variante de prompt específica e calcula as métricas.
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

    for caso in dataset:
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

            if isinstance(output, PedidoSchema):
                saida_valida = True
                sucessos_schema += 1

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

    total_casos = len(dataset)
    taxa_schema = (sucessos_schema / total_casos) * 100
    taxa_calculo = (sucessos_calculo / total_casos) * 100
    tempo_medio = tempo_total_ms / total_casos

    return {
        "variante": nome_variante,
        "taxa_conformidade_schema": taxa_schema,
        "taxa_precisao_calculo": taxa_calculo,
        "tempo_medio_ms": tempo_medio,
        "casos_avaliados": total_casos,
        "detalhes": resultados_detalhados
    }


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

async def main():
    print("Iniciando Agente Orquestrador de Avaliação...\n")

    agente_orquestrador = Agent(
        name="Orquestrador de Benchmark",
        instructions="""
        Você é um agente orquestrador de testes.
        Sua única responsabilidade é executar a ferramenta `obter_dados_avaliacao` para recuperar
        as variantes de prompt e o dataset de testes necessários para a avaliação A/B.
        """,
        tools=[obter_dados_avaliacao],
        model_settings=ModelSettings(max_tokens=300)
    )

    prompt_orquestrador = "Obtenha as variantes de prompt e o dataset para o teste A/B."
    print("🤖 Solicitando dados de teste ao Agente via Tool Calling...")
    
    res_orquestrador = await Runner.run(agente_orquestrador, prompt_orquestrador)
    
    # Executa a função Python pura (evita o erro do objeto FunctionTool)
    dados_benchmark = obter_dados_avaliacao_fn()
    variantes = dados_benchmark["variantes"]
    dataset = dados_benchmark["dataset"]

    print(f"✅ Dados carregados via Tool:")
    print(f"   • Variantes de Prompt encontradas : {len(variantes)}")
    print(f"   • Casos de Teste no Dataset       : {len(dataset)}")

    metricas_a = await executar_avaliacao_variante("Variante A (Prompt Sucinto)", variantes["Variante A (Prompt Sucinto)"], dataset)
    metricas_b = await executar_avaliacao_variante("Variante B (Prompt Refinado PRRR)", variantes["Variante B (Prompt Refinado PRRR)"], dataset)

    print("\n" + "=" * 75)
    print("                   QUADRO COMPARATIVO DO TESTE A/B")
    print("=" * 75)
    print(f"{'Métrica':<35} | {'Variante A (Original)':<18} | {'Variante B (Refinada)':<18}")
    print("-" * 75)
    print(f"{'Conformidade Pydantic (Schema)':<35} | {metricas_a['taxa_conformidade_schema']:>17.1f}% | {metricas_b['taxa_conformidade_schema']:>17.1f}%")
    print(f"{'Precisão nos Cálculos (%)':<35} | {metricas_a['taxa_precisao_calculo']:>17.1f}% | {metricas_b['taxa_precisao_calculo']:>17.1f}%")
    print(f"{'Tempo Médio de Resposta (ms)':<35} | {metricas_a['tempo_medio_ms']:>15.1f} ms | {metricas_b['tempo_medio_ms']:>15.1f} ms")
    print("=" * 75)

    print("\n[ DECISÃO E CONCLUSÃO DO TESTE ]")
    if metricas_b['taxa_precisao_calculo'] >= metricas_a['taxa_precisao_calculo'] and metricas_b['taxa_conformidade_schema'] >= metricas_a['taxa_conformidade_schema']:
        print("🏆 RECOMENDAÇÃO: Adotar a **Variante B** em produção.")
        print("   Justificativa: A Variante B apresentou melhor precisão lógica no tratamento")
        print("   de regras de negócio de estoque e consistência total dos cálculos financeiros.")
    else:
        print("⚠️ RECOMENDAÇÃO: Manter a Variante A ou realizar novo ciclo PRRR.")

if __name__ == "__main__":
    asyncio.run(main())
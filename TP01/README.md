# Projeto de Bloco - TP01

Projeto de desenvolvimento de um assistente de IA para loja de salgadinhos com pedidos via linguagem natural e validação estruturada.

## 📂 Estrutura de Evidências

As evidências de execução dos scripts estão disponíveis na pasta [`Evidencias/`](./Evidencias):

- 📄 [Documentação completa das Evidências](./Evidencias/Links_das_Imagens.md)
- 🖼️ [Evidência `estrutura_json.py`](./Evidencias/estrutura_json.png)
- 🖼️ [Evidência `agente_estruturado.py`](./Evidencias/agente_estruturado.png)
- 🖼️ [Evidência `agente_funcional.py`](./Evidencias/agente_funcional.png)

---

## 📜 Arquivos do Projeto

- [`Arquitetura.md`](./Arquitetura.md) - Descrição da arquitetura, componentes e fluxo de dados.
- [`Problema_e_Solução.md`](./Problema_e_Solução.md) - Definição do problema, requisitos, restrições técnicas.
- [`src/tp01/estrutura_json.py`](./src/tp01/estrutura_json.py) - Script de validação e geração de JSON estruturado (Agente principal).
- [`src/tp01/agente_estruturado.py`](./src/tp01/agente_estruturado.py) - Script do agente com anatomia de prompt para montagem de pedidos.
- [`src/tp01/agente_funcional.py`](./src/tp01/agente_funcional.py) - Script abordando a importância da validação humana.

---

## 🚀 Como Executar

Os scripts estão organizados dentro do pacote `src/tp01/` seguindo a estrutura padrão de projetos Python (`uv` / `pyproject.toml`):

```bash
# Executar o agente principal do projeto (estrutura_json)
uv run tp01

# Ou executar individualmente cada marco avaliativo:
uv run python src/tp01/agente_funcional.py
uv run python src/tp01/agente_estruturado.py
uv run python src/tp01/estrutura_json.py
```


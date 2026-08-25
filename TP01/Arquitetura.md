## Arquitetura Inicial:

# Componentes:
Interface Web:
 - Permite ao cliente visualizar os produtos, escolher quantidades, consultar o pedido e finalizar a compra.
 - Também poderá apresentar o status do pedido.

Assistente de IA:
 - Responsável por interpretar mensagens enviadas pelo cliente, principalmente através do WhatsApp.
 - Identifica produtos, quantidades, dúvidas e informações faltantes.
 - Pode consultar o histórico do cliente para sugerir pedidos semelhantes.

Ferramentas do agente:
 - Consulta de produtos: verifica produtos, preços e disponibilidade.
 - Gerenciamento do pedido: adiciona, remove ou altera produtos e quantidades.
 - Cálculo do pedido: calcula o valor total utilizando os dados reais dos produtos.
 - Consulta de histórico: recupera pedidos anteriores do cliente.
 - Cadastro/consulta do cliente: recupera nome e endereço previamente registrados.
 - Finalização do pedido: valida as informações e registra o pedido.

Modelo de linguagem:    
 - Responsável pela interpretação da linguagem natural utilizada pelo cliente.
 - Por exemplo, ao receber "Quero 10 coxinhas e 5 kibes", o modelo deve identificar os produtos e suas respectivas quantidades e utilizar as ferramentas necessárias para montar o pedido.

Banco de dados:
 - Armazena produtos, preços, disponibilidade, clientes, endereços, pedidos e histórico.
 - O banco será a fonte de verdade para informações como preço e disponibilidade.


# Fluxo de dados:
 - Cliente inicia o atendimento:
  - O cliente pode acessar o site diretamente ou iniciar uma conversa pelo WhatsApp.

 - Cliente fornece uma solicitação:
  - Por exemplo: "Quero 20 coxinhas e 10 bolinhas de queijo."
  - Essas informações entram no sistema como linguagem natural.

 - Agente interpreta a solicitação:
  - O modelo de linguagem identifica:
   - Produto: coxinha → quantidade: 20
   - Produto: bolinha de queijo → quantidade: 10
  - Caso falte alguma informação, o agente solicita ao cliente.

 - Agente consulta as ferramentas:
  - O agente verifica no banco:
   - Se os produtos existem;
   - Se estão disponíveis;
   - Seus preços;
   - Informações do cliente;
  - Pedidos anteriores, quando aplicável.

 - Sistema monta o pedido:
  - As informações são transformadas em uma estrutura organizada, por exemplo:

    Produto              Quantidade
    Coxinha                 20
    Bolinha de queijo       10

    Subtotal: R$ XX,XX
    Taxa de entrega: R$ XX,XX
    Total: R$ XX,XX

  - O cálculo do preço deve ser feito pelo sistema, e não pelo modelo de linguagem.

 - Sistema valida o pedido:
  - Antes de finalizar, verifica se:
   - Todos os produtos estão disponíveis;
   - As quantidades são válidas;
   - Nome e endereço estão preenchidos;
   - Forma de pagamento foi informada;
  - Não existe nenhuma informação ambígua.

 - Cliente confirma:
  - Depois da confirmação, o pedido é registrado e o sistema retorna o status correspondente.


Formato de saída:
 - Saída estruturada em JSON internamente, mas em lingageum natural para o cliente.


# Justificativa:
A escolha do modelo de linguagem se dá pela necessidade de interpretar a linguagem natural do cliente, identificar produtos, quantidades, dúvidas e informações faltantes. A escolha do formato de saída se dá porque o cliente não entenderia caso o assistente enviasse o pedido em formato estruturado. 
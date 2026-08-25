Decidi criar um site de pedidos online para uma loja de salgadinhos junto com um assistente de IA. Usuário-alvo: Pessoas que querem comprar salgadinhos. Contexto de uso: Aprimorar o atendimento online para os clientes que preferem ou não conseguem ir até a loja para fazer seus pedidos, além dos que não conseguem fazer os pedidos pelo site. 

Requsitos: Vou listar apenas alguns, senão a lista ficaria muito extensa.

 - O site deve calcular automaticamente o preço total do pedido.
 - O cliente tem que ter autonimia para escolher quais e quantos salgadinhos quer no pedido.
 - O site tem que bloquear e dizer os produtos indisponíveis.
 - O site terá integração com WhatsApp, permitindo que o cliente faça o pedido por meio de linguagem natural.
 - O site terá memória dos pedidos anteriores. Caso o mesmo cliente, via WhastApp, faça um pedido semelhante ao anterior, o site irá sugerir os produtos e quantidades e se lembrará do nome e endereço do cliente.
 - A integração do site com o WhastApp permitirá ao assistente fazer o pedido no site. O cliente que não consegue ou não quer usar o site, poderá pedir por WhastApp.
 

Inputs esperados: 
 - Nome do cliente.
 - Endereço do cliente.
 - Lista de produtos desejados.
 - Quantidade de cada produto.
 - Forma de pagamento.

Outputs do sistema:
 - Respostas às dúvidas do cliente.
 - Pedido estruturado.
 - Quantidades dos produtos.
 - Valor total.
 - Status do pedido.
 - Confirmações ou mensagens solicitando informações faltantes.

 Restrições Técnicas:

 - O sistema deve ser implementado como uma aplicação web.
 - O agente deve utilizar um modelo de linguagem para interpretar as mensagens do cliente.
 - Os produtos e preços devem estar armazenados em uma estrutura de dados ou banco de dados.
 - O sistema não deve permitir pedidos de produtos indisponíveis.
 - O valor total deve ser calculado pelo sistema, e não pelo modelo de linguagem.
 - Informações estruturadas do pedido devem ser separadas da resposta textual do agente.
 - O agente deve manter o histórico da conversa durante o atendimento.
 - O sistema deve validar informações obrigatórias antes de finalizar o pedido.
 - O sistema deve evitar confirmar um pedido quando houver informações ambíguas ou faltantes.
 
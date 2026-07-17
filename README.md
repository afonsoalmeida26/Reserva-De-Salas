# Reserva-De-Salas
Backend de um sistema de reserva de salas com autenticação, criação, cancelamento, check-in e controlo.


#Este é um projeto pessoal criado para reservar salas. Pode ser utilizado/adaptado para reserva de salas nas escolas, universidades ou qualquer outro estabelcimento que necessite de reservas salas.

---

### FUNCIONALIDADES PRINCIPAIS ###
*Gestão de reservas*: O utilizador pode criar, cancelar ou fazer check-in de reservas.
*Sistema de faltas*: Se passarem 15 minutos desde a hora de inicio da reserva e o utilizador não efetuar o Check-In, será registada uma falta. Se o utilizador possuir 3 faltas nos últimas 30 dias, fica restringido de efetuar reservas.
*Painel de Admininstrador*: Admininstradores têm acesso a um painel, onde podem criar / excluir salas, obter estatísticas como salas mais requesitadas e horas de maior e menor procura, e visualizar todas as reservas dos próximos 90 dias.
**Automação de tarefas (Cron Jobs)** 
*Verificação de faltas*: Onde são verificadas as reservas onde não foram efetuados Check-in's. cancelando-as e registando as respetivas faltas. 
*Atualização automática do estado de Reservas*: Transição automática do estado de reservas para "A decorrer", às quais estejam com Check-In feito e estejam dentro da sua hora.

---

### FERRAMENTAS UTILIZADAS ###
*JWT (Autenticação segura)*
*psycopg (Base de Dados)*
*Flask (Rotas)*


### NOTAS ###
O Frontend foi criado inteiramente por IA, sendo o foco principal o Backend
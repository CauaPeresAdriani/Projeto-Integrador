# Documentação de Adequação à LGPD - ClinSecure

## 1. Objetivo

O ClinSecure possui mecanismos para proteção dos dados pessoais utilizados no gerenciamento de pesquisas clínicas.

Esta documentação apresenta as medidas implementadas para atender aos requisitos relacionados à LGPD.

Os requisitos abordados são:

- 4.1 - Listagem completa dos dados pessoais coletados;
- 4.2 - Associação dos dados às suas finalidades;
- 4.3 - Evidência de minimização de dados;
- 4.4 - Registro explícito de consentimento;
- 4.5 - Associação do consentimento à finalidade;
- 4.6 - Revogação do consentimento;
- 4.7 - Registro de data e versão do consentimento;
- 4.8 - Consulta aos dados do titular;
- 4.9 - Exportação dos dados;
- 4.10 - Exclusão dos dados pessoais;
- 4.11 - Fluxo de atendimento aos direitos do titular.


# 2. Dados pessoais coletados

## 2.1 Dados dos usuários

O sistema utiliza dados necessários para identificação, autenticação, controle de acesso e comunicação.

| Dado | Finalidade |
|---|---|
| Nome de usuário | Identificação do usuário |
| E-mail | Comunicação e recuperação de acesso |
| CPF | Identificação única |
| Perfil | Controle de permissões |
| Senha | Autenticação |
| Dados relacionados ao 2FA | Segurança da conta |

A senha não deve ser disponibilizada ao usuário em formato legível.


## 2.2 Dados dos participantes

| Dado | Finalidade |
|---|---|
| Nome | Identificação do participante |
| CPF | Identificação única |
| Data de nascimento | Identificação e critérios da pesquisa |
| Situação do cadastro | Controle do cadastro |
| Data de cadastro | Rastreabilidade |


## 2.3 Dados de consentimento

| Dado | Finalidade |
|---|---|
| Finalidade | Informar o objetivo do tratamento |
| Versão | Identificar a versão aceita |
| Data do consentimento | Registrar quando o consentimento ocorreu |
| Situação | Identificar se o consentimento está ativo ou revogado |
| Data da revogação | Registrar a revogação |


## 2.4 Dados de auditoria

| Dado | Finalidade |
|---|---|
| Usuário | Identificar quem realizou a operação |
| Evento | Identificar a operação |
| Data e hora | Registrar quando ocorreu |
| IP | Apoiar segurança e auditoria |
| Resultado | Identificar sucesso ou falha |
| Detalhes | Registrar informações da operação |


# 3. Finalidade dos dados

Cada dado pessoal utilizado pelo ClinSecure deve possuir uma finalidade definida.

As principais finalidades são:

1. identificação;
2. autenticação;
3. controle de acesso;
4. gerenciamento de participantes;
5. gerenciamento de consentimentos;
6. realização das atividades relacionadas às pesquisas;
7. segurança da informação;
8. auditoria;
9. atendimento aos direitos do titular.


# 4. Minimização de dados

O ClinSecure busca utilizar somente os dados necessários para cada finalidade.

Dados sem finalidade definida não devem ser coletados.

Informações utilizadas exclusivamente para segurança, como senha e segredos de autenticação, não devem ser disponibilizadas nas consultas ou exportações comuns dos dados do titular.


# 5. Consentimento

O sistema deverá registrar o consentimento do titular de forma explícita.

O registro deverá possuir:

- finalidade;
- versão;
- data e hora;
- situação;
- data de revogação, quando aplicável.


# 6. Revogação

O titular deverá possuir uma funcionalidade para revogar um consentimento anteriormente concedido.

A revogação deverá registrar:

- alteração da situação;
- data da revogação;
- operação no registro de auditoria.


# 7. Consulta dos dados

O titular deverá possuir uma área para consultar seus dados pessoais armazenados pelo sistema.

Informações de segurança, como senha e segredo do segundo fator de autenticação, não deverão ser exibidas.


# 8. Exportação dos dados

O titular deverá possuir uma funcionalidade para exportar seus dados pessoais.

A exportação deverá utilizar um formato estruturado, como JSON.

Informações que possam comprometer a segurança da conta não deverão ser exportadas.


# 9. Exclusão dos dados

O titular deverá possuir uma funcionalidade para solicitar a exclusão de seus dados pessoais.

Quando houver necessidade de manter informações para fins de segurança, auditoria ou cumprimento de obrigações aplicáveis, deverá ser considerada a anonimização ou desvinculação dos dados pessoais.


# 10. Auditoria

As operações relacionadas aos direitos do titular deverão ser registradas no AuditLog.

Entre os eventos registrados estão:

- consulta dos dados;
- exportação;
- revogação de consentimento;
- solicitação de exclusão;
- operações relacionadas ao consentimento.


# 11. Fluxo de atendimento aos direitos do titular

O fluxo será:

1. O titular acessa sua conta.
2. O titular consulta seus dados.
3. O titular consulta seus consentimentos.
4. O titular pode revogar um consentimento.
5. O titular pode exportar seus dados.
6. O titular pode solicitar a exclusão.
7. O sistema processa a solicitação.
8. A operação é registrada no AuditLog.
9. Quando necessário, informações que devam ser preservadas são mantidas conforme a finalidade aplicável.
# Documentação de Adequação à LGPD - ClinSecure

## 1. Introdução

O ClinSecure é um sistema desenvolvido para auxiliar no gerenciamento seguro de informações relacionadas a pesquisas clínicas e seus participantes.

Como o sistema trabalha com dados pessoais, foram definidas medidas para atender aos princípios e direitos previstos na Lei Geral de Proteção de Dados Pessoais (LGPD - Lei nº 13.709/2018).

Esta documentação apresenta as medidas adotadas pelo sistema para atender aos requisitos relacionados à proteção de dados pessoais.

Os requisitos abordados são:

- 4.1 - Listagem completa dos dados pessoais coletados;
- 4.2 - Associação de cada dado a uma finalidade;
- 4.3 - Evidência de minimização de dados;
- 4.4 - Registro explícito de consentimento;
- 4.5 - Consentimento associado à finalidade;
- 4.6 - Possibilidade de revogação do consentimento;
- 4.7 - Registro de data e versão do consentimento;
- 4.8 - Funcionalidade de consulta aos dados do titular;
- 4.9 - Funcionalidade de exportação dos dados;
- 4.10 - Funcionalidade de exclusão dos dados pessoais;
- 4.11 - Fluxo de atendimento aos direitos do titular.

---

# 2. Listagem completa dos dados pessoais coletados

## 2.1 Dados relacionados ao usuário

O sistema possui o modelo `Usuario`, responsável pelo gerenciamento das contas utilizadas para acesso à aplicação.

Os principais dados armazenados são:

| Dado | Finalidade | Necessidade |
|---|---|---|
| Nome de usuário | Identificação da conta | Necessário |
| E-mail | Comunicação e recuperação da conta | Necessário |
| CPF | Identificação única do usuário | Necessário |
| Perfil | Controle de permissões | Necessário |
| Senha | Autenticação | Necessário |
| Ativação do 2FA | Controle da autenticação adicional | Necessário para segurança |
| Chave do 2FA | Funcionamento da autenticação de dois fatores | Necessário para segurança |
| Tentativas de login | Proteção contra ataques de força bruta | Necessário para segurança |
| Bloqueio da conta | Controle de bloqueios temporários | Necessário para segurança |
| Última falha de login | Controle de tentativas de acesso | Necessário para segurança |
| Tentativas de 2FA | Proteção contra tentativas incorretas | Necessário para segurança |
| Bloqueio do 2FA | Controle de bloqueios do segundo fator | Necessário para segurança |

A senha é armazenada pelo mecanismo de autenticação do Django e não deve ser armazenada ou apresentada em texto puro.

Informações utilizadas exclusivamente para autenticação e segurança não devem ser expostas ao titular em consultas comuns ou exportações.

---

## 2.2 Dados relacionados ao participante

O modelo `Participante` armazena informações necessárias para identificação e gerenciamento dos participantes.

Os dados são:

| Dado | Finalidade | Necessidade |
|---|---|---|
| Nome | Identificação do participante | Necessário |
| CPF | Identificação única do participante | Necessário |
| Data de nascimento | Identificação e aplicação de critérios da pesquisa | Necessário quando aplicável |
| Situação do cadastro | Controle da situação do participante | Necessário |
| Data de cadastro | Registro da criação do cadastro | Necessário para rastreabilidade |

---

## 2.3 Dados relacionados ao consentimento

O modelo `Consentimento` é utilizado para registrar as informações relacionadas à autorização do participante.

Os dados são:

| Dado | Finalidade | Necessidade |
|---|---|---|
| Participante | Identificar o titular relacionado ao consentimento | Necessário |
| Usuário que registrou | Identificar quem realizou o registro | Necessário para rastreabilidade |
| Finalidade | Informar o objetivo do tratamento | Necessário |
| Versão | Identificar a versão do consentimento aceita | Necessário |
| Data do consentimento | Comprovar quando o consentimento foi registrado | Necessário |
| Situação de revogação | Informar se o consentimento está ativo ou revogado | Necessário |
| Data da revogação | Registrar quando ocorreu a revogação | Necessário quando houver revogação |

---

## 2.4 Dados relacionados à auditoria

O modelo `AuditLog` é utilizado para registrar operações importantes realizadas no sistema.

Os dados registrados são:

| Dado | Finalidade | Necessidade |
|---|---|---|
| Usuário | Identificar quem realizou a operação | Necessário para auditoria |
| Evento | Identificar qual operação foi realizada | Necessário |
| Data e hora | Registrar quando a operação ocorreu | Necessário |
| Endereço IP | Auxiliar na segurança e investigação de eventos | Necessário para auditoria |
| Resultado | Informar se a operação teve sucesso ou falha | Necessário |
| Detalhes | Armazenar informações relevantes da operação | Necessário |

Os registros de auditoria são utilizados para garantir rastreabilidade e segurança das operações realizadas no sistema.

---

## 2.5 Dados relacionados aos documentos

O modelo `Documento` permite o armazenamento de documentos relacionados aos participantes.

Os dados são:

| Dado | Finalidade | Necessidade |
|---|---|---|
| Participante | Relacionar o documento ao participante | Necessário |
| Responsável | Identificar o responsável pelo documento | Necessário |
| Nome original | Identificar o documento enviado | Necessário |
| Arquivo | Armazenar o documento | Necessário |
| Data do upload | Registrar quando o documento foi enviado | Necessário |
| Status | Controlar o estado do documento | Necessário |

Documentos que possam conter dados pessoais devem possuir proteção adequada contra acesso não autorizado.

---

## 2.6 Dados relacionados aos acessos

O modelo `Acesso` registra informações relacionadas às permissões concedidas sobre documentos.

Os dados são:

| Dado | Finalidade | Necessidade |
|---|---|---|
| Documento | Identificar o documento que possui acesso | Necessário |
| Usuário | Identificar quem possui acesso | Necessário |
| Usuário que concedeu | Identificar quem concedeu a permissão | Necessário |
| Início do acesso | Definir quando o acesso começa | Necessário |
| Fim do acesso | Definir quando o acesso termina | Necessário |
| Revogado | Identificar se o acesso foi revogado | Necessário |
| Data da revogação | Registrar quando o acesso foi revogado | Necessário quando houver revogação |

---

# 3. Associação de cada dado a uma finalidade

## Requisito 4.2

O ClinSecure utiliza os dados pessoais de acordo com finalidades previamente definidas.

A finalidade determina o motivo pelo qual determinado dado é utilizado pelo sistema.

As principais finalidades são apresentadas abaixo.

### 3.1 Identificação

Dados como:

- nome;
- nome de usuário;
- CPF;

são utilizados para identificar corretamente usuários e participantes.

### 3.2 Autenticação

Os dados utilizados para autenticação permitem verificar a identidade do usuário durante o acesso ao sistema.

São utilizados principalmente:

- nome de usuário;
- e-mail;
- senha;
- informações relacionadas ao segundo fator de autenticação.

### 3.3 Comunicação

O endereço de e-mail é utilizado para comunicação relacionada à conta e para recuperação de senha.

### 3.4 Controle de acesso

O perfil do usuário e os registros de acesso são utilizados para determinar quais operações podem ser realizadas.

### 3.5 Gerenciamento de participantes

Os dados dos participantes são utilizados para permitir seu cadastro e gerenciamento dentro do sistema.

### 3.6 Gerenciamento de consentimentos

Os dados de consentimento permitem registrar:

- finalidade;
- versão;
- data;
- situação;
- revogação.

### 3.7 Segurança

Os registros relacionados a tentativas de login, bloqueios, autenticação de dois fatores e auditoria são utilizados para proteger o sistema contra acessos indevidos.

### 3.8 Auditoria

Os registros de auditoria permitem identificar:

- quem realizou determinada operação;
- qual operação foi realizada;
- quando ocorreu;
- se houve sucesso ou falha;
- informações necessárias para investigação.

### 3.9 Atendimento aos direitos do titular

Os dados também são utilizados para possibilitar o atendimento aos direitos do titular, incluindo:

- consulta;
- exportação;
- revogação do consentimento;
- solicitação de exclusão.

---

# 4. Evidência de minimização de dados

## Requisito 4.3

O princípio da minimização determina que sejam utilizados apenas os dados necessários para atingir uma finalidade definida.

No ClinSecure, cada dado armazenado possui uma finalidade relacionada ao funcionamento, segurança, auditoria ou gerenciamento do sistema.

Exemplos:

- o CPF é utilizado para identificação;
- o e-mail é utilizado para comunicação e recuperação da conta;
- o perfil é utilizado para controle de permissões;
- o nome identifica o participante;
- a data de nascimento é utilizada quando necessária para identificação ou critérios relacionados à pesquisa;
- os dados de consentimento comprovam a autorização;
- os registros de auditoria garantem rastreabilidade.

O sistema não deve coletar dados que não possuam finalidade definida.

Também são adotadas medidas para evitar exposição desnecessária de informações.

A senha não deve ser apresentada ao titular.

Informações secretas utilizadas pelo segundo fator de autenticação também não devem ser exibidas ou exportadas.

Dessa forma, o sistema diferencia os dados necessários para o exercício dos direitos do titular das informações técnicas necessárias exclusivamente para a segurança da aplicação.

---

# 5. Registro explícito de consentimento

## Requisito 4.4

O ClinSecure possui mecanismo para registrar o consentimento do titular.

O consentimento deve ser obtido de forma explícita, permitindo que o titular manifeste sua concordância antes do tratamento relacionado à finalidade apresentada.

No cadastro, o sistema deverá apresentar uma opção específica para que o titular confirme seu consentimento.

O consentimento não deve ser considerado válido quando a opção obrigatória não tiver sido aceita.

O fluxo previsto é:

1. O usuário preenche os dados necessários.
2. O sistema apresenta a finalidade do tratamento.
3. O usuário visualiza as informações do consentimento.
4. O usuário confirma explicitamente sua concordância.
5. O sistema registra o consentimento.
6. O sistema registra a finalidade.
7. O sistema registra a versão.
8. O sistema registra a data e hora.
9. O registro fica disponível para auditoria.

---

# 6. Consentimento associado à finalidade

## Requisito 4.5

O consentimento deve estar associado a uma finalidade específica.

O modelo `Consentimento` possui o campo `finalidade`, permitindo identificar o objetivo para o qual o consentimento foi concedido.

Exemplo de finalidade:

> Gerenciamento e participação em pesquisa clínica.

A finalidade é armazenada juntamente com o consentimento.

Isso permite identificar posteriormente:

- qual finalidade foi apresentada;
- qual versão foi aceita;
- quando o consentimento ocorreu;
- se o consentimento continua ativo;
- se o consentimento foi revogado.

O sistema não deve utilizar um consentimento genérico para finalidades diferentes sem que elas estejam devidamente identificadas.

---

# 7. Registro da data e versão do consentimento

## Requisito 4.7

Cada registro de consentimento deve possuir informações suficientes para identificar o momento e a versão do documento ou termo aceito.

O modelo `Consentimento` possui:

- `versao`;
- `data_consentimento`;
- `revogado`;
- `data_revogado`.

A versão permite identificar qual versão do consentimento foi aceita.

A data de consentimento permite identificar quando o registro foi criado.

Quando ocorrer uma revogação, a data da revogação também deve ser registrada.

Exemplo:

| Informação | Exemplo |
|---|---|
| Finalidade | Gerenciamento de pesquisa clínica |
| Versão | 1.0 |
| Data | 10/09/2026 14:30 |
| Status | Ativo |
| Data de revogação | Não aplicável |

Após uma revogação:

| Informação | Exemplo |
|---|---|
| Finalidade | Gerenciamento de pesquisa clínica |
| Versão | 1.0 |
| Data | 10/09/2026 14:30 |
| Status | Revogado |
| Data de revogação | 15/09/2026 10:20 |

---

# 8. Possibilidade de revogação do consentimento

## Requisito 4.6

O titular deve possuir a possibilidade de revogar um consentimento anteriormente concedido.

A revogação não deve apagar automaticamente o histórico do consentimento.

Em vez disso, o registro deve ser atualizado para indicar que foi revogado.

O fluxo de revogação será:

1. O titular acessa sua conta.
2. Acessa a área de seus dados.
3. Visualiza seus consentimentos.
4. Seleciona o consentimento que deseja revogar.
5. Confirma a operação.
6. O sistema altera o campo `revogado` para verdadeiro.
7. O sistema registra a data da revogação.
8. O sistema registra a operação no `AuditLog`.

A manutenção do histórico permite demonstrar que o consentimento existiu e posteriormente foi revogado.

---

# 9. Consulta aos dados do titular

## Requisito 4.8

O ClinSecure deverá disponibilizar uma funcionalidade para que o titular consulte os dados pessoais relacionados à sua conta.

A funcionalidade será disponibilizada em uma área denominada:

> Meus Dados

A página deverá apresentar os dados pessoais de forma organizada.

Entre as informações que poderão ser apresentadas estão:

- nome de usuário;
- e-mail;
- CPF;
- perfil;
- dados do participante, quando relacionados;
- consentimentos;
- finalidade dos consentimentos;
- versão dos consentimentos;
- data dos consentimentos;
- situação dos consentimentos;
- datas de revogação, quando existentes.

Informações de segurança não devem ser apresentadas.

Por exemplo:

- senha;
- chave secreta do 2FA;
- informações internas utilizadas para proteção contra força bruta.

O objetivo é permitir que o titular tenha transparência sobre os dados pessoais armazenados sem comprometer a segurança da conta.

---

# 10. Exportação dos dados

## Requisito 4.9

O ClinSecure deverá disponibilizar uma funcionalidade para exportação dos dados pessoais do titular.

A exportação deverá utilizar um formato estruturado e de fácil processamento.

## Requisito 4.11

O ClinSecure possui um fluxo definido para atendimento aos direitos do titular.

O fluxo geral é:

                 TITULAR
                    |
                    v
              Acessa a conta
                    |
                    v
               MEUS DADOS
                    |
        +-----------+-----------+
        |           |           |
        v           v           v
     Consulta    Exportação   Consentimento
        |           |           |
        |           |           v
        |           |       Revogação
        |           |           |
        +-----------+-----------+
                    |
                    v
              Exclusão
                    |
                    v
              Processamento
                    |
                    v
              AuditLog
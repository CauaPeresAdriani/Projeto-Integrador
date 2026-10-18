# BCP/DRP — Continuidade e Recuperação de Desastres

## 1. Objetivo

Definir objetivos de recuperação, proteção da chave de criptografia e procedimentos recomendados para restaurar o banco de dados do ClinSecure em caso de falha ou perda de dados.

## 2. Arquitetura e limitações atuais

- Aplicação: Django.
- Banco de dados: MySQL hospedado no Railway.
- Instância: única, sem réplica ou failover automático.
- Criptografia de campos: utiliza a variável `FIELD_ENCRYPTION_KEY`.
- Backups automáticos: não configurados.
- Recuperação: depende da disponibilidade de uma cópia válida do banco e da chave de criptografia. **Recomendação futura:** armazenar as cópias de backup do banco em local externo seguro, com retenção mínima de 30 dias e rotina periódica (ex.: backups diários), ainda não implementada.


Os procedimentos deste documento são recomendações. A existência de um plano documentado não significa que os backups ou a recuperação automatizada já estejam implementados ou testados.

## 3. Objetivos de recuperação

**RPO — Recovery Point Objective**

- Meta proposta: até 24 horas de perda de dados.
- Interpretação: após a implantação de backups diários, a recuperação deverá utilizar uma cópia com, idealmente, no máximo 24 horas de defasagem.
- Situação atual: não garantido. Como não há backup automático configurado, a perda potencial de dados não possui um limite confiável.

**RTO — Recovery Time Objective**

- Meta proposta: até 8 horas para restabelecer o sistema após um incidente.
- Interpretação: período entre a identificação do incidente e a recuperação do acesso à aplicação e aos dados necessários.
- Situação atual: não garantido. O tempo real depende da natureza da falha, da disponibilidade dos backups, da infraestrutura e da validação da restauração.

Essas metas são referências para o projeto acadêmico e deverão ser revisadas após testes de recuperação.

## 4. Backup da FIELD_ENCRYPTION_KEY

A variável `FIELD_ENCRYPTION_KEY` é necessária para descriptografar os campos protegidos pela aplicação. A perda ou substituição indevida da chave pode tornar os dados existentes inacessíveis.

### Procedimento recomendado

1. Identificar a chave atualmente utilizada pela aplicação e confirmar que corresponde ao ambiente correto.
2. Armazenar uma cópia segura em um gerenciador de senhas confiável, como um cofre protegido no Bitwarden.
3. Restringir o acesso às pessoas autorizadas e manter a autenticação multifator habilitada no gerenciador, quando disponível.
4. Manter a chave fora do código-fonte, do GitHub, de arquivos de documentação, de logs e de backups desprotegidos.
5. Registrar, sem incluir o valor da chave, onde a cópia está armazenada e quem está autorizado a recuperá-la.
6. Verificar periodicamente se a chave pode ser recuperada pelo procedimento de acesso autorizado.

**Cuidados importantes:**

- Não gerar uma nova chave para substituir a original sem um procedimento planejado de migração ou recriptografia.
- Não compartilhar a chave junto com uma cópia desprotegida do banco.
- Em uma recuperação, utilizar a chave correspondente aos dados criptografados.
- Se a chave original for perdida, um backup do banco, isoladamente, pode não ser suficiente para recuperar os dados criptografados.

## 5. Procedimento de restauração do MySQL

A restauração deve ser realizada por uma pessoa autorizada e, inicialmente, em um ambiente isolado, sem conexão com o banco de produção.

### Etapa 1 — Preparação

1. Identificar o incidente e avaliar a integridade do banco.
2. Localizar o backup disponível mais recente e verificar sua procedência e integridade.
3. Recuperar a `FIELD_ENCRYPTION_KEY` correspondente ao ambiente e aos dados.
4. Confirmar a compatibilidade entre a versão do MySQL, o formato do backup e a versão da aplicação.
5. Registrar a data do backup escolhido e o impacto potencial sobre os dados posteriores a ele.

### Etapa 2 — Restauração isolada

1. Preparar uma instância de teste separada da produção.
2. Restaurar a cópia do banco nesse ambiente isolado, utilizando o procedimento compatível com o formato do backup.
3. Configurar a aplicação de teste com as variáveis de ambiente corretas e a chave original correspondente.
4. Validar a estrutura do banco, a integridade dos dados e a capacidade de descriptografar os campos protegidos.
5. Testar autenticação, permissões, consultas e funcionalidades essenciais da aplicação.
6. Registrar os resultados e os problemas encontrados.

### Etapa 3 — Recuperação do serviço

A restauração em produção somente deverá ocorrer após avaliação do incidente, autorização e definição de uma janela de manutenção.

Antes de iniciar
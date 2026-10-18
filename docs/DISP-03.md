# HA / Backup do MySQL

## 1. Arquitetura atual
- MySQL 9  como addon da Railway (instância única, `DB_HOST` apontando para um host interno).
- Conexão Django configurada via variáveis de ambiente (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).
- Dados armazenados em volume anexado ao serviço.
- Não há réplica, cluster ou proxy; a aplicação depende de um único contêiner.

## 2. Risco associado (SPOF)
- Falha do contêiner MySQL traz indisponibilidade total da aplicação.
- Perda de dados caso o volume seja corrompido antes de um backup.
- O projeto não possui backups automáticos configurados; a migração para um cluster implicaria custos adicionais.

## 3. Backup × Replica × Alta Disponibilidade
| Tipo | O que faz | Situação no projeto |
|------|-----------|---------------------|
| **Backup** | Exporta um dump estático (texto ou binário) | Manual – procedimento descrito abaixo |
| **Replica** | Mantém cópia sincronizada em tempo real | Não existe |
| **Alta Disponibilidade** | Combina réplicas + fail‑over automático | Não existe |

## 4. Custos e restrições
- Não será criado nenhum serviço pago nem alterado o plano de hospedagem.
- Nenhum custo adicional será gerado.

## 5. Risco residual
> O risco de indisponibilidade permanece até que seja implementada HA ou backups automáticos.

## 6. Estratégia de backup e recuperação

Atualmente, o projeto não possui backups automáticos configurados.

Recomenda-se realizar backups manuais periódicos do MySQL, armazenando as cópias em local externo, com criptografia e acesso restrito.

A recuperação deve ser validada por meio de testes em ambiente isolado, sem afetar o banco de produção.

## 7. Retenção e armazenamento

Como recomendação futura, sugere-se realizar backups diários, manter uma retenção de 30 dias e armazenar as cópias de forma segura, fora do ambiente principal.

Essas medidas ainda não estão implementadas.

## 8. Trabalhos futuros

A ausência de alta disponibilidade mantém o banco como ponto único de falha (SPOF). Backups podem reduzir o impacto da perda de dados, mas não garantem a continuidade imediata da aplicação.

A implementação de backups automatizados e de alta disponibilidade poderá ser avaliada futuramente, conforme a disponibilidade de orçamento.
## 9. Estado atual
- Não há nenhum mecanismo de backup automático configurado nem scripts de backup em produção.
- O documento descreve uma estratégia recomendada de backup e recuperação.

## 10. Próximos passos para HA (quando houver orçamento)
- Avaliar replicação nativa (Group Replication) ou migração para um serviço gerenciado com alta disponibilidade.
- Definir estratégia de fail‑over (proxy, DNS health‑check, etc.).
- Automatizar backups e rotação via cron/CI/CD.

## 11. Referências
- Django settings: https://docs.djangoproject.com/en/5.2/topics/settings/
- mysqldump: https://dev.mysql.com/doc/refman/8.0/en/mysqldump.html
- GPG: https://www.gnupg.org/documentation/
- Railway CLI: https://docs.railway.app/cli/database

---
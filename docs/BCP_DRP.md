# Plano de Continuidade de Negócio (BCP) e Recuperação de Desastres (DRP) – ClinSecure

## 1. Objetivo
Garantir a disponibilidade e a integridade dos dados do ClinSecure frente a falhas de infraestrutura, perda de chaves criptográficas ou incidentes de segurança.

## 2. Escopo
- Banco de dados MySQL hospedado no Railway.
- Chave de criptografia de campo `FIELD_ENCRYPTION_KEY`.
- Configurações de aplicação (settings, arquivos de ambiente).

## 3. RPO / RTO
| Item | Valor definido |
|------|-----------------|
| **Recovery Point Objective (RPO)** | Até **24 h** de perda de dados (após implementação de backups diários). |
| **Recovery Time Objective (RTO)** | Até **8 h** para restabelecer a aplicação e a base de dados.

## 4. Procedimentos de Backup
### 4.1 Backup do banco MySQL
```bash
#!/usr/bin/env bash
# scripts/backup_mysql.sh
set -euo pipefail
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="/tmp/clinsecure_mysql_${TIMESTAMP}.sql"
mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" clinsecure > "$DUMP_FILE"
# Criptografa o dump para armazenamento seguro
python - <<PY
import os, sys
from cryptography.fernet import Fernet
key = os.getenv('FIELD_ENCRYPTION_KEY')
if not key:
    sys.exit('FIELD_ENCRYPTION_KEY not set')
fernet = Fernet(key)
with open('$DUMP_FILE', 'rb') as f:
    data = f.read()
enc = fernet.encrypt(data)
with open("$DUMP_FILE.enc", 'wb') as f:
    f.write(enc)
os.remove('$DUMP_FILE')
PY
# Mover para armazenamento externo (ex: bucket S3 ou servidor de backup)
# scp "$DUMP_FILE.enc" backup_user@backup.server:/backups/clinsecure/
```
- **Frequência**: diário (via cron ou scheduler CI).
- **Retenção**: 30 dias.
- **Verificação**: após cada backup, executar `python -c "from cryptography.fernet import Fernet; import os; key=os.getenv('FIELD_ENCRYPTION_KEY'); f=Fernet(key); f.decrypt(open('$DUMP_FILE.enc','rb').read())"` para garantir a integridade.

### 4.2 Backup da chave `FIELD_ENCRYPTION_KEY`
- A chave deve ser armazenada **exclusivamente** em um cofre de segredos (Bitwarden, 1Password, Vault, etc.).
- Exportar a chave para um arquivo criptografado somente quando necessário (ex.: recuperação).
- Documentar responsáveis e procedimentos de acesso no próprio cofre.

## 5. Procedimento de Recuperação
1. **Restaurar a chave** – recuperar a `FIELD_ENCRYPTION_KEY` do cofre e exportá‑la para a variável de ambiente.
2. **Restaurar o dump** – desencriptar o arquivo e importar no MySQL:
```bash
python - <<PY
import os, sys
from cryptography.fernet import Fernet
key = os.getenv('FIELD_ENCRYPTION_KEY')
if not key:
    sys.exit('FIELD_ENCRYPTION_KEY not set')
fernet = Fernet(key)
with open('/tmp/clinsecure_mysql_latest.sql.enc','rb') as f:
    enc = f.read()
plain = fernet.decrypt(enc)
with open('/tmp/clinsecure_mysql_latest.sql','wb') as f:
    f.write(plain)
PY
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" clinsecure < /tmp/clinsecure_mysql_latest.sql
```
3. **Deploy da aplicação** – garantir que o `.env` contenha a mesma chave e as mesmas credenciais de BD.
4. **Validar** – executar script de smoke‑test (`python manage.py check` e alguns endpoints) para confirmar que a aplicação está operando.

## 6. Responsáveis
| Função | Responsável |
|--------|------------|
| Gerente de Segurança | **[Nome]** |
| Administrador de Banco | **[Nome]** |
| Operações de Backup | **[Nome]** |

## 7. Testes de DR
- Realizar exercício de recuperação ao menos **semestralmente**.
- Registrar resultados, tempos e lições aprendidas.
- Atualizar o plano conforme necessário.

---
*Este documento complementa o `docs/DISP-06.md` já existente, detalhando procedimentos operacionais e scripts de backup.*

#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Backup do banco MySQL do ClinSecure com criptografia da
# chave de campo (FIELD_ENCRYPTION_KEY).  O script presume que
# as variáveis de ambiente DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
# e FIELD_ENCRYPTION_KEY estejam definidas.
# ------------------------------------------------------------

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="/tmp/clinsecure_mysql_${TIMESTAMP}.sql"
ENC_FILE="${DUMP_FILE}.enc"

# 1. Dump do MySQL
mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" clinsecure > "$DUMP_FILE"

# 2. Criptografa o dump com Fernet
python - <<PY
import os, sys
from cryptography.fernet import Fernet
key = os.getenv('FIELD_ENCRYPTION_KEY')
if not key:
    sys.exit('FIELD_ENCRYPTION_KEY não definida')
fernet = Fernet(key)
with open('$DUMP_FILE', 'rb') as f:
    data = f.read()
enc = fernet.encrypt(data)
with open('$ENC_FILE', 'wb') as f:
    f.write(enc)
PY

# 3. Remove o dump em texto plano
rm -f "$DUMP_FILE"

echo "Backup criptografado salvo em $ENC_FILE"


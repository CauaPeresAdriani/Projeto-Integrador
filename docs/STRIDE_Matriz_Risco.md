# Análise STRIDE e Matriz de Risco – ClinSecure

## 1. STRIDE

| Categoria | Ameaça | Vetor | Impacto no ClinSecure |
|----------|--------|-------|-----------------------|
| **Spoofing** | Roubo de credenciais (login, 2FA) | Phishing, vazamento de senha | Acesso não‑autorizado a dados sensíveis |
| **Tampering** | Alteração de registros de auditoria via acesso direto ao banco | Acesso privilegiado ao MySQL | Perda de integridade das evidências (INTEG‑01) |
| **Repudiation** | Falta de cadeia de hashes completa nos logs | Falha de auditoria | Impossibilidade de provar ações realizadas |
| **Information Disclosure** | Exposição da chave Fernet ou do `FIELD_ENCRYPTION_KEY` | Comprometimento de segredo | Dados criptografados tornam‑se legíveis |
| **Denial of Service** | Ataques de flood sem rate‑limiting (DISP‑01) ou `time.sleep` síncrono (DISP‑02) | Massivo número de requisições | Indisponibilidade temporária do serviço |
| **Elevation of Privilege** | Uso do Django Admin sem controles (CONF‑04) | Conta super‑usuário | Execução de operações sensíveis sem restrição |

## 2. Matriz de Risco

| ID | Vulnerabilidade | Probabilidade | Impacto | Severidade (P×I) |
|----|------------------|---------------|--------|-------------------|
| DISP‑01 | Ausência de rate limiting por IP | Alta | Alto | **Crítico** |
| DISP‑02 | `time.sleep()` síncrono | Alta | Alto | **Crítico** |
| CONF‑01 | Chave Fernet única sem rotação | Média | Crítico | **Alto** |
| CONF‑04 | Django Admin ativo sem controle | Média | Alto | **Alto** |
| INTEG‑01 | AuditLog bypassável via SQL direto | Baixa | Alto | **Alto** |
| DISP‑05 | Dependência exclusiva da API Brevo | Média | Alto | **Alto** |
| DISP‑04 | Perda da chave Fernet = dados irrecuperáveis | Baixa | Crítico | **Alto** |
| INTEG‑05 | Falta de verificação de CPF duplicado | Alta | Médio | **Médio** |
| CONF‑02 | Enumeração de usuários na recuperação de senha | Média | Médio | **Médio** |
| CONF‑06 | Cabeçalhos HTTP de segurança ausentes (CSP) | Alta | Médio | **Médio** |
| CONF‑05 | Configurações de segurança condicionadas ao DEBUG | Média | Médio | **Médio** |
| INTEG‑06 | Registro TEMP – janela de inconsistência | Baixa | Médio | **Médio** |
| DISP‑03 | MySQL sem HA/replica documentada | Baixa | Alto | **Médio** |
| CONF‑03 | Campo `secret_key` TOTP em plaintext | Baixa | Médio | **Médio** |
| INTEG‑03 | Retorno `None` implícito em `permissions.py` | Baixa | Baixo | **Baixo** |
| INTEG‑02 | Decorator `@login_required` duplicado | Desprezível | Baixo | **Baixo** |
| INTEG‑04 | Sem limite de tamanho em campos livres | Baixa | Baixo | **Baixo** |

*Observação*: A matriz segue a convenção “Probabilidade × Impacto”. Valores **Alta**, **Média**, **Baixa** são qualitativos; a severidade resultante classifica‑se em **Crítico**, **Alto**, **Médio**, **Baixo**.

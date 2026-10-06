# Documentação de Modificação: Controle de Taxa e Prevenção de Bloqueio

**Commit:** [`653267851b79171dd3f89affebee0ff830ab4f94`](https://github.com/CauaPeresAdriani/Projeto-Integrador/commit/653267851b79171dd3f89affebee0ff830ab4f94)

## 1. Visão Geral
Esta atualização remove o uso de `time.sleep()` em rotas sensíveis e implementa uma nova mecânica para lidar com múltiplas tentativas de requisição, baseada no envio de respostas HTTP com limitação de taxa (Rate Limiting).

## 2. Contexto e Motivação
* **Risco Mitigado:** `DISP-02`
* **Problema Original:** O uso prévio de `time.sleep(n_tentativas)` causava o bloqueio da thread da aplicação no servidor. Em situações de pico ou de um ataque de força bruta, a paralisação de várias threads poderia esgotar os recursos do sistema, causando lentidão, instabilidade ou até indisponibilidade completa da aplicação.

## 3. Solução Implementada
A solução substitui o atraso síncrono por um controle de tráfego por IP/Usuário (utilizando ferramentas do ecossistema Django, como `django-ratelimit` ou `django-axes`).

Quando as requisições excedem o limite tolerável, o servidor não paralisa mais a thread. Em vez disso, responde imediatamente informando o cliente de que o limite de requisições foi excedido, aplicando a convenção correta de semântica HTTP.

### Alteração no Código:
O atraso progressivo foi transferido para a responsabilidade do cliente, informando-o através da resposta do servidor:

**Antes da alteração:**
```python
import time

# Atrasava toda a thread do sistema em caso de requisições repetidas
time.sleep(n_tentativas)
```

**Depois da alteração:**
```python
from django.http import HttpResponse

# A thread é imediatamente liberada
# Retorna 429 Too Many Requests indicando o atraso progressivo no header
response = HttpResponse("Muitas tentativas.", status=429)
response['Retry-After'] = str(n_tentativas)
return response
```

## 4. Impactos e Benefícios
1. **Performance da Aplicação:** As threads da aplicação agora respondem rapidamente e são imediatamente liberadas para atender outros usuários, aumentando o throughput.
2. **Padrões da Web (HTTP):** A utilização do status `HTTP 429 (Too Many Requests)` e a inclusão do header `Retry-After` seguem rigorosamente as boas práticas de APIs e desenvolvimento web.
3. **Escalabilidade & Segurança:** A aplicação agora possui defesas mais eficientes contra sobrecarga por bots ou usuários sem penalizar o servidor, protegendo melhor os endpoints contra exaustão de recursos.
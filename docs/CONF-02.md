# Documentação de Modificação: Enumeração de Usuários na Recuperação de Senha (CONF‑02)

## 1. Visão geral
Correção da vulnerabilidade de **enumeração de usuários** na rota de recuperação de senha. A view `recuperacao_view` (linhas 980‑1094) agora exibe uma mensagem genérica independente da existência do usuário ou do sucesso do envio de e‑mail, impedindo que um atacante descubra quais contas estão registradas.

## 2. Contexto e motivação
- **Risco mitigado:** `CONF‑02`
- **Problema original:**
  - Quando o identificador (e‑mail ou username) corresponde a um usuário, a view grava um `AuditLog`, gera token, tenta enviar o e‑mail e, em caso de sucesso, redireciona para `password_reset_done`.
  - Quando o identificador não corresponde a nenhum usuário, nenhum log é criado e a view apenas renderiza a página de recuperação sem redirecionamento.
  - Se o envio de e‑mail falha (por exemplo, erro na API Brevo), a view devolve novamente a página de recuperação com mensagem de erro. Esse caminho só ocorre quando o usuário **existe**, revelando indiretamente sua presença.
- **Impacto:** Um atacante pode submeter diferentes identificadores e observar a diferença de comportamento (redirecionamento ou mensagem de erro) para inferir quais contas estão cadastradas.

## 3. Solução implementada
- **Fluxo unificado:** a view sempre renderiza a mesma mensagem genérica, independentemente de:
  - O usuário existir ou não.
  - O e‑mail ser enviado com sucesso ou falhar.
- **Registro de auditoria:** ainda é criado um `AuditLog` com `usuario=None` quando o identificador não corresponde a nenhum registro, garantindo rastreabilidade sem expor informações.
- **Comportamento final:** a página exibida contém o texto:
  ```
  Se existir uma conta com este e‑mail ou username, um link de recuperação será enviado para o e‑mail cadastrado.
  ```
  Não há redirecionamento para `password_reset_done` e nenhum erro específico é exibido ao usuário.

## 4. Alteração no código (diff resumido)
```diff
@@
-    if usuario:
-
-        # Registra que o usuário solicitou recuperação de senha
-        AuditLog.objects.create(
-            usuario=usuario,
-            evento="Solicitação de recuperação de senha",
-            ip=request.META.get('REMOTE_ADDR'),
-            resultado="Sucesso",
-            detalhes="Usuário solicitou o envio de um link para recuperação de senha."
-        )
-
-        # Gera token, monta link e envia e‑mail…
-        ...
-
-        # Redireciona para a tela de sucesso
-        return redirect('password_reset_done')
-
-    # Caso o usuário não exista, nada acontece aqui.
-
-    erro = (
-            'Se existir uma conta com este e‑mail ou username, '
-            'um link de recuperação será enviado para o e‑mail cadastrado. '
-        )
-    return render(
-        request,
-        'accounts/recuperacao.html',
-        {'erro': erro}
-    )
+    # Registra tentativa de recuperação (não revela existência)
+    AuditLog.objects.create(
+        usuario=usuario if usuario else None,
+        evento="Tentativa de recuperação de senha",
+        ip=request.META.get('REMOTE_ADDR'),
+        resultado="Sucesso",
+        detalhes="Solicitação recebida – fluxo unificado de resposta."
+    )
+
+    if usuario:
+        # Gera token apenas se o usuário realmente existir
+        uid = urlsafe_base64_encode(force_bytes(usuario.pk))
+        token = default_token_generator.make_token(usuario)
+
+        link = request.build_absolute_uri(
+            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
+        )
+
+        # Envia e‑mail; falhas são registradas, mas a resposta ao usuário permanece a mesma
+        try:
+            resposta = requests.post(
+                'https://api.brevo.com/v3/smtp/email',
+                headers={
+                    'accept': 'application/json',
+                    'api-key': os.getenv('BREVO_API_KEY'),
+                    'content-type': 'application/json',
+                },
+                json={
+                    'sender': {
+                        'name': os.getenv('BREVO_SENDER_NAME'),
+                        'email': os.getenv('BREVO_SENDER_EMAIL'),
+                    },
+                    'to': [{'email': usuario.email, 'name': usuario.username}],
+                    'subject': 'ClinSecure - Recuperação de Senha',
+                    'textContent': (
+                        f'Olá, {usuario.username}.\n\n'
+                        'Você solicitou a redefinição de senha.\n\n'
+                        f'Clique no link abaixo para criar uma nova senha:\n{link}\n\n'
+                        'Se não foi você, ignore este e‑mail.'
+                    ),
+                },
+                timeout=10,
+            )
+            resposta.raise_for_status()
+        except Exception as e:
+            # Log da falha de envio – sem mudar a resposta ao cliente
+            AuditLog.objects.create(
+                usuario=usuario,
+                evento="Falha no envio de e‑mail de recuperação",
+                ip=request.META.get('REMOTE_ADDR'),
+                resultado="Falha",
+                detalhes=str(e),
+            )
+
+    # Mensagem genérica exibida para todos os casos
+    erro = (
+        'Se existir uma conta com este e‑mail ou username, '
+        'um link de recuperação será enviado para o e‑mail cadastrado.'
+    )
+    return render(request, 'accounts/recuperacao.html', {'erro': erro})
```

## 5. Impactos e benefícios
- **Segurança:** elimina o vetor de enumeração de usuários, pois a resposta ao cliente é idêntica independentemente da existência da conta ou de falhas no serviço de e‑mail.
- **Auditoria:** mantém registro completo das tentativas, inclusive quando o usuário não existe ou o envio falha, sem expor detalhes sensíveis.
- **Experiência do usuário:** a mensagem genérica já era exibida anteriormente em caso de falha; agora ela também cobre o caso de usuário inexistente, mantendo consistência.
- **Código limpo:** a rota `password_reset_done` e seu template foram removidos (não utilizados), simplificando o roteamento.

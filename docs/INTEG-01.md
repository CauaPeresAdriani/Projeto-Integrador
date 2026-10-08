# INTEG-01 – Cadeia de hashes em AuditLog

## 1. Visão geral
Implementação de um mecanismo de integridade em `AuditLog` que cria uma cadeia de hashes (tipo blockchain simplificado). Cada registro armazena o hash do registro anterior (`hash_anterior`) e um hash de integridade (`hash_integridade`) que inclui esse valor, permitindo detectar adulteração de logs.

## 2. Contexto e motivação
- **Risco mitigado:** `INTEG-01`
- **Problema original:** O modelo `AuditLog` gravava apenas um hash calculado a partir dos próprios campos do registro. Um atacante poderia inserir ou modificar um log e gerar um hash válido, já que o cálculo não incluía o histórico de eventos.
- **Necessidade:** Garantir que toda a sequência de logs seja verificável, dificultando alterações não detectadas e reforçando a auditoria de segurança.

## 3. Solução implementada
- **Novos campos no modelo `AuditLog`** (arquivo `accounts/models.py`):
  ```python
  hash_anterior = models.CharField(
      max_length=64,
      editable=False,
      default='0' * 64,
      help_text="Hash do registro anterior, formando a cadeia."
  )

  hash_integridade = models.CharField(
      max_length=64,
      editable=False,
      help_text="Hash de integridade que inclui o hash_anterior."
  )
  ```
- **Método `save()` reescrito** para garantir que `data_hora` (auto_now_add) esteja preenchido antes do cálculo e para evitar duas chamadas desnecessárias a `super().save`:
  ```python
  def save(self, *args, **kwargs):
      # Impede edição de logs já existentes
      if self.pk is not None and AuditLog.objects.filter(pk=self.pk).exists():
          raise ValueError("Alteração não permitida")

      # Primeira gravação → preenche data_hora
      super().save(*args, **kwargs)

      # Busca o último log (agora que este já tem id)
      ultimo = AuditLog.objects.order_by('-id').first()
      self.hash_anterior = ultimo.hash_integridade if ultimo else '0' * 64

      # Monta o conteúdo que será hashado
      conteudo = f"{self.evento}{self.data_hora}{self.resultado}{self.hash_anterior}"
      self.hash_integridade = hashlib.sha256(conteudo.encode()).hexdigest()

      # Atualiza apenas os campos de hash
      AuditLog.objects.filter(pk=self.pk).update(
          hash_anterior=self.hash_anterior,
          hash_integridade=self.hash_integridade,
      )
  ```
- **Imutabilidade mantida** – o método `delete` ainda levanta `ValueError`, impedindo exclusão de logs.

## 4. Alteração no código (diff resumido)
```diff
+    hash_anterior = models.CharField(
+        max_length=64,
+        editable=False,
+        default='0' * 64,
+        help_text="Hash do registro anterior, formando a cadeia."
+    )
+
+    hash_integridade = models.CharField(
+        max_length=64,
+        editable=False,
+        help_text="Hash de integridade que inclui o hash_anterior."
+    )
-
-    def save(self, *args, **kwargs):
-        if self.pk is not None:
-            if AuditLog.objects.filter(pk=self.pk).exists():
-                raise ValueError("Alteração nao permitida")
-
-        super().save(*args, **kwargs)
-        super().save(*args, **kwargs)
+    def save(self, *args, **kwargs):
+        if self.pk is not None and AuditLog.objects.filter(pk=self.pk).exists():
+            raise ValueError("Alteração não permitida")
+
+        super().save(*args, **kwargs)  # cria registro e preenche data_hora
+
+        ultimo = AuditLog.objects.order_by('-id').first()
+        self.hash_anterior = ultimo.hash_integridade if ultimo else '0' * 64
+        conteudo = f"{self.evento}{self.data_hora}{self.resultado}{self.hash_anterior}"
+        self.hash_integridade = hashlib.sha256(conteudo.encode()).hexdigest()
+
+        AuditLog.objects.filter(pk=self.pk).update(
+            hash_anterior=self.hash_anterior,
+            hash_integridade=self.hash_integridade,
+        )
```

## 5. Impactos e benefícios
- **Detecção de adulteração:** Qualquer modificação ou inserção fora da sequência quebra a correspondência entre `hash_anterior` e `hash_integridade`, permitindo auditoria automática.
- **Imutabilidade preservada:** `save()` ainda impede edição/exclusão de logs já persistidos.
- **Baixo overhead:** Apenas uma consulta adicional (`order_by('-id').first()`) por inserção de log.
- **Compatibilidade com migrações:** Campo `hash_anterior` tem default; `hash_integridade` recebe valor na primeira gravação, permitindo migração sem impactos.
- **Sem alterações de API:** As chamadas existentes `AuditLog.objects.create(...)` continuam funcionando sem mudanças.

## 6. Referências
- Commit que introduz a mudança: **[a definir após o commit]**
- Documentação de auditoria pré‑existente: `docs/Documentação_fix_CIA.md`

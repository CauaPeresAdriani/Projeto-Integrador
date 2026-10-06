Backup e Restauração da FIELD_ENCRYPTION_KEY
Objetivo
Documentar o procedimento de backup e restauração da chave de
criptografia utilizada pelo ClinSecure, reduzindo os riscos de
indisponibilidade e perda de acesso aos dados criptografados.
A chave utilizada em produção permanece configurada como variável de
ambiente no Railway.
Armazenamento da chave
A FIELD_ENCRYPTION_KEY é utilizada pela aplicação através de variável
de ambiente e não deve ser armazenada no código-fonte ou no repositório
Git.
Atualmente, a chave possui dois pontos de armazenamento:
- Railway: armazenamento operacional utilizado pela aplicação em
  produção.
- Bitwarden: cópia de backup mantida em cofre separado para
  recuperação.


A cópia de recuperação da FIELD_ENCRYPTION_KEY foi armazenada em um
cofre seguro no Bitwarden.
O backup deve permanecer protegido contra acesso não autorizado e não
deve ser compartilhado em:
- commits;
- arquivos .env versionados;
- documentação pública;
- mensagens ou chats;
- banco de dados;
- issues ou pull requests.
Procedimento de restauração
Caso a FIELD_ENCRYPTION_KEY seja perdida ou removida das variáveis do
Railway:
1. Acessar o cofre autorizado no Bitwarden.
2. Localizar o registro da FIELD_ENCRYPTION_KEY do ambiente de
   produção.
3. Copiar o valor armazenado no cofre.
4. Acessar o projeto do ClinSecure no Railway.
5. Abrir as variáveis de ambiente do serviço responsável pela aplicação.
6. Restaurar o valor da variável FIELD_ENCRYPTION_KEY.
7. Salvar a alteração e realizar o redeploy/reinicialização da aplicação,
   quando necessário.
8. Executar os testes de funcionamento da aplicação.
9. Validar uma operação que dependa da descriptografia dos dados
   protegidos.
10. Confirmar que os dados anteriormente criptografados continuam
    acessíveis.
Cuidados durante a restauração
A chave deve ser tratada como segredo crítico.
Não gerar uma nova FIELD_ENCRYPTION_KEY simplesmente para substituir
uma chave perdida quando já existem dados criptografados com a chave
anterior. Uma nova chave não descriptografa automaticamente os dados
protegidos pela chave anterior.
Em caso de suspeita de comprometimento da chave, a troca da chave deve
ser tratada como um procedimento de rotação de chaves, com planejamento
específico para migração/recriptografia dos dados afetados.
Verificação pós-restauração
Após restaurar a variável no Railway, verificar:
- aplicação iniciando normalmente;
- conexão com o banco de dados;
- leitura de dados criptografados;
- descriptografia correta dos campos protegidos;
- funcionamento dos fluxos que dependem desses campos;
- ausência de erros relacionados à chave nos logs da aplicação.
Responsabilidade e acesso
O acesso à cópia de backup deve ser restrito às pessoas autorizadas a
administrar o ambiente do ClinSecure.
A chave não deve ser exposta em logs, screenshots, documentação,
commits ou respostas de ferramentas de diagnóstico.
Relação com a Ação 4
Esta documentação implementa a solução de curto prazo definida para os
riscos CONF-01 e DISP-04:
Gerar backup seguro da FIELD_ENCRYPTION_KEY em cofre separado e
documentar o procedimento de restauração.

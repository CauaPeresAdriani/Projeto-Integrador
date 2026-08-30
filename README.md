# ClinSecure Docs
## Sistema Seguro de Gestão de Pesquisas Clínicas e Dados de Participantes
O ClinSecure é uma plataforma web desenvolvida para o gerenciamento seguro de pesquisas clínicas e dos dados de seus participantes.

Atualmente, muitas equipes de pesquisa ainda utilizam planilhas, e-mails e sistemas desconectados para organizar informações de participantes. Essa prática pode gerar riscos de vazamento de dados, falta de controle de acesso, dificuldade no gerenciamento de consentimentos e ausência de rastreabilidade das ações realizadas.

O ClinSecure busca solucionar esse problema centralizando o cadastro de pesquisas, gerenciamento de consentimentos e proteção dos dados de saúde dos participantes, proporcionando maior segurança, organização e controle no cotidiano das equipes de pesquisa.

## Objetivo
O principal objetivo do ClinSecure é oferecer uma plataforma segura para o gerenciamento de pesquisas clínicas, permitindo que equipes organizem participantes e dados clínicos de forma controlada e rastreável.

O sistema busca garantir que:

Os dados sejam acessados somente por usuários autorizados;
Os dados clínicos sejam coletados somente quando houver consentimento ativo;
A identidade dos participantes seja protegida;
Os consentimentos possam ser registrados, versionados e revogados;
As ações importantes realizadas no sistema sejam registradas para auditoria.

Dessa forma, o ClinSecure contribui para uma gestão mais segura e transparente dos dados utilizados em pesquisas clínicas.

## Principais Funcionalidades :

Cadastro e gerenciamento de usuários;
Controle de acesso por diferentes níveis de permissão;
Criação e administração de pesquisas clínicas;
Cadastro e gerenciamento de participantes;
Registro de consentimentos;
Versionamento de consentimentos;
Revogação de consentimentos;
Coleta segura de dados clínicos;
Restrição de coleta quando não houver consentimento ativo;
Proteção da identidade dos participantes por pseudonimização;
Consulta de dados autorizados;
Registro e consulta de auditoria.

## Segurança:

Entre os principais mecanismos de segurança estão:

Controle de acesso por perfil;
Autenticação em dois fatores (2FA);
Proteção da identidade dos participantes;
Pseudonimização dos dados;
Controle de consentimento;
Revogação de consentimentos;
Restrição de acesso aos dados autorizados;
Registro de auditoria das ações importantes.

## Perfis de Acesso:

## Administrador
Gerencia usuários;
Gerencia pesquisas;
Consulta registros de auditoria;
Não possui acesso aos dados clínicos por padrão.

## Pesquisador
Administra suas próprias pesquisas;
Visualiza os dados autorizados;
Acessa somente as pesquisas pelas quais é responsável;
Visualiza apenas o pseudônimo do participante.

## Participante
Visualiza suas pesquisas;
Consulta seus próprios dados;
Gerencia seu consentimento;
Pode autorizar ou revogar o consentimento;
Acessa somente os próprios dados.

## Público-Alvo

O ClinSecure é destinado principalmente a ambientes que realizam pesquisas clínicas e precisam proteger os dados de seus participantes.

Entre os possíveis usuários estão:

Centros de pesquisa clínica;
Universidades;
Institutos de pesquisa;
Equipes de pesquisa;
Coordenadores de estudos.

O sistema pode ser utilizado tanto em pesquisas menores quanto em estudos envolvendo diversos pesquisadores e participantes.

## Tecnologias

## Back-End
 
- Python 3.14.6
- Django 5.2.17
 
## Front-End
 
- HTML5
- CSS3
- Bootstrap 5
- JavaScript
 
## Data Base
 
- MySQL 8.0.46
 
## Versionamento
 
- Git
- GitHub

## Como executar o projeto:

## Windows:

1. Clonar o repositório

Abra o PowerShell e execute:

git clone https://github.com/CauaPeresAdriani/Projeto-Integrador.git
cd Projeto-Integrador

2. Criar o ambiente virtual

python -m venv venv

Ative o ambiente virtual:

.\venv\Scripts\Activate.ps1

3. Instalar as dependências

python -m pip install --upgrade pip
pip install -r requirements.txt

4. Configurar o banco de dados

Crie um banco de dados MySQL local:

CREATE DATABASE clinsecure;

5. Configurar o arquivo .env

Na raiz do projeto, crie um arquivo chamado .env:

SECRET_KEY=sua-chave-secreta
DB_NAME=clinsecure
DB_USER=root
DB_PASSWORD=sua-senha
DB_HOST=localhost
DB_PORT=3306

Substitua os valores pelas configurações do seu MySQL.

6. Executar as migrations

python manage.py migrate

7. Iniciar o servidor

python manage.py runserver

Acesse:

http://127.0.0.1:8000/

## Linux:

1. Clonar o repositório

Abra o terminal e execute:

git clone https://github.com/CauaPeresAdriani/Projeto-Integrador.git
cd Projeto-Integrador

2. Criar o ambiente virtual

python3 -m venv venv

Ative o ambiente virtual:

source venv/bin/activate

3. Instalar as dependências

python -m pip install --upgrade pip
pip install -r requirements.txt

4. Configurar o banco de dados

Crie um banco de dados MySQL local:

CREATE DATABASE clinsecure;

5. Configurar o arquivo .env

Na raiz do projeto, crie um arquivo chamado .env:

SECRET_KEY=sua-chave-secreta
DB_NAME=clinsecure
DB_USER=root
DB_PASSWORD=sua-senha
DB_HOST=localhost
DB_PORT=3306

Substitua os valores pelas configurações do seu MySQL.

6. Executar as migrations

python manage.py migrate

7. Iniciar o servidor

python manage.py runserver

Acesse:

http://127.0.0.1:8000/

## Execução após a primeira configuração 

Depois que o ambiente virtual e o banco de dados já estiverem configurados, não é necessário repetir todas as etapas.

Windows

.\venv\Scripts\Activate.ps1
python manage.py runserver

Linux

source venv/bin/activate
python manage.py runserver

O arquivo .env deve permanecer apenas no ambiente local e não deve ser enviado ao repositório.
  

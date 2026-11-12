# CondoApp

Protótipo de um **Sistema de Registro de Ocorrências de Condomínio**, feito como projeto educacional da faculdade (A3).

Com o CondoApp você cadastra condomínios e abre chamados (ocorrências) para uma ou mais casas/apartamentos. Depois, acompanha cada chamado e altera o status do atendimento.

## Funcionalidades do protótipo

- **Cadastro de condomínio:** nome, endereço, número de casas/apartamentos e dados do síndico (nome, telefone e e-mail). As unidades são criadas automaticamente, numeradas de 1 a N.
- **Abertura de chamado:** tipo de registro, unidades solicitantes (uma ou mais), nível de urgência, nome completo do solicitante e descrição opcional. A data de abertura é registrada automaticamente e todo chamado começa como **Aberto**.
- **Lista de chamados** com filtro por status.
- **Tela do chamado**, onde é possível alterar o status e a urgência.
- **Admin do Django** (`/admin/`) como apoio, por exemplo para renomear unidades ("Bloco A - 101").

| Campo | Opções |
|---|---|
| Tipo de registro | Elétrica, Hidráulica, Estrutura e conservação, Limpeza, Segurança, Barulho e convivência, Outro |
| Urgência | Baixa, Média, Alta |
| Status | Aberto, Em andamento, Concluído, Cancelado |

O protótipo não tem login. Também ficaram fora dele: foto, local, responsável pela execução, notificações e deploy.

## Requisitos

- **Python 3.10 ou superior** (testado com Python 3.11.9)
- Nenhum banco de dados para instalar: o projeto usa **SQLite**, que já vem com o Python.

## Como rodar no Windows

Abra o PowerShell (ou o Prompt de Comando) na pasta do projeto e rode:

1. Crie e ative um ambiente virtual:

   ```bash
   python -m venv .venv
   ```

   ```bash
   .venv\Scripts\activate
   ```

   > Se o PowerShell bloquear o `activate`, use o Prompt de Comando (cmd) e rode `.venv\Scripts\activate.bat`.

2. Instale as dependências (só o Django):

   ```bash
   pip install -r requirements.txt
   ```

3. Crie o banco de dados local. Esse comando gera o arquivo `db.sqlite3` na pasta do projeto:

   ```bash
   python manage.py migrate
   ```

4. (Opcional) Crie um usuário para acessar o admin:

   ```bash
   python manage.py createsuperuser
   ```

5. Inicie o servidor:

   ```bash
   python manage.py runserver
   ```

6. Acesse **http://127.0.0.1:8000** no navegador. O admin fica em **http://127.0.0.1:8000/admin/**.

Para recomeçar com o banco vazio, pare o servidor, apague o arquivo `db.sqlite3` e rode o `migrate` de novo.

## Como usar

1. **Condomínios → + Cadastrar:** preencha os dados do condomínio e do síndico. Ao salvar, as unidades de 1 a N são criadas.
2. **Abrir chamado:** escolha o condomínio (se houver só um, essa etapa é pulada), marque as unidades solicitantes e preencha o restante. Só aparecem as unidades do condomínio escolhido.
3. **Chamados:** veja todos os chamados ou filtre por status.
4. **Clique em um chamado** para ver os detalhes e, no quadro **Atendimento**, alterar o status e a urgência.

## Estrutura

```
CondoApp/
├── manage.py
├── requirements.txt
├── condoapp/           configuração do projeto (settings, urls)
└── core/               app única
    ├── models.py       Condominio, Unidade, Chamado
    ├── forms.py        formulários e validação
    ├── views.py        telas
    ├── urls.py         rotas
    ├── admin.py        admin do Django
    ├── migrations/
    ├── templates/core/ páginas HTML
    └── static/core/    style.css (tema escuro)
```

## Tecnologias

Python, Django 5.2 (LTS), SQLite, templates do Django, HTML e CSS próprio (tema escuro, mobile-first). Não há framework CSS nem etapa de build.

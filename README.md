# CondoApp

Protótipo de um **Sistema de Registro de Ocorrências de Condomínio**, feito como projeto educacional da faculdade (A3).

O CondoApp é o canal oficial das ocorrências do condomínio, com histórico e privacidade, que o síndico coloca no ar em uma tarde. O grupo de WhatsApp continua existindo; o CondoApp guarda o registro.

## Perfis e permissões

| Perfil | O que pode fazer |
|---|---|
| **Síndico** | Administrador do condomínio, com permissão total: edita os dados do condomínio, as unidades, todos os chamados (editar, excluir, mudar status e urgência, conduzir o rito) e os usuários (aprovar, recusar, editar, trocar unidade, dar perfil de síndico, bloquear, definir nova senha, remover). |
| **Morador** | Abre chamados pela própria unidade, acompanha os seus, vê os chamados públicos do condomínio, marca "Também estou afetado", cancela um chamado seu ainda aberto e apresenta defesa quando a unidade dele é notificada. |

Regras de acesso:

- Todas as telas internas exigem login (e-mail e senha).
- Cada usuário pertence a **um único condomínio** e nunca vê dados de outro.
- O morador entra pelo **link ou QR Code de convite** e só acessa depois que o síndico **aprova** o cadastro.
- O morador não muda a própria unidade nem o próprio perfil; só o síndico.
- O síndico não pode tirar o próprio perfil de síndico, bloquear nem remover a própria conta.
- Gerar um novo link de convite invalida o anterior.

## Diferenciais no funcionamento

1. **Implantação em uma tarde.** Um formulário cria a conta do síndico, o condomínio e as unidades (numeradas de 1 a N). As unidades podem ser renomeadas todas de uma vez, uma por linha (ex.: "Bloco A - 101"). O convite sai por link, WhatsApp ou QR Code, e a tela do condomínio mostra os passos da implantação e o tempo até o primeiro chamado.
2. **Ocorrências com privacidade e rito.** Um chamado pode ser **privado** (só o síndico e a unidade que registrou veem; padrão sugerido para barulho e convivência). Vizinhos nunca veem o nome de quem registrou. Com uma **unidade envolvida**, o síndico conduz o caso em etapas: **aviso → notificação → defesa → decisão**. A unidade envolvida só vê o caso a partir do aviso, sem saber quem reclamou, e pode apresentar defesa. Advertência ou multa só podem ser decididas depois da notificação.
3. **Ninguém fica de fora.** O síndico registra chamados em nome de quem não usa o app, imprime um aviso com QR Code para o elevador ou a portaria e pode definir uma nova senha para quem esqueceu.
4. **Ocorrências inteligentes.** Ao abrir um chamado, o app mostra os chamados parecidos em aberto, para o morador marcar **"Também estou afetado"** em vez de duplicar. Quando o mesmo tipo de problema se repete no mesmo local de área comum (3 chamados em 90 dias), o síndico recebe uma **sugestão de manutenção preventiva**. Esse critério é inicial e ainda precisa ser validado com síndicos.

Todo chamado tem **histórico**: abertura, mudanças de status e urgência, edições, "também afetados" e cada etapa do rito, com data e autor.

| Campo | Opções |
|---|---|
| Tipo de registro | Elétrica, Hidráulica, Estrutura e conservação, Limpeza, Segurança, Barulho e convivência, Outro |
| Local | Dentro da unidade, Garagem, Elevador, Escadas e corredores, Portaria e entrada, Área de lazer, Jardim e área externa, Fachada e telhado, Outro local |
| Urgência | Baixa, Média, Alta |
| Status | Aberto, Em andamento, Concluído, Cancelado |

Fora do protótipo: foto, responsável pela execução, notificações por e-mail ou WhatsApp, recuperação de senha por e-mail e deploy.

## Requisitos

- **Python 3.10 ou superior** (testado com Python 3.11.9)
- Nenhum banco de dados para instalar: o projeto usa **SQLite**, que já vem com o Python.
- Internet só para gerar a imagem do QR Code (biblioteca `qrcode-generator`, carregada da cdnjs). Sem internet, o link de convite funciona normalmente.

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

3. Crie ou atualize o banco de dados local (`db.sqlite3`):

   ```bash
   python manage.py migrate
   ```

4. (Opcional) Crie um condomínio de demonstração, com síndico, moradores e chamados de exemplo:

   ```bash
   python manage.py popular_demo
   ```

5. Inicie o servidor:

   ```bash
   python manage.py runserver
   ```

6. Acesse **http://127.0.0.1:8000** no navegador.

Para recomeçar com o banco vazio, pare o servidor, apague o arquivo `db.sqlite3` e rode o `migrate` de novo.

### Contas da demonstração

Criadas pelo `popular_demo`. São contas de teste, só para uso local. Senha de todas: `Condo@2026`.

| E-mail | Perfil | Unidade | Para ver |
|---|---|---|---|
| sindico@example.com | Síndico | Bloco A - 101 | Tudo: aprovação, preventiva, rito, convite |
| morador1@example.com | Morador | Bloco A - 102 | Chamado do elevador com vizinhos afetados |
| morador2@example.com | Morador | Bloco A - 201 | Reclamação de barulho privada |
| morador3@example.com | Morador | Bloco A - 202 | Unidade notificada, com campo de defesa |
| pendente@example.com | Morador | Bloco B - 101 | Login bloqueado até o síndico aprovar |

Para recriar a demonstração do zero: `python manage.py popular_demo --recriar`.

## Como usar

1. **Síndico:** na página inicial, clique em **Cadastrar condomínio**. Ao salvar, as unidades são criadas e você entra direto na tela **Condomínio**.
2. Em **Condomínio**, copie o link de convite, envie no WhatsApp ou imprima o aviso com QR Code. Em **Unidades**, renomeie as casas/apartamentos.
3. **Morador:** abre o link, preenche nome, unidade, e-mail e senha e aguarda a aprovação.
4. **Síndico:** em **Moradores**, aprove os cadastros. Ali também se editam, bloqueiam e removem contas.
5. **Abrir chamado:** o morador registra pela própria unidade; o síndico pode registrar por qualquer unidade, em nome de um morador.
6. **Chamado:** o síndico altera status e urgência, edita todos os campos e conduz o rito quando há unidade envolvida.

## Testes

```bash
python manage.py test
```

Cobrem login, cadastro e aprovação, permissões de síndico e morador, isolamento entre condomínios, privacidade, rito e as ocorrências inteligentes.

## Estrutura

```
CondoApp/
├── manage.py
├── requirements.txt
├── condoapp/              configuração do projeto (settings, urls)
└── core/                  app única
    ├── models.py          Condominio, Unidade, Perfil, Chamado, Andamento
    ├── forms.py           formulários e validação
    ├── views.py           telas
    ├── acesso.py          regras de acesso (login, síndico)
    ├── contexto.py        dados do usuário para os templates
    ├── urls.py            rotas
    ├── admin.py           admin do Django
    ├── tests.py           testes automáticos
    ├── management/        comando popular_demo
    ├── migrations/
    ├── templates/         páginas HTML
    └── static/core/       style.css (tema escuro) e app.js
```

A pasta do projeto guarda só arquivos da aplicação. Apresentações, relatórios e pesquisas ficam fora dela.

## Tecnologias

Python, Django 5.2 (LTS), SQLite, templates do Django, HTML, CSS próprio (tema escuro, mobile-first) e JavaScript puro. Não há framework CSS nem etapa de build.

O admin do Django (`/admin/`) continua disponível para o desenvolvedor. Crie um superusuário com `python manage.py createsuperuser`. Ele não tem condomínio e não entra nas telas do app.

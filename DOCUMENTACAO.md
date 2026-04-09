# Chef IA Premium — Documentação do Projeto

## Visão Geral

Plataforma SaaS de receitas premium com curadoria de alta gastronomia.
Clientes assinam um plano mensal ou anual para acessar receitas exclusivas
personalizadas para momentos especiais.

---

## Stack Tecnológica

| Camada       | Tecnologia              | Status     |
|--------------|-------------------------|------------|
| Frontend     | HTML + CSS + JavaScript | Pronto     |
| Backend      | Python + FastAPI        | Pronto     |
| Banco de dados | PostgreSQL            | Pronto     |
| ORM          | SQLAlchemy              | Pronto     |
| Autenticação | JWT + bcrypt            | Pronto     |
| Cobrança     | Stripe                  | Estrutura pronta |
| Fotos        | Upload local / pasta    | Estrutura pronta |

---

## Estrutura de Arquivos

```
receita_premium/
│
├── encontro_premium.html       # Frontend principal
├── receitas_premium.json       # Base de receitas original
├── iniciar.bat                 # Clique duplo para iniciar o servidor
│
├── fotos/                      # Fotos das receitas (upload)
│
└── backend/
    ├── main.py                 # API FastAPI — todos os endpoints
    ├── models.py               # Tabelas do banco de dados
    ├── database.py             # Conexão com PostgreSQL
    ├── auth.py                 # Login, JWT, controle de planos
    ├── .env                    # Configurações e senhas (não compartilhar)
    └── requirements.txt        # Dependências Python
```

---

## Banco de Dados — Tabelas

### `usuarios`
| Campo          | Tipo    | Descrição                        |
|----------------|---------|----------------------------------|
| id             | int     | Chave primária                   |
| nome           | string  | Nome completo                    |
| email          | string  | E-mail único (login)             |
| senha_hash     | string  | Senha criptografada com bcrypt   |
| plano          | enum    | gratuito / mensal / anual        |
| ativo          | bool    | Conta ativa ou bloqueada         |
| criado_em      | datetime| Data de cadastro                 |

### `receitas`
| Campo          | Tipo    | Descrição                        |
|----------------|---------|----------------------------------|
| id             | int     | Chave primária                   |
| nome           | string  | Nome da receita                  |
| categoria      | string  | Peixe / Carne / Frutos do Mar    |
| descricao      | text    | Descrição completa               |
| tempo_preparo  | string  | Ex: 55 min                       |
| dificuldade    | string  | Fácil / Média / Alta             |
| porcoes        | string  | Ex: 2 pessoas                    |
| foto_url       | string  | Caminho da foto                  |
| ingredientes   | json    | Lista com item e quantidade      |
| tecnica        | json    | Passos de preparo                |
| vinhos         | json    | Sugestões de harmonização        |
| mise_en_place  | json    | Itens de apresentação da mesa    |
| dica_chef      | text    | Dica exclusiva do chef           |
| premium        | bool    | True = só assinantes             |

### `assinaturas`
| Campo              | Tipo    | Descrição                    |
|--------------------|---------|------------------------------|
| id                 | int     | Chave primária               |
| usuario_id         | int     | FK para usuarios             |
| stripe_customer_id | string  | ID do cliente no Stripe      |
| stripe_sub_id      | string  | ID da assinatura no Stripe   |
| plano              | enum    | mensal / anual               |
| status             | enum    | ativa / cancelada / expirada |
| valor              | int     | Valor em centavos            |
| inicio             | datetime| Início da assinatura         |
| vencimento         | datetime| Data de renovação            |

### `favoritos`
| Campo      | Tipo     | Descrição               |
|------------|----------|-------------------------|
| id         | int      | Chave primária          |
| usuario_id | int      | FK para usuarios        |
| receita_id | int      | FK para receitas        |
| salvo_em   | datetime | Data que salvou         |

---

## API — Endpoints Disponíveis

### Autenticação
| Método | Rota             | Descrição              | Acesso   |
|--------|------------------|------------------------|----------|
| POST   | /auth/cadastro   | Criar nova conta       | Público  |
| POST   | /auth/login      | Entrar e receber token | Público  |
| GET    | /auth/perfil     | Ver dados da conta     | Logado   |

### Receitas
| Método | Rota                  | Descrição                  | Acesso         |
|--------|-----------------------|----------------------------|----------------|
| GET    | /receitas             | Listar receitas            | Logado         |
| GET    | /receitas/{id}        | Detalhe de uma receita     | Logado         |
| POST   | /receitas             | Criar receita              | Premium        |
| POST   | /receitas/{id}/foto   | Fazer upload de foto       | Logado         |

### Favoritos
| Método | Rota                    | Descrição          | Acesso |
|--------|-------------------------|--------------------|--------|
| GET    | /favoritos              | Listar favoritos   | Logado |
| POST   | /favoritos/{receita_id} | Salvar favorito    | Logado |
| DELETE | /favoritos/{receita_id} | Remover favorito   | Logado |

### Assinaturas
| Método | Rota                   | Descrição          | Acesso |
|--------|------------------------|--------------------|--------|
| GET    | /planos                | Ver planos         | Público|
| POST   | /assinaturas/assinar   | Assinar um plano   | Logado |
| POST   | /assinaturas/cancelar  | Cancelar assinatura| Logado |

---

## Planos de Assinatura

| Plano    | Valor       | Acesso                          |
|----------|-------------|---------------------------------|
| Gratuito | R$ 0        | Receitas públicas apenas        |
| Mensal   | R$ 29,90/mês| Todas as receitas + favoritos   |
| Anual    | R$ 249,00   | Tudo do mensal + 30% de desconto|

---

## Roteiro de Desenvolvimento

### FASE 1 — Base (CONCLUIDA)
- [x] Frontend HTML com filtros e gerador de receitas
- [x] Banco de dados PostgreSQL configurado
- [x] 10 receitas importadas para o banco
- [x] Backend FastAPI rodando em localhost:8000
- [x] Sistema de autenticação JWT
- [x] Tabelas de usuários, receitas, assinaturas e favoritos
- [x] Estrutura de upload de fotos
- [x] Integração Stripe preparada

---

### FASE 2 — Frontend com Login (PROXIMO PASSO)
- [ ] Página de cadastro de usuário
- [ ] Página de login
- [ ] Menu com nome do usuário logado
- [ ] Redirecionar para login se não autenticado
- [ ] Guardar token JWT no localStorage
- [ ] Conectar busca de receitas ao banco via API

**Arquivos a criar:**
- `login.html`
- `cadastro.html`
- `js/api.js` — funções para chamadas ao backend

---

### FASE 3 — Fotos das Receitas (CONCLUÍDA)
- [x] Painel admin para fazer upload de fotos (`admin.html`)
- [x] Exibir foto no card de cada receita
- [x] Foto de destaque na página da receita
- [x] Otimizar imagens automaticamente (Pillow — resize 1200x900, JPEG 85%)

---

### FASE 4 — Página de Planos e Pagamento
- [ ] Página bonita com os 3 planos (gratuito, mensal, anual)
- [ ] Integrar Stripe Checkout
- [ ] Webhook do Stripe para confirmar pagamento
- [ ] E-mail de boas-vindas após assinatura
- [ ] Página de sucesso/erro de pagamento

**Arquivos a criar:**
- `planos.html`
- `backend/email.py` — envio de e-mail
- Rota `/assinaturas/webhook` no backend

---

### FASE 5 — Painel do Usuário
- [ ] Página "Minha Conta"
- [ ] Ver plano ativo e data de vencimento
- [ ] Histórico de receitas vistas
- [ ] Gerenciar favoritos salvos
- [ ] Botão cancelar assinatura

**Arquivos a criar:**
- `minha-conta.html`

---

### FASE 6 — IA com Claude API (OPCIONAL)
- [ ] Adicionar chave da API Anthropic no .env
- [ ] Rota `/receitas/gerar` que chama o Claude
- [ ] Gerar receitas personalizadas em tempo real
- [ ] Salvar receitas geradas no banco automaticamente

---

### FASE 7 — Publicar Online (FUTURO)
- [ ] Criar conta na Railway ou Render (gratuito)
- [ ] Fazer deploy do backend
- [ ] Migrar banco para PostgreSQL na nuvem
- [ ] Apontar domínio próprio
- [ ] Configurar HTTPS

---

## Como Iniciar o Projeto

### 1. Iniciar o servidor
Dê duplo clique no arquivo `iniciar.bat`
ou no terminal:
```bash
cd backend
python main.py
```

### 2. Acessar
- **Site:** http://localhost:8000
- **Documentação da API:** http://localhost:8000/docs
- **API alternativa:** http://localhost:8000/redoc

### 3. Variáveis de ambiente (backend/.env)
```
DATABASE_URL=postgresql://postgres:123456@localhost:5432/receita_premium
SECRET_KEY=troque_por_uma_chave_secreta_longa_aqui_123456
STRIPE_SECRET_KEY=sk_test_...   (pegar no dashboard do Stripe)
```

---

## Dependências Instaladas

```
fastapi          — framework web
uvicorn          — servidor ASGI
sqlalchemy       — ORM para banco de dados
psycopg2         — driver PostgreSQL
python-jose      — tokens JWT
passlib[bcrypt]  — hash de senhas
python-multipart — upload de arquivos
aiofiles         — leitura de arquivos assíncrona
python-dotenv    — variáveis de ambiente
stripe           — pagamentos
pydantic[email]  — validação de e-mail
email-validator  — validação de e-mail
```

---

## Segurança

- Senhas armazenadas com **bcrypt** (nunca em texto puro)
- Autenticação via **JWT** com expiração de 7 dias
- Chaves sensíveis somente no arquivo **.env** (nunca no código)
- Controle de acesso por plano em cada endpoint
- O arquivo `.env` **nunca deve ser compartilhado ou enviado para o GitHub**

---

*Documentação gerada em 20/03/2026*

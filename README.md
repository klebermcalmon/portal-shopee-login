# API Shopee

Aplicacao web minima em Python para integrar com a Shopee Open API usando o fluxo de autorizacao da loja.

## O que este projeto faz

- Tela de login para avaliacao da integracao
- Painel web com consulta de loja, pedidos e produtos
- Rotas JSON de apoio para loja, pedidos e produtos
- Salva o token em `shopee_token.json`
- Permite renovar o token

## Estrutura

- `app.py`: servidor HTTP simples com rotas web e JSON
- `config.py`: leitura das configuracoes via `.env`
- `portal_ui.py`: interface HTML do portal
- `shopee_client.py`: assinatura HMAC e chamadas HTTP da Shopee
- `.env.example`: modelo das variaveis de ambiente

## Preparacao

1. Opcionalmente crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Copie `.env.example` para `.env` e preencha:

```env
SHOPEE_ENV=test
SHOPEE_PARTNER_ID=1230054
SHOPEE_PARTNER_KEY=sua_partner_key
SHOPEE_REDIRECT_URL=https://www.login.com.br/shopee/callback
SHOPEE_HOST=https://partner.test-stable.shopeemobile.com
SHOPEE_API_HOST=https://openplatform.sandbox.test-stable.shopee.sg
SHOPEE_AUTH_HOST=https://partner.test-stable.shopeemobile.com
FLASK_DEBUG=true
APP_TITLE=Portal Shopee Login
REVIEWER_USERNAME=shopee.review@login.com.br
REVIEWER_PASSWORD=Alterar123!
```

## Importante sobre redirect

O valor de `SHOPEE_REDIRECT_URL` precisa bater com a URL cadastrada na Shopee dentro do dominio permitido. Pelo seu print, o dominio de teste cadastrado e `https://www.login.com.br`.

Se quiser usar esse projeto localmente, voce precisa:

- publicar esse callback em uma rota real do dominio cadastrado, ou
- alterar o redirect cadastrado no painel da Shopee para uma URL que aponte para o servidor onde este app esta rodando

## Como rodar

```powershell
python app.py
```

Servidor padrao:

- `http://127.0.0.1:5000`

## Publicacao no Render

O projeto ja esta preparado para deploy no Render com:

- porta dinamica via variavel `PORT`
- configuracao em `render.yaml`
- health check em `/login`

### O que voce vai precisar

- uma conta no Render
- um repositorio GitHub com esta pasta do projeto

### Configuracao sugerida no Render

- Tipo: `Web Service`
- Runtime: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python app.py`

### Variaveis de ambiente que voce deve configurar no Render

- `SHOPEE_PARTNER_ID`
- `SHOPEE_PARTNER_KEY`
- `SHOPEE_REDIRECT_URL`
- `REVIEWER_USERNAME`
- `REVIEWER_PASSWORD`

As variaveis abaixo ja podem ficar como padrao da sandbox:

- `SHOPEE_ENV=test`
- `SHOPEE_API_HOST=https://openplatform.sandbox.test-stable.shopee.sg`
- `SHOPEE_AUTH_HOST=https://partner.test-stable.shopeemobile.com`
- `APP_TITLE=Portal Shopee Login`

### URL publica para a Shopee

Depois do deploy, o Render entrega uma URL publica no formato:

- `https://nome-do-servico.onrender.com`

Use esta URL com:

- `/login`
- `/dashboard`

Exemplo:

- `https://portal-shopee-login.onrender.com/login`

## Fluxo de uso

1. Abra `GET /auth-url` para ver a URL de autorizacao.
2. Abra `GET /authorize` para ser redirecionado para a Shopee.
3. Autorize a loja de teste.
4. A Shopee chamara `SHOPEE_REDIRECT_URL` com `code` e `shop_id`.
5. A rota `/callback` salva o token em `shopee_token.json`.
6. Acesse o portal:

- `GET /login`
- `GET /dashboard`

7. Consulte as rotas JSON quando precisar:

- `GET /token-status`
- `GET /shop-info`
- `GET /orders?time_from=1711411200&time_to=1711497600`
- `GET /products`

## Fluxo local sem callback publico

Se voce vai rodar apenas localmente, use este caminho:

1. Rode `python app.py`
2. Abra `http://127.0.0.1:5000/auth-url` e copie a URL gerada
3. Abra essa URL no navegador e conclua a autorizacao na Shopee
4. Quando o navegador abrir a URL final do callback em `www.login.com.br`, copie a URL completa da barra de endereco
5. Troque por token localmente:

```powershell
python complete_auth.py --callback-url "https://www.login.com.br/shopee/callback?code=SEU_CODE&shop_id=SEU_SHOP_ID"
```

Depois disso, o arquivo `shopee_token.json` sera criado localmente e voce podera usar:

- `http://127.0.0.1:5000/login`
- `http://127.0.0.1:5000/dashboard`
- `http://127.0.0.1:5000/token-status`
- `http://127.0.0.1:5000/shop-info`
- `http://127.0.0.1:5000/orders`
- `http://127.0.0.1:5000/products`

## Observacoes

- Os endpoints de teste usam o host sandbox: `partner.test-stable.shopeemobile.com`
- As chamadas autenticadas da sandbox usam `openplatform.sandbox.test-stable.shopee.sg`
- Nunca suba `.env` nem `shopee_token.json` para repositorio
- Como a Partner Key apareceu no print, o ideal e rotacionar essa chave antes de usar em producao

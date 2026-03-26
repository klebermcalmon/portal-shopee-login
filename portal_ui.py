from __future__ import annotations

import json
from datetime import datetime
from html import escape
from typing import Any


def fmt_ts(timestamp: int | None) -> str:
    if not timestamp:
        return "-"
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M:%S")


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body{{margin:0;font-family:Segoe UI,Tahoma,sans-serif;background:#edf3f8;color:#1f3448}}
    .wrap{{max-width:1100px;margin:0 auto;padding:24px 16px 40px}}
    .card{{background:#fff;border:1px solid #d9e4ee;border-radius:18px;padding:20px;box-shadow:0 12px 32px rgba(15,23,42,.08);margin-bottom:18px}}
    .top{{display:flex;justify-content:space-between;gap:16px;align-items:end;flex-wrap:wrap}}
    h1,h2{{margin:0 0 12px}} h1{{font-size:32px}} h2{{font-size:18px}}
    p,.muted{{color:#667085}} .pill{{display:inline-block;padding:6px 10px;border-radius:999px;background:#e8f4ff;color:#04568f;font-size:12px;font-weight:700}}
    .stats{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}}
    .stat{{background:#f8fbfd;border:1px solid #d9e4ee;border-radius:14px;padding:14px}}
    .lab{{color:#667085;font-size:12px;text-transform:uppercase}} .val{{margin-top:8px;font-size:22px;font-weight:700}}
    .grid{{display:grid;grid-template-columns:2fr 1fr;gap:18px}} .grid2{{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}}
    table{{width:100%;border-collapse:collapse}} th,td{{padding:12px;border-bottom:1px solid #d9e4ee;text-align:left;font-size:14px;vertical-align:top}}
    th{{color:#667085;background:#f8fbfd}} .table{{overflow:auto;border:1px solid #d9e4ee;border-radius:14px}}
    .btn{{display:inline-block;padding:11px 14px;border-radius:12px;background:#0a73b8;color:#fff;text-decoration:none;font-weight:700}}
    .btn.alt{{background:#fff;color:#1f3448;border:1px solid #d9e4ee}} .actions{{display:flex;gap:10px;flex-wrap:wrap}}
    .note{{padding:12px 14px;border-radius:14px;margin-bottom:14px;font-size:14px}}
    .note.info{{background:#eff8ff;border:1px solid #b2ddff;color:#04568f}}
    .note.error{{background:#fff1f3;border:1px solid #fbcfe8;color:#b42318}}
    input{{width:100%;height:42px;padding:0 12px;border:1px solid #d9e4ee;border-radius:12px}} label{{display:block;margin-bottom:6px;color:#667085;font-size:13px}}
    form.row{{display:flex;gap:12px;flex-wrap:wrap;align-items:end}} .field{{flex:1 1 180px}}
    pre{{margin:0;background:#0f172a;color:#e2e8f0;padding:16px;border-radius:14px;overflow:auto;font-size:12px}}
    .login{{min-height:100vh;display:grid;place-items:center;padding:20px}} .box{{width:min(420px,100%)}}
    @media (max-width:900px){{.stats,.grid,.grid2{{grid-template-columns:1fr}} h1{{font-size:28px}}}}
  </style>
</head>
<body>{body}</body></html>"""


def login(app_title: str, error: str | None = None) -> str:
    notice = f'<div class="note error">{escape(error)}</div>' if error else ""
    return page(
        f"Login | {app_title}",
        f"""
        <main class="login"><section class="card box">
          <div class="pill">Shopee Open Platform</div>
          <h1>{escape(app_title)}</h1>
          <p class="muted">Portal minimo para validacao da integracao com consulta de loja, pedidos e produtos.</p>
          {notice}
          <form method="post" action="/login">
            <div class="field"><label>Usuario</label><input name="username" required></div>
            <div class="field" style="margin-top:12px;"><label>Senha</label><input type="password" name="password" required></div>
            <div class="actions" style="margin-top:16px;"><button class="btn" type="submit">Entrar</button></div>
          </form>
        </section></main>
        """,
    )


def dashboard(
    *,
    app_title: str,
    username: str,
    partner_id: int,
    env: str,
    reviewer_username: str,
    reviewer_password: str,
    shop_info: dict[str, Any] | None,
    orders_payload: dict[str, Any] | None,
    products_payload: dict[str, Any] | None,
    token_data: dict[str, Any] | None,
    messages: list[tuple[str, str]],
    days: int,
) -> str:
    notices = "".join(f'<div class="note {escape(k)}">{escape(v)}</div>' for k, v in messages)
    order_rows = []
    for row in (((orders_payload or {}).get("response") or {}).get("order_list") or []):
        order_rows.append(
            f"<tr><td>{escape(str(row.get('order_sn', '-')))}</td><td>{escape(str(row.get('order_status', '-')))}</td><td>{escape(fmt_ts(row.get('create_time')))}</td></tr>"
        )
    if not order_rows:
        order_rows.append('<tr><td colspan="3">Nenhum pedido no periodo consultado.</td></tr>')
    product_rows = []
    for row in (((products_payload or {}).get("response") or {}).get("item") or []):
        product_rows.append(
            f"<tr><td>{escape(str(row.get('item_id', '-')))}</td><td>{escape(str(row.get('item_status', '-')))}</td><td>{escape(str(row.get('update_time', '-')))}</td></tr>"
        )
    if not product_rows:
        product_rows.append('<tr><td colspan="3">Nenhum SKU retornado pela API no momento.</td></tr>')
    token = token_data or {}
    debug = json.dumps(
        {
            "shop_info": shop_info or {},
            "orders_count": len((((orders_payload or {}).get("response") or {}).get("order_list") or [])),
            "products_count": len((((products_payload or {}).get("response") or {}).get("item") or [])),
        },
        ensure_ascii=True,
        indent=2,
    )
    stats = ""
    if shop_info:
        stats = f"""
        <div class="stats">
          <div class="stat"><div class="lab">Loja</div><div class="val">{escape(str(shop_info.get('shop_name', '-')))}</div></div>
          <div class="stat"><div class="lab">Regiao</div><div class="val">{escape(str(shop_info.get('region', '-')))}</div></div>
          <div class="stat"><div class="lab">Status</div><div class="val">{escape(str(shop_info.get('status', '-')))}</div></div>
          <div class="stat"><div class="lab">Token expira</div><div class="val" style="font-size:16px">{escape(fmt_ts(shop_info.get('expire_time')))}</div></div>
        </div>
        """
    return page(
        f"Dashboard | {app_title}",
        f"""
        <div class="wrap">
          <section class="card top">
            <div>
              <div class="pill">Ambiente {escape(env)}</div>
              <h1>{escape(app_title)}</h1>
              <p>Usuario autenticado: <strong>{escape(username)}</strong>. Partner ID: <strong>{partner_id}</strong>.</p>
            </div>
            <div class="actions"><a class="btn alt" href="/dashboard">Atualizar</a><a class="btn alt" href="/logout">Sair</a></div>
          </section>
          {notices}
          <section class="card">
            <h2>Resumo da loja</h2>
            {stats}
          </section>
          <section class="grid">
            <article class="card">
              <h2>Pedidos recentes</h2>
              <form class="row" method="get" action="/dashboard">
                <div class="field"><label>Periodo em dias</label><input type="number" name="days" min="1" max="90" value="{days}"></div>
                <button class="btn" type="submit">Atualizar</button>
              </form>
              <div class="table"><table><thead><tr><th>Order SN</th><th>Status</th><th>Criado em</th></tr></thead><tbody>{''.join(order_rows)}</tbody></table></div>
            </article>
            <article class="card">
              <h2>Acesso de avaliacao</h2>
              <div class="table"><table><tbody>
                <tr><th>Login</th><td>{escape(reviewer_username)}</td></tr>
                <tr><th>Senha</th><td>{escape(reviewer_password)}</td></tr>
                <tr><th>Rotas JSON</th><td><a href="/shop-info" target="_blank">/shop-info</a><br><a href="/orders" target="_blank">/orders</a><br><a href="/products" target="_blank">/products</a></td></tr>
                <tr><th>Shop ID</th><td>{escape(str(token.get('shop_id', '-')))}</td></tr>
              </tbody></table></div>
            </article>
          </section>
          <section class="grid2">
            <article class="card">
              <h2>SKUs / Produtos</h2>
              <div class="table"><table><thead><tr><th>Item ID</th><th>Status</th><th>Update</th></tr></thead><tbody>{''.join(product_rows)}</tbody></table></div>
            </article>
            <article class="card">
              <h2>Resumo tecnico</h2>
              <pre>{escape(debug)}</pre>
            </article>
          </section>
        </div>
        """,
    )

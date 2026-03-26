from __future__ import annotations

import json
import os
import secrets
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

from config import get_settings
from portal_ui import dashboard as render_dashboard
from portal_ui import login as render_login
from shopee_client import ShopeeClient


settings = get_settings()
client = ShopeeClient(settings=settings)
SESSIONS: dict[str, str] = {}


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _load_token_data() -> dict[str, Any]:
    if not settings.token_file.exists():
        raise FileNotFoundError(
            "Arquivo de token nao encontrado. Acesse /authorize e conclua a autorizacao da loja."
        )
    return json.loads(settings.token_file.read_text(encoding="utf-8"))


def _save_token_data(payload: dict[str, Any]) -> None:
    settings.token_file.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _token_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(payload)
    snapshot["access_token"] = _mask_secret(snapshot.get("access_token"))
    snapshot["refresh_token"] = _mask_secret(snapshot.get("refresh_token"))
    return snapshot


def _json_error(message: str, status_code: int, **details: Any):
    payload = {"error": message}
    if details:
        payload["details"] = details
    return payload, status_code


def _http_error_body(exc: HTTPError | URLError) -> str:
    if isinstance(exc, HTTPError):
        try:
            return exc.read().decode("utf-8")
        except Exception:
            return str(exc)
    return str(exc)


def _root_payload() -> dict[str, Any]:
    return {
        "project": "Shopee API starter",
        "environment": settings.env,
        "api_host": settings.api_host,
        "auth_host": settings.auth_host,
        "redirect_url": settings.redirect_url,
        "partner_id": settings.partner_id,
        "routes": {
            "authorize": "/authorize",
            "auth_url": "/auth-url",
            "callback": "/callback",
            "token_status": "/token-status",
            "refresh_token": "/refresh-token",
            "shop_info": "/shop-info",
            "orders": "/orders?time_from=UNIX&time_to=UNIX",
        },
    }


def _collect_dashboard_data(days: int) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
    dict[str, Any] | None,
    dict[str, Any] | None,
    list[tuple[str, str]],
]:
    messages: list[tuple[str, str]] = []
    try:
        token_data = _load_token_data()
    except FileNotFoundError as exc:
        messages.append(("error", str(exc)))
        return None, None, None, None, messages

    access_token = token_data.get("access_token", "")
    shop_id = int(token_data.get("shop_id", 0))
    if not access_token or not shop_id:
        messages.append(("error", "Token local invalido. Verifique o arquivo shopee_token.json."))
        return None, None, None, token_data, messages

    shop_info = None
    orders_payload = None
    products_payload = None

    try:
        shop_info = client.get_shop_info(access_token=access_token, shop_id=shop_id)
    except (HTTPError, URLError) as exc:
        messages.append(("error", f"Falha ao consultar loja: {_http_error_body(exc)}"))

    now = int(time.time())
    try:
        orders_payload = client.get_order_list(
            access_token=access_token,
            shop_id=shop_id,
            time_from=now - max(days, 1) * 86400,
            time_to=now,
            page_size=20,
        )
    except (HTTPError, URLError) as exc:
        messages.append(("error", f"Falha ao consultar pedidos: {_http_error_body(exc)}"))

    try:
        products_payload = client.get_item_list(
            access_token=access_token,
            shop_id=shop_id,
            offset=0,
            page_size=20,
            item_status="NORMAL",
        )
    except (HTTPError, URLError) as exc:
        messages.append(("info", f"Produtos nao retornados pela API: {_http_error_body(exc)}"))

    if not messages:
        messages.append(("info", "Portal operacional. Integracao Shopee validada com sucesso."))
    return shop_info, orders_payload, products_payload, token_data, messages


class AppHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict[str, Any], status_code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=True, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_content: str, status_code: int = 200) -> None:
        body = html_content.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_redirect(self, location: str, cookie_header: str | None = None) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        if cookie_header:
            self.send_header("Set-Cookie", cookie_header)
        self.end_headers()

    def _send_clear_cookie_redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.send_header("Set-Cookie", "session_id=; Path=/; HttpOnly; Max-Age=0; SameSite=Lax")
        self.end_headers()

    def _query_params(self) -> dict[str, str]:
        parsed = urlparse(self.path)
        raw_params = parse_qs(parsed.query)
        return {key: values[0] for key, values in raw_params.items() if values}

    def _read_form(self) -> dict[str, str]:
        content_length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(content_length).decode("utf-8")
        parsed = parse_qs(raw)
        return {key: values[0] for key, values in parsed.items() if values}

    def _current_username(self) -> str | None:
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return None
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get("session_id")
        if morsel is None:
            return None
        return SESSIONS.get(morsel.value)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        params = self._query_params()

        if path == "/":
            username = self._current_username()
            self._send_redirect("/dashboard" if username else "/login")
            return

        if path == "/login":
            self._send_html(render_login(settings.app_title, params.get("error")))
            return

        if path == "/logout":
            cookie_header = self.headers.get("Cookie", "")
            if cookie_header:
                cookie = SimpleCookie()
                cookie.load(cookie_header)
                morsel = cookie.get("session_id")
                if morsel is not None:
                    SESSIONS.pop(morsel.value, None)
            self._send_clear_cookie_redirect("/login")
            return

        if path == "/dashboard":
            username = self._current_username()
            if not username:
                self._send_redirect("/login")
                return
            try:
                days = max(1, min(int(params.get("days", "7")), 90))
            except ValueError:
                days = 7
            shop_info, orders_payload, products_payload, token_data, messages = _collect_dashboard_data(days)
            self._send_html(
                render_dashboard(
                    app_title=settings.app_title,
                    username=username,
                    partner_id=settings.partner_id,
                    env=settings.env,
                    reviewer_username=settings.reviewer_username,
                    reviewer_password=settings.reviewer_password,
                    shop_info=shop_info,
                    orders_payload=orders_payload,
                    products_payload=products_payload,
                    token_data=token_data,
                    messages=messages,
                    days=days,
                )
            )
            return

        if path == "/auth-url":
            self._send_json({"auth_url": client.build_auth_url()})
            return

        if path == "/authorize":
            self._send_redirect(client.build_auth_url())
            return

        if path == "/callback":
            self._handle_callback(params)
            return

        if path == "/token-status":
            self._handle_token_status()
            return

        if path == "/refresh-token":
            self._handle_refresh_token()
            return

        if path == "/shop-info":
            self._handle_shop_info()
            return

        if path == "/orders":
            self._handle_orders(params)
            return

        if path == "/products":
            self._handle_products(params)
            return

        self._send_json({"error": "Rota nao encontrada."}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/login":
            form = self._read_form()
            username = form.get("username", "").strip()
            password = form.get("password", "").strip()
            if username == settings.reviewer_username and password == settings.reviewer_password:
                session_id = secrets.token_urlsafe(24)
                SESSIONS[session_id] = username
                self._send_redirect(
                    "/dashboard",
                    cookie_header=f"session_id={session_id}; Path=/; HttpOnly; SameSite=Lax",
                )
                return
            self._send_redirect("/login?error=Credenciais%20invalidas")
            return

        if parsed.path == "/refresh-token":
            self._handle_refresh_token()
            return
        self._send_json({"error": "Rota nao encontrada."}, 404)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle_callback(self, params: dict[str, str]) -> None:
        code = params.get("code", "").strip()
        shop_id = params.get("shop_id", "").strip()
        if not code or not shop_id:
            payload, status = _json_error("Callback incompleto.", 400, received_args=params)
            self._send_json(payload, status)
            return

        try:
            token_response = client.exchange_token(code=code, shop_id=int(shop_id))
        except (HTTPError, URLError) as exc:
            payload, status = _json_error(
                "Falha ao trocar code por token.",
                502,
                response=_http_error_body(exc),
            )
            self._send_json(payload, status)
            return

        if token_response.get("error"):
            payload, status = _json_error(
                "Shopee retornou erro ao gerar token.",
                400,
                response=token_response,
            )
            self._send_json(payload, status)
            return

        token_payload = {
            "shop_id": int(shop_id),
            "code": code,
            "generated_at": int(time.time()),
            **token_response,
        }
        _save_token_data(token_payload)
        self._send_json(
            {
                "message": "Autorizacao concluida e token salvo em shopee_token.json.",
                "token_data": _token_snapshot(token_payload),
            }
        )

    def _handle_token_status(self) -> None:
        try:
            token_data = _load_token_data()
        except FileNotFoundError as exc:
            payload, status = _json_error(str(exc), 404)
            self._send_json(payload, status)
            return

        self._send_json(
            {
                "token_file": str(Path(settings.token_file).name),
                "token_data": _token_snapshot(token_data),
            }
        )

    def _handle_refresh_token(self) -> None:
        try:
            token_data = _load_token_data()
        except FileNotFoundError as exc:
            payload, status = _json_error(str(exc), 404)
            self._send_json(payload, status)
            return

        refresh_token_value = token_data.get("refresh_token")
        shop_id = token_data.get("shop_id")
        if not refresh_token_value or not shop_id:
            payload, status = _json_error("Token salvo nao possui refresh_token ou shop_id.", 400)
            self._send_json(payload, status)
            return

        try:
            refresh_response = client.refresh_access_token(
                refresh_token=refresh_token_value,
                shop_id=int(shop_id),
            )
        except (HTTPError, URLError) as exc:
            payload, status = _json_error(
                "Falha ao renovar token.",
                502,
                response=_http_error_body(exc),
            )
            self._send_json(payload, status)
            return

        if refresh_response.get("error"):
            payload, status = _json_error(
                "Shopee retornou erro ao renovar token.",
                400,
                response=refresh_response,
            )
            self._send_json(payload, status)
            return

        new_payload = {
            **token_data,
            "generated_at": int(time.time()),
            **refresh_response,
        }
        _save_token_data(new_payload)
        self._send_json(
            {
                "message": "Token renovado e arquivo atualizado.",
                "token_data": _token_snapshot(new_payload),
            }
        )

    def _handle_shop_info(self) -> None:
        try:
            token_data = _load_token_data()
        except FileNotFoundError as exc:
            payload, status = _json_error(str(exc), 404)
            self._send_json(payload, status)
            return

        try:
            response = client.get_shop_info(
                access_token=token_data["access_token"],
                shop_id=int(token_data["shop_id"]),
            )
        except (HTTPError, URLError) as exc:
            payload, status = _json_error(
                "Falha ao consultar dados da loja.",
                502,
                response=_http_error_body(exc),
            )
            self._send_json(payload, status)
            return

        self._send_json(response)

    def _handle_orders(self, params: dict[str, str]) -> None:
        try:
            token_data = _load_token_data()
        except FileNotFoundError as exc:
            payload, status = _json_error(str(exc), 404)
            self._send_json(payload, status)
            return

        now = int(time.time())
        time_from = int(params.get("time_from", now - 86400))
        time_to = int(params.get("time_to", now))
        page_size = int(params.get("page_size", 20))

        try:
            response = client.get_order_list(
                access_token=token_data["access_token"],
                shop_id=int(token_data["shop_id"]),
                time_from=time_from,
                time_to=time_to,
                page_size=page_size,
                cursor=params.get("cursor"),
                order_status=params.get("order_status"),
                response_optional_fields=params.get("response_optional_fields"),
                time_range_field=params.get("time_range_field", "create_time"),
            )
        except (HTTPError, URLError) as exc:
            payload, status = _json_error(
                "Falha ao consultar pedidos.",
                502,
                response=_http_error_body(exc),
            )
            self._send_json(payload, status)
            return

        self._send_json(response)

    def _handle_products(self, params: dict[str, str]) -> None:
        try:
            token_data = _load_token_data()
        except FileNotFoundError as exc:
            payload, status = _json_error(str(exc), 404)
            self._send_json(payload, status)
            return

        try:
            response = client.get_item_list(
                access_token=token_data["access_token"],
                shop_id=int(token_data["shop_id"]),
                offset=int(params.get("offset", 0)),
                page_size=int(params.get("page_size", 20)),
                item_status=params.get("item_status", "NORMAL"),
            )
        except (HTTPError, URLError) as exc:
            payload, status = _json_error(
                "Falha ao consultar produtos.",
                502,
                response=_http_error_body(exc),
            )
            self._send_json(payload, status)
            return

        self._send_json(response)


def run() -> None:
    port = int(os.getenv("PORT", "5000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), AppHandler)
    print(f"Servidor iniciado em http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

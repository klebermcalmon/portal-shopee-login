from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from config import Settings, get_settings


class ShopeeClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _partner_key_bytes(self) -> bytes:
        return self.settings.partner_key.strip().encode("utf-8")

    def _sign(
        self,
        path: str,
        timestamp: int,
        access_token: str | None = None,
        shop_id: int | None = None,
        include_shop_context: bool = True,
        key_bytes: bytes | None = None,
    ) -> str:
        base_string = f"{self.settings.partner_id}{path}{timestamp}"
        if include_shop_context and access_token:
            base_string += access_token
        if include_shop_context and shop_id is not None:
            base_string += str(shop_id)
        return hmac.new(
            key_bytes or self._partner_key_bytes(),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def build_auth_url(self) -> str:
        path = "/api/v2/shop/auth_partner"
        timestamp = int(time.time())
        query = {
            "partner_id": self.settings.partner_id,
            "timestamp": timestamp,
            "sign": self._sign(path, timestamp, include_shop_context=False),
            "redirect": self.settings.redirect_url,
        }
        return f"{self.settings.auth_host}{path}?{urlencode(query)}"

    def _send_request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any],
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.settings.api_host}{path}?{urlencode(query)}"
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(url=url, data=data, headers=headers, method=method)
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
        return json.loads(body) if body else {}

    def _send_request_raw(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        payload_mode: str = "json",
    ) -> dict[str, Any]:
        url = f"{self.settings.api_host}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        data = None
        headers = {}
        if payload is not None:
            if payload_mode == "form":
                data = urlencode(payload).encode("utf-8")
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                data = json.dumps(payload).encode("utf-8")
                headers["Content-Type"] = "application/json"

        request = Request(url=url, data=data, headers=headers, method=method)
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
        return json.loads(body) if body else {}

    def exchange_token(self, code: str, shop_id: int) -> dict[str, Any]:
        path = "/api/v2/auth/token/get"
        timestamp = int(time.time())
        query = {
            "partner_id": self.settings.partner_id,
            "timestamp": timestamp,
            "sign": self._sign(path, timestamp, include_shop_context=False),
        }
        payload = {
            "code": code,
            "shop_id": int(shop_id),
            "partner_id": self.settings.partner_id,
        }
        url = f"{self.settings.auth_host}{path}?{urlencode(query)}"
        data = json.dumps(payload).encode("utf-8")
        request = Request(url=url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
        return json.loads(body) if body else {}

    def refresh_access_token(self, refresh_token: str, shop_id: int) -> dict[str, Any]:
        path = "/api/v2/auth/access_token/get"
        timestamp = int(time.time())
        query = {
            "partner_id": self.settings.partner_id,
            "timestamp": timestamp,
            "sign": self._sign(path, timestamp, include_shop_context=False),
        }
        payload = {
            "refresh_token": refresh_token,
            "shop_id": int(shop_id),
            "partner_id": self.settings.partner_id,
        }
        url = f"{self.settings.auth_host}{path}?{urlencode(query)}"
        data = json.dumps(payload).encode("utf-8")
        request = Request(url=url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
        return json.loads(body) if body else {}

    def _request(
        self,
        method: str,
        path: str,
        *,
        access_token: str,
        shop_id: int,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        timestamp = int(time.time())
        query: dict[str, Any] = {
            "partner_id": self.settings.partner_id,
            "timestamp": timestamp,
            "access_token": access_token,
            "shop_id": int(shop_id),
            "sign": self._sign(path, timestamp, access_token=access_token, shop_id=shop_id),
        }
        query.update({key: value for key, value in (params or {}).items() if value is not None})
        return self._send_request(method, path, query=query, payload=json_body)

    def get_shop_info(self, access_token: str, shop_id: int) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/v2/shop/get_shop_info",
            access_token=access_token,
            shop_id=shop_id,
        )

    def get_order_list(
        self,
        access_token: str,
        shop_id: int,
        *,
        time_from: int,
        time_to: int,
        page_size: int = 20,
        cursor: str | None = None,
        order_status: str | None = None,
        response_optional_fields: str | None = None,
        time_range_field: str = "create_time",
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/v2/order/get_order_list",
            access_token=access_token,
            shop_id=shop_id,
            params={
                "time_range_field": time_range_field,
                "time_from": int(time_from),
                "time_to": int(time_to),
                "page_size": int(page_size),
                "cursor": cursor,
                "order_status": order_status,
                "response_optional_fields": response_optional_fields,
            },
        )

    def get_item_list(
        self,
        access_token: str,
        shop_id: int,
        *,
        offset: int = 0,
        page_size: int = 20,
        item_status: str = "NORMAL",
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/v2/product/get_item_list",
            access_token=access_token,
            shop_id=shop_id,
            params={
                "offset": int(offset),
                "page_size": int(page_size),
                "item_status": item_status,
            },
        )

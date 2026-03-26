from __future__ import annotations

import argparse
import json
import time
from urllib.parse import parse_qs, urlparse
from urllib.error import HTTPError, URLError

from config import get_settings
from shopee_client import ShopeeClient


def _extract_from_callback_url(callback_url: str) -> tuple[str, int]:
    parsed = urlparse(callback_url)
    params = parse_qs(parsed.query)
    code = (params.get("code") or [""])[0].strip()
    shop_id_raw = (params.get("shop_id") or [""])[0].strip()
    if not code or not shop_id_raw:
        raise ValueError("A URL informada nao contem code e shop_id.")
    return code, int(shop_id_raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Troca o code de autorizacao da Shopee por token e salva em shopee_token.json."
    )
    parser.add_argument("--callback-url", help="URL completa retornada pela Shopee apos autorizacao.")
    parser.add_argument("--code", help="Code retornado pela Shopee.")
    parser.add_argument("--shop-id", type=int, help="Shop ID retornado pela Shopee.")
    args = parser.parse_args()

    if args.callback_url:
        code, shop_id = _extract_from_callback_url(args.callback_url)
    else:
        if not args.code or not args.shop_id:
            parser.error("Informe --callback-url ou entao --code e --shop-id.")
        code, shop_id = args.code.strip(), int(args.shop_id)

    settings = get_settings()
    client = ShopeeClient(settings=settings)

    try:
        token_response = client.exchange_token(code=code, shop_id=shop_id)
    except HTTPError as exc:
        try:
            response_body = exc.read().decode("utf-8")
        except Exception:
            response_body = ""
        print(f"Falha ao trocar code por token: {exc}")
        if response_body:
            print("Resposta da Shopee:")
            print(response_body)
        return 1
    except URLError as exc:
        print(f"Falha ao trocar code por token: {exc}")
        return 1

    if token_response.get("error"):
        print(json.dumps(token_response, ensure_ascii=True, indent=2))
        return 1

    token_payload = {
        "shop_id": shop_id,
        "code": code,
        "generated_at": int(time.time()),
        **token_response,
    }
    settings.token_file.write_text(
        json.dumps(token_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    print(f"Token salvo em {settings.token_file}")
    print(json.dumps(token_payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

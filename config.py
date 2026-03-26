from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv_file(BASE_DIR / ".env")


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Variavel de ambiente obrigatoria nao definida: {name}")
    return value


@dataclass(slots=True)
class Settings:
    env: str
    api_host: str
    auth_host: str
    partner_id: int
    partner_key: str
    redirect_url: str
    flask_debug: bool
    token_file: Path
    app_title: str
    reviewer_username: str
    reviewer_password: str
    shopee_shop_id: int | None
    shopee_access_token: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env = os.getenv("SHOPEE_ENV", "test").strip().lower() or "test"
    default_api_host = (
        "https://openplatform.sandbox.test-stable.shopee.sg"
        if env == "test"
        else "https://partner.shopeemobile.com"
    )
    default_auth_host = (
        "https://partner.test-stable.shopeemobile.com"
        if env == "test"
        else "https://partner.shopeemobile.com"
    )
    return Settings(
        env=env,
        api_host=os.getenv("SHOPEE_API_HOST", default_api_host).strip(),
        auth_host=os.getenv("SHOPEE_AUTH_HOST", os.getenv("SHOPEE_HOST", default_auth_host)).strip(),
        partner_id=int(_get_required_env("SHOPEE_PARTNER_ID")),
        partner_key=_get_required_env("SHOPEE_PARTNER_KEY"),
        redirect_url=_get_required_env("SHOPEE_REDIRECT_URL"),
        flask_debug=os.getenv("FLASK_DEBUG", "false").strip().lower() == "true",
        token_file=BASE_DIR / "shopee_token.json",
        app_title=os.getenv("APP_TITLE", "Portal Shopee Login").strip() or "Portal Shopee Login",
        reviewer_username=os.getenv("REVIEWER_USERNAME", "shopee.review@login.com.br").strip(),
        reviewer_password=os.getenv("REVIEWER_PASSWORD", "Alterar123!").strip(),
        shopee_shop_id=int(os.getenv("SHOPEE_SHOP_ID", "0") or 0) or None,
        shopee_access_token=os.getenv("SHOPEE_ACCESS_TOKEN", "").strip(),
    )

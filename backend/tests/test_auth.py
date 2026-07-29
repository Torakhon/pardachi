"""Autentifikatsiya endpointlari testlari."""

from __future__ import annotations

from httpx import AsyncClient

from tests.test_init_data import build_init_data


async def test_telegram_login_creates_user(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/telegram", json={"init_data": build_init_data(user_id=777)})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["telegram_id"] == 777
    assert body["user"]["role"] == "measurer"
    assert body["user"]["role_label"] == "O'lchovchi"


async def test_telegram_login_with_bad_signature_returns_uzbek_error(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/telegram", json={"init_data": "hash=deadbeef&auth_date=1"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Telegram imzosi noto'g'ri. Ilovani qaytadan oching."


async def test_me_requires_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "avtorizatsiya_xatosi"


async def test_me_returns_profile(client: AsyncClient, measurer_headers: dict[str, str]) -> None:
    response = await client.get("/api/v1/auth/me", headers=measurer_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Test"


async def test_refresh_token_flow(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/dev-login",
        json={"secret": "test-secret", "telegram_id": 6001, "first_name": "Refresh", "role": "measurer"},
    )
    refresh_token = login.json()["refresh_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_rejects_access_token(client: AsyncClient, measurer_headers: dict[str, str]) -> None:
    access_token = measurer_headers["Authorization"].removeprefix("Bearer ")
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


async def test_dev_login_wrong_secret(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/dev-login",
        json={"secret": "wrong", "telegram_id": 1, "first_name": "X", "role": "admin"},
    )
    assert response.status_code == 401


async def test_update_own_profile(client: AsyncClient, measurer_headers: dict[str, str]) -> None:
    response = await client.patch("/api/v1/auth/me", headers=measurer_headers, json={"phone": "901112233"})
    assert response.status_code == 200
    assert response.json()["phone"] == "+998901112233"


async def test_users_endpoint_is_admin_only(client: AsyncClient, measurer_headers: dict[str, str]) -> None:
    response = await client.get("/api/v1/users", headers=measurer_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ruxsat_yoq"


async def test_admin_can_list_users(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    response = await client.get("/api/v1/users", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["meta"]["total"] >= 1


async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


async def test_enums_endpoint_is_in_uzbek(client: AsyncClient) -> None:
    response = await client.get("/api/v1/meta/enums")
    assert response.status_code == 200
    body = response.json()
    labels = {option["value"]: option["label"] for option in body["room_types"]}
    assert labels["living_room"] == "Mehmonxona"
    assert labels["bathroom"] == "Hammom"
    assert {option["label"] for option in body["item_types"]} == {"Oyna", "Eshik"}

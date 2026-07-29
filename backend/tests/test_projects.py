"""Obyekt (loyiha) endpointlari testlari."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from tests.conftest import auth_headers


async def create_project(client: AsyncClient, headers: dict[str, str], payload: dict) -> dict:
    response = await client.post("/api/v1/projects", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_project_normalizes_phone(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    project = await create_project(client, measurer_headers, project_payload)
    assert project["customer_phone"] == "+998901234567"
    assert project["status"] == "draft"
    assert project["status_label"] == "Yangi"
    assert project["creator"]["full_name"] == "Test"


async def test_duplicate_order_number_is_rejected(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    await create_project(client, measurer_headers, project_payload)
    response = await client.post("/api/v1/projects", headers=measurer_headers, json=project_payload)
    assert response.status_code == 409
    assert "buyurtma raqami" in response.json()["error"]["message"]


async def test_offline_sync_is_idempotent(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    client_id = str(uuid.uuid4())
    payload = {**project_payload, "id": client_id}

    first = await create_project(client, measurer_headers, payload)
    second = await client.post("/api/v1/projects", headers=measurer_headers, json=payload)

    assert second.status_code == 201
    assert first["id"] == client_id == second.json()["id"]

    listing = await client.get("/api/v1/projects", headers=measurer_headers)
    assert listing.json()["meta"]["total"] == 1


async def test_create_project_with_rooms_and_items(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    payload = {
        **project_payload,
        "location": {"latitude": "41.311081", "longitude": "69.240562", "source": "telegram"},
        "rooms": [
            {
                "name": "Mehmonxona",
                "room_type": "living_room",
                "items": [
                    {
                        "name": "Oyna 1",
                        "item_type": "window",
                        "width_cm": "150.00",
                        "height_cm": "220.00",
                        "curtain_width_cm": "300.00",
                        "fabric_type": "Blackout",
                    }
                ],
            }
        ],
    }
    project = await create_project(client, measurer_headers, payload)

    assert project["rooms_count"] == 1
    assert project["rooms"][0]["room_type_label"] == "Mehmonxona"
    assert project["rooms"][0]["windows_count"] == 1
    assert project["rooms"][0]["items"][0]["size_label"] == "150 × 220 sm"
    assert project["location"]["maps_url"].startswith("https://www.google.com/maps?q=41.311081")


async def test_measurer_cannot_see_other_projects(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    project = await create_project(client, measurer_headers, project_payload)
    other_headers = await auth_headers(client, role="measurer", telegram_id=999888)

    response = await client.get(f"/api/v1/projects/{project['id']}", headers=other_headers)
    assert response.status_code == 403

    listing = await client.get("/api/v1/projects", headers=other_headers)
    assert listing.json()["meta"]["total"] == 0


async def test_admin_sees_all_projects(
    client: AsyncClient,
    measurer_headers: dict[str, str],
    admin_headers: dict[str, str],
    project_payload: dict,
) -> None:
    project = await create_project(client, measurer_headers, project_payload)
    response = await client.get(f"/api/v1/projects/{project['id']}", headers=admin_headers)
    assert response.status_code == 200

    listing = await client.get("/api/v1/projects", headers=admin_headers)
    assert listing.json()["meta"]["total"] == 1


async def test_search_and_filters(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    await create_project(client, measurer_headers, project_payload)
    await create_project(
        client,
        measurer_headers,
        {
            **project_payload,
            "name": "Yunusobod xonadon",
            "order_number": "OB-TEST-002",
            "customer_name": "Nilufar Karimova",
            "customer_phone": "+998935558877",
        },
    )

    by_name = await client.get("/api/v1/projects?search=Yunusobod", headers=measurer_headers)
    assert by_name.json()["meta"]["total"] == 1

    by_customer = await client.get("/api/v1/projects?search=Nilufar", headers=measurer_headers)
    assert by_customer.json()["meta"]["total"] == 1

    by_order = await client.get("/api/v1/projects?search=OB-TEST-001", headers=measurer_headers)
    assert by_order.json()["meta"]["total"] == 1

    by_phone = await client.get("/api/v1/projects?search=935558877", headers=measurer_headers)
    assert by_phone.json()["meta"]["total"] == 1

    by_status = await client.get("/api/v1/projects?status=completed", headers=measurer_headers)
    assert by_status.json()["meta"]["total"] == 0


async def test_update_project(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    project = await create_project(client, measurer_headers, project_payload)
    response = await client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=measurer_headers,
        json={"name": "Yangilangan nom", "address": "Yangi manzil"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Yangilangan nom"


async def test_completion_requires_photo_and_items(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    project = await create_project(client, measurer_headers, project_payload)

    empty = await client.patch(
        f"/api/v1/projects/{project['id']}/status",
        headers=measurer_headers,
        json={"status": "completed"},
    )
    assert empty.status_code == 422
    assert "xona qo'shing" in empty.json()["error"]["message"]

    await client.post(
        f"/api/v1/projects/{project['id']}/rooms",
        headers=measurer_headers,
        json={"name": "Zal", "room_type": "hall"},
    )
    without_photo = await client.patch(
        f"/api/v1/projects/{project['id']}/status",
        headers=measurer_headers,
        json={"status": "completed"},
    )
    assert without_photo.status_code == 422
    assert "rasm yuklanmagan" in without_photo.json()["error"]["message"]


async def test_soft_delete_hides_project(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    project = await create_project(client, measurer_headers, project_payload)

    response = await client.delete(f"/api/v1/projects/{project['id']}", headers=measurer_headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Obyekt o'chirildi."

    missing = await client.get(f"/api/v1/projects/{project['id']}", headers=measurer_headers)
    assert missing.status_code == 404

    listing = await client.get("/api/v1/projects", headers=measurer_headers)
    assert listing.json()["meta"]["total"] == 0


async def test_admin_can_restore_project(
    client: AsyncClient,
    measurer_headers: dict[str, str],
    admin_headers: dict[str, str],
    project_payload: dict,
) -> None:
    project = await create_project(client, measurer_headers, project_payload)
    await client.delete(f"/api/v1/projects/{project['id']}", headers=measurer_headers)

    restored = await client.post(f"/api/v1/projects/{project['id']}/restore", headers=admin_headers)
    assert restored.status_code == 200
    assert restored.json()["id"] == project["id"]


async def test_next_order_number_is_unique(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    first = await client.get("/api/v1/projects/next-order-number", headers=measurer_headers)
    number = first.json()["order_number"]
    assert number.startswith("OB-")

    await create_project(client, measurer_headers, {**project_payload, "order_number": number})

    second = await client.get("/api/v1/projects/next-order-number", headers=measurer_headers)
    assert second.json()["order_number"] != number


async def test_validation_errors_are_in_uzbek(client: AsyncClient, measurer_headers: dict[str, str]) -> None:
    response = await client.post(
        "/api/v1/projects",
        headers=measurer_headers,
        json={"name": "A", "order_number": "", "customer_name": "B", "customer_phone": "telefon"},
    )
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["message"] == "Ma'lumotlar to'liq yoki to'g'ri kiritilmagan."
    assert "customer_phone" in body["details"]["fields"]
    assert body["details"]["fields"]["customer_phone"].startswith("Telefon raqami noto'g'ri")


async def test_dashboard_stats(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    await create_project(client, measurer_headers, project_payload)
    response = await client.get("/api/v1/stats/dashboard", headers=measurer_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["projects_total"] == 1
    assert body["projects_draft"] == 1
    assert len(body["recent_projects"]) == 1

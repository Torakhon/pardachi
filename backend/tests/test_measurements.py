"""Xona, o'lchov va rasm endpointlari testlari."""

from __future__ import annotations

import io

import pytest
from httpx import AsyncClient
from PIL import Image


async def make_project(client: AsyncClient, headers: dict[str, str], payload: dict) -> str:
    response = await client.post("/api/v1/projects", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def make_room(client: AsyncClient, headers: dict[str, str], project_id: str, name: str = "Zal") -> str:
    response = await client.post(
        f"/api/v1/projects/{project_id}/rooms",
        headers=headers,
        json={"name": name, "room_type": "hall"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def sample_image(size: tuple[int, int] = (2400, 1800), fmt: str = "JPEG") -> bytes:
    image = Image.new("RGB", size, (120, 90, 60))
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
async def room_id(client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict) -> str:
    project_id = await make_project(client, measurer_headers, project_payload)
    return await make_room(client, measurer_headers, project_id)


async def test_adding_room_moves_project_to_in_progress(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    project_id = await make_project(client, measurer_headers, project_payload)
    await make_room(client, measurer_headers, project_id)

    project = await client.get(f"/api/v1/projects/{project_id}", headers=measurer_headers)
    assert project.json()["status"] == "in_progress"
    assert project.json()["status_label"] == "Jarayonda"


async def test_create_and_read_measurement(
    client: AsyncClient, measurer_headers: dict[str, str], room_id: str
) -> None:
    response = await client.post(
        f"/api/v1/rooms/{room_id}/items",
        headers=measurer_headers,
        json={
            "name": "Oyna 1",
            "item_type": "window",
            "width_cm": "150.5",
            "height_cm": "220",
            "curtain_width_cm": "301",
            "curtain_height_cm": "230",
            "cornice_width_cm": "190",
            "cornice_height_cm": "8",
            "fabric_type": "Blackout",
            "curtain_model": "Klassik",
            "fabric_color": "Bej",
            "notes": "Karniz shift ostida",
        },
    )
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["type_label"] == "Oyna"
    assert item["size_label"] == "150.5 × 220 sm"
    assert item["area_m2"] == pytest.approx(3.311, abs=0.01)
    assert item["sort_order"] == 1

    listing = await client.get(f"/api/v1/rooms/{room_id}/items", headers=measurer_headers)
    assert len(listing.json()) == 1


async def test_measurement_validation_rejects_zero_width(
    client: AsyncClient, measurer_headers: dict[str, str], room_id: str
) -> None:
    response = await client.post(
        f"/api/v1/rooms/{room_id}/items",
        headers=measurer_headers,
        json={"name": "Oyna", "item_type": "window", "width_cm": "0", "height_cm": "200"},
    )
    assert response.status_code == 422
    fields = response.json()["error"]["details"]["fields"]
    assert fields["width_cm"] == "Qiymat noldan katta bo'lishi kerak."


async def test_suggest_name_counts_by_type(
    client: AsyncClient, measurer_headers: dict[str, str], room_id: str
) -> None:
    first = await client.get(
        f"/api/v1/rooms/{room_id}/items/suggest-name?item_type=window", headers=measurer_headers
    )
    assert first.json()["name"] == "Oyna 1"

    await client.post(
        f"/api/v1/rooms/{room_id}/items",
        headers=measurer_headers,
        json={"name": "Oyna 1", "item_type": "window", "width_cm": "100", "height_cm": "200"},
    )

    second = await client.get(
        f"/api/v1/rooms/{room_id}/items/suggest-name?item_type=window", headers=measurer_headers
    )
    assert second.json()["name"] == "Oyna 2"

    door = await client.get(
        f"/api/v1/rooms/{room_id}/items/suggest-name?item_type=door", headers=measurer_headers
    )
    assert door.json()["name"] == "Eshik 1"


async def test_update_and_delete_measurement(
    client: AsyncClient, measurer_headers: dict[str, str], room_id: str
) -> None:
    created = await client.post(
        f"/api/v1/rooms/{room_id}/items",
        headers=measurer_headers,
        json={"name": "Eshik 1", "item_type": "door", "width_cm": "90", "height_cm": "210"},
    )
    item_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/measurements/{item_id}",
        headers=measurer_headers,
        json={"fabric_color": "Oq", "width_cm": "95"},
    )
    assert updated.status_code == 200
    assert updated.json()["fabric_color"] == "Oq"
    assert float(updated.json()["width_cm"]) == 95

    deleted = await client.delete(f"/api/v1/measurements/{item_id}", headers=measurer_headers)
    assert deleted.status_code == 200

    missing = await client.get(f"/api/v1/measurements/{item_id}", headers=measurer_headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["message"] == "O'lchov topilmadi."


async def test_reorder_items(client: AsyncClient, measurer_headers: dict[str, str], room_id: str) -> None:
    ids = []
    for index in range(3):
        response = await client.post(
            f"/api/v1/rooms/{room_id}/items",
            headers=measurer_headers,
            json={
                "name": f"Oyna {index + 1}",
                "item_type": "window",
                "width_cm": "120",
                "height_cm": "200",
            },
        )
        ids.append(response.json()["id"])

    reordered = await client.post(
        f"/api/v1/rooms/{room_id}/items/reorder",
        headers=measurer_headers,
        json={"item_ids": list(reversed(ids))},
    )
    assert reordered.status_code == 200
    assert [item["id"] for item in reordered.json()] == list(reversed(ids))


async def test_upload_compresses_and_replaces_image(
    client: AsyncClient, measurer_headers: dict[str, str], room_id: str
) -> None:
    response = await client.post(
        f"/api/v1/rooms/{room_id}/image",
        headers=measurer_headers,
        files={"file": ("xona.jpg", sample_image(), "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    image = response.json()
    assert image["width"] <= 1600 and image["height"] <= 1600
    assert image["content_type"] == "image/jpeg"
    first_url = image["url"]

    replaced = await client.post(
        f"/api/v1/rooms/{room_id}/image",
        headers=measurer_headers,
        files={"file": ("xona2.png", sample_image((800, 600), "PNG"), "image/png")},
    )
    assert replaced.status_code == 201
    assert replaced.json()["url"] != first_url

    room = await client.get(f"/api/v1/rooms/{room_id}", headers=measurer_headers)
    assert room.json()["has_image"] is True
    assert room.json()["image"]["url"] == replaced.json()["url"]


async def test_upload_rejects_non_image(
    client: AsyncClient, measurer_headers: dict[str, str], room_id: str
) -> None:
    response = await client.post(
        f"/api/v1/rooms/{room_id}/image",
        headers=measurer_headers,
        files={"file": ("hujjat.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 422
    assert "JPG" in response.json()["error"]["message"]


async def test_delete_room_image(client: AsyncClient, measurer_headers: dict[str, str], room_id: str) -> None:
    await client.post(
        f"/api/v1/rooms/{room_id}/image",
        headers=measurer_headers,
        files={"file": ("xona.jpg", sample_image((600, 400)), "image/jpeg")},
    )
    deleted = await client.delete(f"/api/v1/rooms/{room_id}/image", headers=measurer_headers)
    assert deleted.status_code == 200

    missing = await client.get(f"/api/v1/rooms/{room_id}/image", headers=measurer_headers)
    assert missing.status_code == 404


async def test_full_project_can_be_completed(
    client: AsyncClient, measurer_headers: dict[str, str], project_payload: dict
) -> None:
    project_id = await make_project(client, measurer_headers, project_payload)
    room = await make_room(client, measurer_headers, project_id, "Mehmonxona")

    await client.post(
        f"/api/v1/rooms/{room}/items",
        headers=measurer_headers,
        json={"name": "Oyna 1", "item_type": "window", "width_cm": "150", "height_cm": "220"},
    )
    await client.post(
        f"/api/v1/rooms/{room}/image",
        headers=measurer_headers,
        files={"file": ("xona.jpg", sample_image((1200, 900)), "image/jpeg")},
    )

    completed = await client.patch(
        f"/api/v1/projects/{project_id}/status",
        headers=measurer_headers,
        json={"status": "completed"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status_label"] == "Yakunlangan"
    assert completed.json()["completed_at"] is not None

    measurements = await client.get(f"/api/v1/projects/{project_id}/measurements", headers=measurer_headers)
    assert len(measurements.json()) == 1


async def test_delete_room_removes_items(
    client: AsyncClient, measurer_headers: dict[str, str], room_id: str
) -> None:
    created = await client.post(
        f"/api/v1/rooms/{room_id}/items",
        headers=measurer_headers,
        json={"name": "Oyna 1", "item_type": "window", "width_cm": "150", "height_cm": "220"},
    )
    item_id = created.json()["id"]

    deleted = await client.delete(f"/api/v1/rooms/{room_id}", headers=measurer_headers)
    assert deleted.status_code == 200

    missing = await client.get(f"/api/v1/measurements/{item_id}", headers=measurer_headers)
    assert missing.status_code == 404

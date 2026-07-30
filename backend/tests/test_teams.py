"""Jamoalar va ma'lumotlar izolyatsiyasi testlari."""

from __future__ import annotations

from httpx import AsyncClient

API = "/api/v1"


async def _create_project(client: AsyncClient, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "name": "Jamoa obyekti",
        "order_number": "OB-TEAM-001",
        "customer_name": "Sardor Aliyev",
        "customer_phone": "+998901234567",
        "address": "Toshkent",
    }
    payload.update(overrides)
    response = await client.post(f"{API}/projects", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ------------------------------------------------------------ jamoa CRUD


async def test_admin_creates_team(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    response = await client.post(
        f"{API}/teams",
        headers=admin_headers,
        json={"name": "Andijon jamoasi", "description": "Andijon yo'nalishi"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Andijon jamoasi"
    assert body["is_active"] is True
    assert body["status_label"] == "Faol"


async def test_duplicate_team_name_is_rejected(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    await client.post(f"{API}/teams", headers=admin_headers, json={"name": "Farg'ona jamoasi"})
    response = await client.post(f"{API}/teams", headers=admin_headers, json={"name": "farg'ona jamoasi"})
    assert response.status_code == 409
    assert "allaqachon mavjud" in response.json()["error"]["message"]


async def test_measurer_cannot_create_team(client: AsyncClient, measurer_headers: dict[str, str]) -> None:
    response = await client.post(f"{API}/teams", headers=measurer_headers, json={"name": "Yangi"})
    assert response.status_code == 403


async def test_member_sees_only_own_team_in_list(
    client: AsyncClient, measurer_headers: dict[str, str], other_headers: dict[str, str]
) -> None:
    mine = await client.get(f"{API}/teams", headers=measurer_headers)
    theirs = await client.get(f"{API}/teams", headers=other_headers)
    assert mine.status_code == 200 and theirs.status_code == 200

    my_teams = [team["name"] for team in mine.json()]
    their_teams = [team["name"] for team in theirs.json()]
    assert my_teams == ["Toshkent jamoasi"]
    assert their_teams == ["Samarqand jamoasi"]


# ------------------------------------------------------ a'zolarni boshqarish


async def test_admin_assigns_member_by_telegram_id(
    client: AsyncClient, admin_headers: dict[str, str], team
) -> None:
    """Hali ilovaga kirmagan odamni ham Telegram ID orqali jamoaga qo'shish mumkin."""
    response = await client.post(
        f"{API}/teams/{team.id}/members",
        headers=admin_headers,
        json={"telegram_id": 991001, "first_name": "Yangi O'lchovchi", "role": "measurer"},
    )
    assert response.status_code == 201, response.text
    member = response.json()
    assert member["telegram_id"] == 991001
    assert member["role"] == "measurer"
    assert member["team_id"] == str(team.id)

    members = await client.get(f"{API}/teams/{team.id}/members", headers=admin_headers)
    assert any(m["telegram_id"] == 991001 for m in members.json())


async def test_assigned_user_keeps_role_after_first_login(
    client: AsyncClient, admin_headers: dict[str, str], team
) -> None:
    """Oldindan biriktirilgan foydalanuvchi Telegram orqali kirganda roli saqlanadi."""
    from tests.test_init_data import build_init_data

    await client.post(
        f"{API}/teams/{team.id}/members",
        headers=admin_headers,
        json={"telegram_id": 991002, "role": "measurer"},
    )
    response = await client.post(f"{API}/auth/telegram", json={"init_data": build_init_data(user_id=991002)})
    assert response.status_code == 200, response.text
    user = response.json()["user"]
    assert user["role"] == "measurer"
    assert user["team_id"] == str(team.id)
    assert user["team_name"] == "Toshkent jamoasi"


async def test_remove_member_from_team(client: AsyncClient, admin_headers: dict[str, str], team) -> None:
    created = await client.post(
        f"{API}/teams/{team.id}/members",
        headers=admin_headers,
        json={"telegram_id": 991003, "role": "viewer"},
    )
    user_id = created.json()["id"]

    response = await client.delete(f"{API}/teams/{team.id}/members/{user_id}", headers=admin_headers)
    assert response.status_code == 200

    members = await client.get(f"{API}/teams/{team.id}/members", headers=admin_headers)
    assert all(m["id"] != user_id for m in members.json())


# ------------------------------------------------- ma'lumotlar izolyatsiyasi


async def test_other_team_cannot_see_project(
    client: AsyncClient, measurer_headers: dict[str, str], other_headers: dict[str, str]
) -> None:
    project = await _create_project(client, measurer_headers)

    detail = await client.get(f"{API}/projects/{project['id']}", headers=other_headers)
    assert detail.status_code == 403
    assert "boshqa jamoaga tegishli" in detail.json()["error"]["message"]

    listing = await client.get(f"{API}/projects", headers=other_headers)
    assert listing.json()["meta"]["total"] == 0


async def test_teammate_sees_but_cannot_edit_others_project(
    client: AsyncClient, measurer_headers: dict[str, str], teammate_headers: dict[str, str]
) -> None:
    """Bitta jamoadagilar bir-birining ishini ko'radi, lekin tahrirlay olmaydi."""
    project = await _create_project(client, measurer_headers)

    detail = await client.get(f"{API}/projects/{project['id']}", headers=teammate_headers)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Jamoa obyekti"

    edit = await client.patch(
        f"{API}/projects/{project['id']}", headers=teammate_headers, json={"name": "O'zgardi"}
    )
    assert edit.status_code == 403


async def test_admin_sees_all_teams_projects(
    client: AsyncClient,
    admin_headers: dict[str, str],
    measurer_headers: dict[str, str],
    other_headers: dict[str, str],
) -> None:
    await _create_project(client, measurer_headers, order_number="OB-T1")
    await _create_project(client, other_headers, order_number="OB-T2")

    listing = await client.get(f"{API}/projects?size=50", headers=admin_headers)
    assert listing.json()["meta"]["total"] == 2

    teams = {item["team_name"] for item in listing.json()["items"]}
    assert teams == {"Toshkent jamoasi", "Samarqand jamoasi"}


async def test_admin_can_filter_projects_by_team(
    client: AsyncClient,
    admin_headers: dict[str, str],
    measurer_headers: dict[str, str],
    other_headers: dict[str, str],
    team,
) -> None:
    await _create_project(client, measurer_headers, order_number="OB-F1")
    await _create_project(client, other_headers, order_number="OB-F2")

    filtered = await client.get(f"{API}/projects?team_id={team.id}", headers=admin_headers)
    assert filtered.json()["meta"]["total"] == 1
    assert filtered.json()["items"][0]["team_name"] == "Toshkent jamoasi"


async def test_search_does_not_leak_across_teams(
    client: AsyncClient, measurer_headers: dict[str, str], other_headers: dict[str, str]
) -> None:
    await _create_project(client, measurer_headers, customer_name="Maxfiy Mijoz")

    found = await client.get(f"{API}/projects?search=Maxfiy", headers=other_headers)
    assert found.json()["meta"]["total"] == 0


async def test_dashboard_is_scoped_to_team(
    client: AsyncClient, measurer_headers: dict[str, str], other_headers: dict[str, str]
) -> None:
    await _create_project(client, measurer_headers)

    mine = await client.get(f"{API}/stats/dashboard", headers=measurer_headers)
    theirs = await client.get(f"{API}/stats/dashboard", headers=other_headers)
    assert mine.json()["projects_total"] == 1
    assert theirs.json()["projects_total"] == 0


# ------------------------------------------------------------ Ko'ruvchi roli


async def test_viewer_can_read_team_projects(
    client: AsyncClient, measurer_headers: dict[str, str], viewer_headers: dict[str, str]
) -> None:
    project = await _create_project(client, measurer_headers)

    detail = await client.get(f"{API}/projects/{project['id']}", headers=viewer_headers)
    assert detail.status_code == 200

    listing = await client.get(f"{API}/projects", headers=viewer_headers)
    assert listing.json()["meta"]["total"] == 1


async def test_viewer_cannot_create_or_edit(
    client: AsyncClient, measurer_headers: dict[str, str], viewer_headers: dict[str, str]
) -> None:
    project = await _create_project(client, measurer_headers)

    create = await client.post(
        f"{API}/projects",
        headers=viewer_headers,
        json={
            "name": "Ko'ruvchi obyekti",
            "order_number": "OB-V1",
            "customer_name": "Mijoz",
            "customer_phone": "+998901112233",
            "address": "Toshkent",
        },
    )
    assert create.status_code == 403
    assert "Ko'ruvchi" in create.json()["error"]["message"]

    edit = await client.patch(
        f"{API}/projects/{project['id']}", headers=viewer_headers, json={"name": "O'zgardi"}
    )
    assert edit.status_code == 403

    delete = await client.delete(f"{API}/projects/{project['id']}", headers=viewer_headers)
    assert delete.status_code == 403


async def test_viewer_cannot_add_rooms_or_measurements(
    client: AsyncClient, measurer_headers: dict[str, str], viewer_headers: dict[str, str]
) -> None:
    project = await _create_project(client, measurer_headers)
    room = await client.post(
        f"{API}/projects/{project['id']}/rooms",
        headers=measurer_headers,
        json={"name": "Mehmonxona", "room_type": "living_room"},
    )
    room_id = room.json()["id"]

    add_room = await client.post(
        f"{API}/projects/{project['id']}/rooms", headers=viewer_headers, json={"name": "Yotoqxona"}
    )
    assert add_room.status_code == 403

    add_item = await client.post(
        f"{API}/rooms/{room_id}/items",
        headers=viewer_headers,
        json={"name": "Oyna 1", "item_type": "window", "width_cm": "150", "height_cm": "220"},
    )
    assert add_item.status_code == 403


# -------------------------------------------------------- jamoasiz foydalanuvchi


async def test_user_without_team_sees_nothing(
    client: AsyncClient, measurer_headers: dict[str, str], teamless_headers: dict[str, str]
) -> None:
    await _create_project(client, measurer_headers)

    listing = await client.get(f"{API}/projects", headers=teamless_headers)
    assert listing.json()["meta"]["total"] == 0

    dashboard = await client.get(f"{API}/stats/dashboard", headers=teamless_headers)
    assert dashboard.json()["projects_total"] == 0


async def test_user_without_team_cannot_create_project(
    client: AsyncClient, teamless_headers: dict[str, str]
) -> None:
    response = await client.post(
        f"{API}/projects",
        headers=teamless_headers,
        json={
            "name": "Obyekt",
            "order_number": "OB-NT-1",
            "customer_name": "Mijoz",
            "customer_phone": "+998901112233",
            "address": "Toshkent",
        },
    )
    assert response.status_code == 422
    assert "jamoaga biriktirilmagansiz" in response.json()["error"]["message"]


# ------------------------------------------------------------ jamoani o'chirish


async def test_team_with_projects_cannot_be_deleted(
    client: AsyncClient, admin_headers: dict[str, str], measurer_headers: dict[str, str], team
) -> None:
    await _create_project(client, measurer_headers)

    response = await client.delete(f"{API}/teams/{team.id}", headers=admin_headers)
    assert response.status_code == 409
    assert "obyekt bor" in response.json()["error"]["message"]

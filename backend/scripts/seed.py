"""Namunaviy ma'lumotlarni bazaga yuklash.

Ishlatish:
    python -m scripts.seed            # namunaviy ma'lumot qo'shadi
    python -m scripts.seed --reset    # avval barcha ma'lumotni tozalaydi
"""

from __future__ import annotations

import argparse
import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, select

from app.core.logging import setup_logging
from app.domain.enums import LocationSource, MeasurementItemType, ProjectStatus, RoomType, UserRole
from app.domain.models import (
    AuditLog,
    MeasurementItem,
    Project,
    ProjectLocation,
    Room,
    RoomImage,
    User,
)
from app.infrastructure.db.session import session_scope

ROOM_PRESETS: list[tuple[str, RoomType]] = [
    ("Mehmonxona", RoomType.LIVING_ROOM),
    ("Yotoqxona", RoomType.BEDROOM),
    ("Oshxona", RoomType.KITCHEN),
    ("Bolalar xonasi", RoomType.KIDS_ROOM),
    ("Zal", RoomType.HALL),
    ("Koridor", RoomType.CORRIDOR),
    ("Hammom", RoomType.BATHROOM),
]

FABRICS = ["Tyul", "Blackout", "Baxmal", "Jakkard", "Organza"]
MODELS = ["Klassik", "Rim pardasi", "Rulon parda", "Tyul + portyera", "Lambrekenli"]
COLORS = ["Oq", "Bej", "Kulrang", "To'q ko'k", "Zaytun yashil", "Shokolad"]

CUSTOMERS = [
    ("Sardor Aliyev", "+998901234567", "Toshkent sh., Chilonzor 12-kvartal, 45-uy"),
    ("Nilufar Karimova", "+998935558877", "Toshkent sh., Yunusobod 19-mavze, 7-uy, 34-xonadon"),
    ("Jasur Rahimov", "+998971112233", "Samarqand sh., Registon ko'chasi 15-uy"),
    ("Malika To'xtayeva", "+998944445566", "Buxoro sh., Mustaqillik ko'chasi 88-uy"),
    ("Bekzod Yo'ldoshev", "+998909998877", "Toshkent v., Zangiota tumani, Bog'ishamol 4"),
    ("Zilola Ergasheva", "+998912223344", "Andijon sh., Navoiy shoh ko'chasi 21-uy"),
]

PROJECT_NAMES = [
    "Chilonzor kvartira",
    "Yunusobod xonadon",
    "Registon uyi",
    "Buxoro kottej",
    "Zangiota bog' uyi",
    "Andijon ofis",
]


async def reset_data() -> None:
    async with session_scope() as session:
        for model in (AuditLog, MeasurementItem, RoomImage, Room, ProjectLocation, Project, User):
            await session.execute(delete(model))
    print("Barcha ma'lumotlar tozalandi.")


async def seed() -> None:
    random.seed(2026)
    async with session_scope() as session:
        existing = (await session.execute(select(User).limit(1))).scalar_one_or_none()
        if existing is not None:
            print("Bazada allaqachon ma'lumot bor. Avval `--reset` bilan tozalang.")
            return

        admin = User(
            telegram_id=100000001,
            username="pardachi_admin",
            first_name="Alisher",
            last_name="Nazarov",
            phone="+998901110011",
            role=UserRole.ADMIN,
        )
        measurers = [
            User(
                telegram_id=100000002,
                username="olchovchi_1",
                first_name="Rustam",
                last_name="Qodirov",
                phone="+998902220022",
                role=UserRole.MEASURER,
            ),
            User(
                telegram_id=100000003,
                username="olchovchi_2",
                first_name="Dilnoza",
                last_name="Yusupova",
                phone="+998903330033",
                role=UserRole.MEASURER,
            ),
        ]
        session.add_all([admin, *measurers])
        await session.flush()

        statuses = [
            ProjectStatus.COMPLETED,
            ProjectStatus.IN_PROGRESS,
            ProjectStatus.DRAFT,
            ProjectStatus.COMPLETED,
            ProjectStatus.IN_PROGRESS,
            ProjectStatus.DRAFT,
        ]

        pairs = zip(PROJECT_NAMES, CUSTOMERS, strict=True)
        for index, (name, (customer, phone, address)) in enumerate(pairs):
            created_at = datetime.now(UTC) - timedelta(days=len(PROJECT_NAMES) - index, hours=index)
            measurer = measurers[index % len(measurers)]
            status = statuses[index]

            project = Project(
                id=uuid.uuid4(),
                name=name,
                order_number=f"OB-{created_at:%Y%m%d}-{index + 1:03d}",
                customer_name=customer,
                customer_phone=phone,
                address=address,
                note="Mijoz och rangdagi pardalarni afzal ko'radi." if index % 2 == 0 else None,
                status=status,
                created_by_id=measurer.id,
                updated_by_id=measurer.id,
                created_at=created_at,
                updated_at=created_at,
                completed_at=created_at + timedelta(hours=3) if status is ProjectStatus.COMPLETED else None,
            )
            project.location = ProjectLocation(
                latitude=Decimal(str(round(random.uniform(39.6, 41.4), 6))),
                longitude=Decimal(str(round(random.uniform(64.4, 72.3), 6))),
                accuracy_m=Decimal(str(round(random.uniform(4, 25), 2))),
                source=LocationSource.TELEGRAM if index % 2 == 0 else LocationSource.BROWSER,
                captured_at=created_at,
            )

            for room_index, (room_name, room_type) in enumerate(
                random.sample(ROOM_PRESETS, k=random.randint(2, 4)), start=1
            ):
                room = Room(
                    id=uuid.uuid4(),
                    name=room_name,
                    room_type=room_type,
                    sort_order=room_index,
                    note=None,
                    created_at=created_at,
                    updated_at=created_at,
                )

                windows = random.randint(1, 3)
                doors = random.randint(0, 1)
                sort_order = 0
                for window_index in range(1, windows + 1):
                    sort_order += 1
                    width = Decimal(str(random.choice([120, 140, 150, 165, 180, 210])))
                    height = Decimal(str(random.choice([140, 180, 210, 240, 265])))
                    room.items.append(
                        MeasurementItem(
                            name=f"Oyna {window_index}",
                            item_type=MeasurementItemType.WINDOW,
                            quantity=1,
                            width_cm=width,
                            height_cm=height,
                            curtain_width_cm=width * Decimal("2.0"),
                            curtain_height_cm=height + Decimal("10"),
                            cornice_width_cm=width + Decimal("40"),
                            cornice_height_cm=Decimal("8.00"),
                            fabric_type=random.choice(FABRICS),
                            curtain_model=random.choice(MODELS),
                            fabric_color=random.choice(COLORS),
                            notes="Karniz shift ostiga o'rnatiladi." if window_index == 1 else None,
                            sort_order=sort_order,
                        )
                    )
                for door_index in range(1, doors + 1):
                    sort_order += 1
                    room.items.append(
                        MeasurementItem(
                            name=f"Eshik {door_index}",
                            item_type=MeasurementItemType.DOOR,
                            quantity=1,
                            width_cm=Decimal(str(random.choice([80, 90, 120]))),
                            height_cm=Decimal("210"),
                            curtain_width_cm=Decimal("200"),
                            curtain_height_cm=Decimal("215"),
                            cornice_width_cm=Decimal("160"),
                            cornice_height_cm=Decimal("8.00"),
                            fabric_type=random.choice(FABRICS),
                            curtain_model=random.choice(MODELS),
                            fabric_color=random.choice(COLORS),
                            sort_order=sort_order,
                        )
                    )

                if status is not ProjectStatus.DRAFT:
                    room.image = RoomImage(
                        storage_key=f"rooms/sample/{room.id}.jpg",
                        url=f"/media/rooms/sample/{room.id}.jpg",
                        content_type="image/jpeg",
                        size_bytes=random.randint(180_000, 900_000),
                        width=1600,
                        height=1200,
                        uploaded_by_id=measurer.id,
                    )

                project.rooms.append(room)

            session.add(project)

        print("Namunaviy ma'lumotlar qo'shildi:")
        print("  Admin      : Alisher Nazarov (telegram_id=100000001)")
        print("  O'lchovchi : Rustam Qodirov (telegram_id=100000002)")
        print("  O'lchovchi : Dilnoza Yusupova (telegram_id=100000003)")
        print(f"  Obyektlar  : {len(PROJECT_NAMES)} ta")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Pardachi namunaviy ma'lumotlari")
    parser.add_argument("--reset", action="store_true", help="Avval barcha ma'lumotni o'chirish")
    args = parser.parse_args()

    setup_logging("WARNING", json_logs=False)
    if args.reset:
        await reset_data()
    await seed()


if __name__ == "__main__":
    asyncio.run(main())

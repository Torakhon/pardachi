#!/bin/sh
set -e

echo "[pardachi] Ma'lumotlar bazasi kutilmoqda..."
python - <<'PY'
import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import create_async_engine

url = os.environ.get("DATABASE_URL", "")


async def wait_for_db() -> None:
    from sqlalchemy import text

    for attempt in range(1, 31):
        try:
            engine = create_async_engine(url)
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            await engine.dispose()
            print(f"[pardachi] Baza tayyor ({attempt}-urinish).")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[pardachi] Baza hali tayyor emas ({attempt}/30): {exc}")
            await asyncio.sleep(2)
    sys.exit("[pardachi] Bazaga ulanib bo'lmadi.")


asyncio.run(wait_for_db())
PY

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "[pardachi] Migratsiyalar qo'llanmoqda..."
    alembic upgrade head
fi

if [ "${RUN_SEED:-false}" = "true" ]; then
    echo "[pardachi] Namunaviy ma'lumotlar yuklanmoqda..."
    python -m scripts.seed || true
fi

echo "[pardachi] Server ishga tushmoqda: $*"
exec "$@"

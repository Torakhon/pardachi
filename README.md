# Pardachi — parda o'lchov boshqaruv tizimi

Parda va to'qimachilik kompaniyalari uchun **Telegram Mini App**. O'lchovchi mijoznikiga borib,
obyekt yaratadi, har bir xonani rasmga oladi va oyna/eshiklarning o'lchamlarini kiritadi.
Tikuv bo'limi esa barcha ma'lumotni raqamli ko'rinishda oladi — daftar va qog'oz kerak emas.

**Ilova interfeysi 100% o'zbek tilida.**

---

## Mundarija

- [Imkoniyatlar](#imkoniyatlar)
- [Texnologiyalar](#texnologiyalar)
- [Tez ishga tushirish](#tez-ishga-tushirish)
- [Telegram botni sozlash](#telegram-botni-sozlash)
- [Loyiha tuzilmasi](#loyiha-tuzilmasi)
- [Ma'lumotlar bazasi](#malumotlar-bazasi)
- [API](#api)
- [Muhit o'zgaruvchilari](#muhit-ozgaruvchilari)
- [Development](#development)
- [Testlar](#testlar)
- [Xavfsizlik](#xavfsizlik)
- [Oflayn rejim qanday ishlaydi](#oflayn-rejim-qanday-ishlaydi)
- [Ishlab chiqarishga chiqarish](#ishlab-chiqarishga-chiqarish)

---

## Imkoniyatlar

### O'lchovchi uchun

| Bosqich | Nima qiladi |
| --- | --- |
| 1. Bosh sahifa | Obyektlar, o'lchovlar va oxirgi ishlar statistikasi |
| 2. Yangi obyekt | Nomi, buyurtma raqami, mijoz, telefon, manzil, GPS lokatsiya, izoh |
| 3. Xonalar | Cheksiz xona: mehmonxona, yotoqxona, oshxona, bolalar xonasi, zal, koridor, hammom... |
| 4. Xona rasmi | Har bir xonaga aynan bitta rasm (interyer, mebel, rang va yorug'likni ko'rsatish uchun) |
| 5. Oyna / eshik | Har bir xonada cheksiz o'lchov elementi |
| 6. O'lchov formasi | Eni, bo'yi, parda eni/bo'yi, karniz eni/bo'yi, mato turi, model, rang, soni, izoh |
| 7. Yakunlash | Barcha xonada rasm va o'lchov bo'lsa, obyekt "Yakunlangan" holatiga o'tadi |

Qo'shimcha: qidiruv (obyekt nomi, mijoz, buyurtma raqami, telefon), filtrlar (holat, o'lchovchi,
sana), oflayn rejim, avtomatik nom taklifi («Oyna 1», «Oyna 2»), rasmni brauzerda siqish,
tungi rejim va Telegram mavzusiga moslashish.

### Administrator uchun

- Barcha obyektlar, xonalar va o'lchovlarni ko'rish
- Xodimlarni boshqarish: rolni o'zgartirish, bloklash/faollashtirish
- O'lchovchilar kesimidagi statistika
- Obyektni tahrirlash, arxivlash (soft delete), tiklash va butunlay o'chirish
- Barcha o'zgarishlar audit jurnalida saqlanadi

---

## Texnologiyalar

| Qatlam | Texnologiya |
| --- | --- |
| Backend | Python 3.13, FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, JWT |
| Baza | PostgreSQL 17 |
| Frontend | React 19, TypeScript, Vite, TailwindCSS, Telegram WebApp SDK |
| Rasm saqlash | Lokal disk yoki Telegram File API |
| Infratuzilma | Docker, Docker Compose, nginx |
| Arxitektura | Clean Architecture, Repository Pattern, Unit of Work, Dependency Injection |

---

## Tez ishga tushirish

Talab: **Docker** va **Docker Compose**.

```bash
git clone <repo-url> pardachi && cd pardachi
make setup
```

`make setup` `.env` faylini yaratadi va `SECRET_KEY` ni avtomatik generatsiya qiladi.
So'ng `.env` ichida quyidagilarni to'ldiring:

```env
TELEGRAM_BOT_TOKEN=123456789:AA...      # @BotFather dan
TELEGRAM_BOT_USERNAME=pardachi_bot
ADMIN_TELEGRAM_IDS=123456789            # o'zingizning Telegram ID ingiz
WEBAPP_URL=https://sizning-domeningiz   # bot tugmasi uchun (HTTPS shart)
```

Ishga tushiring:

```bash
make up
```

| Manzil | Nima |
| --- | --- |
| http://localhost:8080 | Mini App (front-end) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/api/v1/health | Servis holati |

Namunaviy ma'lumot yuklash:

```bash
make seed
```

Barcha buyruqlar ro'yxati:

```bash
make help
```

---

## Telegram botni sozlash

1. [@BotFather](https://t.me/BotFather) da `/newbot` orqali bot yarating, tokenni oling.
2. Mini App HTTPS domenda turishi **shart**. Test uchun:
   ```bash
   ngrok http 8080
   ```
3. BotFather'da: `/newapp` → botni tanlang → nom, tavsif, rasm → **Web App URL** sifatida
   HTTPS manzilingizni kiriting.
4. `.env` da `WEBAPP_URL` ni o'sha manzilga tenglashtiring va botni ishga tushiring:
   ```bash
   docker compose --profile bot up -d bot
   ```
5. Botga `/start` yozing — «📏 Ilovani ochish» tugmasi paydo bo'ladi.

Birinchi kirgan foydalanuvchi avtomatik **administrator** bo'ladi
(`FIRST_USER_IS_ADMIN=true`). Muqobil variant — `ADMIN_TELEGRAM_IDS` ga ID kiritish.

---

## Loyiha tuzilmasi

```
pardachi/
├── backend/                     # FastAPI ilovasi
│   ├── app/
│   │   ├── core/                # Sozlamalar, JWT, loglash, xatoliklar
│   │   ├── domain/              # Modellar, enumlar, repozitoriy interfeyslari
│   │   ├── application/         # Biznes logika (servislar) va ruxsat qoidalari
│   │   │   ├── permissions.py
│   │   │   └── services/        # auth, project, room, measurement, image, user, stats
│   │   ├── infrastructure/      # SQLAlchemy, saqlagichlar, Telegram klienti
│   │   │   ├── db/              # session, Unit of Work
│   │   │   ├── repositories/    # Repozitoriylar implementatsiyasi
│   │   │   ├── storage/         # local / telegram fayl saqlagichlari
│   │   │   └── telegram/        # initData tekshiruvi, Bot API klienti
│   │   ├── api/                 # HTTP qatlami
│   │   │   ├── deps.py          # Dependency Injection
│   │   │   ├── errors.py        # Xatoliklarni o'zbekcha formatlash
│   │   │   ├── middleware.py    # Request ID, xavfsizlik, rate limit, Origin guard
│   │   │   └── v1/              # auth, projects, rooms, measurements, users, stats
│   │   ├── schemas/             # Pydantic sxemalari
│   │   └── main.py
│   ├── alembic/                 # Migratsiyalar
│   ├── scripts/seed.py          # Namunaviy ma'lumotlar
│   ├── tests/                   # Pytest (44 ta test)
│   └── Dockerfile
├── frontend/                    # React Mini App
│   ├── src/
│   │   ├── components/          # Button, Input, Sheet, PhotoPicker, cards...
│   │   ├── pages/               # Dashboard, Projects, ProjectForm, RoomDetail...
│   │   ├── lib/                 # api, offline, telegram, image, format
│   │   ├── store/               # auth, toast, network kontekstlari
│   │   ├── hooks/               # useResource, useEnums, useDebounce
│   │   └── i18n/uz.ts           # Barcha matnlar
│   ├── nginx.conf
│   └── Dockerfile
├── bot/                         # Mini App tugmasini ko'rsatuvchi bot
├── docs/                        # API.md, INSTALL.md, ARCHITECTURE.md
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Ma'lumotlar bazasi

Normallashtirilgan sxema (7 ta jadval):

```
users ──────< projects ──────< rooms ──────< measurement_items
                  │                │
                  │                └──────── room_images (1:1)
                  └──────────────── project_locations (1:1)

audit_logs — barcha o'zgarishlar tarixi
```

| Jadval | Vazifasi | Muhim maydonlar |
| --- | --- | --- |
| `users` | Foydalanuvchilar | `telegram_id` (unique), `role` (admin/measurer), `is_active` |
| `projects` | Obyektlar | `order_number` (unique), `status`, `created_by_id`, `deleted_at` (soft delete) |
| `project_locations` | GPS | `latitude`, `longitude`, `accuracy_m`, `source`, `captured_at` |
| `rooms` | Xonalar | `project_id`, `room_type`, `sort_order` |
| `room_images` | Xona rasmi | `room_id` **unique** — har xonada bitta rasm |
| `measurement_items` | Oyna/eshik o'lchovlari | `width_cm`, `height_cm`, parda va karniz o'lchamlari, mato |
| `audit_logs` | Audit | `actor_id`, `action`, `entity_type`, `entity_id`, `payload` (JSONB) |

Yaxlitlik: `CHECK` cheklovlari (o'lcham > 0 va ≤ 10000, kenglik/uzunlik chegaralari),
`ON DELETE CASCADE` (obyekt o'chsa — xonalar, rasmlar va o'lchovlar ham), qidiruv uchun indekslar.

Migratsiyalar:

```bash
make migrate                                    # yoki
docker compose exec backend alembic upgrade head
docker compose exec backend alembic revision --autogenerate -m "izoh"
```

---

## API

To'liq hujjat: **http://localhost:8000/docs** (Swagger) va [docs/API.md](docs/API.md).

| Metod | Yo'l | Tavsif |
| --- | --- | --- |
| POST | `/api/v1/auth/telegram` | `initData` orqali kirish, JWT olish |
| POST | `/api/v1/auth/refresh` | Tokenni yangilash |
| GET/PATCH | `/api/v1/auth/me` | O'z profili |
| GET | `/api/v1/projects` | Ro'yxat: qidiruv, filtr, sahifalash |
| POST | `/api/v1/projects` | Yangi obyekt (oflayn uchun `id` yuborish mumkin) |
| GET/PATCH/DELETE | `/api/v1/projects/{id}` | Ko'rish / tahrirlash / arxivlash |
| PATCH | `/api/v1/projects/{id}/status` | Holatni o'zgartirish (yakunlash) |
| POST | `/api/v1/projects/{id}/location` | GPS lokatsiyani saqlash |
| GET/POST | `/api/v1/projects/{id}/rooms` | Xonalar |
| GET | `/api/v1/projects/{id}/measurements` | Tikuv bo'limi uchun barcha o'lchovlar |
| GET/PATCH/DELETE | `/api/v1/rooms/{id}` | Xona |
| POST/GET/DELETE | `/api/v1/rooms/{id}/image` | Xona rasmi (bitta) |
| GET/POST | `/api/v1/rooms/{id}/items` | O'lchovlar |
| GET | `/api/v1/rooms/{id}/items/suggest-name` | «Oyna 3» kabi nom taklifi |
| GET/PATCH/DELETE | `/api/v1/measurements/{id}` | Alohida o'lchov |
| GET | `/api/v1/users` | Xodimlar (admin) |
| GET | `/api/v1/stats/dashboard` | Bosh sahifa statistikasi |
| GET | `/api/v1/meta/enums` | Ro'yxatlar va o'zbekcha nomlari |
| GET | `/api/v1/health` | Servis holati |

Xatoliklar yagona formatda va o'zbek tilida qaytadi:

```json
{
  "error": {
    "code": "notogri_malumot",
    "message": "Ma'lumotlar to'liq yoki to'g'ri kiritilmagan.",
    "details": { "fields": { "customer_phone": "Telefon raqami noto'g'ri. Masalan: +998901234567" } }
  }
}
```

---

## Muhit o'zgaruvchilari

Asosiylari (to'liq ro'yxat — [.env.example](.env.example)):

| O'zgaruvchi | Standart | Tavsif |
| --- | --- | --- |
| `SECRET_KEY` | — | **Majburiy.** JWT imzosi. `openssl rand -hex 32` |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL DSN |
| `TELEGRAM_BOT_TOKEN` | — | initData imzosini tekshirish uchun **majburiy** |
| `ADMIN_TELEGRAM_IDS` | bo'sh | Vergul bilan: `111,222` |
| `FIRST_USER_IS_ADMIN` | `true` | Birinchi foydalanuvchi admin bo'ladi |
| `ALLOW_SELF_REGISTRATION` | `true` | Yangi foydalanuvchi o'zi ro'yxatdan o'ta oladimi |
| `STORAGE_BACKEND` | `local` | `local` yoki `telegram` |
| `TELEGRAM_STORAGE_CHAT_ID` | bo'sh | `telegram` saqlagichi uchun chat |
| `MAX_UPLOAD_SIZE_MB` | `12` | Rasm hajmi chegarasi |
| `IMAGE_MAX_DIMENSION` | `1600` | Serverdagi maksimal tomon (px) |
| `CORS_ORIGINS` | localhost:8080, :5173 | Ruxsat etilgan manbalar |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `720` | Access token muddati |
| `RATE_LIMIT_PER_MINUTE` | `240` | IP bo'yicha so'rovlar chegarasi |
| `ALLOW_DEV_LOGIN` | `false` | Telegramsiz sinov kirishi (faqat development) |

---

## Development

Docker'siz lokal ishlash:

```bash
# Backend
cd backend
python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env                     # DATABASE_URL va ALLOW_DEV_LOGIN=true
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.seed
.venv/bin/uvicorn app.main:app --reload

# Frontend (alohida terminalda)
cd frontend
npm install
cp .env.example .env.local
npm run dev                              # http://localhost:5173
```

Brauzerda `ALLOW_DEV_LOGIN=true` bo'lsa, kirish sahifasida «Sinov rejimida kirish» tugmalari
chiqadi — Telegramsiz ham butun ilovani sinash mumkin. Dev-server `http://localhost:5173`
manzilida ishlagani uchun `CORS_ORIGINS` ro'yxatida shu manzil turishi kerak.

---

## Testlar

```bash
make test                    # yoki: cd backend && .venv/bin/python -m pytest -q
make lint                    # ruff + tsc
```

Qamrov: Telegram `initData` imzosi (soxta imzo, eskirgan sessiya, boshqa token), JWT oqimi,
rollar va ruxsatlar, obyekt CRUD, qidiruv va filtrlar, oflayn idempotentlik, o'lchov
validatsiyasi, rasm yuklash/siqish/almashtirish, obyektni yakunlash shartlari,
o'zbekcha xato xabarlari.

---

## Xavfsizlik

- **Telegram initData** — HMAC-SHA256 imzosi va `auth_date` yoshi tekshiriladi.
- **JWT** — access/refresh tokenlar, rol token ichida, muddati tugaganda avtomatik yangilanadi.
- **Rollar** — o'lchovchi faqat o'z obyektlarini ko'radi va tahrirlaydi (servis qatlamida).
- **SQL injection** — barcha so'rovlar SQLAlchemy parametrlangan so'rovlari orqali.
- **XSS** — React avtomatik ekranlaydi, `dangerouslySetInnerHTML` ishlatilmagan,
  javob sarlavhalarida `X-Content-Type-Options`, `Content-Security-Policy`.
- **CSRF** — API cookie ishlatmaydi (faqat `Authorization` sarlavhasi), qo'shimcha ravishda
  holatni o'zgartiruvchi so'rovlarda `Origin` tekshiriladi.
- **Fayl yuklash** — MIME va hajm tekshiruvi, rasm Pillow orqali qayta kodlanadi
  (EXIF va yashirin yuk tozalanadi).
- **Rate limiting** — IP bo'yicha daqiqasiga so'rovlar chegarasi.
- **Audit** — kirish, yaratish, tahrirlash, o'chirish va yuklashlar `audit_logs` da.
- Konteynerlar `root` bo'lmagan foydalanuvchi ostida ishlaydi.

---

## Oflayn rejim qanday ishlaydi

Uy ichida internet yo'qolishi odatiy hol, shuning uchun:

1. **Kesh** — muvaffaqiyatli `GET` javoblari IndexedDB'ga yoziladi va internet yo'qda ekranga
   chiqariladi («Oflayn ko'rinish» belgisi bilan).
2. **Navbat (outbox)** — yaratish/tahrirlash/o'chirish so'rovlari (rasm fayli bilan birga)
   IndexedDB navbatiga tushadi, foydalanuvchiga «Ma'lumot telefonda saqlandi» deb aytiladi.
3. **Idempotentlik** — mijoz obyekt/xona/o'lchov uchun UUID ni o'zi generatsiya qiladi va
   `id` maydonida yuboradi. Server bir xil `id` bilan kelgan takroriy so'rovda yangi yozuv
   yaratmaydi — shuning uchun navbatni qayta yuborish xavfsiz.
4. **Sinxronizatsiya** — `online` hodisasida, ilova ochilganda va har 60 soniyada navbat
   ketma-ket yuboriladi. Yuqoridagi banner yuborilmagan o'zgarishlar sonini ko'rsatadi.

---

## Ishlab chiqarishga chiqarish

1. `.env` da `ENVIRONMENT=production`, `ALLOW_DEV_LOGIN=false`, kuchli `SECRET_KEY`.
2. `CORS_ORIGINS` — faqat haqiqiy domeningiz.
3. HTTPS majburiy (Telegram Mini App faqat HTTPS bilan ishlaydi) — nginx/Traefik + Let's Encrypt.
4. `make up` — migratsiyalar konteyner ishga tushganda avtomatik qo'llanadi.
5. Zaxira nusxa:
   ```bash
   docker compose exec db pg_dump -U pardachi pardachi > backup_$(date +%F).sql
   docker run --rm -v pardachi_media:/media -v $(pwd):/backup alpine \
     tar czf /backup/media_$(date +%F).tar.gz -C /media .
   ```
6. Loglar JSON formatda (`ENVIRONMENT=production`) — `docker compose logs -f backend`.

Batafsil: [docs/INSTALL.md](docs/INSTALL.md) va [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Litsenziya

MIT

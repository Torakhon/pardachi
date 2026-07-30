#!/usr/bin/env bash
#
# Pardachi — Mini App'ni internetga chiqarish (bir buyruq bilan).
#
# Nima qiladi:
#   1. Eski cloudflared jarayonlarini to'xtatadi (ikkitasi bir vaqtda ishlasa chalkashlik bo'ladi);
#   2. Docker stack'ni ko'taradi (db + backend + frontend);
#   3. Yangi tunnel ochib, HTTPS manzilini oladi;
#   4. `.env` dagi WEBAPP_URL va CORS_ORIGINS ni o'sha manzilga yangilaydi;
#   5. Backend va botni qayta ishga tushiradi (bot menyu tugmasini o'zi sozlaydi);
#   6. Hammasi ishlayotganini tekshirib, manzilni chiqaradi.
#
# Ishlatish:
#   ./scripts/tunnel.sh          yoki      make tunnel
#
set -euo pipefail

cd "$(dirname "$0")/.."
ENV_FILE=.env
LOG=/tmp/pardachi-cloudflared.log

step() { printf "\n\033[1;36m==> %s\033[0m\n" "$1"; }
ok()   { printf "    \033[32mOK\033[0m  %s\n" "$1"; }
die()  { printf "    \033[31mXATO\033[0m %s\n" "$1" >&2; exit 1; }

command -v cloudflared >/dev/null || die "cloudflared o'rnatilmagan. O'rnatish: brew install cloudflared"
[ -f "$ENV_FILE" ] || die ".env fayli topilmadi. Avval: make setup"

step "1/6 Eski tunnellarni to'xtatish"
if pgrep -f 'cloudflared tunnel' >/dev/null; then
  pkill -f 'cloudflared tunnel' || true
  sleep 2
  ok "eski tunnel(lar) to'xtatildi"
else
  ok "eski tunnel yo'q"
fi

step "2/6 Docker stack'ni ko'tarish"
docker compose up -d db backend frontend >/dev/null 2>&1
for _ in $(seq 1 45); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 http://localhost:8080/api/v1/health || true)
  [ "$code" = "200" ] && break
  sleep 2
done
[ "${code:-}" = "200" ] || die "backend javob bermadi. Loglar: docker compose logs backend"
ok "backend va frontend ishlayapti (localhost:8080)"

step "3/6 Tunnel ochish"
: > "$LOG"
nohup cloudflared tunnel --url http://localhost:8080 --no-autoupdate > "$LOG" 2>&1 &
URL=""
for _ in $(seq 1 30); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1 || true)
  [ -n "$URL" ] && break
  sleep 1
done
[ -n "$URL" ] || die "tunnel manzili olinmadi. Loglar: $LOG"
ok "manzil: $URL"

step "4/6 .env ni yangilash"
python3 - "$URL" <<'PY'
import re, sys, pathlib
url = sys.argv[1]
path = pathlib.Path(".env")
text = path.read_text()

def upsert(text: str, key: str, value: str) -> str:
    if re.search(rf"^{key}=.*$", text, flags=re.M):
        return re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.M)
    return text.rstrip("\n") + f"\n{key}={value}\n"

text = upsert(text, "WEBAPP_URL", url)
text = upsert(text, "CORS_ORIGINS", url)
path.write_text(text)
PY
ok "WEBAPP_URL va CORS_ORIGINS yangilandi"

step "5/6 Backend va botni qayta ishga tushirish"
docker compose up -d --force-recreate backend >/dev/null 2>&1
docker compose --profile bot up -d --force-recreate bot >/dev/null 2>&1
sleep 8
ok "backend va bot yangi manzil bilan ishga tushdi"

step "6/6 Tekshirish"
HOST=${URL#https://}
DNS_WARNING=""
RESOLVE=()

# Ba'zi uy routerlari/provayderlari `*.trycloudflare.com` subdomenlarini hal qilmaydi.
# Shunda tekshiruvni ochiq DNS orqali bajaramiz va foydalanuvchini ogohlantiramiz.
if [ -z "$(dig +short +time=3 "$HOST" | head -1)" ]; then
  PUBLIC_IP=$(dig +short +time=3 @1.1.1.1 "$HOST" | head -1)
  [ -z "$PUBLIC_IP" ] && PUBLIC_IP=$(dig +short +time=3 @8.8.8.8 "$HOST" | head -1)
  [ -n "$PUBLIC_IP" ] || die "manzil DNS'da topilmadi (tunnel hali tayyor emas). Qayta urinib ko'ring."
  RESOLVE=(--resolve "$HOST:443:$PUBLIC_IP")
  DNS_WARNING="yes"
fi

spa=$(curl -s -o /dev/null -w '%{http_code}' "${RESOLVE[@]}" --max-time 25 "$URL/")
api=$(curl -s -o /dev/null -w '%{http_code}' "${RESOLVE[@]}" --max-time 25 "$URL/api/v1/health")
[ "$spa" = "200" ] || die "Mini App sahifasi ochilmadi (HTTP $spa)"
[ "$api" = "200" ] || die "API javob bermadi (HTTP $api)"
ok "Mini App: HTTP $spa   |   API: HTTP $api"

if [ -n "$DNS_WARNING" ]; then
  cat <<'WARN'

    ⚠️  DIQQAT — DNS muammosi aniqlandi
    Sizning tarmog'ingiz (Wi-Fi router yoki provayder) DNS'i
    `*.trycloudflare.com` manzillarini hal qilmayapti. Tunnel ishlayapti,
    lekin shu tarmoqdagi telefon ilovani ocha olmasligi mumkin.

    Yechim (birini tanlang):
      • Telefonda Wi-Fi'ni o'chirib, mobil internet bilan sinab ko'ring;
      • Telefon/router DNS'ini 1.1.1.1 yoki 8.8.8.8 ga o'zgartiring;
      • Doimiy yechim: backend'ni o'z domeningizda joylashtiring (README, B variant).
WARN
fi

TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2-)
if [ -n "$TOKEN" ]; then
  menu=$(curl -s --max-time 15 "https://api.telegram.org/bot$TOKEN/getChatMenuButton" |
    python3 -c "import sys,json;r=json.load(sys.stdin).get('result',{});print((r.get('web_app') or {}).get('url',''))" 2>/dev/null || true)
  case "$menu" in
    "$URL"*) ok "bot menyu tugmasi to'g'ri manzilga qaragan" ;;
    "")      printf "    \033[33mDIQQAT\033[0m menyu tugmasi tekshirilmadi\n" ;;
    *)       printf "    \033[33mDIQQAT\033[0m menyu tugmasi: %s (bot qayta ishga tushishini kutib, /start yozing)\n" "$menu" ;;
  esac
fi

cat <<EOF

============================================================
  TAYYOR. Mini App manzili:

    $URL

  Telegramda botni oching va /start yozing.
  Tunnel loglari: $LOG
  DIQQAT: bu terminal yopilsa ham tunnel ishlaydi, lekin
  kompyuter o'chsa yoki tunnel to'xtasa — shu skriptni
  qayta ishga tushiring (manzil o'zgaradi).
============================================================
EOF

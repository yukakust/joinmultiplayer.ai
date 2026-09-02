# Запуск · runbook волны №1

Цель волны: семь писем с одним эмодзи → семь гостей проходят рацию → терминал →
свою фигурку-ремесло → личную щель → первый ход. Один контакт, без напоминаний.
Всё, что ниже, — чтобы ни один из семи не наткнулся на тишину или ложь.

## Блокеры (без них не отправляем)

| # | Что | Кто | Статус |
|---|---|---|---|
| 1 | **Уведомление о новом следе.** Гость отправляет ход → Юке должно прийти сообщение. Нужен Telegram-бот (BotFather, 2 минуты) → токен в `/etc/joinmultiplayer-crier.env` → включаем таймер `pending → TG`. | Юка: токен · Claude: подключение | ⛔ ждёт токен |
| 2 | **Канал ответа.** В слоте написано «ответь на письмо, которое тебя нашло» — значит ящик, с которого уходят письма, читается ежедневно всю волну. | Юка | ☐ |
| 3 | **Проверка ссылок** из писем в чистом браузере за час до отправки: `/game/?lit=M0001&piece=<kind>` для всех семи фигурок → рация → терминал → «фигурка ждала тебя» → слот → ссылки на JSON отдают `application/json`. | Claude | ☐ (скрипт ниже) |

## Не блокеры, но до конца волны

- Бэкап новой базы — есть (03:10 UTC, `/var/backups/joinmultiplayer-new`). Проверить, что снапшот открывается: `gunzip -c <файл> | head -c 16` → `SQLite format 3`.
- Аптайм: раз в 5 минут `curl -fsS https://new.joinmultiplayer.ai/api/health` с yukabox; при двух подряд отказах — сообщение в тот же TG-канал.
- `.dmg` полевого комплекта: без Apple Developer ID и нотаризации **не** предлагать скачивание — Gatekeeper убьёт магию. Пока билд не подписан, сайт про билд молчит (закон I).
- Записи терминала 003–005 зашить (RU есть в библии, EN перевести) — чтобы у первых зажжённых было что расшифровывать.

## Порядок отправки

1. День 0: 📦 ivgranite и 🪨 Glukhov (валидация — самая горячая щель), 🏮 Mastracci (латентность).
2. День 1: 🔍 Hanel, ⚡ Zhang.
3. День 2: 🕯️ Kidd (Mastodon DM), 🎇 Vidra.
Разнос по дням — чтобы модерация и ответы успевали за первыми ходами, и чтобы стол на `/game/` заполнялся на глазах у следующих.

## Что смотреть каждый день волны

- **Открыл ли гость ссылку** — в журнале сервера видны запросы с его фигуркой:
  `journalctl -u joinmultiplayer-new-static --since "1 day ago" | grep -E "piece=(matchbox|lens|flint|candle|lantern|lighter|sparkler)"`.
- **Пришёл ли след** — `python3 new/server/moderate.py --db /var/lib/joinmultiplayer-new/contributions.sqlite3 list` (до TG-бота — руками, утром и вечером).
- **Зажечь** — `moderate.py status T01xx public`; после этого фигурка гостя загорается, у него появляется личная ссылка «зажги следующего».
- **Ошибки** — `journalctl -u joinmultiplayer-new-static | grep -iE "failed|error"` (GET-ошибки теперь логируются с телом исключения).

## Скрипт предстартовой проверки

```bash
for p in matchbox lens flint candle lantern lighter sparkler; do
  printf "%-9s game=%s " "$p" "$(curl -s -o /dev/null -w '%{http_code}' "https://new.joinmultiplayer.ai/game/?lit=M0001&piece=$p")"
done; echo
for f in chatgpt-single-container-gate16g3-result-v0.1.json chat-first-qwen-gate16g6-result-v0.3.json outbound-secret-gate16f1-result-v0.1.json; do
  curl -s -o /dev/null -w "$f %{http_code} %{content_type}\n" "https://joinmultiplayer.ai/experiments/E007/$f"
done
curl -s https://new.joinmultiplayer.ai/api/health
```

## Откат

Сайт: `git reset --hard <прошлый коммит>` в `/srv/joinmultiplayer-new/checkout` + `systemctl restart joinmultiplayer-new-static`.
База: последний снапшот из `/var/backups/joinmultiplayer-new/` → `gunzip` → подменить файл при остановленном сервисе.
Старый сайт не участвует в волне и не трогается.

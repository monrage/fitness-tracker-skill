# Backend: Notion

Данные хранятся в вашем Notion-аккаунте — три базы создаются автоматически.
Работает через официальный Internal Integration API (версия `2022-06-28`).

---

## Шаг 1 — Подготовьте страницу в Notion

1. Создайте (или откройте) **workspace** в Notion.
2. Создайте в нём **чистую страницу** (например, `FitnessLife`) — лишнее содержимое
   можно удалить. Под этой страницей скилл создаст три базы данных.
3. Скопируйте **ссылку на страницу**: кнопка **Share** (или `•••` вверху справа) →
   **Copy link**. Либо возьмите URL прямо из адресной строки браузера. Ссылка
   понадобится дальше — из неё Claude извлечёт `parent_page_id`.

---

## Шаг 2 — Создайте интеграцию и дайте ей доступ к странице

1. Откройте [notion.so/my-integrations](https://www.notion.so/my-integrations) → **New integration**.
2. **Associated workspace** — выберите **тот же** workspace, где лежит ваша страница.
   Тип — **Internal**. Название любое (например, `FitnessLife`).
3. Откройте вкладку **Content access** (в некоторых версиях — **Access**) →
   режим **Private** → раздел **Top level pages** → **выберите созданную страницу**.
   Это и даёт интеграции доступ именно к ней. **Без этого шага — ошибка 403.**
4. На вкладке **Configuration** скопируйте **Internal Integration Token** —
   он начинается с `ntn_`. Храните его как секрет.

> Альтернативный способ дать доступ: открыть саму страницу → `•••` → **Connections** →
> подключить интеграцию. Достаточно чего-то одного.

---

## Шаг 3 — Передайте данные Claude

Отправьте в чат **токен** (`ntn_…`) и **ссылку на страницу** — вместе, одним сообщением.
Дальше Claude сделает всё сам: извлечёт `parent_page_id` из ссылки, сохранит токен и id
в конфиг, создаст три базы (`ensure-schema`) и запишет их id.

Эквивалент вручную (если делаете сами): `parent_page_id` — это 32 hex-символа из ссылки
на страницу (между последним `/` и `?`, без дефисов).

```
python scripts/fittrack.py config-set --patch '{"backend":{"type":"notion","notion":{"token":"ntn_XXXXXXXX","parent_page_id":"<32-hex из ссылки>"}}}'
```

---

## Шаг 4 — Базы данных (Claude создаёт их сам)

```
python scripts/fittrack.py ensure-schema
```

Команда создаёт три базы под родительской страницей и возвращает их id:

```json
{
  "backend": "notion",
  "databases": {
    "food":        "<database_id>",
    "workout":     "<database_id>",
    "bodyweight":  "<database_id>"
  },
  "created": { ... }
}
```

Сохраните полученные id:

```
python scripts/fittrack.py config-set --patch '{"backend":{"notion":{"databases":{"food":"<id>","workout":"<id>","bodyweight":"<id>"}}}}'
```

`ensure-schema` — идемпотентная операция: повторный запуск ничего не сломает.

---

## Структура создаваемых баз

### FitnessLife — Food log

| Свойство | Тип Notion | Значения (select) |
|---|---|---|
| Item | title | — |
| Date | date | — |
| Meal | select | breakfast, lunch, dinner, snack |
| Qty g | number | — |
| Calories | number | — |
| Protein g | number | — |
| Fat g | number | — |
| Carbs g | number | — |
| Source | select | claude, off, label, manual |
| Notes | rich_text | — |

### FitnessLife — Workout log

| Свойство | Тип Notion | Значения (select) |
|---|---|---|
| Exercise | title | — |
| Date | date | — |
| Type | select | strength, cardio, mobility, sport |
| Sets | number | — |
| Reps | number | — |
| Weight kg | number | — |
| Duration min | number | — |
| Distance km | number | — |
| RPE | number | — |
| Volume | number | — |
| Notes | rich_text | — |

### FitnessLife — Bodyweight

| Свойство | Тип Notion | Значения (select) |
|---|---|---|
| Entry | title | — |
| Date | date | — |
| Weight kg | number | — |
| Notes | rich_text | — |

---

## Технические детали

- **API version**: `2022-06-28` (classic `database_id` model).
- **Rate limit**: ~3 запроса/сек. При ошибке 429 скрипт автоматически повторяет запрос, соблюдая `Retry-After`.
- **Данные в вашем Notion**: видны в браузере и в мобильном приложении Notion — можно просматривать, фильтровать, строить views вручную.
- **Конфиг остаётся локальным**: `fitness-config.json` с токеном нужно держать как файл в Claude Project. Облачный бэкенд хранит только записи.

---

## Устранение ошибок

| Код | Причина | Решение |
|---|---|---|
| 401 | Неверный токен | Проверьте `backend.notion.token`; скопируйте заново с notion.so/my-integrations |
| 403 | У интеграции нет доступа к странице | Открыть интеграцию → **Content access** → Private → Top level pages → выбрать страницу (Шаг 2) |
| 404 | Неверный `parent_page_id` | Скопируйте id заново из URL страницы (32 hex-символа) |
| 429 | Rate limit | Скрипт ретраит автоматически; если ошибка не уходит — подождите минуту |

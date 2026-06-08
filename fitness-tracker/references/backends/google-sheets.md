# Backend: Google Sheets

> **Сложность настройки:** выше, чем у Notion — требует одноразовой OAuth-авторизации в браузере.
> Зато данные живут в вашей таблице; строить кастомные графики и формулы — без ограничений.

## Почему refresh-token, а не service account

Скилл работает на чистой stdlib Python (нет сторонних зависимостей). Service account требует
RS256 JWT-подписи, для которой нужен пакет `cryptography` — он может отсутствовать в sandbox
claude.ai. Refresh-token flow обходится обычным HTTP POST: скилл обменивает refresh_token на
короткоживущий access_token через `https://oauth2.googleapis.com/token` и делает запросы к
Sheets API. Никаких дополнительных пакетов.

---

## Пошаговая настройка

### 1. Google Cloud — создать проект и включить API

1. Откройте [console.cloud.google.com](https://console.cloud.google.com) → **Select a project → New Project**.
2. Дайте проекту любое имя (например, `fitness-tracker`).
3. В меню слева: **APIs & Services → Library** → найдите **Google Sheets API** → **Enable**.

### 2. OAuth consent screen

1. **APIs & Services → OAuth consent screen**.
2. **User type: External** → Create.
3. Заполните обязательные поля (App name, support email) — содержимое не важно.
4. **Test users** → **Add users** → добавьте **свой** аккаунт Google.
   > Критично: пока приложение не прошло верификацию Google, refresh_token работает только
   > для аккаунтов из списка Test users. Если не добавить себя — обновление токена будет
   > возвращать `invalid_grant`.
5. Сохраните и перейдите к следующему шагу (публиковать приложение не нужно).

### 3. Создать OAuth Client ID

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
2. **Application type: Desktop app** → любое имя → **Create**.
3. Скопируйте **client_id** и **client_secret** — они понадобятся на следующем шаге.

### 4. Получить refresh_token (один раз)

Используйте [OAuth 2.0 Playground](https://developers.google.com/oauthplayground):

1. Нажмите шестерёнку (⚙) в правом верхнем углу → отметьте
   **"Use your own OAuth credentials"** → вставьте `client_id` и `client_secret`.
2. В **Step 1** введите scope:
   ```
   https://www.googleapis.com/auth/spreadsheets
   ```
   → **Authorize APIs** → войдите под своим Google аккаунтом (тем, что добавлен как Test user).
3. **Step 2 → Exchange authorization code for tokens**.
4. Скопируйте **refresh_token** из ответа.

> Этот шаг происходит в браузере пользователя, вне скилла. После получения refresh_token
> в браузер возвращаться не нужно.

### 5. Создать таблицу Google Sheets

1. Откройте [sheets.google.com](https://sheets.google.com) → создайте пустую таблицу.
2. Из URL скопируйте **spreadsheet_id** — длинный идентификатор между `/d/` и `/edit`:
   ```
   https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
   ```

### 6. Сохранить в конфиг

```
python scripts/fittrack.py config-set --patch '{
  "backend": {
    "type": "sheets",
    "sheets": {
      "spreadsheet_id": "<SPREADSHEET_ID>",
      "oauth": {
        "client_id": "<CLIENT_ID>",
        "client_secret": "<CLIENT_SECRET>",
        "refresh_token": "<REFRESH_TOKEN>"
      }
    }
  }
}'
```

### 7. Инициализировать схему

```
python scripts/fittrack.py ensure-schema
```

Команда создаёт четыре вкладки (если их ещё нет) и записывает заголовочные строки автоматически.
Операция идемпотентна — запускать повторно безопасно.

---

## Структура таблицы

После `ensure-schema` в таблице появятся четыре вкладки со следующими колонками (порядок строгий):

### Food

| # | Колонка | Тип | Описание |
|---|---------|-----|----------|
| A | `date` | YYYY-MM-DD | Дата приёма пищи |
| B | `meal` | enum | breakfast / lunch / dinner / snack |
| C | `item` | string | Что съедено |
| D | `qty_g` | number | Граммы (или порция) |
| E | `kcal` | number | Калории |
| F | `protein_g` | number | Белок, г |
| G | `fat_g` | number | Жиры, г |
| H | `carbs_g` | number | Углеводы, г |
| I | `source` | enum | claude / off / label / manual |
| J | `notes` | string | Заметки |

### Workout

| # | Колонка | Тип | Описание |
|---|---------|-----|----------|
| A | `date` | YYYY-MM-DD | Дата тренировки |
| B | `type` | enum | strength / cardio / mobility / sport |
| C | `exercise` | string | Упражнение |
| D | `sets` | number | Подходы |
| E | `reps` | number | Повторения |
| F | `weight_kg` | number | Рабочий вес, кг |
| G | `duration_min` | number | Длительность, мин |
| H | `distance_km` | number | Дистанция, км |
| I | `rpe` | number | RPE 1–10 |
| J | `volume` | number | Объём = sets·reps·weight |
| K | `notes` | string | Заметки |

### Bodyweight

| # | Колонка | Тип | Описание |
|---|---------|-----|----------|
| A | `date` | YYYY-MM-DD | Дата взвешивания |
| B | `weight_kg` | number | Вес, кг |
| C | `muscle_kg` | number | Скелетная мускулатура, кг |
| D | `fat_kg` | number | Масса жировой ткани, кг |
| E | `fat_pct` | number | Процент жира |
| F | `water_kg` | number | Вода в организме, кг |
| G | `notes` | string | Заметки |

### Energy

| # | Колонка | Тип | Описание |
|---|---------|-----|----------|
| A | `date` | YYYY-MM-DD | Дата |
| B | `activity_kcal` | number | Потрачено на активность, ккал |
| C | `basal_kcal` | number | Базовый расход (BMR), ккал |
| D | `total_out_kcal` | number | Всего потрачено, ккал |
| E | `notes` | string | Заметки |

> CSV-пример заголовка и одной строки для вкладки **Food** — см. `assets/sheet-template.csv`.
> Вкладки Workout, Bodyweight и Energy создаются автоматически командой `ensure-schema`.

---

## Устранение неполадок

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `invalid_grant` | refresh_token отозван/истёк, или аккаунт не в списке Test users | Добавьте аккаунт в Test users (п. 2.4) и получите новый refresh_token (п. 4) |
| HTTP 403 | Sheets API не включён или неверный scope | Включите Google Sheets API (п. 1.3); убедитесь, что scope `spreadsheets` (не `drive`) |
| HTTP 404 | Неверный spreadsheet_id | Проверьте id в URL таблицы; убедитесь, что таблица не удалена |
| "Access blocked" в браузере при авторизации | Аккаунт не в списке Test users | **APIs & Services → OAuth consent screen → Test users** → добавьте свой email |
| `backend.sheets.spreadsheet_id is missing` | Конфиг не сохранён полностью | Повторите шаг 6 с полным patch |

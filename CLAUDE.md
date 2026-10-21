# Pain Radar

Збирає скарги ("болі") бухгалтерів малого та середнього бізнесу в Україні з публічних джерел (Telegram, форуми, RSS, Facebook, відгуки на банки-конкуренти), класифікує їх через LLM і показує в Streamlit-дашборді. Мета — знаходити проблеми клієнтів monobank Business і слабкі місця банків-конкурентів для продуктових рішень.

## Пайплайн

```
collectors/*  →  raw_messages  →  classifier  →  classified_pains  →  dashboard.py
   (збір)         (сира БД)      (LLM-розмітка)      (розмічена БД)      (Streamlit)
```

Спільна логіка `collect`+`classify` лежить у `src/pipeline.py` (`run_collect()`, `run_classify(since=...)`) і використовується двома шляхами:

1. **CLI** — `scripts/run_collect.py` і `scripts/run_classify.py` — тонкі обгортки над `src/pipeline.py`, запускаються локально (`make collect`, `make classify`).
2. **UI-кнопка** — `dashboard.py` має сайдбар із вибором періоду (Сьогодні/Тиждень/Місяць/Весь час) і кнопкою "Зібрати та класифікувати". На клік синхронно (`st.spinner`) викликає `run_collect()` потім `run_classify(since=...)`, де `since` фільтрує, які необроблені `raw_messages` класифікувати (прості пост-фільтр по `published_at`, колектори самі не вміють "збирати за період" — просто тягнуть фіксовану кількість останніх записів).

Деталі:
- Кожен колектор у `src/collectors/` тягне пости з одного типу джерела, рахує `content_hash` (sha256 від `source + перші 500 символів`) і пише в `raw_messages` через `insert_raw()` (ON CONFLICT DO NOTHING — дедуп на рівні хешу).
- Класифікація бере необроблені (`is_classified = FALSE`) записи по кожному `source` з `CLASSIFY_SOURCES` (`src/pipeline.py`) і прогонить через `classify_one()` (`src/classifier/pain_classifier.py`), пише результат у `classified_pains`, позначає `raw_messages.is_classified = TRUE`.
- Дашборд (`dashboard.py`) — Streamlit, читає `classified_pains JOIN raw_messages`, кешує на 5 хв (`st.cache_data(ttl=300)`), фільтрує `is_pain=TRUE AND intensity>=2 AND pain_category!='other'` + відсікає сільгосп/агро шум текстовим фільтром.

## Схема БД

`raw_messages` (`migrations/001_raw_messages.sql`): `id, source, source_url, content_hash (UNIQUE), title, body, author, published_at, collected_at, is_classified`.

`classified_pains` (`migrations/002_classified_pains.sql` + `migrations/003_add_emotional_fields.sql`): `id, raw_message_id, is_pain, pain_category, pain_description, target, intensity (1-5), classified_at, model_used, emotional_layer, quote, competitor_name`. Останні три колонки колись додали прямо в БД поза міграціями — тепер `003_add_emotional_fields.sql` наздоганяє файл до реального стану, `make migrate` на чистій БД більше не падає.

## Значення полів класифікації

- `pain_category`: `integration | payments | reporting | support | interface | limits | currency | monobank | other`
- `target`: `bank | monobank | accounting_system | government | other`
- `intensity`: 1 (незручність) … 5 (зупинка бізнесу)
- `emotional_layer`: `frustration | anxiety | helplessness | anger | confusion`
- `competitor_name`: `privatbank | pumb | abank | oschadbank | ukrsibbank | raiffeisen | sense | null`

Повний опис критеріїв — у `SYSTEM_PROMPT` в `src/classifier/pain_classifier.py`. Якщо додаєш нову категорію/поле — міняй одразу в трьох місцях: `SYSTEM_PROMPT`, `insert_classified()` у `src/db/client.py`, і мапінги в `dashboard.py` (`CATEGORY_UA`, `ICON`, `CAT_COLOR`).

## Джерела (`source` у `raw_messages`)

| Префікс | Колектор | Що |
|---|---|---|
| `tg_<channel>` | `telegram_public_collector.py` | публічні Telegram-канали (bu911, golovbukh, Zrobleno_buhgalter, UAtaxesYou, buhi1c + канали банків-конкурентів) |
| `tg_<chat>` | `telegram_chat_collector.py` | Telegram-чати (buhgalteri_kiev) — потребує заздалегідь створеної Telethon-сесії, інакше падає м'яко (ізольовано в `src/pipeline.py`) |
| `buh911_<forum>` | `forum_collector.py` | форум buhgalter911.com (911_help, bank_cash, audit_fines, accounting, reporting) |
| `dtkt_news` | `rss_collector.py` | RSS dtkt.ua + повний текст через Jina Reader |
| `fb_<group>` | `facebook_collector.py` | Facebook-групи через ScrapeCreators API (потребує `SCRAPECREATORS_API_KEY`, інакше пропускається) |
| `minfin_<bank>` | `minfin_collector.py` | відгуки на банки-конкуренти з minfin.com.ua |

`src/collectors/telegram_collector.py` — старий/невикористаний колектор (не імпортується нікуди), не плутати з `telegram_public_collector.py` / `telegram_chat_collector.py`.

Новий колектор додається так: написати `collect_x()` у `src/collectors/x_collector.py` з тим самим `_hash()`/`insert_raw()`-контрактом, додати в `COLLECTORS` у `src/pipeline.py`, додати відповідний `source`-префікс у `CLASSIFY_SOURCES` там же.

## Команди (`Makefile`, локальна розробка)

```
make install    # venv + requirements.txt
make migrate    # прогнати migrations/*.sql
make collect    # запустити всі колектори → raw_messages
make classify   # класифікувати нові raw_messages → classified_pains
make dashboard  # streamlit run dashboard.py
```

Локально можна й контейнерами (ті самі образи, що й на LUMI): `docker compose up --build` — піднімає `app` (Streamlit, :8501) + `db` (postgres:17-alpine, named volume `pgdata`).

## Конфіг

`.env` (див. `.env.example`): `DB_*` (локально Postgres.app, порт 5434, або `docker compose` з `POSTGRES_*`), `LUMI_API_KEY` (класифікатор ходить через LUMI, `base_url=https://lumi.monobank.com.ua/v1`, модель `Mistral-Large-3`), `SCRAPECREATORS_API_KEY`, `TG_API_ID/TG_API_HASH/TG_SESSION` (Telethon).

## Деплой

**Основний прод — платформа LUMI** (`lumi-artifactory.monobank.com.ua`), проєкт `pain-radar`: **https://pain-radar.lumi-artifactory.app/**

Формат — `docker-compose.yml` у корені (правила платформи: рівно один публічний сервіс, `healthcheck` у кожного сервіса, `${VAR:-default}` для конфігу з "Змінні середовища", `$$` для runtime-змінних усередині `healthcheck.test`):
- `app` — Streamlit (`Dockerfile`), публікує порт `$PORT` (8501), `healthcheck` на `/_stcore/health`.
- `db` — `postgres:17-alpine` (`db/Dockerfile`), застосовує `migrations/*.sql` через офіційний `/docker-entrypoint-initdb.d/` механізм (спрацьовує лише на порожньому томі!), `expose` 5432 (внутрішній, без публічного порту), named volume `pgdata` — переживає перезапуски й передеплої.

Керування — через MCP `lumi-mcp` (`deploy_list_projects`, `deploy_project_status`, `deploy_start`/`deploy_restart`/`deploy_stop`, `deploy_upload_file`, `deploy_set_env_vars`, `deploy_get_logs`). Секрети (`LUMI_API_KEY`, `POSTGRES_PASSWORD`, `TG_API_HASH`) задані через `deploy_set_env_vars` з `visibility: masked`, не лежать у файлах проєкту.

**Перенесення даних з Supabase (без повторного збору):** дамп зроблено через `psycopg2 copy_expert` (НЕ `pg_dump` — несумісність версій клієнта й серверу), стиснуто gzip (`raw_messages.csv.gz`, `classified_pains.csv.gz`), завантажено в корінь LUMI-проєкту через веб-UI (вкладка "Файли" — великі файли через MCP channel невигідні, платформа сама радить веб-UI). Завантаження в БД — `scripts/seed_if_empty.py`, запускається перед `streamlit run` при **кожному** старті `app`-контейнера: перевіряє `SELECT count(*) FROM raw_messages`, і лише якщо порожньо — довантажує CSV через `COPY ... FROM STDIN`. Ідемпотентно, тож безпечно для будь-якого майбутнього передеплою.

⚠️ **Важливо:** не намагайся повернути завантаження seed-даних на `db`-сервіс через `docker-entrypoint-initdb.d` — спрацює лише один раз на абсолютно порожньому томі (перший `deploy_start` на проєкті). Якщо том уже ініціалізований (а він ініціалізується міграціями одразу при першому старті), наступні перезбірки `db`-образу цей крок просто проігнорують. Саме тому seed тепер на стороні `app`.

**Legacy/вторинний деплой — Streamlit Community Cloud.** `runtime.txt` пінить Python 3.12, `psycopg2-binary==2.9.13` — мінімальна версія з готовим wheel. БД там була Supabase (прибрано з основного флоу — `src/db/wake.py` і `.github/workflows/daily.yml` видалені, бо LUMI-деплой з власною постгрес не засинає і не залежить від зовнішнього пінгу). Якщо Streamlit Cloud ще використовується — там потрібні окремі секрети БД у Secrets.

## Відомий стан / обмеження

Деталі й історія рішень — `planning/STATE.md` (веди його в актуальному стані далі, фіксуй кожен крок). Коротко: Facebook-скрапінг через requests блокується (перейшли на ScrapeCreators API), club.dtkt.ua і buhgalter.com.ua недоступні скраперам (JS-рендер / 403).

**LUMI і класифікатор.** `lumi.monobank.com.ua` резолвиться у приватну адресу `172.24.253.216` — ззовні периметру monobank недосяжний. Але задеплоєні на LUMI-платформі (`lumi-artifactory.monobank.com.ua`) проєкти **мають** доступ до LUMI API (підтверджено командою LUMI) — це виняток із загального правила "тільки публічний інтернет" для застосунків на платформі. Тож `classify` **працює** в задеплоєному на LUMI проєкті, на відміну від GitHub Actions чи іншої зовнішньої хмари.

**Бюджет.** Проєкт на LUMI платить погодинно за compute (кост-центр "Deploy · Іван Кечик", $100/міс дефолт) — окремо від цього, не до кінця з'ясовано, чи звернення до Mistral через LUMI API тарифікуються за тим самим лімітом чи окремо.

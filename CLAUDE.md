# Pain Radar

Збирає скарги ("болі") бухгалтерів малого та середнього бізнесу в Україні з публічних джерел (Telegram, форуми, RSS, Facebook, відгуки на банки-конкуренти), класифікує їх через LLM і показує в Streamlit-дашборді. Мета — знаходити проблеми клієнтів monobank Business і слабкі місця банків-конкурентів для продуктових рішень.

## Пайплайн

```
collectors/*  →  raw_messages  →  classifier  →  classified_pains  →  dashboard.py
   (збір)         (сира БД)      (LLM-розмітка)      (розмічена БД)      (Streamlit)
```

1. **Збір** (`scripts/run_collect.py`) — кожен колектор у `src/collectors/` тягне пости з одного типу джерела, рахує `content_hash` (sha256 від `source + перші 500 символів`) і пише в `raw_messages` через `insert_raw()` (ON CONFLICT DO NOTHING — дедуп на рівні хешу).
2. **Класифікація** (`scripts/run_classify.py`) — бере необроблені (`is_classified = FALSE`) записи по кожному `source` з `SOURCES` і прогонить через `classify_one()` (`src/classifier/pain_classifier.py`), пише результат у `classified_pains`, позначає `raw_messages.is_classified = TRUE`.
3. **Дашборд** (`dashboard.py`) — Streamlit, читає `classified_pains JOIN raw_messages`, кешує на 5 хв (`st.cache_data(ttl=300)`), фільтрує `is_pain=TRUE AND intensity>=2 AND pain_category!='other'` + відсікає сільгосп/агро шум текстовим фільтром.

## Схема БД

`raw_messages` (`migrations/001_raw_messages.sql`): `id, source, source_url, content_hash (UNIQUE), title, body, author, published_at, collected_at, is_classified`.

`classified_pains` (`migrations/002_classified_pains.sql` + ручні правки поза migrations!): `id, raw_message_id, is_pain, pain_category, pain_description, target, intensity (1-5), classified_at, model_used`, а також **`emotional_layer`, `quote`, `competitor_name`** — ці три колонки використовує код (`src/db/client.py`, `dashboard.py`, `pain_classifier.py`), але в `migrations/002_classified_pains.sql` їх немає. Їх додали прямо в БД (Supabase prod + локальна), файл міграції не оновили. **Якщо робиш `make migrate` на чистій БД — додай ці колонки вручну або допиши нову міграцію**, інакше класифікатор впаде на insert.

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
| `tg_<chat>` | `telegram_chat_collector.py` | Telegram-чати (buhgalteri_kiev) |
| `buh911_<forum>` | `forum_collector.py` | форум buhgalter911.com (911_help, bank_cash, audit_fines, accounting, reporting) |
| `dtkt_news` | `rss_collector.py` | RSS dtkt.ua + повний текст через Jina Reader |
| `fb_<group>` | `facebook_collector.py` | Facebook-групи через ScrapeCreators API (потребує `SCRAPECREATORS_API_KEY`) |
| `minfin_<bank>` | `minfin_collector.py` | відгуки на банки-конкуренти з minfin.com.ua |

`src/collectors/telegram_collector.py` — старий/невикористаний колектор (не імпортується в `run_collect.py`), не плутати з `telegram_public_collector.py` / `telegram_chat_collector.py`.

Новий колектор додається так: написати `collect_x()` у `src/collectors/x_collector.py` з тим самим `_hash()`/`insert_raw()`-контрактом, викликати його в `scripts/run_collect.py`, додати відповідний `source`-префікс у `SOURCES` в `scripts/run_classify.py`.

## Команди (`Makefile`)

```
make install    # venv + requirements.txt
make migrate    # прогнати migrations/*.sql
make collect    # запустити всі колектори → raw_messages
make classify   # класифікувати нові raw_messages → classified_pains
make dashboard  # streamlit run dashboard.py
```

## Конфіг

`.env` (див. `.env.example`): `DB_*` (локально Postgres.app, порт 5434), `GEMINI_API_KEY`/`LUMI_API_KEY` (класифікатор зараз реально ходить через LUMI, `base_url=https://lumi.monobank.com.ua/v1`, модель `Mistral-Large-3` — не Gemini, назва env-змінної історична), `SCRAPECREATORS_API_KEY`, `TG_API_ID/TG_API_HASH/TG_SESSION` (Telethon).

## Деплой

Streamlit Community Cloud. `runtime.txt` пінить Python 3.12 (Streamlit Cloud ще не підтримує 3.14 стабільно), `psycopg2-binary==2.9.13` — мінімальна версія з готовим wheel під нові Python. У проді БД — Supabase (не локальний Postgres.app), креди передаються через Secrets у Streamlit Cloud.

## Відомий стан / обмеження

Деталі й історія рішень — `planning/STATE.md` (веди його в актуальному стані далі, фіксуй кожен крок). Коротко: Facebook-скрапінг через requests блокується (перейшли на ScrapeCreators API), club.dtkt.ua і buhgalter.com.ua недоступні скраперам (JS-рендер / 403), автоматизація через cron ще не підключена.

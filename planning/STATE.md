# Pain Radar — STATE.md

Фіксуємо кожен крок: що зроблено, що відкрито, що далі.

---

## Поточний стан

**Фаза:** збір даних + класифікатор (тестування)
**БД:** PostgreSQL 18 локально (Postgres.app, порт 5434), БД `pain_radar`

---

## Зроблено

### Інфраструктура
- [x] Postgres 18 локально через Postgres.app (порт 5434)
- [x] БД `pain_radar`, таблиці `raw_messages` + `classified_pains`
- [x] Python 3.12 venv, всі залежності встановлено
- [x] `.env` з `GEMINI_API_KEY` (gemini-3.6-flash)

### Колектори
- [x] **RSS dtkt.ua** — `src/collectors/rss_collector.py`
  - feedparser + Jina Reader для повного тексту
  - 30 статей за запуск
- [x] **Telegram публічні канали** — `src/collectors/telegram_public_collector.py`
  - Скрапінг через `t.me/s/{username}` (BeautifulSoup)
  - 5 каналів: @bu911, @golovbukh, @Zrobleno_buhgalter, @UAtaxesYou, @buhi1c
  - ~87 постів за запуск
- [x] **Форум buhgalter911.com** — `src/collectors/forum_collector.py`
  - phpBB скрапінг по розділах: 911-допомога, Банк/каса, Перевірки/штрафи, Звітність
  - ~134 пости (10 тем × 4 розділи)
- [x] **Facebook групи** — `src/collectors/facebook_collector.py`
  - Через `facebook-scraper` (requests-based)
  - **Потребує `FB_COOKIE` в `.env`** (c_user + xs cookies з браузера)
  - 3 групи: ClubOfAccountants, Бухгалтери України, ДЕБЕТ ЗЛІВА

### Класифікатор
- [x] Gemini 3.6 Flash — `src/classifier/pain_classifier.py`
- [x] Retry на 429 (rate limit free tier: 20 req/хв)
- [x] Категорії болей включають окрему `"monobank"` категорію
- [x] `target` включає `"monobank"` як окреме значення

### Дашборд
- [x] Streamlit `dashboard.py` — готовий, не запускався з реальними даними

---

## Відкрито / В роботі

| Що | Статус | Що потрібно |
|----|--------|-------------|
| Класифікація 364 повідомлень | 🔄 Іде у фоні (~25 хв) | Авто-retry на rate limit |
| Facebook збір | ❌ Заблоковано | Facebook перевіряє IP/fingerprint, requests не проходять |
| Telegram групи (@klerkforum, @buhgalteri_kiev) | ⏳ Відкладено | Потрібен Telethon + окремий номер |
| club.dtkt.ua форум | ❌ JS-рендеринг | Потребує Playwright — відкладено |
| buhgalter.com.ua | ❌ 403 | Блокує скрапери |
| Автоматизація (cron) | 🔜 Після тесту | `make collect && make classify` щодня |

---

## Джерела збору

| Джерело | Тип | Статус | ~К-сть/запуск |
|---------|-----|--------|---------------|
| dtkt.ua | RSS + Jina | ✅ | 30 |
| @bu911 | Telegram канал | ✅ | 20 |
| @golovbukh | Telegram канал | ✅ | 15 |
| @Zrobleno_buhgalter | Telegram канал | ✅ | 20 |
| @UAtaxesYou | Telegram канал | ✅ | 20 |
| @buhi1c | Telegram канал | ✅ | 12 |
| buhgalter911.com/forum | phpBB форум | ✅ | 130+ |
| Facebook (2 групи) | ScrapeCreators API | ✅ | ~20/запуск |
| Facebook — Клуб бухгалтерів Дт-Кт | ScrapeCreators API | ❌ закрита група, posts недоступні через API | — |
| @buhgalteri_kiev | Telegram група | ⏳ Telethon | — |
| @klerkforum | Telegram група | ⏳ Telethon | — |

---

## Категорії болей (класифікатор)

| Категорія | Що включає |
|-----------|-----------|
| `integration` | M.E.Doc, 1С, BAS, API, виписки |
| `payments` | Завислі платежі, помилки переказів, ПДВ |
| `reporting` | Звітність, ДПС, декларації, перевірки, штрафи |
| `support` | Погана підтримка банку або сервісу |
| `interface` | Незручний інтерфейс |
| `limits` | Ліміти, блокування рахунків |
| `currency` | Валютні операції, НБУ |
| `monobank` | **Окремо** — будь-яка проблема з monobank Business |
| `other` | Інше |

`target`: `bank` / `monobank` / `accounting_system` / `government` / `other`

---

---

## 2026-10-20 — хмарний рантайм (репо в Гіті, запуск із хмари)

Задача від замовника: документація/конфіг лежать у Гіті, а агент запускається з
хмари, щоб менеджер міг сам дивитись болі без локального сетапу.

### Проблема, з якої все почалось: Supabase засинає

Supabase ставить free-проєкт на паузу після ~7 днів низької активності. На паузі
проєкт **не приймає з'єднання** — конект його не будить, а падає з оманливою
помилкою `FATAL: (ENOTFOUND) tenant/user postgres.<ref> not found` (пулер не знає
тенанта). Станом на 2026-10-20 прод-проєкт `ucrgpbcjgughxxevycnv` саме в такому
стані.

Рішення — не будити, а не давати заснути: активності раз на добу достатньо, а
щоденний `collect` проєкту і так був потрібен. Тобто автоматизація збору закриває
засинання як побічний ефект.

### Зроблено

- [x] `.claude/` більше не гітігнориться (крім `settings.local.json`) — скіли й
      конфіг тепер їдуть у хмару разом з репо
- [x] `.github/workflows/daily.yml` — щоденний `collect` о 06:00 UTC + ручний запуск
- [x] `src/db/wake.py` — перевірка статусу проєкту через Supabase Management API і
      пробудження, якщо на паузі (потребує `SUPABASE_PAT`, `SUPABASE_PROJECT_REF`)
- [x] `scripts/run_collect.py` — ізоляція збоїв: падіння одного колектора більше не
      вбиває весь запуск; імпорт Telegram-чатів став лінивим (читав `TG_API_ID` на
      імпорті й валив увесь скрипт без TG-змінних). Код виходу 1 лише якщо не
      спрацював жоден колектор
- [x] `src/db/client.py` — прибрано тихий дефолт на `localhost:5434`, тепер явна
      помилка про відсутні змінні
- [x] `scripts/query.py` — read-only SQL-раннер (тільки SELECT/WITH)
- [x] `.claude/skills/pain-query/SKILL.md` — скіл для менеджерських питань:
      базовий фільтр болю (копія дашбордного), SQL-рецепти, детект паузи

### Обмеження, знайдене по дорозі

`classify` **не можна** запускати з GitHub Actions: класифікатор ходить у
`https://lumi.monobank.com.ua`, а цей хост резолвиться в приватну адресу
`172.24.253.216` (RFC1918) — ззовні периметру monobank недосяжний. Тому в хмарному
workflow тільки `collect`; `classify` поки лишається ручним запуском зсередини.

Наслідок: `raw_messages` наповнюється автоматично, `classified_pains` — ні.
Дашборд показуватиме старі болі, поки хтось не запустить `make classify`.

### Відкрито

| Що | Що потрібно |
|----|-------------|
| Розбудити прод-базу | PAT у `supabase.com/dashboard/account/tokens` → `SUPABASE_PAT` |
| Секрети у GitHub | `DB_*`, `SCRAPECREATORS_API_KEY`, `SUPABASE_*` у Settings → Secrets |
| Автоматизація `classify` | self-hosted runner у периметрі / внутрішній cron / публічна LLM |
| Доступ менеджерів | read-only роль у Postgres + доступ до репо |
| GitHub вимикає cron | у репо без комітів ~60 днів розклад вимикається — тримати в голові |

### Старі наступні кроки (досі актуальні)

1. Запустити `make classify` — класифікувати всі зібрані повідомлення
2. Запустити `make dashboard` → перший погляд на болі
3. Після першого огляду — підкрутити промпт класифікатора якщо є помилки

---

## 2026-10-21 — повний перенос у хмару через LUMI deploy platform

Антон спитав про перенос усього проєкту в хмару, щоб не залежати від локального
компʼютера. Дослідив `lumi-mcp` (deploy-платформа LUMI, AWS ECS за балансувальником,
`lumi-artifactory.monobank.com.ua`) — її власний guide прямо пише, що задеплоєні
проєкти мають доступ лише до публічного інтернету і **не можуть** звертатись до
корпоративних сервісів ("never call corporate services ... such calls hang until
they time out"). З цього я зробив висновок, що LUMI-платформа теж не підходить для
`classify`, бо `lumi.monobank.com.ua` резолвиться в приватну адресу.

**Це виявилось неправильним.** Едуард Маврикін (розробник LUMI) підтвердив у Slack:
звернення до самого LUMI API з задеплоєного на платформі проєкту — **працює без
проблем** ("можно спокойно к люми обращаться"). Тобто LUMI API, вочевидь, є
винятком із загального обмеження "тільки публічний інтернет" (whitelisted як
частина самої платформи). Текст guide — не вичерпне джерело правди, довіряти варто
прямому підтвердженню від власника платформи.

### Оновлений висновок

Весь пайплайн (`collect` + `classify` + `dashboard`) можна задеплоїти одним
проєктом на LUMI-платформу — це знімає обмеження, яке раніше блокувало `classify`
у хмарі. Платформа підтримує:
- **Розклад роботи** — можна налаштувати, коли проєкт має бути активний (не 24/7,
  контроль вартості).
- **Автозатухання** — неактивний місяць → автовидалення, але на сайті буде
  попередження заздалегідь, і ре-деплой піднімає проєкт знову. Невисокий ризик.

### Відкрито

| Що | Що потрібно |
|----|-------------|
| Бюджет на Mistral-Large-3 через LUMI | Іван перевіряє, чи впишеться в ліміти — відкрите питання, не технічне |
| Формат деплою | Один docker-compose проєкт (3 сервіси max) — звести collect/classify (cron внутрі контейнера чи окремий сервіс) + dashboard під правила `deploy_project_guide` (named volumes, PORT з env, healthcheck, path prefix `/p/<project-id>/`) |
| DB | Лишити Supabase чи використати managed DB LUMI-платформи — рішення не прийняте |
| Старий план "classify лишається ручним/self-hosted runner" | Застарів, замінюється деплоєм на LUMI |

### Реалізовано (2026-10-21)

- [x] **Дамп даних з Supabase** — `seed/raw_messages.csv` (7706 рядків) +
      `seed/classified_pains.csv` (4160 рядків), через `psycopg2 copy_expert`
      (pg_dump не підійшов — клієнт 14 проти сервера Supabase 17, версії не
      сумісні). Id/FK збережені як є. Файли гітігноряться (`seed/*.csv`) —
      великі й не секретні, але не варто тягнути в git-історію; включати вручну
      в архів при деплої на LUMI.
- [x] `migrations/003_add_emotional_fields.sql` — `emotional_layer`, `quote`,
      `competitor_name` для `classified_pains` (раніше тільки ручний патч у БД)
- [x] `src/pipeline.py` — `run_collect()` / `run_classify(since=...)`, спільні
      для CLI (`scripts/run_collect.py`, `scripts/run_classify.py` стали тонкими
      обгортками) і кнопки в дашборді
- [x] `src/db/client.py::get_unclassified_by_source` — параметр `since` для
      фільтра по періоду
- [x] `dashboard.py` — сайдбар із вибором періоду (Сьогодні/Тиждень/Місяць/Весь
      час) і кнопкою "Зібрати та класифікувати" замість фонового cron
- [x] `Dockerfile` (app, Streamlit) + `db/Dockerfile` (postgres:17-alpine,
      `/docker-entrypoint-initdb.d/` = 001+002+003 міграції + `004_load_seed.sh`,
      що одноразово (тільки на порожньому томі) підвантажує `seed/*.csv`) +
      `docker-compose.yml` (2 сервіси, healthcheck у кожного, `$$`-синтаксис для
      runtime-змінних у healthcheck, `${VAR:-default}` для конфігу)
- [x] Прибрано Supabase-залежність: `src/db/wake.py`,
      `.github/workflows/daily.yml`, `SUPABASE_PAT/PROJECT_REF` з
      `.env.example`
- [x] Локально перевірено: `docker compose build && up` — обидва сервіси
      `healthy`, в БД рівно 7706/4160 рядків (seed підвантажився), Streamlit
      віддає 200 на `/` і `/_stcore/health`, з контейнера `app` є мережевий
      доступ до `lumi.monobank.com.ua` (401 на фейковий токен — хост
      резолвиться й відповідає)

### Відкрито — залишилось до повного деплою на LUMI

| Що | Що потрібно |
|----|-------------|
| Сам деплой | `deploy_create_project` → завантажити репо + `seed/*.csv` (архівом, бо гітігнорені) → `deploy_validate_project` → `deploy_start` |
| Бюджет AI-викликів через LUMI | Ще не підтверджено, чи окрема стаття витрат від deploy-бюджету $100/міс — Іван перевіряє |
| Справжня перевірка LUMI з усередині платформи | Локальний curl підтвердив тільки мережеву доступність з мого компʼютера; остаточна перевірка — тільки після реального деплою на LUMI |
| `make migrate`/`make collect`/`make classify` локально | Лишаються для розробки з Postgres.app, не зачіпались |

### Деплой на LUMI завершено (2026-10-21)

Проєкт `pain-radar` (`prj_4p6sswgtyoonyqer`) розгорнутий і працює:
**https://pain-radar.lumi-artifactory.app/**

- `app` (Streamlit) + `db` (postgres:17-alpine) — 2 контейнери, обидва healthy
- Env vars задані через `deploy_set_env_vars` (masked): `LUMI_API_KEY`,
  `POSTGRES_PASSWORD`, `TG_API_HASH`; видимі: `POSTGRES_DB/USER`, `TG_API_ID`,
  `TG_SESSION`. `SCRAPECREATORS_API_KEY` не задано — Facebook-колектор
  пропускається (graceful, як і локально)
- Вартість: ~$0.05/год (t3.large), витрачено $0.19 з $100/міс на момент запуску

**Важливий урок по дорозі:** перша спроба підвантажити seed через
`docker-entrypoint-initdb.d` на `db`-сервісі (підхід, що локально працював на
чистому томі) **не спрацювала на LUMI** — том БД вже був ініціалізований
міграціями при першому `deploy_start`, тож init-скрипти при наступному
перезапуску/перезбірці вже не виконуються (поведінка офіційного postgres-образу:
`/docker-entrypoint-initdb.d` запускається лише коли `PGDATA` порожній).
Переробив на ідемпотентну перевірку зі сторони `app`-контейнера —
`scripts/seed_if_empty.py` виконується перед `streamlit run` при кожному старті,
перевіряє `SELECT count(*) FROM raw_messages` і довантажує
`raw_messages.csv.gz`/`classified_pains.csv.gz` (лежать у корені проєкту, не в
`seed/` — веб-UI LUMI заливає файли в корінь, а не у вказану підпапку) лише якщо
таблиця порожня. Такий підхід універсальний — спрацює і при деплої з нуля, і при
відновленні вже наповненої БД (просто нічого не робить вдруге).

### Відкрито

| Що | Що потрібно |
|----|-------------|
| Бюджет AI-викликів Mistral через LUMI | Окремий від deploy-бюджету чи той самий — Іван ще перевіряє |
| Перевірка кнопки "Зібрати та класифікувати" з реальним трафіком | Ще не натискали на проді — варто перевірити вручну, що колектори й LUMI-класифікатор відпрацьовують зсередини платформи |
| `.github/workflows` | Видалено разом з Supabase-залежністю — якщо знадобиться окремий зовнішній тригер колекції, треба продумати нарізно |

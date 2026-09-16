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

## Наступні кроки

1. Запустити `make classify` — класифікувати всі зібрані повідомлення
2. Додати `FB_COOKIE` → запустити `make collect` → отримати Facebook дані
3. Запустити `make dashboard` → перший погляд на болі
4. Після першого огляду — підкрутити промпт класифікатора якщо є помилки

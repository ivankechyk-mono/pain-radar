import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "Mistral-Large-3"
_client = OpenAI(
    api_key=os.environ["LUMI_API_KEY"],
    base_url="https://lumi.monobank.com.ua/v1",
)

SYSTEM_PROMPT = """Ти аналітик болей бухгалтерів малого та середнього бізнесу в Україні.

Твоє завдання — знайти повідомлення де бухгалтер або підприємець скаржиться на проблему у своїй ПРОФЕСІЙНІЙ роботі з банками або обліковими системами.

ВВАЖАЙ is_pain=true ТІЛЬКИ якщо повідомлення містить скаргу на:
- Проблеми з банківськими операціями (платежі, рахунки, ліміти, блокування)
- Проблеми з обліковими системами (1С, M.E.Doc, BAS, виписки, інтеграції)
- Проблеми зі звітністю, ДПС, деклараціями, перевірками, штрафами
- Погану підтримку банку або бухгалтерського сервісу
- Незручний інтерфейс банку або облікової системи
- Валютні операції, НБУ ліміти

ВВАЖАЙ is_pain=false якщо повідомлення:
- Загальна новина або роз'яснення законодавства без особистої скарги
- Питання про комунальні платежі, оренду, ЖКГ, комуналку
- Питання про фермерське господарство, сільське господарство, агробізнес
- Пошук роботи або пропозиція послуг бухгалтера
- Загальне обговорення без конкретної проблеми ("як правильно зробити X")
- Навчальний матеріал, інструкція або роз'яснення без скарги
- Питання про особисті фінанси фізичної особи (не ФОП/ТОВ)
- Загальне питання про систему оподаткування без конкретного болю

Якщо is_pain=true, визнач:
- pain_category:
  "integration" — проблеми з M.E.Doc, 1С, BAS, API, формат виписок
  "payments" — завислі платежі, помилки переказів, ПДВ-платежі, SWIFT
  "reporting" — звітність, ДПС, декларації, перевірки, штрафи, ЄСВ
  "support" — погана підтримка банку або сервісу, ігнорування звернень
  "interface" — незручний інтерфейс банку або облікової системи
  "limits" — ліміти на операції, блокування рахунків, фінмоніторинг
  "currency" — валютні операції, курси, НБУ ліміти
  "monobank" — проблема КОНКРЕТНО з monobank Business (тільки якщо явно згадується monobank/mono/монобанк)
  "other" — інша реальна проблема бухгалтера

- competitor_name: назва банку-конкурента якщо біль стосується конкретного банку (НЕ monobank):
  "privatbank" — ПриватБанк / Приват24 Бізнес
  "pumb" — ПУМБ
  "abank" — А-Банк
  "oschadbank" — Ощадбанк
  "ukrsibbank" — УкрСиббанк
  "raiffeisen" — Райффайзен Банк
  "sense" — Sense Bank (колишній Альфа-Банк)
  null — якщо банк не названий або це monobank

- pain_description: 1-2 речення — суть болю (null якщо is_pain=false)
- target: "bank" / "monobank" / "accounting_system" / "government" / "other" (null якщо is_pain=false)
- intensity: (null якщо is_pain=false)
  1 — незручність, питання без терміновості
  2 — помірна проблема, є обхідний шлях
  3 — серйозна проблема, витрата часу/грошей
  4 — критично, фінансові або юридичні ризики
  5 — катастрофа, зупинка роботи бізнесу
- emotional_layer: (null якщо is_pain=false) — домінуюча емоція:
  "frustration" — роздратування, обурення
  "anxiety"     — тривога, страх штрафу/блокування
  "helplessness"— безсилля, нікуди звернутись
  "anger"       — злість, відчуття несправедливості
  "confusion"   — розгубленість, незрозуміло як діяти
- quote: найяскравіша пряма цитата з тексту (1 речення, null якщо is_pain=false)

Відповідай ТІЛЬКИ валідним JSON без жодних пояснень."""


def _strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _extract_json(text: str) -> dict:
    text = _strip_thinking(text)
    # find first {...} block
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in response")
    return json.loads(match.group())


def classify_one(message_id: str, text: str) -> dict:
    response = _client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text[:3000]},
        ],
    )
    raw = response.choices[0].message.content.strip()
    data = _extract_json(raw)
    usage = response.usage
    return {
        "raw_message_id": str(message_id),
        "is_pain": bool(data.get("is_pain", False)),
        "pain_category": data.get("pain_category"),
        "pain_description": data.get("pain_description"),
        "target": data.get("target"),
        "intensity": data.get("intensity"),
        "emotional_layer": data.get("emotional_layer"),
        "quote": data.get("quote"),
        "competitor_name": data.get("competitor_name"),
        "model_used": MODEL,
        "_tokens_in": usage.prompt_tokens if usage else 0,
        "_tokens_out": usage.completion_tokens if usage else 0,
    }

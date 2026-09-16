import os
import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Pain Radar", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
body, .stApp { background: #0f1117; color: #e0e0e0; }
.block-container { padding-top: 1.5rem; }
.kpi-card { background: #1c1f2e; border-radius: 10px; padding: 18px 22px; text-align: center; }
.kpi-val { font-size: 34px; font-weight: 800; }
.kpi-lbl { font-size: 12px; color: #888; margin-top: 3px; }
.section { font-size: 19px; font-weight: 700; color: #fff; margin: 28px 0 12px; }
.quote-card { background: #1c1f2e; border-left: 3px solid #5c6bc0; border-radius: 8px;
              padding: 12px 16px; margin-bottom: 8px; font-size: 14px; color: #ccc; }
.quote-card .meta { margin-bottom: 6px; }
.quote-card .body { margin-top: 4px; }
.new-card { background: #1c2e1c; border-left: 3px solid #4caf50; border-radius: 8px;
            padding: 12px 16px; margin-bottom: 8px; font-size: 14px; color: #ccc; }
.pill { display:inline-block; border-radius:5px; padding:2px 8px; font-size:11px;
        font-weight:600; margin-right:4px; background:#ffffff15; color:#aaa; }
</style>
""", unsafe_allow_html=True)


def emotion_badge(layer):
    emap = {
        "frustration":  ("😤", "#ff7043"),
        "anxiety":      ("😰", "#ffa726"),
        "helplessness": ("😔", "#ab47bc"),
        "anger":        ("😡", "#ef5350"),
        "confusion":    ("😕", "#29b6f6"),
    }
    if not layer or isinstance(layer, float):
        return ""
    icon, color = emap.get(layer, ("", "#888"))
    return f'<span class="pill" style="color:{color}">{icon} {layer}</span>'


def safe_text(desc, quote="", body="", limit=300):
    for val in (desc, quote, body):
        if val is not None and not isinstance(val, float) and str(val).strip():
            return str(val).strip()[:limit]
    return ""


def quote_card(q, color, src_override=None):
    text   = safe_text(q["description"], q.get("quote"), q["body"])
    src    = src_override or q["source"] or ""
    i_bar  = "█" * int(q["intensity"] or 0) + "░" * (5 - int(q["intensity"] or 0))
    emotion = emotion_badge(q.get("emotional_layer"))
    link   = (f' <a href="{q["url"]}" target="_blank" '
              f'style="color:{color};font-size:12px">→ джерело</a>') if q["url"] else ""
    return (
        f'<div class="quote-card" style="border-left-color:{color}">'
        f'<div class="meta"><span class="pill">{src}</span>'
        f'<span class="pill" style="color:{color}">{i_bar}</span>{emotion}</div>'
        f'<div class="body">{text}{link}</div></div>'
    )


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 5434)),
        dbname=os.environ.get("DB_NAME", "pain_radar"),
        user=os.environ.get("DB_USER", "redbull1122"),
        password=os.environ.get("DB_PASSWORD", ""),
    )


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql("""
        SELECT
            cp.pain_category    AS category,
            cp.pain_description AS description,
            cp.quote,
            cp.emotional_layer,
            cp.competitor_name,
            cp.target,
            cp.intensity,
            rm.source,
            LEFT(rm.body, 500)  AS body,
            rm.source_url       AS url,
            rm.published_at
        FROM classified_pains cp
        JOIN raw_messages rm ON rm.id = cp.raw_message_id
        WHERE cp.is_pain = TRUE
          AND cp.intensity >= 2
          AND cp.pain_category != 'other'
          AND (COALESCE(cp.pain_description, '') NOT ILIKE '%фермерськ%'
               AND COALESCE(cp.pain_description, '') NOT ILIKE '%сільгосп%'
               AND COALESCE(cp.pain_description, '') NOT ILIKE '%оранк%'
               AND COALESCE(cp.pain_description, '') NOT ILIKE '%агро%')
        ORDER BY cp.intensity DESC, rm.published_at DESC
        LIMIT 2000
    """, conn)
    conn.close()
    if not df.empty:
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    return df


CATEGORY_UA = {
    "integration": "Інтеграції",
    "payments":    "Платежі",
    "reporting":   "Звітність / ДПС",
    "support":     "Підтримка",
    "interface":   "Інтерфейс",
    "limits":      "Ліміти / блокування",
    "currency":    "Валюта",
    "monobank":    "monobank",
}
ICON = {
    "integration": "🔌", "payments": "💸", "reporting": "📋",
    "support": "📞", "interface": "🖥️", "limits": "🚫",
    "currency": "💱", "monobank": "🟡",
}
CAT_COLOR = {
    "integration": "#5c6bc0", "payments": "#ef5350", "reporting": "#ff7043",
    "support":     "#ab47bc", "interface": "#26a69a", "limits": "#ffa726",
    "currency":    "#29b6f6", "monobank": "#f5a623",
}
COMPETITOR_LABEL = {
    "privatbank": ("💙 ПриватБанк", "#1565C0"),
    "pumb":       ("🟠 ПУМБ",        "#E65100"),
    "abank":      ("🔵 А-Банк",      "#0288D1"),
    "oschadbank": ("🟢 Ощадбанк",    "#2E7D32"),
    "ukrsibbank": ("🟣 УкрСиббанк",  "#6A1B9A"),
    "raiffeisen": ("🟡 Райффайзен",  "#F9A825"),
    "sense":      ("🔴 Sense Bank",  "#B71C1C"),
}

# ── Load ──────────────────────────────────────────────────────────────────────
df = load_data()

st.markdown("## 📡 Pain Radar — болі бухгалтерів")

if df.empty:
    st.warning("Даних немає. Запусти класифікацію.")
    st.stop()

now      = pd.Timestamp.now(tz="UTC")
week_ago = now - pd.Timedelta(days=7)

total    = len(df)
critical = len(df[df["intensity"] >= 4])
mono_cnt = len(df[df["category"] == "monobank"])
new_cnt  = len(df[df["published_at"] >= week_ago])

dated = df["published_at"].dropna()
if not dated.empty:
    date_range = f"{dated.min().strftime('%d.%m.%Y')} – {dated.max().strftime('%d.%m.%Y')}"
else:
    date_range = "дати невідомі"

# ── KPI row ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
for col, val, lbl, color in [
    (c1, total,      "Болей зібрано",      "#5c6bc0"),
    (c2, critical,   "🔴 Критичних (4-5)", "#ef5350"),
    (c3, mono_cnt,   "🟡 Про monobank",    "#f5a623"),
    (c4, new_cnt,    "🆕 Нових за тиждень","#4caf50"),
]:
    col.markdown(
        f'<div class="kpi-card"><div class="kpi-val" style="color:{color}">{val}</div>'
        f'<div class="kpi-lbl">{lbl}</div></div>',
        unsafe_allow_html=True,
    )

st.caption(f"Період: {date_range}")

st.markdown("---")

# ── Категорії — цитати ────────────────────────────────────────────────────────
st.markdown('<div class="section">🔥 Болі по категоріях</div>', unsafe_allow_html=True)

cat_stats = (
    df.groupby("category")
    .agg(count=("category", "count"), avg_i=("intensity", "mean"))
    .reset_index()
    .sort_values(["avg_i", "count"], ascending=False)
)

for _, row in cat_stats.iterrows():
    cat   = row["category"]
    label = CATEGORY_UA.get(cat, cat)
    icon  = ICON.get(cat, "❓")
    color = CAT_COLOR.get(cat, "#5c6bc0")
    cat_df = df[df["category"] == cat].sort_values("intensity", ascending=False)

    with st.expander(f"{icon} {label}  —  {int(row['count'])} згадок · гострота {row['avg_i']:.1f}/5"):
        cards_html = "".join(quote_card(q, color) for _, q in cat_df.iterrows())
        st.markdown(
            f'<div style="max-height:500px;overflow-y:auto;padding-right:6px">{cards_html}</div>',
            unsafe_allow_html=True,
        )

st.markdown("---")

# ── monobank окремо ───────────────────────────────────────────────────────────
st.markdown('<div class="section">🟡 monobank Business — окремо</div>', unsafe_allow_html=True)

mono_df = df[df["category"] == "monobank"].sort_values("intensity", ascending=False)

if mono_df.empty:
    st.info("Згадок про monobank поки не знайдено.")
else:
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Згадок", len(mono_df))
    mc2.metric("Середня гострота", f"{mono_df['intensity'].mean():.1f} / 5")
    mc3.metric("Критичних (4-5)", len(mono_df[mono_df["intensity"] >= 4]))

    st.markdown("")
    cards_html = "".join(
        quote_card(q, "#f5a623") for _, q in mono_df.iterrows()
    )
    st.markdown(
        f'<div style="max-height:500px;overflow-y:auto;padding-right:6px">{cards_html}</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Конкуренти ────────────────────────────────────────────────────────────────
st.markdown('<div class="section">🏦 Конкуренти — болі клієнтів</div>', unsafe_allow_html=True)
st.caption("Скарги клієнтів банків-конкурентів з minfin.com.ua та інших джерел")

comp_df = df[df["competitor_name"].notna() & (df["competitor_name"] != "")].copy()

if comp_df.empty:
    st.info("Конкурентних болей поки не класифіковано. Запусти класифікацію для minfin джерел.")
else:
    comp_stats = (
        comp_df.groupby("competitor_name")
        .agg(count=("competitor_name", "count"), avg_i=("intensity", "mean"))
        .reset_index()
        .sort_values("count", ascending=False)
    )

    cols = st.columns(min(len(comp_stats), 4))
    for i, (_, row) in enumerate(comp_stats.head(4).iterrows()):
        bank = row["competitor_name"]
        lbl, color = COMPETITOR_LABEL.get(bank, (f"🏦 {bank}", "#5c6bc0"))
        cols[i].markdown(
            f'<div class="kpi-card" style="border-top:3px solid {color}">'
            f'<div style="font-size:15px;font-weight:700;margin:4px 0">{lbl}</div>'
            f'<div class="kpi-val" style="color:{color};font-size:26px">{int(row["count"])}</div>'
            f'<div class="kpi-lbl">скарг · гострота {row["avg_i"]:.1f}/5</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")
    for _, row in comp_stats.iterrows():
        bank = row["competitor_name"]
        lbl, color = COMPETITOR_LABEL.get(bank, (f"🏦 {bank}", "#5c6bc0"))
        bank_df = comp_df[comp_df["competitor_name"] == bank].sort_values("intensity", ascending=False)

        with st.expander(f"{lbl}  —  {int(row['count'])} скарг · гострота {row['avg_i']:.1f}/5"):
            cards_html = "".join(quote_card(q, color) for _, q in bank_df.iterrows())
            st.markdown(
                f'<div style="max-height:500px;overflow-y:auto;padding-right:6px">{cards_html}</div>',
                unsafe_allow_html=True,
            )

st.markdown("---")

# ── Нове за тиждень ───────────────────────────────────────────────────────────
st.markdown('<div class="section">🆕 Нове за останній тиждень</div>', unsafe_allow_html=True)

new_df = df[df["published_at"] >= week_ago].sort_values("intensity", ascending=False)

if new_df.empty:
    st.info("За останній тиждень нових болей не знайдено.")
else:
    cards_html = ""
    for _, q in new_df.head(20).iterrows():
        cat   = q["category"]
        color = CAT_COLOR.get(cat, "#5c6bc0")
        icon  = ICON.get(cat, "❓")
        label = CATEGORY_UA.get(cat, cat)
        text  = safe_text(q["description"], q.get("quote"), q["body"])
        src   = q["source"] or ""
        link  = (f' <a href="{q["url"]}" target="_blank" '
                 f'style="color:{color};font-size:12px">→ джерело</a>') if q["url"] else ""
        cards_html += (
            f'<div class="new-card" style="border-left-color:{color}">'
            f'<div class="meta"><span class="pill" style="color:{color}">{icon} {label}</span>'
            f'<span class="pill">{src}</span></div>'
            f'<div class="body">{text}{link}</div></div>'
        )
    st.markdown(
        f'<div style="max-height:600px;overflow-y:auto;padding-right:6px">{cards_html}</div>',
        unsafe_allow_html=True,
    )

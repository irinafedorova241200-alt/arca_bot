import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")

SYMPTOMS = {
    "energy":       {"zone": "Энергетический метаболизм",      "markers": "Митохондрии · Кортизол · Ферритин",     "adj": 2.1, "rec": "Панель энергетических маркеров — митохондриальная функция, ферритин, кортизол."},
    "focus":        {"zone": "Когнитивная функция",             "markers": "ТТГ · Тестостерон · Витамин D",         "adj": 1.8, "rec": "Гормональная панель — ТТГ, тестостерон, витамин D."},
    "sleep":        {"zone": "Циркадный ритм и восстановление", "markers": "Кортизол · Мелатонин · Магний",         "adj": 2.4, "rec": "Анализ кортизол / мелатонин — нарушение ритма видно в крови."},
    "productivity": {"zone": "Надпочечниковая ось",             "markers": "ДГЭА · Кортизол · Адреналин",           "adj": 1.6, "rec": "Стресс-гормональная панель — ДГЭА-сульфат и суточный кортизол."},
    "weight":       {"zone": "Метаболический профиль",          "markers": "Инсулин · Лептин · ТТГ",                "adj": 2.2, "rec": "Метаболический чекап — инсулинорезистентность, щитовидная железа."},
    "mood":         {"zone": "Гормональный баланс",             "markers": "Кортизол · Серотонин · Прогестерон",    "adj": 1.9, "rec": "Нейроэндокринная панель — кортизол, серотонин, прогестерон."},
    "libido":       {"zone": "Половые гормоны",                 "markers": "Тестостерон · ДГЭА · ЛГ / ФСГ",        "adj": 2.0, "rec": "Панель половых гормонов — тестостерон, ДГЭА, ЛГ / ФСГ."},
    "immunity":     {"zone": "Иммунный статус и воспаление",    "markers": "СРБ · ИЛ-6 · Витамин D",               "adj": 1.5, "rec": "Воспалительные маркеры — СРБ и ИЛ-6 показывают хроническое воспаление."},
}

SYMPTOM_LABELS = {
    "energy":       "Хроническая усталость, нет энергии",
    "focus":        "Туман в голове, сложно концентрироваться",
    "sleep":        "Плохой сон, не высыпаюсь",
    "productivity": "Снизилась продуктивность",
    "weight":       "Лишний вес, не уходит",
    "mood":         "Раздражительность, тревога",
    "libido":       "Снизилось либидо",
    "immunity":     "Частые болезни, слабый иммунитет",
}

GOLD      = colors.HexColor("#B8962E")
GOLD_PALE = colors.HexColor("#F5EDD6")
DARK      = colors.HexColor("#141414")
MUTED     = colors.HexColor("#888880")
RED       = colors.HexColor("#C05050")
AMBER     = colors.HexColor("#B8962E")
GREEN     = colors.HexColor("#6A9E3A")
LINE      = colors.HexColor("#E8E3D5")


def calc_bio_age(passport_age, sym_keys):
    adj = sum(SYMPTOMS[s]["adj"] for s in sym_keys if s in SYMPTOMS)
    bio = max(passport_age, round(passport_age + adj * 0.72))
    return bio, bio - passport_age


def get_load(adj):
    pct = min(94, round(50 + adj * 9))
    if pct > 78:   return pct, "Высокая нагрузка",   RED
    elif pct > 62: return pct, "Умеренная нагрузка", AMBER
    else:          return pct, "Под контролем",       GREEN


def build_pdf(name, passport_age, sym_keys, contact):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=18*mm, bottomMargin=18*mm)
    bio, diff = calc_bio_age(passport_age, sym_keys)
    S = ParagraphStyle  # alias

    def ps(name, **kw):
        return S(name, fontName=kw.pop("font","Helvetica"),
                 fontSize=kw.pop("size",10), textColor=kw.pop("color",DARK), **kw)

    story = []

    # Header
    hdr = Table([[
        Paragraph("<b>ARCA</b>", ps("logo", font="Helvetica-Bold", size=22, color=GOLD)),
        Paragraph("Карта биологического старения", ps("r", size=9, color=MUTED, alignment=TA_RIGHT)),
    ]], colWidths=[90*mm, 80*mm])
    hdr.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LINEBELOW",(0,0),(-1,-1),0.5,LINE),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    story += [hdr, Spacer(1,6*mm)]

    # Person
    story += [
        Paragraph("ПЕРСОНАЛЬНЫЙ ОТЧЁТ", ps("k", size=8, color=MUTED, spaceAfter=4)),
        Paragraph(name, ps("nm", font="Helvetica-Bold", size=18, spaceAfter=2)),
        Paragraph(f"Паспортный возраст: {passport_age} лет", ps("ag", size=10, color=MUTED, spaceAfter=6)),
        HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=6*mm),
    ]

    # Bio age box
    age_tbl = Table([[
        Paragraph(f"<font size=11 color='#888880'>Паспортный</font><br/>"
                  f"<font size=44 color='#CCCCCC'><b>{passport_age}</b></font>",
                  ps("pa", alignment=TA_CENTER)),
        Paragraph("<font size=18 color='#DDDDDD'>vs</font>",
                  ps("vs", alignment=TA_CENTER)),
        Paragraph(f"<font size=11 color='#888880'>Биологический</font><br/>"
                  f"<font size=44 color='#B8962E'><b>{bio}</b></font>",
                  ps("ba", alignment=TA_CENTER)),
    ]], colWidths=[60*mm,20*mm,60*mm])
    age_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F9F6EE")),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),10),
        ("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("BOX",(0,0),(-1,-1),0.5,LINE),
    ]))
    story.append(age_tbl)
    story.append(Spacer(1,3*mm))

    if diff > 0:
        delta_txt  = f"Биовозраст старше на {diff} {'год' if diff==1 else 'года' if diff<5 else 'лет'}"
        delta_col  = RED
        note_txt   = "По симптомам видна нагрузка на несколько систем. Точный биовозраст — по анализам крови (±1–2 года)."
    elif diff < 0:
        delta_txt  = f"Биовозраст моложе на {abs(diff)} {'год' if abs(diff)==1 else 'года' if abs(diff)<5 else 'лет'}"
        delta_col  = GREEN
        note_txt   = "Хороший сигнал. Анализы крови покажут зоны, которые стоит поддержать."
    else:
        delta_txt  = "Биовозраст совпадает с паспортным"
        delta_col  = AMBER
        note_txt   = "По симптомам есть скрытые зоны нагрузки. Анализы крови покажут, что именно скорректировать."

    story += [
        Paragraph(delta_txt, ps("dt", font="Helvetica-Bold", size=10, color=delta_col,
                                alignment=TA_CENTER, spaceAfter=3)),
        Paragraph(note_txt,  ps("nt", size=9, color=MUTED, alignment=TA_CENTER, spaceAfter=6*mm)),
    ]

    # Zones
    story.append(Paragraph("СИСТЕМЫ ПОД НАГРУЗКОЙ",
        ps("sh", font="Helvetica-Bold", size=8, color=MUTED, spaceAfter=4*mm)))

    for key in sym_keys:
        if key not in SYMPTOMS: continue
        d = SYMPTOMS[key]
        pct, status, col = get_load(d["adj"])
        zt = Table([[
            Paragraph(f"<b>{d['zone']}</b>",       ps("zn", font="Helvetica-Bold", size=10)),
            Paragraph(f"<font color='#{col.hexval()[2:]}'><b>{pct}%</b></font>",
                      ps("zp", size=10, alignment=TA_RIGHT)),
        ],[
            Paragraph(f"<font size=8 color='#888880'>{d['markers']}</font>", ps("zm",size=8,color=MUTED)),
            Paragraph(f"<font size=8 color='#{col.hexval()[2:]}'>{status}</font>",
                      ps("zs",size=8,alignment=TA_RIGHT)),
        ]], colWidths=[120*mm,30*mm])
        zt.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),3),
            ("BOTTOMPADDING",(0,0),(-1,-1),2),
        ]))
        story.append(zt)
        story.append(HRFlowable(width=f"{pct}%", thickness=3, color=col, spaceAfter=3*mm))

    # Recommendations
    story += [
        Spacer(1,2*mm),
        HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=4*mm),
        Paragraph("ЧТО ПРОВЕРИТЬ В ПЕРВУЮ ОЧЕРЕДЬ",
            ps("sh2", font="Helvetica-Bold", size=8, color=MUTED, spaceAfter=4*mm)),
    ]
    for i, key in enumerate(sorted([k for k in sym_keys if k in SYMPTOMS],
                                   key=lambda k: SYMPTOMS[k]["adj"], reverse=True)[:4], 1):
        d = SYMPTOMS[key]
        story += [
            Paragraph(f"<b>{i}. {d['zone']}</b>",
                      ps("rt", font="Helvetica-Bold", size=10, spaceAfter=2)),
            Paragraph(d["rec"],
                      ps("rx", size=9, color=MUTED, spaceAfter=5, leftIndent=10)),
        ]

    # CTA footer
    story += [
        Spacer(1,4*mm),
        HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=4*mm),
    ]
    cta = Table([[
        Paragraph("<b>Следующий шаг — точная диагностика по анализам крови</b><br/>"
                  "<font size=9 color='#888880'>ARCA определяет биологический возраст по 50+ биомаркерам (±1–2 года)</font>",
                  ps("cl", size=10)),
        Paragraph(f"<font color='#B8962E'><b>@ARCA_Manager</b></font><br/>"
                  "<font size=8 color='#888880'>Осталось 4 места в июне</font>",
                  ps("cr", size=10, alignment=TA_RIGHT)),
    ]], colWidths=[100*mm,50*mm])
    cta.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),GOLD_PALE),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
    ]))
    story += [
        cta, Spacer(1,3*mm),
        Paragraph("* Расчёт носит информационный характер. Основан на адаптированной методике Levine PhenoAge.",
                  ps("disc", size=7, color=colors.HexColor("#BBBBBB"), alignment=TA_CENTER)),
    ]

    doc.build(story)
    buf.seek(0)
    return buf.read()


def parse_message(text):
    data = {}
    lines = text.strip().split("\n")
    for line in lines:
        # Name
        if "Имя:" in line:
            data["name"] = line.split("Имя:")[-1].strip().split(",")[0].strip()
        # Age — works for both "возраст: 35" and "Имя: Иван, возраст: 35"
        m = re.search(r"возраст[:\s]+(\d+)", line, re.IGNORECASE)
        if m:
            data["age"] = int(m.group(1))
        # Contact
        if "Контакт:" in line or "Телефон:" in line:
            data["contact"] = line.split(":", 1)[-1].strip()
        # Symptoms — match Russian symptom labels
        if "Симптомы:" in line or "Зоны" in line:
            raw = line.split(":", 1)[-1].strip()
            found = []
            for key, lbl in SYMPTOM_LABELS.items():
                if lbl.lower() in raw.lower() and key not in found:
                    found.append(key)
            # Also try zone names
            for key, sym in SYMPTOMS.items():
                if sym["zone"].lower() in raw.lower() and key not in found:
                    found.append(key)
            if found:
                data["symptoms"] = found
    return data


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот ARCA — генерирую персональную карту старения в PDF.\n\n"
        "Когда клиент заполняет форму на сайте и нажимает кнопку — "
        "его данные приходят сюда, и я сразу отправляю ему PDF.\n\n"
        "Напишите /help для справки."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Ожидаемый формат сообщения от сайта:\n\n"
        "Заявка с мини-квиза ARCA\n"
        "Имя: Иван\n"
        "Контакт: +79991234567\n"
        "Симптомы: Хроническая усталость, нет энергии, Плохой сон...\n\n"
        "Бот распарсит данные и вышлет PDF карту старения."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return

    # Accept ANY message that looks like a form submission
    is_submission = any(kw in text for kw in [
        "Заявка", "ARCA", "Имя:", "Симптомы:", "Контакт:", "Телефон:"
    ])

    if not is_submission:
        await update.message.reply_text(
            "Сообщение получено, но не похоже на заявку с сайта.\n"
            "Напишите /help чтобы увидеть нужный формат."
        )
        return

    data    = parse_message(text)
    name    = data.get("name", "Клиент")
    age     = data.get("age", 38)
    syms    = data.get("symptoms") or ["energy", "sleep", "focus"]
    contact = data.get("contact", "не указан")

    await update.message.reply_text(
        f"✅ Заявка от {name}, {age} лет\n"
        f"Контакт: {contact}\n"
        f"⏳ Генерирую карту старения..."
    )

    try:
        pdf_bytes = build_pdf(name, age, syms, contact)
        fname     = f"ARCA_Karta_{name.replace(' ','_')}.pdf"
        await update.message.reply_document(
            document=io.BytesIO(pdf_bytes),
            filename=fname,
            caption=(
                f"📊 Карта старения — {name}, {age} лет\n\n"
                f"Биовозраст рассчитан по симптомам.\n"
                f"Контакт клиента: {contact}\n\n"
                f"Для точной диагностики по анализам крови — свяжитесь с клиентом."
            )
        )
    except Exception as e:
        logger.error(f"PDF error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка генерации PDF: {e}")


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN не задан в переменных окружения Railway.")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("✅ Бот запущен")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

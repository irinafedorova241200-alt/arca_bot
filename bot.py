import os, logging, io, re, math
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TOKEN = os.environ.get("BOT_TOKEN", "")

# ── Fonts (system fonts, no download needed) ──
FONT_PATH = "/usr/share/fonts/truetype/liberation/"
pdfmetrics.registerFont(TTFont("R",  FONT_PATH + "LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("B",  FONT_PATH + "LiberationSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("I",  FONT_PATH + "LiberationSans-Italic.ttf"))
pdfmetrics.registerFont(TTFont("BI", FONT_PATH + "LiberationSans-BoldItalic.ttf"))

# ── Colours ──
GOLD   = colors.HexColor("#B8962E")
GOLD2  = colors.HexColor("#D4AF5A")
CREAM  = colors.HexColor("#FAF7EF")
DARK   = colors.HexColor("#1A1A18")
MUTED  = colors.HexColor("#6B6B68")
LINE   = colors.HexColor("#E2DDD2")
RED    = colors.HexColor("#C05050")
AMBER  = colors.HexColor("#D4822A")
GREEN  = colors.HexColor("#5A9E3A")
BGDARK = colors.HexColor("#1C1C18")
WHITE  = colors.white
PALE   = colors.HexColor("#F5EDD6")
PALE2  = colors.HexColor("#FEF9F0")

# ── Data ──
SYMPTOMS = {
    "energy":       {"zone":"Энергетический метаболизм",  "markers":"Митохондрии · Кортизол · Ферритин",    "adj":2.1,
                     "rec":"Митохондриальная дисфункция — ключевая причина хронической усталости. Снижение АТФ-синтеза нарушает работу всех клеток.",
                     "action":"Сдать: Ферритин, Кортизол (4 точки), Коэнзим Q10, Витамин B12, Гомоцистеин"},
    "focus":        {"zone":"Когнитивная функция",         "markers":"ТТГ · Тестостерон · Витамин D",        "adj":1.8,
                     "rec":"Когнитивный туман связан с субоптимальной работой щитовидной железы или дефицитом половых гормонов. Нейровоспаление усиливает симптомы.",
                     "action":"Сдать: ТТГ, Т3 своб., Тестостерон (общ./своб.), Витамин D, СРБ вч"},
    "sleep":        {"zone":"Циркадный ритм и восстановление","markers":"Кортизол · Мелатонин · Магний",     "adj":2.4,
                     "rec":"Высокий вечерний кортизол блокирует мелатонин и нарушает фазы сна. Дефицит магния усиливает тревожность и поверхностный сон.",
                     "action":"Сдать: Кортизол (вечер), Мелатонин (ночь), Магний RBC, ГАМК, Витамин B6"},
    "productivity": {"zone":"Надпочечниковая ось",         "markers":"ДГЭА · Кортизол · Адреналин",          "adj":1.6,
                     "rec":"Хроническая перегрузка надпочечников истощает резервы ДГЭА. Это напрямую влияет на мотивацию, стрессоустойчивость и работоспособность.",
                     "action":"Сдать: ДГЭА-С, Кортизол (утро), Катехоламины мочи, Органические кислоты"},
    "weight":       {"zone":"Метаболический профиль",      "markers":"Инсулин · Лептин · ТТГ",               "adj":2.2,
                     "rec":"Инсулинорезистентность и лептинорезистентность — ведущие причины избыточного веса. Маскируются под 'нормальную' глюкозу натощак.",
                     "action":"Сдать: Инсулин натощак, HOMA-IR, Лептин, ТТГ, Т3 реверс, АМГ"},
    "mood":         {"zone":"Гормональный баланс",         "markers":"Кортизол · Серотонин · Прогестерон",   "adj":1.9,
                     "rec":"Дисбаланс кортизол/прогестерон — главная причина тревожности. У мужчин критично соотношение тестостерон/эстрадиол.",
                     "action":"Сдать: Кортизол, Прогестерон, Эстрадиол, ГСПГ, Серотонин (тромбоциты)"},
    "libido":       {"zone":"Половые гормоны",             "markers":"Тестостерон · ДГЭА · ЛГ/ФСГ",         "adj":2.0,
                     "rec":"Снижение либидо — ранний маркер гормонального дисбаланса. Важна не только общая концентрация, но и свободная фракция тестостерона.",
                     "action":"Сдать: Тестостерон (общ./своб.), ГСПГ, ЛГ, ФСГ, Пролактин, ДГЭА-С"},
    "immunity":     {"zone":"Иммунитет и воспаление",      "markers":"СРБ · ИЛ-6 · Витамин D",              "adj":1.5,
                     "rec":"Хроническое субклиническое воспаление — основной механизм ускоренного биологического старения. СРБ выше 1 мг/л уже клинически значим.",
                     "action":"Сдать: СРБ высокочувствительный, ИЛ-6, Гомоцистеин, Витамин D, Ферритин"},
}

LABELS = {
    "energy":"Хроническая усталость, нет энергии",
    "focus":"Туман в голове, сложно концентрироваться",
    "sleep":"Плохой сон, не высыпаюсь",
    "productivity":"Снизилась продуктивность",
    "weight":"Лишний вес, не уходит",
    "mood":"Раздражительность, тревога",
    "libido":"Снизилось либидо",
    "immunity":"Частые болезни, слабый иммунитет",
}

# ── Custom Flowables ──
class GaugeChart(Flowable):
    def __init__(self, passport, bio, w=170*mm, h=60*mm):
        super().__init__()
        self.passport = passport
        self.bio = bio
        self.width = w
        self.height = h

    def draw(self):
        c = self.canv
        cx = self.width / 2
        cy = 10*mm
        r = 40*mm
        diff = self.bio - self.passport

        # Colored arc background
        segments = [
            (150, 180, colors.HexColor("#E8F5E0")),
            (120, 150, colors.HexColor("#F0F8E8")),
            (90,  120, colors.HexColor("#FFF8E0")),
            (60,  90,  colors.HexColor("#FFEBD0")),
            (30,  60,  colors.HexColor("#FCE4E4")),
            (0,   30,  colors.HexColor("#F8D0D0")),
        ]
        for start, end, col in segments:
            for angle in range(start, end):
                rad = math.radians(angle)
                x1 = cx + (r - 5*mm) * math.cos(rad)
                y1 = cy + (r - 5*mm) * math.sin(rad)
                x2 = cx + r * math.cos(rad)
                y2 = cy + r * math.sin(rad)
                c.setStrokeColor(col)
                c.setLineWidth(10)
                c.line(x1, y1, x2, y2)

        # Thin border arc
        for angle in range(0, 181):
            rad = math.radians(angle)
            x1 = cx + (r - 5*mm) * math.cos(rad)
            y1 = cy + (r - 5*mm) * math.sin(rad)
            x2 = cx + r * math.cos(rad)
            y2 = cy + r * math.sin(rad)
            c.setStrokeColor(colors.HexColor("#E0DDD5"))
            c.setLineWidth(0.5)
            c.line(x1, y1, x2, y2)

        # Needle
        max_diff = 12
        norm = max(-1, min(1, diff / max_diff))
        needle_angle = math.radians(90 - norm * 80)
        nl = r - 8*mm
        nx = cx + nl * math.cos(needle_angle)
        ny = cy + nl * math.sin(needle_angle)
        c.setStrokeColor(DARK)
        c.setLineWidth(2)
        c.line(cx, cy, nx, ny)
        c.setFillColor(DARK)
        c.circle(cx, cy, 3*mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.circle(cx, cy, 1.5*mm, fill=1, stroke=0)

        # Bio age big number
        col = RED if diff > 3 else AMBER if diff > 0 else GREEN
        c.setFont("B", 36)
        c.setFillColor(col)
        c.drawCentredString(cx, cy + 14*mm, str(self.bio))
        c.setFont("R", 8)
        c.setFillColor(MUTED)
        c.drawCentredString(cx, cy + 8*mm, "лет — биологический возраст")

        # Passport badge left
        c.setFillColor(colors.HexColor("#F0EDE5"))
        c.roundRect(cx - r - 2*mm, cy - 12*mm, 38*mm, 10*mm, 1.5*mm, fill=1, stroke=0)
        c.setFont("R", 7)
        c.setFillColor(MUTED)
        c.drawCentredString(cx - r + 17*mm, cy - 8.5*mm, "Паспортный")
        c.setFont("B", 9)
        c.setFillColor(DARK)
        c.drawCentredString(cx - r + 17*mm, cy - 14*mm, f"{self.passport} лет")

        # Diff badge right
        sign = "+" if diff >= 0 else ""
        c.setFillColor(col)
        c.roundRect(cx + r - 36*mm, cy - 12*mm, 38*mm, 10*mm, 1.5*mm, fill=1, stroke=0)
        c.setFont("B", 9)
        c.setFillColor(WHITE)
        c.drawCentredString(cx + r - 17*mm, cy - 8.5*mm, f"{sign}{diff} лет от нормы")

        # Scale labels
        c.setFont("R", 7)
        c.setFillColor(GREEN)
        c.drawString(cx - r - 2*mm, cy + 2*mm, "Моложе")
        c.setFillColor(RED)
        c.drawRightString(cx + r + 2*mm, cy + 2*mm, "Старше")


class HBarChart(Flowable):
    """Horizontal bar for zone load"""
    def __init__(self, pct, col, w=80*mm, h=6*mm):
        super().__init__()
        self.pct = pct
        self.col = col
        self.width = w
        self.height = h

    def draw(self):
        c = self.canv
        # Background
        c.setFillColor(LINE)
        c.roundRect(0, 0.5*mm, self.width, 4*mm, 2*mm, fill=1, stroke=0)
        # Fill
        fw = max(4*mm, self.width * self.pct / 100)
        c.setFillColor(self.col)
        c.roundRect(0, 0.5*mm, fw, 4*mm, 2*mm, fill=1, stroke=0)


# ── Styles helper ──
def ps(name, **k):
    return ParagraphStyle(name,
        fontName=k.pop("f", "R"),
        fontSize=k.pop("s", 10),
        textColor=k.pop("c", DARK),
        leading=k.pop("leading", 14),
        **k)


# ── Build PDF ──
def build_pdf(name, age, syms, contact):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=16*mm, bottomMargin=16*mm)

    adj  = sum(SYMPTOMS[s]["adj"] for s in syms if s in SYMPTOMS)
    bio  = max(age, round(age + adj * 0.72))
    diff = bio - age
    today = datetime.date.today().strftime("%d.%m.%Y")
    story = []

    # ══ HEADER ══
    hdr = Table([[
        Paragraph("ARCA", ps("logo", f="B", s=28, c=WHITE)),
        Table([[
            [Paragraph("БИОЛОГИЧЕСКИЙ ПАСПОРТ", ps("ht", f="B", s=8, c=GOLD2, leading=10))],
            [Paragraph(f"{name}  ·  {today}", ps("hs", s=8, c=colors.HexColor("#AAAAAA"), leading=10))],
        ]], colWidths=[100*mm]),
    ]], colWidths=[62*mm, 104*mm])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),BGDARK),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
    ]))
    story += [hdr, Spacer(1,5*mm)]

    # ══ GAUGE ══
    story += [
        Paragraph("БИОЛОГИЧЕСКИЙ ВОЗРАСТ", ps("sec0", f="B", s=8, c=MUTED, spaceAfter=1*mm)),
        GaugeChart(age, bio),
        Spacer(1,3*mm),
    ]

    # Delta box
    if diff > 0:
        msg  = f"Биологический возраст на {diff} {'год' if diff==1 else 'года' if diff<5 else 'лет'} старше паспортного."
        msg2 = "Это поддаётся коррекции — именно с этим работает программа ARCA."
        bc, lc = colors.HexColor("#FDF0F0"), RED
    elif diff < 0:
        msg  = f"Биологический возраст на {abs(diff)} {'год' if abs(diff)==1 else 'года' if abs(diff)<5 else 'лет'} моложе паспортного."
        msg2 = "Хороший результат. Есть зоны, которые стоит поддержать и улучшить."
        bc, lc = colors.HexColor("#F0FDF0"), GREEN
    else:
        msg  = "Биологический возраст совпадает с паспортным."
        msg2 = "По симптомам есть скрытые зоны нагрузки. Анализы крови покажут полную картину."
        bc, lc = PALE2, GOLD

    db = Table([[
        Paragraph(f"{msg}  {msg2}", ps("dm", s=10, c=DARK, leading=15))
    ]], colWidths=[166*mm])
    db.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bc),
        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
        ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),
        ("LINEABOVE",(0,0),(-1,-1),3,lc),
    ]))
    story += [db, Spacer(1,6*mm)]

    # ══ ZONES ══
    story.append(Paragraph("СИСТЕМЫ ПОД НАГРУЗКОЙ", ps("sec1", f="B", s=8, c=MUTED, spaceAfter=2*mm)))

    for sk in syms:
        if sk not in SYMPTOMS: continue
        d = SYMPTOMS[sk]
        pct = min(94, round(50 + d["adj"] * 9))
        col = RED if pct > 78 else AMBER if pct > 62 else GREEN
        status = "Высокая нагрузка" if pct > 78 else "Умеренная нагрузка" if pct > 62 else "Под контролем"

        zone = Table([[
            # Zone name + markers
            Table([[
                [Paragraph(d["zone"], ps("zn", f="B", s=10, c=DARK, spaceAfter=2))],
                [Paragraph(d["markers"], ps("zm", s=8, c=MUTED, leading=10))],
            ]], colWidths=[84*mm]),
            # Bar + pct + status
            Table([[
                [Table([[
                    [HBarChart(pct, col, w=60*mm)],
                ]], colWidths=[60*mm])],
                [Table([[
                    [Paragraph(f"{pct}%", ps("zpct", f="B", s=9, c=col))],
                    [Paragraph(status, ps("zst", s=8, c=col, alignment=TA_RIGHT))],
                ]], colWidths=[28*mm, 52*mm])],
            ]], colWidths=[82*mm]),
        ]], colWidths=[86*mm, 84*mm])
        zone.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),CREAM),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
            ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
            ("LINEBELOW",(0,0),(-1,-1),0.5,LINE),
        ]))
        story.append(zone)

    story.append(Spacer(1,6*mm))

    # ══ RECOMMENDATIONS ══
    story.append(Paragraph("ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ", ps("sec2", f="B", s=8, c=MUTED, spaceAfter=2*mm)))

    top = sorted([k for k in syms if k in SYMPTOMS], key=lambda k: SYMPTOMS[k]["adj"], reverse=True)[:4]
    for i, sk in enumerate(top, 1):
        d = SYMPTOMS[sk]
        pct = min(94, round(50 + d["adj"] * 9))
        col = RED if pct > 78 else AMBER if pct > 62 else GREEN

        rec = Table([[
            # Number
            Paragraph(str(i), ps("num", f="B", s=16, c=WHITE, alignment=TA_CENTER)),
            # Content
            Table([[
                [Paragraph(d["zone"], ps("rh", f="B", s=10, c=DARK, spaceAfter=3))],
                [Paragraph(d["rec"], ps("rb", s=9, c=MUTED, leading=13, spaceAfter=4))],
                [Paragraph(f"Рекомендуется: {d['action']}", ps("ra", f="I", s=8, c=col, leading=11))],
            ]], colWidths=[146*mm]),
        ]], colWidths=[16*mm, 150*mm])
        rec.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(0,-1),col),
            ("BACKGROUND",(1,0),(1,-1),WHITE),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("VALIGN",(1,0),(1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(0,-1),0),
            ("LEFTPADDING",(1,0),(1,-1),10),
            ("RIGHTPADDING",(0,0),(-1,-1),10),
            ("LINEBELOW",(0,0),(-1,-1),0.5,LINE),
        ]))
        story.append(KeepTogether([rec]))

    story.append(Spacer(1,6*mm))

    # ══ CTA ══
    cta = Table([[
        Table([[
            [Paragraph("СЛЕДУЮЩИЙ ШАГ", ps("c1", f="B", s=7, c=GOLD2, leading=9, spaceAfter=3))],
            [Paragraph("Точная диагностика по анализам крови и ДНК", ps("c2", f="B", s=12, c=WHITE, leading=15, spaceAfter=4))],
            [Paragraph("50+ биомаркеров  ·  ДНК-тест 55 генов  ·  точность ±1–2 года  ·  выезд на дом", ps("c3", s=8, c=colors.HexColor("#999999"), leading=11))],
        ]], colWidths=[110*mm]),
        Table([[
            [Paragraph("мест в июне", ps("s1", s=7, c=colors.HexColor("#999999"), alignment=TA_CENTER, leading=9))],
            [Paragraph("4", ps("s2", f="B", s=32, c=GOLD, alignment=TA_CENTER, leading=34))],
            [Spacer(1,2*mm)],
            [Paragraph("@ARCA_Manager", ps("s3", f="B", s=8, c=WHITE, alignment=TA_CENTER))],
        ]], colWidths=[48*mm]),
    ]], colWidths=[116*mm, 50*mm])
    cta.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),BGDARK),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12),
        ("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),14),
        ("LINEABOVE",(0,0),(-1,-1),2.5,GOLD),
        ("LINEAFTER",(0,0),(0,-1),0.5,colors.HexColor("#444444")),
        ("LEFTPADDING",(1,0),(1,-1),14),
    ]))
    story += [cta, Spacer(1,4*mm)]

    story.append(Paragraph(
        "* Отчёт носит информационный характер и не является медицинским заключением. "
        "Расчёт биологического возраста основан на адаптированной методике Levine PhenoAge "
        "с поправочными коэффициентами образа жизни и симптоматическим анализом. "
        "Для постановки диагноза необходима консультация врача.",
        ps("disc", s=6.5, c=colors.HexColor("#AAAAAA"), leading=9)))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── Parsing ──
def parse_msg(text):
    data = {}
    for line in text.strip().split("\n"):
        if "Имя:" in line:
            data["name"] = line.split("Имя:")[-1].strip().split(",")[0].strip()
        m = re.search(r"возраст[:\s]+(\d+)", line, re.I)
        if m:
            data["age"] = int(m.group(1))
        if any(k in line for k in ["Контакт:", "Телефон:"]):
            data["contact"] = line.split(":", 1)[-1].strip()
        if any(k in line for k in ["Симптомы:", "Зоны"]):
            raw = line.split(":", 1)[-1].strip()
            found = [k for k,v in LABELS.items() if v.lower() in raw.lower()]
            found += [k for k,v in SYMPTOMS.items() if v["zone"].lower() in raw.lower() and k not in found]
            if found:
                data["symptoms"] = found
    return data


# ── Handlers ──
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот ARCA готов. Жду заявки с сайта.")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return
    if not any(k in text for k in ["Заявка","ARCA","Имя:","Симптомы:","Контакт:","Телефон:"]):
        await update.message.reply_text("Сообщение не похоже на заявку с сайта.")
        return
    d       = parse_msg(text)
    name    = d.get("name", "Клиент")
    age     = d.get("age", 38)
    syms    = d.get("symptoms") or ["energy","sleep","focus"]
    contact = d.get("contact", "не указан")
    await update.message.reply_text(f"Заявка от {name}, {age} лет — генерирую карту...")
    try:
        pdf = build_pdf(name, age, syms, contact)
        await update.message.reply_document(
            document=io.BytesIO(pdf),
            filename=f"ARCA_{name.replace(' ','_')}.pdf",
            caption=f"Карта биологического старения — {name}\nКонтакт: {contact}"
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        await update.message.reply_text(f"Ошибка генерации: {e}")

def main():
    if not TOKEN: raise ValueError("BOT_TOKEN не задан")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    logger.info("Бот запущен")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

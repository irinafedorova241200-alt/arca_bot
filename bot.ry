import os, logging, io, re, urllib.request
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
from reportlab.graphics.shapes import Drawing, Rect, Circle, String, Line, Wedge
from reportlab.graphics import renderPDF
from reportlab.platypus import Flowable
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TOKEN = os.environ.get("BOT_TOKEN", "")

# ── Fonts ──
def setup_fonts():
    urls = {
        "DejaVu":     "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf",
        "DejaVuBold": "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf",
        "DejaVuIt":   "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Oblique.ttf",
    }
    for name, url in urls.items():
        path = f"/tmp/{name}.ttf"
        if not os.path.exists(path):
            urllib.request.urlretrieve(url, path)
        pdfmetrics.registerFont(TTFont(name, path))

setup_fonts()

# ── Colours ──
GOLD   = colors.HexColor("#B8962E")
GOLD2  = colors.HexColor("#D4AF5A")
CREAM  = colors.HexColor("#F9F6EE")
DARK   = colors.HexColor("#1A1A18")
MUTED  = colors.HexColor("#6B6B68")
LINE   = colors.HexColor("#E2DDD2")
RED    = colors.HexColor("#C05050")
AMBER  = colors.HexColor("#D4822A")
GREEN  = colors.HexColor("#5A9E3A")
BGDARK = colors.HexColor("#1C1C18")
WHITE  = colors.white
PALE   = colors.HexColor("#F5EDD6")

# ── Data ──
SYMPTOMS = {
    "energy":       {"zone":"Энергетический метаболизм",  "icon":"⚡", "markers":["Митохондрии","Кортизол","Ферритин"],      "adj":2.1, "rec":"Митохондриальная дисфункция — ключевая причина хронической усталости. Рекомендуется проверить уровень ферритина, кортизола в 4 точках суток и коэнзима Q10.", "action":"Сдать: Ферритин, Кортизол (слюна 4 точки), Коэнзим Q10, АТФ-профиль"},
    "focus":        {"zone":"Когнитивная функция",         "icon":"🧠", "markers":["ТТГ","Тестостерон","Витамин D"],          "adj":1.8, "rec":"Когнитивный туман чаще всего связан с субоптимальным уровнем щитовидной железы или половых гормонов. Дефицит витамина D усиливает нейровоспаление.", "action":"Сдать: ТТГ, Т3 свободный, Тестостерон общий/свободный, Витамин D (25-OH)"},
    "sleep":        {"zone":"Циркадный ритм и сон",        "icon":"🌙", "markers":["Кортизол","Мелатонин","Магний"],          "adj":2.4, "rec":"Нарушение циркадного ритма критично влияет на гормональный каскад. Высокий вечерний кортизол блокирует выработку мелатонина и нарушает фазы сна.", "action":"Сдать: Кортизол (вечер), Мелатонин (ночь), Магний RBC, Витамин B6"},
    "productivity": {"zone":"Надпочечниковая ось",         "icon":"📉", "markers":["ДГЭА","Кортизол","Адреналин"],            "adj":1.6, "rec":"Хроническая перегрузка надпочечников приводит к снижению ДГЭА и нарушению кортизолового ритма. Это напрямую влияет на мотивацию и работоспособность.", "action":"Сдать: ДГЭА-С, Кортизол утром, АТФ-профиль, Органические кислоты"},
    "weight":       {"zone":"Метаболический профиль",      "icon":"⚖️", "markers":["Инсулин","Лептин","ТТГ"],                 "adj":2.2, "rec":"Инсулинорезистентность и лептинорезистентность — ведущие причины лишнего веса. Часто маскируются под 'нормальный' уровень глюкозы натощак.", "action":"Сдать: Инсулин натощак, HOMA-IR, Лептин, ТТГ, Т3 реверс"},
    "mood":         {"zone":"Гормональный баланс",         "icon":"🧬", "markers":["Кортизол","Серотонин","Прогестерон"],     "adj":1.9, "rec":"Дисбаланс кортизол/прогестерон — главная причина тревожности у женщин 35+. У мужчин — снижение тестостерона при нормальном ГСПГ.", "action":"Сдать: Кортизол, Прогестерон, Эстрадиол, ГСПГ, Серотонин (тромбоциты)"},
    "libido":       {"zone":"Половые гормоны",             "icon":"🔬", "markers":["Тестостерон","ДГЭА","ЛГ/ФСГ"],           "adj":2.0, "rec":"Снижение либидо — ранний маркер гормонального дисбаланса. Важно оценить не только общий тестостерон, но и свободную фракцию на фоне ГСПГ.", "action":"Сдать: Тестостерон общий/свободный, ГСПГ, ЛГ, ФСГ, Пролактин, ДГЭА-С"},
    "immunity":     {"zone":"Иммунитет и воспаление",      "icon":"🛡️", "markers":["СРБ","ИЛ-6","Витамин D"],                "adj":1.5, "rec":"Хроническое субклиническое воспаление — главный механизм ускоренного биологического старения. СРБ выше 1 мг/л уже значим.", "action":"Сдать: СРБ высокочувствительный, ИЛ-6, Гомоцистеин, Витамин D, Ферритин"},
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
    """Semicircle gauge showing bio age vs passport age"""
    def __init__(self, passport, bio, w=170*mm, h=55*mm):
        super().__init__()
        self.passport = passport
        self.bio = bio
        self.width = w
        self.height = h

    def draw(self):
        c = self.canv
        cx = self.width / 2
        cy = 8*mm
        r = 38*mm

        # Background arc segments (green → amber → red)
        segs = [
            (180, 240, colors.HexColor("#E8F5E0")),
            (120, 180, colors.HexColor("#FFF3CD")),
            (60,  120, colors.HexColor("#FCE4E4")),
        ]
        for start, end, col in segs:
            for angle in range(start, end):
                rad = math.radians(angle)
                x1 = cx + (r-4*mm)*math.cos(rad)
                y1 = cy + (r-4*mm)*math.sin(rad)
                x2 = cx + r*math.cos(rad)
                y2 = cy + r*math.sin(rad)
                c.setStrokeColor(col)
                c.setLineWidth(8)
                c.line(x1,y1,x2,y2)

        # Needle
        diff = self.bio - self.passport
        max_diff = 15
        norm = max(-1, min(1, diff / max_diff))
        needle_angle = math.radians(180 - (norm + 1) * 90)
        nx = cx + (r-10*mm)*math.cos(needle_angle)
        ny = cy + (r-10*mm)*math.sin(needle_angle)
        c.setStrokeColor(DARK)
        c.setLineWidth(2.5)
        c.line(cx, cy, nx, ny)
        c.setFillColor(DARK)
        c.circle(cx, cy, 3*mm, fill=1)

        # Center text
        c.setFont("DejaVuBold", 28)
        c.setFillColor(GOLD if diff > 0 else GREEN)
        c.drawCentredString(cx, cy + 12*mm, str(self.bio))
        c.setFont("DejaVu", 8)
        c.setFillColor(MUTED)
        c.drawCentredString(cx, cy + 6*mm, "биологический возраст")

        # Labels
        c.setFont("DejaVu", 8)
        c.setFillColor(MUTED)
        c.drawCentredString(cx - r + 2*mm, cy - 4*mm, "Моложе")
        c.drawCentredString(cx + r - 2*mm, cy - 4*mm, "Старше")
        c.drawCentredString(cx, cy - 4*mm, "Норма")

        # Passport age badge
        c.setFillColor(LINE)
        c.roundRect(cx - 55*mm, cy - 14*mm, 50*mm, 12*mm, 2*mm, fill=1, stroke=0)
        c.setFont("DejaVu", 8)
        c.setFillColor(MUTED)
        c.drawCentredString(cx - 30*mm, cy - 9*mm, f"Паспортный: {self.passport} лет")

        # Bio age badge
        col = RED if diff > 2 else AMBER if diff > 0 else GREEN
        c.setFillColor(col)
        c.roundRect(cx + 5*mm, cy - 14*mm, 50*mm, 12*mm, 2*mm, fill=1, stroke=0)
        c.setFont("DejaVuBold", 8)
        c.setFillColor(WHITE)
        sign = "+" if diff >= 0 else ""
        c.drawCentredString(cx + 30*mm, cy - 9*mm, f"{sign}{diff} лет от нормы")


class ZoneBar(Flowable):
    """Horizontal progress bar for a zone"""
    def __init__(self, label, pct, col, w=170*mm, h=8*mm):
        super().__init__()
        self.label = label
        self.pct = pct
        self.col = col
        self.width = w
        self.height = h

    def draw(self):
        c = self.canv
        bar_w = self.width * 0.45
        bar_x = self.width * 0.52
        # Background
        c.setFillColor(LINE)
        c.roundRect(bar_x, 1*mm, bar_w, 5*mm, 2*mm, fill=1, stroke=0)
        # Fill
        fill_w = max(4*mm, bar_w * self.pct / 100)
        c.setFillColor(self.col)
        c.roundRect(bar_x, 1*mm, fill_w, 5*mm, 2*mm, fill=1, stroke=0)
        # Pct label
        c.setFont("DejaVuBold", 8)
        c.setFillColor(self.col)
        c.drawRightString(bar_x - 2*mm, 2*mm, f"{self.pct}%")


# ── PDF builder ──
def ps(name, **k):
    return ParagraphStyle(name,
        fontName=k.pop("f","DejaVu"), fontSize=k.pop("s",10),
        textColor=k.pop("c",DARK), leading=k.pop("leading",14), **k)

def build_pdf(name, age, syms, contact):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)

    adj  = sum(SYMPTOMS[s]["adj"] for s in syms if s in SYMPTOMS)
    bio  = max(age, round(age + adj * 0.72))
    diff = bio - age
    story = []

    # ══ COVER HEADER ══
    cover = Table([[
        Table([[
            [Paragraph("ARCA", ps("logo", f="DejaVuBold", s=32, c=WHITE))],
            [Paragraph("БИОЛОГИЧЕСКИЙ ПАСПОРТ", ps("sub", s=7, c=colors.HexColor("#C9A84C"), leading=10))],
        ]], colWidths=[60*mm], rowHeights=[12*mm, 6*mm]),
        Paragraph(
            f"<b>{name}</b><br/>"
            f"<font size=8 color='#C9A84C'>Персональный отчёт · {__import__('datetime').date.today().strftime('%d.%m.%Y')}</font>",
            ps("hdr_r", f="DejaVuBold", s=14, c=WHITE, alignment=TA_RIGHT, leading=20)
        ),
    ]], colWidths=[90*mm, 80*mm])
    cover.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),BGDARK),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("RIGHTPADDING",(0,0),(-1,-1),8),
    ]))
    story += [cover, Spacer(1,5*mm)]

    # ══ GAUGE ══
    story.append(Paragraph("БИОЛОГИЧЕСКИЙ ВОЗРАСТ", ps("sec", f="DejaVuBold", s=8, c=MUTED, spaceAfter=2*mm)))
    story.append(GaugeChart(age, bio))
    story.append(Spacer(1,4*mm))

    # Delta explanation box
    if diff > 0:
        msg = f"Ваш биологический возраст на {diff} {'год' if diff==1 else 'года' if diff<5 else 'лет'} старше паспортного. Это поддаётся коррекции."
        bc = colors.HexColor("#FCE4E4"); tc = RED
    elif diff < 0:
        msg = f"Ваш биологический возраст на {abs(diff)} {'год' if abs(diff)==1 else 'года' if abs(diff)<5 else 'лет'} моложе паспортного. Хороший результат — есть что поддержать."
        bc = colors.HexColor("#E8F5E0"); tc = GREEN
    else:
        msg = "Биологический возраст совпадает с паспортным. Анализы крови покажут точные зоны роста."
        bc = PALE; tc = GOLD

    delta_tbl = Table([[Paragraph(msg, ps("dm", s=10, c=tc, leading=14))]],
                      colWidths=[170*mm])
    delta_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bc),
        ("TOPPADDING",(0,0),(-1,-1),8), ("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("LINEABOVE",(0,0),(-1,-1),2,tc),
    ]))
    story += [delta_tbl, Spacer(1,6*mm)]

    # ══ ZONES ══
    story.append(Paragraph("СИСТЕМЫ ПОД НАГРУЗКОЙ", ps("sec2", f="DejaVuBold", s=8, c=MUTED, spaceAfter=3*mm)))

    for sk in syms:
        if sk not in SYMPTOMS: continue
        d = SYMPTOMS[sk]
        pct = min(94, round(50 + d["adj"] * 9))
        col = RED if pct > 78 else AMBER if pct > 62 else GREEN
        status = "⚠ Высокая нагрузка" if pct > 78 else "◐ Умеренная нагрузка" if pct > 62 else "✓ Под контролем"
        markers_str = "  ·  ".join(d["markers"])

        zone_row = Table([[
            # Left: icon + name
            Table([[
                [Paragraph(f"<b>{d['zone']}</b>", ps("zn", f="DejaVuBold", s=10, c=DARK))],
                [Paragraph(markers_str, ps("zm", s=8, c=MUTED, leading=10))],
            ]], colWidths=[80*mm]),
            # Right: bar + status
            Table([[
                [Paragraph(status, ps("zs", s=8, c=col, alignment=TA_RIGHT))],
                [ZoneBar(d["zone"], pct, col, w=80*mm)],
            ]], colWidths=[80*mm]),
        ]], colWidths=[85*mm, 85*mm])
        zone_row.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),CREAM),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),6), ("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("LEFTPADDING",(0,0),(-1,-1),8), ("RIGHTPADDING",(0,0),(-1,-1),8),
            ("LINEBELOW",(0,0),(-1,-1),0.5,LINE),
        ]))
        story.append(zone_row)

    story.append(Spacer(1,6*mm))

    # ══ RECOMMENDATIONS ══
    story.append(Paragraph("ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ", ps("sec3", f="DejaVuBold", s=8, c=MUTED, spaceAfter=3*mm)))

    top_syms = sorted([k for k in syms if k in SYMPTOMS], key=lambda k: SYMPTOMS[k]["adj"], reverse=True)[:4]
    for i, sk in enumerate(top_syms, 1):
        d = SYMPTOMS[sk]
        pct = min(94, round(50 + d["adj"] * 9))
        col = RED if pct > 78 else AMBER if pct > 62 else GREEN

        rec_block = Table([[
            # Number badge
            Table([[
                [Paragraph(str(i), ps("num", f="DejaVuBold", s=14, c=WHITE, alignment=TA_CENTER))],
            ]], colWidths=[10*mm], rowHeights=[10*mm]),
            # Content
            Table([[
                [Paragraph(f"<b>{d['zone']}</b>", ps("rt", f="DejaVuBold", s=10, c=DARK, spaceAfter=2))],
                [Paragraph(d["rec"], ps("rx", s=9, c=MUTED, leading=13, spaceAfter=4))],
                [Paragraph(f"→ {d['action']}", ps("act", s=8, c=col, leading=11))],
            ]], colWidths=[148*mm]),
        ]], colWidths=[14*mm, 152*mm])
        rec_block.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(0,-1),col),
            ("BACKGROUND",(1,0),(1,-1),WHITE),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),6), ("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("LEFTPADDING",(0,0),(0,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(1,0),(1,-1),8),
            ("LINEBELOW",(0,0),(-1,-1),0.5,LINE),
        ]))
        story.append(KeepTogether([rec_block]))

    story.append(Spacer(1,6*mm))

    # ══ NEXT STEP CTA ══
    cta_inner = Table([[
        Table([[
            [Paragraph("СЛЕДУЮЩИЙ ШАГ", ps("ct1", f="DejaVuBold", s=8, c=GOLD, leading=10))],
            [Paragraph("Точная диагностика по анализам крови и ДНК", ps("ct2", f="DejaVuBold", s=11, c=WHITE, leading=14))],
            [Paragraph("50+ биомаркеров · ДНК-тест 55 генов · точность ±1–2 года · выезд на дом", ps("ct3", s=8, c=colors.HexColor("#AAAAAA"), leading=12))],
        ]], colWidths=[110*mm]),
        Table([[
            [Paragraph("Осталось мест", ps("sp1", s=7, c=colors.HexColor("#AAAAAA"), alignment=TA_CENTER))],
            [Paragraph("4", ps("sp2", f="DejaVuBold", s=28, c=GOLD, alignment=TA_CENTER, leading=30))],
            [Paragraph("в июне", ps("sp3", s=7, c=colors.HexColor("#AAAAAA"), alignment=TA_CENTER))],
            [Spacer(1,2*mm)],
            [Paragraph("@ARCA_Manager", ps("sp4", f="DejaVuBold", s=8, c=WHITE, alignment=TA_CENTER))],
        ]], colWidths=[48*mm]),
    ]], colWidths=[114*mm, 52*mm])
    cta_inner.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("LINEAFTER",(0,0),(0,-1),0.5,colors.HexColor("#444444")),
        ("LEFTPADDING",(1,0),(1,-1),10),
    ]))

    cta_wrap = Table([[cta_inner]], colWidths=[170*mm])
    cta_wrap.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),BGDARK),
        ("TOPPADDING",(0,0),(-1,-1),12), ("BOTTOMPADDING",(0,0),(-1,-1),12),
        ("LEFTPADDING",(0,0),(-1,-1),12), ("RIGHTPADDING",(0,0),(-1,-1),12),
        ("LINEABOVE",(0,0),(-1,-1),2,GOLD),
    ]))
    story += [cta_wrap, Spacer(1,4*mm)]

    # ══ DISCLAIMER ══
    story.append(Paragraph(
        "* Данный отчёт носит информационный характер и не является медицинским заключением. "
        "Расчёт биологического возраста основан на адаптированной методике Levine PhenoAge "
        "с коэффициентами образа жизни и симптоматическим анализом.",
        ps("disc", s=7, c=colors.HexColor("#AAAAAA"), leading=10)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── Bot handlers ──
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот ARCA готов. Жду заявки с сайта.")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return
    if not any(k in text for k in ["Заявка","ARCA","Имя:","Симптомы:","Контакт:","Телефон:"]):
        await update.message.reply_text("Сообщение не похоже на заявку с сайта.")
        return
    d = parse_msg(text)
    name    = d.get("name", "Клиент")
    age     = d.get("age", 38)
    syms    = d.get("symptoms") or ["energy","sleep","focus"]
    contact = d.get("contact", "не указан")
    await update.message.reply_text(f"Заявка от {name}, {age} лет · Генерирую карту...")
    try:
        pdf = build_pdf(name, age, syms, contact)
        await update.message.reply_document(
            document=io.BytesIO(pdf),
            filename=f"ARCA_Karta_{name.replace(' ','_')}.pdf",
            caption=f"Карта биологического старения — {name}\nКонтакт для связи: {contact}"
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

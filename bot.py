import os
import logging
import io
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TOKEN = os.environ.get("BOT_TOKEN", "")

SYMPTOMS = {
    "energy":       {"zone":"Энергетический метаболизм",      "markers":"Митохондрии · Кортизол · Ферритин",    "adj":2.1,"rec":"Митохондриальная функция, ферритин и кортизол — стартовая точка. Объясняют усталость в 80% случаев."},
    "focus":        {"zone":"Когнитивная функция",             "markers":"ТТГ · Тестостерон · Витамин D",        "adj":1.8,"rec":"ТТГ, тестостерон, витамин D — три маркера большинства когнитивных проблем после 35."},
    "sleep":        {"zone":"Циркадный ритм",                  "markers":"Кортизол · Мелатонин · Магний",        "adj":2.4,"rec":"Нарушение циркадного ритма видно в крови. Первое что корректирует ARCA."},
    "productivity": {"zone":"Надпочечниковая ось",             "markers":"ДГЭА · Кортизол · Адреналин",          "adj":1.6,"rec":"ДГЭА-сульфат и суточный кортизол — ключ к выгоранию и снижению работоспособности."},
    "weight":       {"zone":"Метаболический профиль",          "markers":"Инсулин · Лептин · ТТГ",               "adj":2.2,"rec":"Инсулинорезистентность и щитовидная — главные причины, почему вес не уходит."},
    "mood":         {"zone":"Гормональный баланс",             "markers":"Кортизол · Серотонин · Прогестерон",   "adj":1.9,"rec":"Раздражительность и тревога — чаще гормональный дисбаланс, а не характер."},
    "libido":       {"zone":"Половые гормоны",                 "markers":"Тестостерон · ДГЭА · ЛГ/ФСГ",         "adj":2.0,"rec":"Снижение либидо — часто первый сигнал системного гормонального сбоя."},
    "immunity":     {"zone":"Иммунитет и воспаление",          "markers":"СРБ · ИЛ-6 · Витамин D",              "adj":1.5,"rec":"СРБ и ИЛ-6 показывают хроническое воспаление — механизм ускоренного старения."},
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

GOLD=colors.HexColor("#B8962E"); PALE=colors.HexColor("#F5EDD6"); DARK=colors.HexColor("#141414")
MUTED=colors.HexColor("#888880"); RED=colors.HexColor("#C05050"); GREEN=colors.HexColor("#6A9E3A")
LINE=colors.HexColor("#E8E3D5")

def ps(name,**k):
    return ParagraphStyle(name,fontName=k.pop("f","Helvetica"),fontSize=k.pop("s",10),textColor=k.pop("c",DARK),**k)

def build_pdf(name,age,syms,contact):
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=18*mm,bottomMargin=18*mm)
    adj=sum(SYMPTOMS[s]["adj"] for s in syms if s in SYMPTOMS)
    bio=max(age,round(age+adj*0.72)); diff=bio-age
    story=[]
    # Header
    h=Table([[Paragraph("<b>ARCA</b>",ps("l",f="Helvetica-Bold",s=22,c=GOLD)),
              Paragraph("Карта биологического старения",ps("r",s=9,c=MUTED,alignment=TA_RIGHT))]],
            colWidths=[90*mm,80*mm])
    h.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LINEBELOW",(0,0),(-1,-1),0.5,LINE),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
    story+=[h,Spacer(1,6*mm)]
    story+=[Paragraph("ПЕРСОНАЛЬНЫЙ ОТЧЁТ",ps("k",s=8,c=MUTED,spaceAfter=4)),
            Paragraph(name,ps("n",f="Helvetica-Bold",s=18,spaceAfter=2)),
            Paragraph(f"Паспортный возраст: {age} лет",ps("a",s=10,c=MUTED,spaceAfter=6)),
            HRFlowable(width="100%",thickness=0.5,color=LINE,spaceAfter=6*mm)]
    # Ages
    at=Table([[Paragraph(f"<font size=11 color='#888880'>Паспортный</font><br/><font size=44 color='#CCCCCC'><b>{age}</b></font>",ps("pa",alignment=TA_CENTER)),
               Paragraph("<font size=18 color='#DDDDDD'>vs</font>",ps("vs",alignment=TA_CENTER)),
               Paragraph(f"<font size=11 color='#888880'>Биологический</font><br/><font size=44 color='#B8962E'><b>{bio}</b></font>",ps("ba",alignment=TA_CENTER))]],
             colWidths=[60*mm,20*mm,60*mm])
    at.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F9F6EE")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                             ("ALIGN",(0,0),(-1,-1),"CENTER"),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),("BOX",(0,0),(-1,-1),0.5,LINE)]))
    story+=[at,Spacer(1,3*mm)]
    if diff>0: dt=f"Биовозраст старше на {diff} {'год' if diff==1 else 'года' if diff<5 else 'лет'}"; dc=RED; dn="По симптомам видна нагрузка. Точный биовозраст — по анализам крови (±1–2 года)."
    elif diff<0: dt=f"Биовозраст моложе на {abs(diff)} {'год' if abs(diff)==1 else 'года' if abs(diff)<5 else 'лет'}"; dc=GREEN; dn="Хороший сигнал. Анализы крови покажут зоны для улучшения."
    else: dt="Биовозраст совпадает с паспортным"; dc=GOLD; dn="По симптомам есть скрытые зоны нагрузки."
    story+=[Paragraph(dt,ps("dt",f="Helvetica-Bold",s=10,c=dc,alignment=TA_CENTER,spaceAfter=3)),
            Paragraph(dn,ps("dn",s=9,c=MUTED,alignment=TA_CENTER,spaceAfter=6*mm)),
            Paragraph("СИСТЕМЫ ПОД НАГРУЗКОЙ",ps("sh",f="Helvetica-Bold",s=8,c=MUTED,spaceAfter=4*mm))]
    for sk in syms:
        if sk not in SYMPTOMS: continue
        d=SYMPTOMS[sk]; p=min(94,round(50+d["adj"]*9))
        col=RED if p>78 else GOLD if p>62 else GREEN; st="Высокая нагрузка" if p>78 else "Умеренная нагрузка" if p>62 else "Под контролем"
        zt=Table([[Paragraph(f"<b>{d['zone']}</b>",ps("zn",f="Helvetica-Bold",s=10)),
                   Paragraph(f"<font color='#{col.hexval()[2:]}'><b>{p}%</b></font>",ps("zp",s=10,alignment=TA_RIGHT))],
                  [Paragraph(f"<font size=8 color='#888880'>{d['markers']}</font>",ps("zm",s=8,c=MUTED)),
                   Paragraph(f"<font size=8 color='#{col.hexval()[2:]}'>{st}</font>",ps("zs",s=8,alignment=TA_RIGHT))]],
                 colWidths=[120*mm,30*mm])
        zt.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
        story+=[zt,HRFlowable(width=f"{p}%",thickness=3,color=col,spaceAfter=3*mm)]
    story+=[Spacer(1,2*mm),HRFlowable(width="100%",thickness=0.5,color=LINE,spaceAfter=4*mm),
            Paragraph("ЧТО ПРОВЕРИТЬ В ПЕРВУЮ ОЧЕРЕДЬ",ps("sh2",f="Helvetica-Bold",s=8,c=MUTED,spaceAfter=4*mm))]
    for i,sk in enumerate(sorted([k for k in syms if k in SYMPTOMS],key=lambda k:SYMPTOMS[k]["adj"],reverse=True)[:4],1):
        d=SYMPTOMS[sk]
        story+=[Paragraph(f"<b>{i}. {d['zone']}</b>",ps("rt",f="Helvetica-Bold",s=10,spaceAfter=2)),
                Paragraph(d["rec"],ps("rx",s=9,c=MUTED,spaceAfter=5,leftIndent=10))]
    ct=Table([[Paragraph("<b>Следующий шаг — диагностика по анализам крови</b><br/><font size=9 color='#888880'>50+ биомаркеров · ДНК-тест · точность ±1–2 года</font>",ps("cl",s=10)),
               Paragraph(f"<font color='#B8962E'><b>@ARCA_Manager</b></font><br/><font size=8 color='#888880'>Осталось 4 места в июне</font>",ps("cr",s=10,alignment=TA_RIGHT))]],
             colWidths=[100*mm,50*mm])
    ct.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                             ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
                             ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10)]))
    story+=[Spacer(1,4*mm),HRFlowable(width="100%",thickness=0.5,color=LINE,spaceAfter=4*mm),ct,Spacer(1,3*mm),
            Paragraph("* Расчёт носит информационный характер. Основан на методике Levine PhenoAge.",
                       ps("disc",s=7,c=colors.HexColor("#BBBBBB"),alignment=TA_CENTER))]
    doc.build(story); buf.seek(0); return buf.read()

def parse_msg(text):
    data={}
    for line in text.strip().split("\n"):
        if "Имя:" in line: data["name"]=line.split("Имя:")[-1].strip().split(",")[0].strip()
        m=re.search(r"возраст[:\s]+(\d+)",line,re.I)
        if m: data["age"]=int(m.group(1))
        if any(k in line for k in ["Контакт:","Телефон:"]): data["contact"]=line.split(":",1)[-1].strip()
        if any(k in line for k in ["Симптомы:","Зоны"]): 
            raw=line.split(":",1)[-1].strip()
            found=[k for k,v in LABELS.items() if v.lower() in raw.lower()]
            found+=[k for k,v in SYMPTOMS.items() if v["zone"].lower() in raw.lower() and k not in found]
            if found: data["symptoms"]=found
    return data

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Бот ARCA готов. Жду заявки с сайта.")

async def handle(update:Update,context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text
    if not text: return
    if not any(k in text for k in ["Заявка","ARCA","Имя:","Симптомы:","Контакт:","Телефон:"]):
        await update.message.reply_text("Сообщение не похоже на заявку с сайта."); return
    d=parse_msg(text)
    name=d.get("name","Клиент"); age=d.get("age",38)
    syms=d.get("symptoms") or ["energy","sleep","focus"]; contact=d.get("contact","не указан")
    await update.message.reply_text(f"✅ Заявка от {name}, {age} лет\nКонтакт: {contact}\n⏳ Генерирую PDF...")
    try:
        pdf=build_pdf(name,age,syms,contact)
        await update.message.reply_document(document=io.BytesIO(pdf),filename=f"ARCA_{name.replace(' ','_')}.pdf",
            caption=f"📊 Карта старения — {name}, {age} лет\nКонтакт: {contact}")
    except Exception as e:
        logger.error(e,exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {e}")

def main():
    if not TOKEN: raise ValueError("BOT_TOKEN не задан")
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(MessageHandler(filters.TEXT&~filters.COMMAND,handle))
    logger.info("✅ Бот запущен")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__": main()

import asyncio
import json
import os
import threading
from datetime import datetime, time as dtime
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Health server для Render Web Service (free план требует порт)
def start_health_server():
    port = int(os.getenv("PORT", "10000"))
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"jadval-bot alive")
        def log_message(self, format, *args):
            return
    try:
        srv = HTTPServer(("0.0.0.0", port), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print(f"Health server on {port}")
    except Exception as e:
        print(f"health server failed: {e}")

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()  # возьми у @BotFather
TZ = ZoneInfo("Asia/Tashkent")
CHAT_FILE = "chats.json"

# Точное расписание из твоего фото (1-в-1)
RAW = {
 1: {"Du":"", "Se":"Tarbiya", "Ch":"Tarix", "Pa":"Ingliz tili ×g", "Ju":"Texnologiya ×g", "Sh":"Ingliz tili ×g"},
 2: {"Du":"Geometriya", "Se":"Biologiya", "Ch":"Algebra", "Pa":"Ona tili", "Ju":"Tarix", "Sh":"Adabi"},
 3: {"Du":"Geografiya", "Se":"Tarix", "Ch":"Fizika", "Pa":"Chizmachilik", "Ju":"Huquq", "Sh":"Ona tili"},
 4: {"Du":"Jismoniy t. ×g", "Se":"Kimyo", "Ch":"Geometriya", "Pa":"Geografiya", "Ju":"Algebra", "Sh":"Rus tili ×g"},
 5: {"Du":"Biologiya", "Se":"Jismoniy t. ×g", "Ch":"Rus tili ×g", "Pa":"Adabiyot", "Ju":"Fizika", "Sh":"Algebra"},
 6: {"Du":"Ingliz tili ×g", "Se":"", "Ch":"Ona tili", "Pa":"Kimyo", "Ju":"Informatika ×g", "Sh":"Informatika ×g"},
}

TIMES = {
 1: (dtime(8,0), dtime(8,45)),
 2: (dtime(8,50), dtime(9,35)),
 3: (dtime(9,40), dtime(10,25)),
 4: (dtime(10,40), dtime(11,25)),
 5: (dtime(11,30), dtime(12,15)),
 6: (dtime(12,20), dtime(13,5)),
}

DAY_MAP = ["Ya","Du","Se","Ch","Pa","Ju","Sh"]  # 0=Вс
DAY_FULL = {"Du":"Dushanba","Se":"Seshanba","Ch":"Chorshanba","Pa":"Payshanba","Ju":"Juma","Sh":"Shanba","Ya":"Yakshanba"}

def today_key():
    return DAY_MAP[datetime.now(TZ).weekday()+1 if datetime.now(TZ).weekday()<6 else 0] if False else DAY_MAP[datetime.now(TZ).isoweekday() % 7]
    # isoweekday: Mon=1 ... Sun=7

def get_today_key():
    # datetime.weekday(): Mon=0 ... Sun=6 -> map to Du..Sh,Ya
    wd = datetime.now(TZ).weekday()
    return ["Du","Se","Ch","Pa","Ju","Sh","Ya"][wd]

def parse_cell(v):
    if not v or not v.strip(): return None
    g = "×g" in v
    base = v.replace(" ×g","").strip()
    return {"base":base,"g":g,"raw":v}

def current_lesson():
    k = get_today_key()
    if k=="Ya": return None
    now = datetime.now(TZ).time()
    for n in range(1,7):
        s,e = TIMES[n]
        if s <= now <= e:
            cell = parse_cell(RAW[n][k])
            if not cell: return None
            return {"n":n,"k":k,"cell":cell,"s":s,"e":e}
    return None

def next_lesson():
    k=get_today_key()
    if k=="Ya": return None
    now=datetime.now(TZ).time()
    for n in range(1,7):
        s,e=TIMES[n]
        if now < s:
            cell=parse_cell(RAW[n][k])
            if cell: return {"n":n,"cell":cell,"s":s}
    return None

def load_chats():
    if not os.path.exists(CHAT_FILE): return set()
    try: return set(json.load(open(CHAT_FILE,encoding="utf-8")))
    except: return set()

def save_chats(s):
    json.dump(list(s), open(CHAT_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

CHATS = load_chats()

# === КОМАНДЫ ===
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    CHATS.add(update.effective_chat.id)
    save_chats(CHATS)
    await update.message.reply_text(
        "Salom! Men *JadvalBot* 👋\n\n"
        "Men har kuni avtomatik yuboraman:\n"
        "• 08:00 da — bugungi jadval\n"
        "• Har dars boshida — qaysi dars\n"
        "• 5 daqiqa oldin tugashidan — eslatma ⏰\n\n"
        "Buyruqlar:\n"
        "/now — hozir qaysi dars?\n"
        "/today — bugungi jadval\n"
        "/jadval — haftalik jadval\n"
        "/help — yordam",
        parse_mode="Markdown"
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/now — hozirgi dars\n/today — bugun\n/jadval — hafta\n/start — obuna\n/stop — to'xtatish"
    )

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    CHATS.discard(update.effective_chat.id)
    save_chats(CHATS)
    await update.message.reply_text("Obuna to'xtatildi. /start bilan qayta yoqasan.")

async def cmd_now(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cur = current_lesson()
    if not cur:
        nxt = next_lesson()
        if not nxt:
            await update.message.reply_text("Hozir dars yo'q 😴\nKeyingi dars ertaga.")
        else:
            await update.message.reply_text(f"⏳ Keyingi: {nxt['n']}-soat — {nxt['cell']['base']} ({nxt['s'].strftime('%H:%M')})")
        return
    await update.message.reply_text(
        f"📚 Hozir {cur['n']}-soat — *{cur['cell']['base']}*{' (guruh)' if cur['cell']['g'] else ''}\n"
        f"{cur['s'].strftime('%H:%M')} — {cur['e'].strftime('%H:%M')} • {DAY_FULL[cur['k']]}",
        parse_mode="Markdown"
    )

async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    k=get_today_key()
    if k=="Ya":
        await update.message.reply_text("Yakshanba — dam olish 😴")
        return
    lines=[f"📅 *{DAY_FULL[k]} — bugun*"]
    for n in range(1,7):
        c=parse_cell(RAW[n][k])
        s,e=TIMES[n]
        if not c: lines.append(f"{n}. — —")
        else: lines.append(f"{n}. {c['base']}{' (guruh)' if c['g'] else ''} — {s.strftime('%H:%M')}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_jadval(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt=[]
    for dk in ["Du","Se","Ch","Pa","Ju","Sh"]:
        txt.append(f"*{DAY_FULL[dk]}*")
        for n in range(1,7):
            c=parse_cell(RAW[n][dk])
            if c: txt.append(f" {n}. {c['base']}{'⁽ᵍ⁾' if c['g'] else ''}")
        txt.append("")
    await update.message.reply_text("\n".join(txt), parse_mode="Markdown")

# === АВТО-РАССЫЛКА ===
async def notifier(app: Application):
    sent_today=set()   # (date, n, kind)
    sent_5min=set()
    while True:
        try:
            now=datetime.now(TZ)
            k=get_today_key()
            today_str=now.strftime("%Y-%m-%d")
            # 1) Утреннее расписание в 07:55
            if now.hour==7 and now.minute==55 and (today_str,"morning") not in sent_today and k!="Ya":
                lines=[f"☀️ *{DAY_FULL[k]} — bugungi jadval*"]
                for n in range(1,7):
                    c=parse_cell(RAW[n][k])
                    s,e=TIMES[n]
                    if c: lines.append(f"{n}. {c['base']} — {s.strftime('%H:%M')}")
                text="\n".join(lines)
                for cid in list(CHATS):
                    try: await app.bot.send_message(cid, text, parse_mode="Markdown")
                    except: pass
                sent_today.add((today_str,"morning"))

            # 2) Старт урока и 3) за 5 минут до конца
            if k!="Ya":
                cur_time=now.time()
                for n in range(1,7):
                    s,e=TIMES[n]
                    cell=parse_cell(RAW[n][k])
                    if not cell: continue
                    # старт в 08:00:00 - 08:00:59
                    if cur_time.hour==s.hour and cur_time.minute==s.minute and cur_time.second<10 and (today_str,n,"start") not in sent_today:
                        text=f"🔔 *{n}-soat boshlandi* — {cell['base']}{' (guruh)' if cell['g'] else ''}\n{s.strftime('%H:%M')} — {e.strftime('%H:%M')}"
                        for cid in list(CHATS):
                            try: await app.bot.send_message(cid, text, parse_mode="Markdown")
                            except: pass
                        sent_today.add((today_str,n,"start"))
                    # за 5 минут до конца: e -5 min
                    em = e.hour*60+e.minute -5
                    eh, emin = divmod(em,60)
                    if cur_time.hour==eh and cur_time.minute==emin and cur_time.second<10 and (today_str,n,"5min") not in sent_5min:
                        text=f"⏰ *5 daqiqadan so'ng tugaydi* — {n}-soat {cell['base']}\nTugash: {e.strftime('%H:%M')}"
                        for cid in list(CHATS):
                            try: await app.bot.send_message(cid, text, parse_mode="Markdown")
                            except: pass
                        sent_5min.add((today_str,n,"5min"))
            # сброс в полночь
            if now.hour==0 and now.minute==0:
                sent_today.clear(); sent_5min.clear()
        except Exception as e:
            print("notifier err",e)
        await asyncio.sleep(10)

def main():
    start_health_server()
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN yo'q. .env ga BOT_TOKEN=... qo'sh yoki muhitda o'rnat.")
        print("BotFather da @BotFather -> /newbot -> token ol.")
        return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("now", cmd_now))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("jadval", cmd_jadval))
    # фоновая задача
    async def on_startup(a):
        asyncio.create_task(notifier(a))
    app.post_init = on_startup
    print("JadvalBot ishga tushdi... Tashkent vaqti", datetime.now(TZ).strftime("%H:%M %d.%m"))
    app.run_polling()

if __name__=="__main__":
    main()

"""One-shot cron for GitHub Actions — checks schedule and handles Telegram updates.
Run every minute via workflow. Handles:
- morning 07:55
- lesson start (08:00 etc)
- 5 min before end
- pending /start /now etc via getUpdates
Persist chats.json via git commit in workflow.
"""
import os, json, requests
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

BOT_TOKEN = os.getenv("BOT_TOKEN","").strip()
TZ = ZoneInfo("Asia/Tashkent")
CHAT_FILE = "chats.json"

RAW = {
 1: {"Du":"", "Se":"Tarbiya", "Ch":"Tarix", "Pa":"Ingliz tili A-g", "Ju":"Texnologiya A-g", "Sh":"Ingliz tili A-g"},
 2: {"Du":"Geometriya", "Se":"Biologiya", "Ch":"Algebra", "Pa":"Ona tili", "Ju":"Tarix", "Sh":"Adabi"},
 3: {"Du":"Geografiya", "Se":"Tarix", "Ch":"Fizika", "Pa":"Chizmachilik", "Ju":"Huquq", "Sh":"Ona tili"},
 4: {"Du":"Jismoniy t. A-g", "Se":"Kimyo", "Ch":"Geometriya", "Pa":"Geografiya", "Ju":"Algebra", "Sh":"Rus tili A-g"},
 5: {"Du":"Biologiya", "Se":"Jismoniy t. A-g", "Ch":"Rus tili A-g", "Pa":"Adabiyot", "Ju":"Fizika", "Sh":"Algebra"},
 6: {"Du":"Ingliz tili A-g", "Se":"", "Ch":"Ona tili", "Pa":"Kimyo", "Ju":"Informatika A-g", "Sh":"Informatika A-g"},
}
TIMES = {1:(dtime(8,0),dtime(8,45)),2:(dtime(8,50),dtime(9,35)),3:(dtime(9,40),dtime(10,25)),4:(dtime(10,40),dtime(11,25)),5:(dtime(11,30),dtime(12,15)),6:(dtime(12,20),dtime(13,5))}
DAY_FULL = {"Du":"Dushanba","Se":"Seshanba","Ch":"Chorshanba","Pa":"Payshanba","Ju":"Juma","Sh":"Shanba","Ya":"Yakshanba"}

def get_today_key():
    wd = datetime.now(TZ).weekday()
    return ["Du","Se","Ch","Pa","Ju","Sh","Ya"][wd]
def parse_cell(v):
    if not v or not v.strip(): return None
    return {"base": v.replace(" A-g","").strip(), "g": "A-g" in v, "raw": v}
def load_chats():
    if not os.path.exists(CHAT_FILE): return set()
    try: return set(json.load(open(CHAT_FILE,encoding="utf-8")))
    except: return set()
def save_chats(s):
    json.dump(list(s), open(CHAT_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

def send(chat_id, text, parse_mode="Markdown"):
    try:
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": chat_id, "text": text, "parse_mode": parse_mode}, timeout=10)
        print(f"send to {chat_id}: {r.status_code}")
    except Exception as e:
        print(f"send err {e}")

def handle_updates(chats):
    # poll getUpdates
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", params={"timeout":0}, timeout=10)
        data = r.json()
        if not data.get("ok") or not data.get("result"):
            return chats, 0
        updates = data["result"]
        if not updates:
            return chats, 0
        max_id = max(u["update_id"] for u in updates)
        # process
        changed=False
        for u in updates:
            msg = u.get("message") or u.get("edited_message")
            if not msg: continue
            chat_id = msg["chat"]["id"]
            text = msg.get("text","").strip()
            if text.startswith("/start"):
                chats.add(chat_id); changed=True
                send(chat_id, "Salom! Men *JadvalBot* 👋\n\nMen har kuni avtomatik yuboraman:\n• 07:55 da — bugungi jadval\n• Har dars boshida — qaysi dars\n• 5 daqiqa oldin tugashidan — eslatma ⏰\n\nBuyruqlar:\n/now — hozir qaysi dars?\n/today — bugungi jadval\n/jadval — haftalik jadval\n/help — yordam")
            elif text.startswith("/stop"):
                chats.discard(chat_id); changed=True
                send(chat_id, "Obuna to'xtatildi. /start bilan qayta yoqasan.")
            elif text.startswith("/now"):
                # simple now
                k=get_today_key()
                now=datetime.now(TZ).time()
                found=None
                for n in range(1,7):
                    s,e=TIMES[n]
                    if s <= now <= e:
                        cell=parse_cell(RAW[n][k])
                        if cell:
                            found=(n,cell,s,e,k)
                            break
                if not found:
                    # next
                    nxt=None
                    for n in range(1,7):
                        s,_=TIMES[n]
                        if now < s:
                            cell=parse_cell(RAW[n][k])
                            if cell:
                                nxt=(n,cell,s); break
                    if not nxt:
                        send(chat_id, "Hozir dars yo'q 😴\nKeyingi dars ertaga.")
                    else:
                        send(chat_id, f"⏳ Keyingi: {nxt[0]}-soat — {nxt[1]['base']} ({nxt[2].strftime('%H:%M')})")
                else:
                    n,cell,s,e,k=found
                    send(chat_id, f"📚 Hozir {n}-soat — *{cell['base']}*{' (guruh)' if cell['g'] else ''}\n{s.strftime('%H:%M')} — {e.strftime('%H:%M')} • {DAY_FULL[k]}")
            elif text.startswith("/today"):
                k=get_today_key()
                if k=="Ya":
                    send(chat_id, "Yakshanba — dam olish 😴")
                else:
                    lines=[f"📅 *{DAY_FULL[k]} — bugun*"]
                    for n in range(1,7):
                        c=parse_cell(RAW[n][k])
                        s,_=TIMES[n]
                        if not c: lines.append(f"{n}. — —")
                        else: lines.append(f"{n}. {c['base']}{' (guruh)' if c['g'] else ''} — {s.strftime('%H:%M')}")
                    send(chat_id, "\n".join(lines))
            elif text.startswith("/jadval"):
                txt=[]
                for dk in ["Du","Se","Ch","Pa","Ju","Sh"]:
                    txt.append(f"*{DAY_FULL[dk]}*")
                    for n in range(1,7):
                        c=parse_cell(RAW[n][dk])
                        if c: txt.append(f" {n}. {c['base']}")
                    txt.append("")
                send(chat_id, "\n".join(txt))
            elif text.startswith("/help"):
                send(chat_id, "/now — hozirgi dars\n/today — bugun\n/jadval — hafta\n/start — obuna\n/stop — to'xtatish")
        # ack updates
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", params={"offset": max_id+1, "timeout":0}, timeout=10)
        if changed:
            save_chats(chats)
        return chats, len(updates)
    except Exception as e:
        print(f"handle_updates err {e}")
        return chats, 0

def check_schedule(chats):
    if not chats: return
    now=datetime.now(TZ)
    k=get_today_key()
    if k=="Ya": return
    today_str=now.strftime("%Y-%m-%d")
    # state file for deduplication today
    state_file=".cron_state.json"
    try:
        state=json.load(open(state_file,encoding="utf-8")) if os.path.exists(state_file) else {}
    except: state={}
    # morning 07:55
    if now.hour==7 and now.minute==55:
        key=f"{today_str}_morning"
        if key not in state:
            lines=[f"☀️ *{DAY_FULL[k]} — bugungi jadval*"]
            for n in range(1,7):
                c=parse_cell(RAW[n][k])
                s,_=TIMES[n]
                if c: lines.append(f"{n}. {c['base']} — {s.strftime('%H:%M')}")
            text="\n".join(lines)
            for cid in list(chats):
                send(cid, text)
            state[key]=1
            json.dump(state, open(state_file,"w",encoding="utf-8"))
            print("morning sent")
            return # avoid double send same minute
    # lesson start and 5min before end
    cur=now.time()
    for n in range(1,7):
        s,e=TIMES[n]
        cell=parse_cell(RAW[n][k])
        if not cell: continue
        if cur.hour==s.hour and cur.minute==s.minute and cur.second<60:
            key=f"{today_str}_{n}_start"
            if key not in state:
                text=f"🔔 *{n}-soat boshlandi* — {cell['base']}{' (guruh)' if cell['g'] else ''}\n{s.strftime('%H:%M')} — {e.strftime('%H:%M')}"
                for cid in list(chats): send(cid, text)
                state[key]=1
                json.dump(state, open(state_file,"w",encoding="utf-8"))
                print(f"start {n} sent")
        em = e.hour*60+e.minute -5
        eh, emin = divmod(em,60)
        if cur.hour==eh and cur.minute==emin and cur.second<60:
            key=f"{today_str}_{n}_5min"
            if key not in state:
                text=f"⏰ *5 daqiqadan so'ng tugaydi* — {n}-soat {cell['base']}\nTugash: {e.strftime('%H:%M')}"
                for cid in list(chats): send(cid, text)
                state[key]=1
                json.dump(state, open(state_file,"w",encoding="utf-8"))
                print(f"5min {n} sent")
    # midnight reset
    if now.hour==0 and now.minute==0:
        if os.path.exists(state_file):
            os.remove(state_file)

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN missing"); return
    chats=load_chats()
    print(f"chats {len(chats)}")
    chats, n = handle_updates(chats)
    print(f"handled {n} updates, chats now {len(chats)}")
    check_schedule(chats)
    print("done")

if __name__=="__main__":
    main()

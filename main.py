import asyncio
# Pyrogram ishlashi uchun zarur bo'lgan muhitni oldindan yaratib beramiz:
asyncio.set_event_loop(asyncio.new_event_loop())

from flask import Flask
import threading
from pyrogram import Client, filters
# ... (va qolgan barcha kodingiz o'zgarishsiz qoladi)
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot 100% ishlap turibdi!"

def run_server():
    # Render xostingi uchun 8080 porti ochiladi
    app.run(host="0.0.0.0", port=8080)

# BU YERDA SIZNING ASOSIY BOT KODINGIZ BO'LADI...
# (Avval tashlab bergan pyrogram bot kodimni shu yerga qo'yasiz)
import asyncio
import json
import os
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, FloodWait, PasswordHashInvalid

# ================= SOZLAMALAR =================
API_ID = 20543586 # O'zingizning API_ID ni kiriting (my.telegram.org dan olinadi)
API_HASH = "dba6965b60c1efd690789adb1dedb0fe" # O'zingizning API_HASH ni kiriting
BOT_TOKEN = "8281537480:AAEc0EvoGjkka0LHop4zgkDsk48pP6BHGDc" # BotFather dan olingan token
ADMIN_ID = 8281537480 # O'zingizning Telegram ID raqamingizni kiriting

DATA_FILE = "bot_data.json"
# ===============================================

# Ma'lumotlarni xotirada va faylda saqlash tizimi
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"session": None}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Bot va Foydalanuvchi mijozlari
bot = Client("admin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
temp_client = None

# Admin qadamlarini kuzatish uchun FSM (State Machine) o'rniga oddiy lug'at
user_states = {}
temp_data = {}

# Asosiy menyu klaviaturasi
main_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("👤 Akkount boshqaruvi"), KeyboardButton("🚀 Tasdiqlash bo'limi")]
    ], resize_keyboard=True
)

acc_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ Akkount qo'shish"), KeyboardButton("🗑 Akkountni o'chirish")],
        [KeyboardButton("🔙 Orqaga")]
    ], resize_keyboard=True
)

# ======== ADMIN TEKSHIRUVI ========
@bot.on_message(filters.private & ~filters.user(ADMIN_ID))
async def not_admin(client, message):
    await message.reply_text("⛔️ Kechirasiz, bu bot faqat admin uchun ishlaydi.")

# ======== START BUYRUG'I ========
@bot.on_message(filters.private & filters.command("start") & filters.user(ADMIN_ID))
async def start_cmd(client, message):
    user_states[ADMIN_ID] = "main_menu"
    await message.reply_text("👋 Xush kelibsiz, Admin! \nKerakli bo'limni tanlang:", reply_markup=main_menu)

# ======== MENYU NAVIGATSIYASI ========
@bot.on_message(filters.private & filters.text & filters.user(ADMIN_ID))
async def handle_text(client, message):
    text = message.text
    state = user_states.get(ADMIN_ID, "main_menu")

    # Orqaga qaytish
    if text == "🔙 Orqaga":
        user_states[ADMIN_ID] = "main_menu"
        await message.reply_text("Asosiy menyuga qaytdingiz.", reply_markup=main_menu)
        return

    # 1. AKKOUNT BOSHQARUVI
    if text == "👤 Akkount boshqaruvi":
        data = load_data()
        status = "✅ Ulangan" if data.get("session") else "❌ Ulanmagan"
        await message.reply_text(f"Hozirgi akkaunt holati: {status}\nNima qilamiz?", reply_markup=acc_menu)
        return

    if text == "🗑 Akkountni o'chirish":
        save_data({"session": None})
        await message.reply_text("🗑 Akkount tizimdan o'chirildi!", reply_markup=main_menu)
        return

    if text == "➕ Akkount qo'shish":
        user_states[ADMIN_ID] = "waiting_phone"
        await message.reply_text("Telefon raqamingizni xalqaro formatda yuboring:\nMasalan: +998901234567")
        return

    # 2. TASDIQLASH BO'LIMI
    if text == "🚀 Tasdiqlash bo'limi":
        data = load_data()
        if not data.get("session"):
            await message.reply_text("⚠️ Avval akkaunt qo'shishingiz kerak!")
            return
        
        user_states[ADMIN_ID] = "waiting_channel"
        await message.reply_text("Kanal Username'ini (@kanal) yoki ID raqamini yuboring:")
        return

    # --- AKKOUNT QO'SHISH QADAMLARI ---
    if state == "waiting_phone":
        global temp_client
        phone = text.strip()
        temp_data["phone"] = phone
        
        msg = await message.reply_text("⏳ Kod so'ralmoqda, kuting...")
        
        try:
            temp_client = Client("temp_session", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_client.connect()
            sent_code = await temp_client.send_code(phone)
            temp_data["phone_code_hash"] = sent_code.phone_code_hash
            
            user_states[ADMIN_ID] = "waiting_code"
            await msg.edit_text("📩 Telegramdan kelgan kodni yuboring.\n(Agar kod 12345 bo'lsa, uni 1 2 3 4 5 shaklida yoki to'g'ridan-to'g'ri yozing)")
        except Exception as e:
            await msg.edit_text(f"❌ Xatolik: {e}")
            user_states[ADMIN_ID] = "main_menu"

    elif state == "waiting_code":
        code = text.replace(" ", "")
        msg = await message.reply_text("⏳ Tizimga kirilmoqda...")
        
        try:
            await temp_client.sign_in(temp_data["phone"], temp_data["phone_code_hash"], code)
            session_string = await temp_client.export_session_string()
            save_data({"session": session_string})
            await temp_client.disconnect()
            
            user_states[ADMIN_ID] = "main_menu"
            await msg.edit_text("✅ Akkaunt muvaffaqiyatli ulandi va saqlandi!", reply_markup=main_menu)
            
        except SessionPasswordNeeded:
            user_states[ADMIN_ID] = "waiting_password"
            await msg.edit_text("🔐 Akkauntda 2 bosqichli parol (2FA) bor ekan. Parolni yuboring:")
        except PhoneCodeInvalid:
            await msg.edit_text("❌ Kod xato! Boshqatdan urinib ko'ring.")
            user_states[ADMIN_ID] = "main_menu"
            await temp_client.disconnect()

    elif state == "waiting_password":
        password = text
        msg = await message.reply_text("⏳ Parol tekshirilmoqda...")
        
        try:
            await temp_client.check_password(password)
            session_string = await temp_client.export_session_string()
            save_data({"session": session_string})
            await temp_client.disconnect()
            
            user_states[ADMIN_ID] = "main_menu"
            await msg.edit_text("✅ Akkaunt muvaffaqiyatli ulandi va saqlandi!", reply_markup=main_menu)
        except PasswordHashInvalid:
            await msg.edit_text("❌ Parol xato! Tizimga kirish bekor qilindi.")
            user_states[ADMIN_ID] = "main_menu"
            await temp_client.disconnect()

    # --- TASDIQLASH QADAMLARI ---
    elif state == "waiting_channel":
        temp_data["channel"] = text
        user_states[ADMIN_ID] = "waiting_count"
        # Izoh: 100k so'rovni oldindan sanab chiqish API limitiga tushib qoladi.
        # Shuning uchun bot qancha tasdiqlashni o'zingizdan so'raydi.
        await message.reply_text("Qabul qilish uchun so'rovlar soni aniqlanmoqda (API cheklovini oldini olish uchun aniq raqam o'rniga mo'ljalni kiriting).\n\nJami qancha so'rovni tasdiqlamoqchisiz? (Masalan: 100000)")

    elif state == "waiting_count":
        if not text.isdigit():
            await message.reply_text("Iltimos, faqat raqam kiriting!")
            return
        temp_data["target_count"] = int(text)
        user_states[ADMIN_ID] = "waiting_rate"
        await message.reply_text("Bir daqiqada o'rtacha qancha so'rov tasdiqlansin? (Masalan: 40)")

    elif state == "waiting_rate":
        if not text.isdigit():
            await message.reply_text("Iltimos, faqat raqam kiriting!")
            return
        
        rate = int(text)
        target = temp_data["target_count"]
        channel = temp_data["channel"]
        
        user_states[ADMIN_ID] = "main_menu"
        await message.reply_text(f"🚀 Jarayon boshlandi!\nKanal: {channel}\nMaqsad: {target} ta\nTezlik: Daqiqasiga {rate} ta.", reply_markup=main_menu)
        
        # Fon rejimida jarayonni ishga tushirish (bot qotib qolmasligi uchun)
        asyncio.create_task(approve_requests(channel, target, rate, message))

# ======== TASDIQLASH JARAYONI (WORKER) ========
async def approve_requests(channel, target_count, rate_per_minute, message):
    data = load_data()
    session_string = data.get("session")
    
    if not session_string:
        await message.reply_text("❌ Akkount topilmadi. Jarayon bekor qilindi.")
        return

    app = Client("worker_session", session_string=session_string, in_memory=True)
    
    try:
        await app.connect()
        approved = 0
        failed = 0
        sleep_time = 60.0 / rate_per_minute if rate_per_minute > 0 else 1.5

        # ID yoki Username ekanini tekshiramiz
        chat_target = int(channel) if channel.replace("-", "").isdigit() else channel

        async for request in app.get_chat_join_requests(chat_target):
            try:
                await app.approve_chat_join_request(chat_target, request.user.id)
                approved += 1
                
                # Har 500 tada adminga hisobot yuboradi (100k limitda bot spam bo'lmasligi uchun)
                if approved % 500 == 0:
                    await message.reply_text(f"🔄 Kuting, jarayon ketmoqda...\nTasdiqlandi: {approved} ta.")
                
                if approved >= target_count:
                    break
                    
                await asyncio.sleep(sleep_time)

            except FloodWait as e:
                await message.reply_text(f"⚠️ Telegram tomonidan vaqtinchalik cheklov (FloodWait)!\nBot {e.value} soniya kutadi...")
                await asyncio.sleep(e.value + 5)
            except Exception as e:
                failed += 1

        await message.reply_text(f"✅ JARAYON YAKUNLANDI!\n\nKanal: {channel}\nMuvaffaqiyatli tasdiqlandi: {approved} ta\nXatoliklar: {failed} ta.")

    except Exception as e:
        await message.reply_text(f"❌ Xatolik yuz berdi: {e}")
    finally:
        if app.is_connected:
            await app.disconnect()

# ================= ISHGA TUSHIRISH =================
if __name__ == "__main__":
    print("🤖 Bot ishga tushdi...")
    bot.run()
# KODNING ENG PASTGI QISMI QUYIDAGICHA BO'LADI:
if __name__ == "__main__":
    print("🤖 Bot va Veb-server ishga tushdi...")
    # Flask serverni alohida oqimda ishga tushiramiz
    threading.Thread(target=run_server).start()
    # Pyrogram botni ishga tushiramiz
    bot.run()

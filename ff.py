import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
API_TOKEN = "8660698606:AAH6uygG8y5nHKv1qjAy4QcsWwdtusVDyDk"
OWNER_ID = 6225749847
BKASH_NO = "01761214398"
SUPPORT_LINK = "https://t.me/BEEGHK"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    uid TEXT,
    package TEXT,
    txn TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    role TEXT
)
""")
conn.commit()

# Ensure owner is in DB
cursor.execute("INSERT OR REPLACE INTO admins (user_id, role) VALUES (?, ?)", (OWNER_ID, "owner"))
conn.commit()

user_temp = {}

# ================= HELPERS =================
def get_role(uid: int):
    cursor.execute("SELECT role FROM admins WHERE user_id=?", (uid,))
    res = cursor.fetchone()
    return res[0] if res else None

def is_admin(uid: int):
    return get_role(uid) in ["owner", "subadmin"]

def is_owner(uid: int):
    return get_role(uid) == "owner"

# ================= MENUS =================
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💎 টপ আপ")],
            [KeyboardButton(text="📦 আমার অর্ডার")],
            [KeyboardButton(text="📞 সাপোর্ট")]
        ],
        resize_keyboard=True
    )

def admin_menu(uid):
    btns = [
        [KeyboardButton(text="➕ প্যাকেজ যুক্ত করুন"), KeyboardButton(text="❌ প্যাকেজ ডিলিট")],
        [KeyboardButton(text="📦 প্যাকেজসমূহ"), KeyboardButton(text="📊 অর্ডার তালিকা")]
    ]
    if is_owner(uid):
        btns.append([KeyboardButton(text="👤 নতুন অ্যাডমিন যোগ করুন")])
    btns.append([KeyboardButton(text="🏠 ইউজার মেনু")])
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

# ================= START =================
@dp.message(Command("start"))
async def start(message: types.Message):
    uid = message.from_user.id
    user_temp[uid] = {}
    if uid == OWNER_ID:
        cursor.execute("INSERT OR REPLACE INTO admins (user_id, role) VALUES (?, ?)", (uid, "owner"))
        conn.commit()
    if is_admin(uid):
        await message.answer("👑 Admin Panel", reply_markup=admin_menu(uid))
    else:
        await message.answer("🎮 User Panel", reply_markup=main_menu())

# ================= SUPPORT =================
@dp.message(F.text == "📞 সাপোর্ট")
async def support(message: types.Message):
    await message.answer(f"📞 Support: {SUPPORT_LINK}")

# ================= MY ORDERS =================
@dp.message(F.text == "📦 আমার অর্ডার")
async def my_orders(message: types.Message):
    uid = message.from_user.id
    cursor.execute("SELECT id, package, status, created_at, txn FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 5", (uid,))
    data = cursor.fetchall()
    if not data:
        return await message.answer("📁 কোনো অর্ডার নেই।")
    msg = "📦 <b>আপনার অর্ডারসমূহ:</b>\n\n"
    for o in data:
        txn = o[4] if o[4] else "Pending"
        msg += f"🆔 #{o[0]}\n📦 Package: {o[1]}\n🎫 Txn: {txn}\n⏳ Status: {o[2]}\n🕒 {o[3]}\n\n"
    await message.answer(msg, parse_mode="HTML")

# ================= ADMIN PANEL =================
@dp.message(F.text == "➕ প্যাকেজ যুক্ত করুন")
async def add_pkg(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    user_temp[message.from_user.id] = {"st": "add_pkg"}
    await message.answer("📦 প্যাকেজ লিখুন (যেমন: Weekly Lite - 45 BDT):")

@dp.message(F.text == "❌ প্যাকেজ ডিলিট")
async def del_pkg(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    cursor.execute("SELECT id, name FROM packages")
    data = cursor.fetchall()
    if not data:
        return await message.answer("❌ কোনো প্যাকেজ নেই")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"🗑 {d[1]}", callback_data=f"del_{d[0]}")] for d in data]
    )
    await message.answer("ডিলিট করুন:", reply_markup=kb)

@dp.message(F.text == "📦 প্যাকেজসমূহ")
async def show_pkg(message: types.Message):
    cursor.execute("SELECT name FROM packages")
    data = cursor.fetchall()
    msg = "\n".join([f"• {d[0]}" for d in data]) if data else "❌ কোনো প্যাকেজ নেই"
    await message.answer(msg)

@dp.message(F.text == "📊 অর্ডার তালিকা")
async def order_list(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    cursor.execute("SELECT id, uid, package, status FROM orders ORDER BY id DESC LIMIT 10")
    data = cursor.fetchall()
    msg = ""
    for o in data:
        msg += f"#{o[0]} | UID: {o[1]} | {o[2]} | Status: {o[3]}\n"
    await message.answer(msg)

# ================= ADD ADMIN =================
@dp.message(F.text == "👤 নতুন অ্যাডমিন যোগ করুন")
async def add_admin(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    user_temp[message.from_user.id] = {"st": "add_admin_id"}
    await message.answer("👤 নতুন অ্যাডমিনের Telegram ID দিন:")

# ================= USER FLOW =================
@dp.message(F.text == "💎 টপ আপ")
async def topup(message: types.Message):
    user_temp[message.from_user.id] = {"st": "get_uid"}
    await message.answer("🎮 Player UID দিন:")

@dp.message(F.text == "🏠 ইউজার মেনু")
async def back_user(message: types.Message):
    await message.answer("🏠 User Mode", reply_markup=main_menu())

# ================= INPUT HANDLER =================
@dp.message()
async def input_handler(message: types.Message):
    uid = message.from_user.id
    text = message.text
    state = user_temp.get(uid, {}).get("st")
    if not state:
        return

    # ====== ADD PACKAGE ======
    if state == "add_pkg":
        cursor.execute("INSERT OR IGNORE INTO packages (name) VALUES (?)", (text,))
        conn.commit()
        user_temp[uid] = {}
        await message.answer(f"✅ প্যাকেজ যুক্ত হয়েছে: {text}", reply_markup=admin_menu(uid))

    # ====== ADD NEW ADMIN (PENDING) ======
    elif state == "add_admin_id":
        if not text.isdigit():
            return await message.answer("❌ ID ভুল")
        new_id = int(text)
        cursor.execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, ?)", (new_id, "pending"))
        conn.commit()
        user_temp[uid] = {}

        # Notify existing admins for confirm/decline
        cursor.execute("SELECT user_id FROM admins WHERE role IN ('owner','subadmin')")
        all_admins = [row[0] for row in cursor.fetchall()]
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_admin_{new_id}"),
                InlineKeyboardButton(text="❌ Decline", callback_data=f"decline_admin_{new_id}")
            ]]
        )
        for adm_id in all_admins:
            try:
                await bot.send_message(
                    adm_id,
                    f"👤 নতুন অ্যাডমিন চাওয়া হয়েছে: {new_id}",
                    reply_markup=kb
                )
            except Exception as e:
                logging.warning(f"Cannot notify admin {adm_id}: {e}")
        await message.answer("✅ নতুন অ্যাডমিন রিকুয়েস্ট পাঠানো হয়েছে admin panel এ")

    # ====== TOPUP UID ======
    elif state == "get_uid":
        user_temp[uid] = {"uid": text, "st": "select_pkg"}
        cursor.execute("SELECT id, name FROM packages")
        pkgs = cursor.fetchall()
        if not pkgs:
            return await message.answer("❌ কোনো প্যাকেজ নেই")
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=p[1], callback_data=f"pkg_{p[0]}")] for p in pkgs]
        )
        await message.answer("প্যাকেজ বাছুন:", reply_markup=kb)

    # ====== SEND TXN ======
    elif state == "send_txn":
        cursor.execute(
            "SELECT id, uid, package FROM orders WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
            (uid,)
        )
        ord = cursor.fetchone()
        if not ord:
            return await message.answer("❌ অর্ডার পাওয়া যায়নি")
        txn = text.strip()
        if not txn:
            return await message.answer("❌ Txn ID খালি, আবার পাঠান।")
        cursor.execute(
            "UPDATE orders SET txn=?, status='Reviewing', created_at=? WHERE id=?",
            (txn, datetime.now().strftime("%d %b %Y %H:%M"), ord[0])
        )
        conn.commit()

        # Notify all admins for review
        cursor.execute("SELECT user_id FROM admins WHERE role IN ('owner','subadmin')")
        all_admins = [row[0] for row in cursor.fetchall()]
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_order_{ord[0]}"),
                InlineKeyboardButton(text="❌ Decline", callback_data=f"decline_order_{ord[0]}")
            ]]
        )
        for adm_id in all_admins:
            try:
                await bot.send_message(
                    adm_id,
                    f"🔔 নতুন অর্ডার!\n🆔 Order ID: #{ord[0]}\n🎮 UID: {ord[1]}\n📦 Package: {ord[2]}\n💳 Txn ID: {txn}",
                    reply_markup=kb
                )
            except Exception as e:
                logging.warning(f"Cannot notify admin {adm_id}: {e}")

        await message.answer(
            f"✅ <b>অর্ডার রিভিউতে গেছে!</b>\n\n🆔 Order ID: #{ord[0]}\n🎮 UID: {ord[1]}\n📦 প্যাকেজ: {ord[2]}\n🎫 Txn ID: <code>{txn}</code>\n⏳ Status: Pending",
            parse_mode="HTML"
        )
        user_temp[uid] = {}

# ================= CALLBACK HANDLER =================
@dp.callback_query()
async def cb_handler(call: types.CallbackQuery):
    data = call.data
    uid = call.from_user.id

    # ===== PACKAGE SELECT =====
    if data.startswith("pkg_"):
        pid = int(data.split("_")[1])
        cursor.execute("SELECT name FROM packages WHERE id=?", (pid,))
        pname = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO orders (user_id, uid, package, created_at) VALUES (?, ?, ?, ?)",
            (uid, user_temp[uid]['uid'], pname, datetime.now().strftime("%d %b %Y %H:%M"))
        )
        conn.commit()
        user_temp[uid] = {"st": "send_txn"}
        await call.message.edit_text(
            f"📦 <b>{pname}</b>\n💰 BDT: 45\n💳 bKash: {BKASH_NO}\n\n⚠️ পেমেন্ট করে Txn ID লিখে পাঠান।", parse_mode="HTML"
        )

    # ===== DELETE PACKAGE =====
    elif data.startswith("del_"):
        pid = int(data.split("_")[1])
        cursor.execute("DELETE FROM packages WHERE id=?", (pid,))
        conn.commit()
        await call.message.edit_text("✅ ডিলিট হয়েছে")

    # ===== ADMIN CONFIRM/DENY =====
    elif data.startswith("confirm_admin_") or data.startswith("decline_admin_"):
        action, _, new_id = data.split("_")
        new_id = int(new_id)
        if action == "confirm":
            cursor.execute("UPDATE admins SET role='subadmin' WHERE user_id=?", (new_id,))
            msg = f"✅ অ্যাডমিন Active: {new_id}"
        else:
            cursor.execute("DELETE FROM admins WHERE user_id=?", (new_id,))
            msg = f"❌ অ্যাডমিন Declined: {new_id}"
        conn.commit()
        await call.message.edit_text(f"{call.message.text}\n\n📢 {msg}")
        try:
            await bot.send_message(new_id, f"আপনার অ্যাডমিন রিকুয়েস্ট: {msg}")
        except:
            pass
        await call.answer()

    # ===== ORDER CONFIRM / DECLINE =====
    elif data.startswith("confirm_order_") or data.startswith("decline_order_"):
        parts = data.split("_")  # ["confirm","order","26"]
        action = parts[0]        # "confirm" বা "decline"
        oid = int(parts[2])      # order id
        cursor.execute("SELECT user_id, uid, package, txn FROM orders WHERE id=?", (oid,))
        order = cursor.fetchone()
        if not order:
            return await call.answer("Order not found!", show_alert=True)
        user_id, uid_val, pkg, txn = order
        status = "Completed ✅" if action == "confirm" else "Cancelled ❌"
        cursor.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))
        conn.commit()
        # Notify user
        await bot.send_message(
            user_id,
            f"📢 আপনার অর্ডার #{oid} ({pkg}) এখন <b>{status}</b>\n🎫 Txn: {txn}\n🎮 UID: {uid_val}",
            parse_mode="HTML"
        )
        await call.message.edit_text(f"{call.message.text}\n\n📢 অর্ডারটি {status}")
        await call.answer()

# ================= RUN BOT =================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

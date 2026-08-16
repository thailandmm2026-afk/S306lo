#!/usr/bin/env python3
"""
LOTTERY PRO BOT - WITH EXPIRY & STICKERS + FULL ADMIN PANEL
====================================
- 1-Minute and 30-Second only
- Pattern-based prediction only
- User expiry system (1 Day / Unlimited)
- Win sticker only (Lose no sticker)
- Full Admin Panel (Ban/Unban, User List, Broadcast)
====================================
"""

import os
import requests
import asyncio
import json
import sqlite3
import hashlib
import time
import random
from datetime import datetime, timedelta
from collections import deque
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# ==================== CONFIG (from Environment Variables) ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8707027344:AAFOGuDVUpKgGaCmOruhyh1Z5plgeclsa00")
OWNER_ID = int(os.getenv("OWNER_ID", "7308292609"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@kiki20251")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", str(OWNER_ID)).split(",") if x.strip()]

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable is required!")

GAME_TYPES = {
    "1M": {"name": "1-Minute", "emoji": "⚡", "type_id": 1},
    "30S": {"name": "30-Second", "emoji": "🔥", "type_id": 30}
}

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://6lottery.com",
    "Referer": "https://6lottery.com/",
    "User-Agent": "Mozilla/5.0"
}

# ==================== STICKERS ====================
STICKER_WIN = "CAACAgUAAxkBAAFRtAtqfVwKT4KVe08zkmEKg_K3N5ACYQAC8hQAAupZYFZJUhDoOEcVPj0E"

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('lottery_pro.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_active INTEGER DEFAULT 0,
            is_pending INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            registered_date TEXT,
            last_active TEXT,
            game_type TEXT DEFAULT '1M',
            bot_running INTEGER DEFAULT 0,
            approved_by INTEGER DEFAULT NULL,
            approved_date TEXT DEFAULT NULL,
            expiry_date TEXT DEFAULT NULL,
            plan_type TEXT DEFAULT 'Unlimited'
        )''')
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
            self.conn.commit()
        except:
            pass

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS pending_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            request_date TEXT,
            status TEXT DEFAULT 'pending'
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp TEXT
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS stats (
            user_id INTEGER PRIMARY KEY,
            win_count INTEGER DEFAULT 0,
            lose_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            current_streak INTEGER DEFAULT 0,
            bet INTEGER DEFAULT 1
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER UNIQUE,
            channel_name TEXT,
            added_by INTEGER,
            added_date TEXT,
            is_active INTEGER DEFAULT 1
        )''')
        self.conn.commit()
    
    def execute(self, query, params=()):
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor
    def fetchone(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()
    def fetchall(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

db = Database()

# ==================== API FUNCTIONS ====================
def sign_md5(data_dict):
    sign_data = data_dict.copy()
    for k in ['signature', 'timestamp']:
        if k in sign_data: del sign_data[k]
    sorted_data = dict(sorted(sign_data.items()))
    hash_string = json.dumps(sorted_data, separators=(',', ':')).replace(' ', '')
    return hashlib.md5(hash_string.encode('utf-8')).hexdigest()

def get_current_issue_6lottery(type_id):
    try:
        body = {"typeId": type_id, "language": 0, "random": "b05034ba4a2642009350ee863f29e2e9", "timestamp": int(time.time())}
        body["signature"] = sign_md5(body).upper()
        resp = requests.post("https://6lotteryapi.com/api/webapi/GetGameIssue", headers=HEADERS, json=body, timeout=15)
        if resp.status_code == 200:
            d = resp.json()
            if d.get('msgCode') == 0:
                return d.get('data', {}).get('issueNumber', '')
        return None
    except: return None

def get_result_for_issue_6lottery(type_id, issue_number):
    try:
        body = {"pageNo": 1, "pageSize": 10, "language": 0, "typeId": type_id,
                "random": "6DEB0766860C42151A193692ED16D65A", "timestamp": int(time.time())}
        body["signature"] = sign_md5(body).upper()
        resp = requests.post("https://6lotteryapi.com/api/webapi/GetNoaverageEmerdList", headers=HEADERS, json=body, timeout=15)
        if resp.status_code == 200:
            d = resp.json()
            if d.get('msgCode') == 0:
                for item in d.get('data', {}).get('list', []):
                    if item.get('issueNumber') == issue_number:
                        return int(item.get('number'))
        return None
    except: return None

def get_last_results_6lottery(type_id, limit=10):
    try:
        body = {"pageNo": 1, "pageSize": limit, "language": 0, "typeId": type_id,
                "random": "6DEB0766860C42151A193692ED16D65A", "timestamp": int(time.time())}
        body["signature"] = sign_md5(body).upper()
        resp = requests.post("https://6lotteryapi.com/api/webapi/GetNoaverageEmerdList", headers=HEADERS, json=body, timeout=15)
        if resp.status_code == 200:
            d = resp.json()
            if d.get('msgCode') == 0:
                return [int(item.get('number')) for item in d.get('data', {}).get('list', [])]
        return []
    except: return []

# ==================== PREDICTION ENGINE ====================
class PredictionEngine:
    def __init__(self, user_id):
        self.user_id = user_id
        self.all_numbers = deque(maxlen=200)
        self.bet = 1
        self.win_count = 0
        self.lose_count = 0
        self.current_streak = 0
        self.load_stats()
        
        self.patterns = {
            "BSBSB": "SMALL", "SBSBS": "BIG", "SSBBS": "SMALL", "BBSSB": "BIG",
            "SSSBB": "BIG", "BBBSS": "SMALL", "BSSBS": "SMALL", "SBBSB": "BIG",
            "BSSSB": "SMALL", "SBBBS": "BIG", "SBBSS": "BIG", "BSSBB": "SMALL",
            "BBSBB": "SMALL", "SSBSS": "BIG", "SBBBB": "BIG", "BSSSS": "SMALL",
            "SSSSB": "SMALL", "BBBBS": "SMALL", "SBSBB": "BIG", "BSBSS": "SMALL",
            "SSBSB": "BIG", "BBSSS": "SMALL", "BBBBB": "BIG", "SSSSS": "SMALL",
            "BBBB": "SMALL", "SSSS": "BIG", "SBSSB": "BIG", "BBSBB": "SMALL",
            "SSBSS": "BIG", "BSSBB": "BIG", "SBBSS": "SMALL", "BSBBS": "SMALL",
            "SSSBS": "BIG", "SSB": "BIG", "BBS": "SMALL", "SBS": "BIG",
            "BSB": "SMALL", "BSSBS": "SMALL", "BSBSS": "SMALL", "SBBSB": "BIG",
            "BSBBS": "BIG", "SBSBS": "SMALL", "BBBSS": "BIG", "SBBBB": "SMALL",
            "BSSSS": "BIG", "BBSBB": "SMALL", "BBSSS": "BIG", "SSBBB": "SMALL",
            "BSBBS": "SMALL", "SBSBB": "BIG", "BSSBB": "BIG", "SBBSS": "SMALL",
        }
    
    def load_stats(self):
        stats = db.fetchone("SELECT win_count, lose_count, current_streak, bet FROM stats WHERE user_id = ?", (self.user_id,))
        if stats:
            self.win_count, self.lose_count, self.current_streak, self.bet = stats
    
    def save_stats(self):
        db.execute("INSERT OR REPLACE INTO stats (user_id, win_count, lose_count, total_count, current_streak, bet) VALUES (?, ?, ?, ?, ?, ?)",
                   (self.user_id, self.win_count, self.lose_count, self.win_count + self.lose_count, self.current_streak, self.bet))
    
    def get_prediction(self):
        if len(self.all_numbers) < 3:
            return random.choice(["BIG", "SMALL"])
        numbers = list(self.all_numbers)[:8]
        seq = ''.join(['B' if n >= 5 else 'S' for n in numbers])
        for length in [5, 4, 3]:
            if len(seq) >= length:
                pattern = seq[:length]
                if pattern in self.patterns:
                    return self.patterns[pattern]
        return random.choice(["BIG", "SMALL"])
    
    def update_result(self, number, prediction):
        actual = "BIG" if number >= 5 else "SMALL"
        is_win = prediction == actual
        self.all_numbers.appendleft(number)
        if is_win:
            self.win_count += 1
            self.current_streak = 0
            self.bet = 1
        else:
            self.lose_count += 1
            self.current_streak += 1
            self.bet += 1
        self.save_stats()
        return is_win, actual

# ==================== BOT HANDLERS ====================
class BotHandlers:
    def __init__(self):
        self.application = None
        self.engines = {}
        self.bot_tasks = {}
    
    def get_engine(self, user_id):
        if user_id not in self.engines:
            self.engines[user_id] = PredictionEngine(user_id)
        return self.engines[user_id]
    
    def _format_prediction(self, period, prediction, bet):
        emoji = "🔴" if prediction == "BIG" else "🟢"
        return f"🎯 <b>Period</b> : <code>{period}</code>\n📊 <b>Prediction</b> : {emoji} {prediction}\n💰 <b>Multiplier</b> : {bet}×"
    
    def _format_result(self, period, actual, number, is_win, bet):
        emoji = "🔴" if actual == "BIG" else "🟢"
        status_emoji = "✅" if is_win else "❌"
        status_text = "🎉 <b>WIN</b> 🎉" if is_win else "😢 <b>LOSE</b> 💔"
        sticker = STICKER_WIN if is_win else None
        return {
            "text": f"📊 <b>Result</b>\n━━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Period</b> : <code>{period}</code>\n📊 <b>Result</b> : {emoji} {actual} ({number})\n📈 <b>Status</b> : {status_emoji} {status_text}\n💰 <b>Next Bet</b> : {bet}×",
            "sticker": sticker
        }
    
    def get_reply_keyboard(self, is_admin=False):
        keyboard = [["▶️ Start Bot", "⏹️ Stop Bot"], ["🎮 Game Type"], ["📊 My Stats"]]
        if is_admin:
            keyboard.append(["🔐 Admin Panel"])
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def get_game_type_keyboard(self):
        return ReplyKeyboardMarkup([["⚡ 1-Minute", "🔥 30-Second"], ["🔙 Back"]], resize_keyboard=True)
    
    def check_expiry(self, user_id):
        user = db.fetchone("SELECT expiry_date, plan_type, is_banned FROM users WHERE user_id = ?", (user_id,))
        if not user:
            return False
        expiry_date, plan_type, is_banned = user
        if is_banned:
            return False
        if plan_type == "Unlimited":
            return True
        if expiry_date:
            try:
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                if datetime.now() < expiry:
                    return True
            except:
                return False
        return False
    
    def is_banned(self, user_id):
        row = db.fetchone("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        return row and row[0] == 1
    
    # ==================== START ====================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if user.id in ADMIN_IDS:
            db.execute("""INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, is_active, is_pending, is_banned, registered_date, game_type, plan_type, expiry_date) 
                VALUES (?, ?, ?, ?, 1, 0, 0, ?, '1M', 'Unlimited', NULL)""",
                (user.id, user.username or "", user.first_name or "", user.last_name or "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            await self._show_main_menu(update, user, "1M")
            return
        
        existing = db.fetchone("SELECT user_id, is_active, is_pending, game_type, is_banned FROM users WHERE user_id = ?", (user.id,))
        if existing:
            if existing[4] == 1:
                await update.message.reply_text(
                    f"🚫 <b>You are banned!</b>\n━━━━━━━━━━━━━━━━━━━━━\nPlease contact admin.\n👑 Owner: {OWNER_USERNAME}",
                    parse_mode=ParseMode.HTML
                )
                return
            if existing[1] == 1:
                if not self.check_expiry(user.id):
                    await update.message.reply_text(
                        f"⏰ <b>Your plan has expired!</b>\n━━━━━━━━━━━━━━━━━━━━━\nPlease contact admin to renew your plan.\n👑 Owner: {OWNER_USERNAME}",
                        parse_mode=ParseMode.HTML
                    )
                    return
                await self._show_main_menu(update, user, existing[3])
            elif existing[2] == 1:
                await update.message.reply_text(f"⏳ <b>Pending approval...</b>\n👑 Owner: {OWNER_USERNAME}", parse_mode=ParseMode.HTML)
            else:
                await self._send_approval_request(update, user)
        else:
            await self._send_approval_request(update, user)
    
    async def _show_main_menu(self, update, user, game_type):
        user_id = user.id
        game_info = GAME_TYPES.get(game_type, GAME_TYPES["1M"])
        is_admin = user_id in ADMIN_IDS
        stats = db.fetchone("SELECT win_count, lose_count, bet FROM stats WHERE user_id = ?", (user_id,))
        win, lose, bet = stats if stats else (0, 0, 1)
        total = win + lose
        rate = (win / total * 100) if total > 0 else 0
        running = db.fetchone("SELECT bot_running FROM users WHERE user_id = ?", (user_id,))
        running = running[0] if running else 0
        
        user_data = db.fetchone("SELECT plan_type, expiry_date FROM users WHERE user_id = ?", (user_id,))
        plan = user_data[0] if user_data else "Unlimited"
        expiry = user_data[1] if user_data and user_data[1] else "Never"
        
        await update.message.reply_text(
            f"👋 <b>Welcome {user.first_name}</b>!\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎮 <b>Game</b> : {game_info['emoji']} {game_info['name']}\n"
            f"🤖 <b>Bot</b> : {'🟢 Running' if running else '🔴 Stopped'}\n"
            f"📋 <b>Plan</b> : {plan}\n"
            f"⏰ <b>Expiry</b> : {expiry}\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Stats</b> :\n   🏆 Wins: {win}\n   💸 Losses: {lose}\n   📈 Rate: {rate:.1f}%\n   💰 Bet: {bet}×",
            parse_mode=ParseMode.HTML,
            reply_markup=self.get_reply_keyboard(is_admin)
        )
    
    async def _send_approval_request(self, update, user):
        user_id = user.id
        db.execute("""INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, is_active, is_pending, is_banned, registered_date, game_type, plan_type) 
            VALUES (?, ?, ?, ?, 0, 1, 0, ?, '1M', '1 Day')""",
            (user_id, user.username or "", user.first_name or "", user.last_name or "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        db.execute("INSERT INTO pending_requests (user_id, username, first_name, request_date, status) VALUES (?, ?, ?, ?, 'pending')",
                   (user_id, user.username or "", user.first_name or "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        await update.message.reply_text(f"📨 <b>Request sent to admin!</b>\n👑 Owner: {OWNER_USERNAME}", parse_mode=ParseMode.HTML)
        await self._notify_admins(user)
    
    async def _notify_admins(self, user):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_user_{user.id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_user_{user.id}")]
        ])
        for admin_id in ADMIN_IDS:
            try:
                await self.application.bot.send_message(
                    admin_id,
                    f"📨 <b>New Request!</b>\n━━━━━━━━━━━━━━━━━━━━━\n👤 {user.first_name}\n🆔 <code>{user.id}</code>\n📋 Plan: 1 Day",
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
            except: pass
    
    async def approve_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return await query.message.reply_text("❌ Unauthorized!")
        
        user_id = int(query.data.replace("approve_user_", ""))
        expiry_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        
        db.execute("""UPDATE users SET is_active=1, is_pending=0, is_banned=0, approved_by=?, approved_date=?, 
                      last_active=?, expiry_date=?, plan_type='1 Day' WHERE user_id=?""",
                   (query.from_user.id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), expiry_date, user_id))
        db.execute("UPDATE pending_requests SET status='approved' WHERE user_id=? AND status='pending'", (user_id,))
        
        await query.message.edit_text(f"✅ <b>User {user_id} approved!</b>\n📋 Plan: 1 Day\n⏰ Expires: {expiry_date}", parse_mode=ParseMode.HTML)
        
        try:
            await self.application.bot.send_message(
                user_id,
                f"✅ <b>Approved!</b>\n━━━━━━━━━━━━━━━━━━━━━\n📋 Plan: 1 Day\n⏰ Expires: {expiry_date}\n\nType /start to begin.",
                parse_mode=ParseMode.HTML
            )
        except: pass
    
    async def reject_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return await query.message.reply_text("❌ Unauthorized!")
        user_id = int(query.data.replace("reject_user_", ""))
        db.execute("UPDATE users SET is_pending=0 WHERE user_id=?", (user_id,))
        db.execute("UPDATE pending_requests SET status='rejected' WHERE user_id=? AND status='pending'", (user_id,))
        await query.message.edit_text(f"❌ User {user_id} rejected.")
    
    async def handle_keyboard_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = update.message.text
        
        if text == "🔐 Admin Panel" and user.id in ADMIN_IDS:
            await self.admin_command(update, context)
            return
        
        user_data = db.fetchone("SELECT is_active, game_type, is_banned FROM users WHERE user_id = ?", (user.id,))
        if not user_data:
            return await update.message.reply_text("❌ Please /start first.")
        
        if user_data[2] == 1:
            return await update.message.reply_text(
                f"🚫 <b>You are banned!</b>\nPlease contact admin.\n👑 {OWNER_USERNAME}",
                parse_mode=ParseMode.HTML
            )
        
        if user_data[0] == 0:
            return await update.message.reply_text("❌ Inactive. Contact owner.")
        
        if not self.check_expiry(user.id):
            return await update.message.reply_text(
                f"⏰ <b>Your plan has expired!</b>\n━━━━━━━━━━━━━━━━━━━━━\nPlease contact admin to renew.\n👑 Owner: {OWNER_USERNAME}",
                parse_mode=ParseMode.HTML
            )
        
        game_type = user_data[1] or "1M"
        
        if text == "▶️ Start Bot":
            if user.id in self.bot_tasks and not self.bot_tasks[user.id].done():
                return await update.message.reply_text("🔄 Already running!")
            db.execute("UPDATE users SET bot_running=1 WHERE user_id=?", (user.id,))
            self.bot_tasks[user.id] = asyncio.create_task(self._run_bot(user.id, game_type))
            await update.message.reply_text(f"🚀 <b>Bot started!</b>\n🎮 {GAME_TYPES[game_type]['emoji']} {GAME_TYPES[game_type]['name']}", parse_mode=ParseMode.HTML)
        elif text == "⏹️ Stop Bot":
            if user.id in self.bot_tasks:
                self.bot_tasks[user.id].cancel()
                del self.bot_tasks[user.id]
            db.execute("UPDATE users SET bot_running=0 WHERE user_id=?", (user.id,))
            await update.message.reply_text("⏹️ <b>Bot stopped!</b>", parse_mode=ParseMode.HTML)
        elif text == "🎮 Game Type":
            await update.message.reply_text("🎮 <b>Choose game:</b>", parse_mode=ParseMode.HTML, reply_markup=self.get_game_type_keyboard())
        elif text == "⚡ 1-Minute":
            await self._switch_game(update, user.id, "1M")
        elif text == "🔥 30-Second":
            await self._switch_game(update, user.id, "30S")
        elif text == "🔙 Back":
            await self._show_main_menu(update, user, game_type)
        elif text == "📊 My Stats":
            await self._show_stats(update, user.id)
    
    async def _switch_game(self, update, user_id, new_game):
        if user_id in self.bot_tasks:
            self.bot_tasks[user_id].cancel()
            del self.bot_tasks[user_id]
        db.execute("UPDATE users SET game_type=?, bot_running=0 WHERE user_id=?", (new_game, user_id))
        await update.message.reply_text(f"✅ <b>Switched to</b> {GAME_TYPES[new_game]['emoji']} {GAME_TYPES[new_game]['name']}", parse_mode=ParseMode.HTML)
    
    async def _show_stats(self, update, user_id):
        stats = db.fetchone("SELECT win_count, lose_count, total_count, current_streak, bet FROM stats WHERE user_id=?", (user_id,))
        if not stats:
            return await update.message.reply_text("📊 <b>No stats yet.</b>", parse_mode=ParseMode.HTML)
        win, lose, total, streak, bet = stats
        rate = (win / total * 100) if total > 0 else 0
        await update.message.reply_text(
            f"📊 <b>Your Statistics</b>\n━━━━━━━━━━━━━━━━━━━━━\n🏆 Wins: {win}\n💸 Losses: {lose}\n📈 Rate: {rate:.1f}%\n🔄 Streak: {streak}\n💰 Bet: {bet}×",
            parse_mode=ParseMode.HTML
        )
    
    async def _run_bot(self, user_id, game_type):
        engine = self.get_engine(user_id)
        game_info = GAME_TYPES[game_type]
        last_issue = None
        waiting = False
        pred = ""
        issue = ""
        msg_id = None
        
        while True:
            try:
                if self.is_banned(user_id):
                    db.execute("UPDATE users SET bot_running=0 WHERE user_id=?", (user_id,))
                    try:
                        await self.application.bot.send_message(user_id, "🚫 You have been banned. Bot stopped.")
                    except: pass
                    break
                
                current = get_current_issue_6lottery(game_info["type_id"])
                if not current:
                    await asyncio.sleep(1)
                    continue
                
                if waiting and current != issue:
                    number = get_result_for_issue_6lottery(game_info["type_id"], issue)
                    if number is not None:
                        is_win, actual = engine.update_result(number, pred)
                        result_data = self._format_result(issue, actual, number, is_win, engine.bet)
                        
                        if msg_id:
                            try:
                                await self.application.bot.edit_message_text(
                                    chat_id=user_id, message_id=msg_id,
                                    text=result_data["text"], parse_mode=ParseMode.HTML
                                )
                            except:
                                await self.application.bot.send_message(user_id, result_data["text"], parse_mode=ParseMode.HTML)
                        else:
                            await self.application.bot.send_message(user_id, result_data["text"], parse_mode=ParseMode.HTML)
                        
                        if is_win and result_data["sticker"]:
                            try:
                                await self.application.bot.send_sticker(chat_id=user_id, sticker=result_data["sticker"])
                            except Exception as e:
                                print(f"Sticker error: {e}")
                        
                        waiting = False
                        msg_id = None
                        last_issue = issue
                
                if current != last_issue and not waiting:
                    results = get_last_results_6lottery(game_info["type_id"], 10)
                    for n in results:
                        if n not in engine.all_numbers:
                            engine.all_numbers.appendleft(n)
                    prediction = engine.get_prediction()
                    msg = self._format_prediction(current, prediction, engine.bet)
                    sent = await self.application.bot.send_message(user_id, msg, parse_mode=ParseMode.HTML)
                    msg_id = sent.message_id
                    pred = prediction
                    issue = current
                    waiting = True
                    last_issue = current
                
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                db.execute("UPDATE users SET bot_running=0 WHERE user_id=?", (user_id,))
                break
            except Exception as e:
                print(f"Bot error: {e}")
                await asyncio.sleep(5)
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            return await update.message.reply_text("❌ Unauthorized!")
        
        pending = db.fetchone("SELECT COUNT(*) FROM pending_requests WHERE status='pending'")[0]
        total_users = db.fetchone("SELECT COUNT(*) FROM users")[0]
        active_users = db.fetchone("SELECT COUNT(*) FROM users WHERE is_active=1 AND is_banned=0")[0]
        banned_users = db.fetchone("SELECT COUNT(*) FROM users WHERE is_banned=1")[0]
        running = db.fetchone("SELECT COUNT(*) FROM users WHERE bot_running=1")[0]
        
        keyboard = [
            [InlineKeyboardButton(f"📨 Pending ({pending})", callback_data="admin_pending")],
            [InlineKeyboardButton(f"👥 All Users ({total_users})", callback_data="admin_userlist")],
            [InlineKeyboardButton(f"🟢 Active Users ({active_users})", callback_data="admin_active")],
            [InlineKeyboardButton(f"🚫 Banned Users ({banned_users})", callback_data="admin_banned")],
            [InlineKeyboardButton(f"🤖 Running Now ({running})", callback_data="admin_running")],
            [InlineKeyboardButton("📢 Broadcast to All", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📊 Stats Overview", callback_data="admin_stats")],
            [InlineKeyboardButton("📝 Recent Logs", callback_data="admin_logs")]
        ]
        
        text = (
            f"🔐 <b>Admin Panel</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 Owner: {OWNER_USERNAME}\n"
            f"👥 Total Users: {total_users}\n"
            f"🟢 Active: {active_users}\n"
            f"🚫 Banned: {banned_users}\n"
            f"🤖 Running: {running}\n"
            f"📨 Pending: {pending}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        
        if update.callback_query:
            await update.callback_query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def admin_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return await query.message.reply_text("❌ Unauthorized!")
        
        data = query.data
        
        if data == "admin_pending":
            pending = db.fetchall("SELECT user_id, first_name, username FROM pending_requests WHERE status='pending'")
            text = "📨 <b>Pending Requests</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
            if pending:
                for p in pending:
                    name = p[1] or p[2] or "Unknown"
                    text += f"• {name} | <code>{p[0]}</code>\n"
            else:
                text += "No pending requests."
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
            await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data == "admin_userlist":
            await self._show_user_list(query, filter_type="all")
        elif data == "admin_active":
            await self._show_user_list(query, filter_type="active")
        elif data == "admin_banned":
            await self._show_user_list(query, filter_type="banned")
        elif data == "admin_running":
            await self._show_user_list(query, filter_type="running")
        
        elif data == "admin_stats":
            total = db.fetchone("SELECT COUNT(*) FROM users")[0]
            active = db.fetchone("SELECT COUNT(*) FROM users WHERE is_active=1 AND is_banned=0")[0]
            banned = db.fetchone("SELECT COUNT(*) FROM users WHERE is_banned=1")[0]
            running = db.fetchone("SELECT COUNT(*) FROM users WHERE bot_running=1")[0]
            pending = db.fetchone("SELECT COUNT(*) FROM pending_requests WHERE status='pending'")[0]
            
            await query.message.edit_text(
                f"📊 <b>Stats Overview</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 Total Users: {total}\n"
                f"🟢 Active: {active}\n"
                f"🚫 Banned: {banned}\n"
                f"🤖 Running: {running}\n"
                f"📨 Pending: {pending}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]])
            )
        
        elif data == "admin_broadcast":
            await query.message.edit_text(
                "📢 <b>Broadcast Message</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
                "Usage:\n<code>/broadcast Your message here</code>\n\n"
                "This will send to all active (non-banned) users.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]])
            )
        
        elif data == "admin_logs":
            logs = db.fetchall("SELECT action, details, timestamp FROM logs ORDER BY id DESC LIMIT 15")
            text = "📝 <b>Recent Logs</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
            if logs:
                for l in logs:
                    text += f"• {l[2]} | {l[0]}\n"
            else:
                text += "No logs yet."
            await query.message.edit_text(text, parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]))
        
        elif data == "admin_back":
            await self.admin_command(update, context)
        
        elif data.startswith("ban_user_"):
            target_id = int(data.replace("ban_user_", ""))
            await self._ban_user(query, target_id)
        elif data.startswith("unban_user_"):
            target_id = int(data.replace("unban_user_", ""))
            await self._unban_user(query, target_id)
        elif data.startswith("remove_user_"):
            target_id = int(data.replace("remove_user_", ""))
            await self._remove_user_confirm(query, target_id)
        elif data.startswith("confirm_remove_"):
            target_id = int(data.replace("confirm_remove_", ""))
            await self._do_remove_user(query, target_id)
    
    async def _show_user_list(self, query, filter_type="all"):
        if filter_type == "active":
            users = db.fetchall("""
                SELECT user_id, username, first_name, is_active, is_banned, game_type, bot_running, plan_type, expiry_date
                FROM users WHERE is_active=1 AND is_banned=0
                ORDER BY last_active DESC LIMIT 40
            """)
            title = "🟢 Active Users"
        elif filter_type == "banned":
            users = db.fetchall("""
                SELECT user_id, username, first_name, is_active, is_banned, game_type, bot_running, plan_type, expiry_date
                FROM users WHERE is_banned=1
                ORDER BY registered_date DESC LIMIT 40
            """)
            title = "🚫 Banned Users"
        elif filter_type == "running":
            users = db.fetchall("""
                SELECT user_id, username, first_name, is_active, is_banned, game_type, bot_running, plan_type, expiry_date
                FROM users WHERE bot_running=1
                ORDER BY last_active DESC LIMIT 40
            """)
            title = "🤖 Currently Running"
        else:
            users = db.fetchall("""
                SELECT user_id, username, first_name, is_active, is_banned, game_type, bot_running, plan_type, expiry_date
                FROM users ORDER BY registered_date DESC LIMIT 40
            """)
            title = "👥 All Users"
        
        if not users:
            await query.message.edit_text(
                f"{title}\n━━━━━━━━━━━━━━━━━━━━━\nNo users found.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]])
            )
            return
        
        text = f"<b>{title}</b> (showing {len(users)})\n━━━━━━━━━━━━━━━━━━━━━\n"
        keyboard = []
        
        for u in users:
            user_id, username, first_name, is_active, is_banned, game_type, bot_running, plan, expiry = u
            
            if is_banned:
                status = "🚫"
            elif is_active:
                status = "🟢"
            else:
                status = "🔴"
            
            bot_icon = "🤖" if bot_running else "⏹️"
            name = first_name or "NoName"
            uname = f"@{username}" if username else "NoUsername"
            
            text += f"{status}{bot_icon} <b>{name}</b>\n"
            text += f"   🆔 <code>{user_id}</code>\n"
            text += f"   👤 {uname} | {plan}\n"
            text += f"   🎮 {game_type}\n\n"
            
            row = []
            if is_banned:
                row.append(InlineKeyboardButton(f"✅ Unban {user_id}", callback_data=f"unban_user_{user_id}"))
            else:
                row.append(InlineKeyboardButton(f"🚫 Ban {user_id}", callback_data=f"ban_user_{user_id}"))
            row.append(InlineKeyboardButton(f"❌ Del", callback_data=f"remove_user_{user_id}"))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")])
        
        if len(text) > 3800:
            text = text[:3800] + "\n... (truncated)"
        
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _ban_user(self, query, target_id):
        if target_id in ADMIN_IDS:
            await query.answer("Cannot ban admin!", show_alert=True)
            return
        
        if target_id in self.bot_tasks:
            self.bot_tasks[target_id].cancel()
            del self.bot_tasks[target_id]
        
        db.execute("UPDATE users SET is_banned=1, bot_running=0, is_active=0 WHERE user_id=?", (target_id,))
        db.execute("INSERT INTO logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                   (query.from_user.id, "BAN", f"Banned user {target_id}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        try:
            await self.application.bot.send_message(target_id, "🚫 <b>You have been banned by admin.</b>", parse_mode=ParseMode.HTML)
        except: pass
        
        await query.answer(f"User {target_id} banned!", show_alert=True)
        await self._show_user_list(query, filter_type="all")
    
    async def _unban_user(self, query, target_id):
        db.execute("UPDATE users SET is_banned=0, is_active=1 WHERE user_id=?", (target_id,))
        db.execute("INSERT INTO logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                   (query.from_user.id, "UNBAN", f"Unbanned user {target_id}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        try:
            await self.application.bot.send_message(
                target_id, 
                f"✅ <b>You have been unbanned!</b>\nType /start to continue.",
                parse_mode=ParseMode.HTML
            )
        except: pass
        
        await query.answer(f"User {target_id} unbanned!", show_alert=True)
        await self._show_user_list(query, filter_type="banned")
    
    async def _remove_user_confirm(self, query, target_id):
        user = db.fetchone("SELECT first_name, username FROM users WHERE user_id = ?", (target_id,))
        name = (user[0] or user[1] or str(target_id)) if user else str(target_id)
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_remove_{target_id}"),
             InlineKeyboardButton("❌ Cancel", callback_data="admin_userlist")]
        ]
        await query.message.edit_text(
            f"⚠️ <b>Delete user permanently?</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {name}\n🆔 <code>{target_id}</code>\n\nThis cannot be undone!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _do_remove_user(self, query, target_id):
        if target_id in self.bot_tasks:
            self.bot_tasks[target_id].cancel()
            del self.bot_tasks[target_id]
        
        db.execute("DELETE FROM users WHERE user_id = ?", (target_id,))
        db.execute("DELETE FROM stats WHERE user_id = ?", (target_id,))
        db.execute("INSERT INTO logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                   (query.from_user.id, "DELETE", f"Deleted user {target_id}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        await query.message.edit_text(f"✅ User <code>{target_id}</code> permanently deleted!", parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.5)
        await self._show_user_list(query, filter_type="all")
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            return await update.message.reply_text("❌ Unauthorized!")
        
        if not context.args:
            return await update.message.reply_text(
                "📢 <b>Broadcast</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
                "Usage: <code>/broadcast Your message here</code>",
                parse_mode=ParseMode.HTML
            )
        
        msg = ' '.join(context.args)
        users = db.fetchall("SELECT user_id FROM users WHERE is_active=1 AND is_banned=0")
        
        sent = 0
        failed = 0
        for u in users:
            try:
                await context.bot.send_message(
                    u[0],
                    f"📢 <b>Admin Notification</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n{msg}",
                    parse_mode=ParseMode.HTML
                )
                sent += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1
        
        await update.message.reply_text(
            f"✅ <b>Broadcast Complete</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Sent: {sent}\n❌ Failed: {failed}",
            parse_mode=ParseMode.HTML
        )
    
    async def addchannel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            return await update.message.reply_text("❌ Unauthorized!")
        if not context.args:
            return await update.message.reply_text("📢 Usage: <code>/addchannel -1001234567890</code>", parse_mode=ParseMode.HTML)
        channel_id = context.args[0]
        if not channel_id.startswith('-100'):
            return await update.message.reply_text("❌ Must start with -100")
        try:
            cid = int(channel_id)
            db.execute("INSERT OR REPLACE INTO channels (channel_id, channel_name, added_by, added_date, is_active) VALUES (?, ?, ?, ?, 1)",
                       (cid, "Channel", update.effective_user.id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            await update.message.reply_text(f"✅ Channel <code>{channel_id}</code> added!", parse_mode=ParseMode.HTML)
        except:
            await update.message.reply_text("❌ Invalid ID")
    
    async def error_handler(self, update, context):
        print(f"Error: {context.error}")
    
    def run(self):
        print("=" * 60)
        print("🎰 LOTTERY PRO BOT - FULL ADMIN PANEL")
        print("=" * 60)
        print(f"👑 Owner: {OWNER_USERNAME}")
        print(f"🆔 Owner ID: {OWNER_ID}")
        print("📊 Prediction: Pattern-based only")
        print("📋 Plans: 1 Day / Unlimited")
        print("📢 Win Sticker: Yes | Lose Sticker: No")
        print("🔐 Admin: Ban/Unban + Broadcast + User List")
        print("=" * 60)
        print("🚀 Bot is running...")
        print("=" * 60)
        
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("addchannel", self.addchannel_command))
        self.application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        
        self.application.add_handler(CallbackQueryHandler(self.admin_callback_handler, pattern="^admin_"))
        self.application.add_handler(CallbackQueryHandler(self.approve_user, pattern="^approve_user_"))
        self.application.add_handler(CallbackQueryHandler(self.reject_user, pattern="^reject_user_"))
        self.application.add_handler(CallbackQueryHandler(self.admin_callback_handler, pattern="^(ban_user_|unban_user_|remove_user_|confirm_remove_)"))
        
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_keyboard_input))
        self.application.add_error_handler(self.error_handler)
        
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = BotHandlers()
    bot.run()

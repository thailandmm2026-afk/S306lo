# 🎰 Lottery Pro Bot

Telegram Lottery Prediction Bot with full Admin Panel.

## Features
- 1-Minute & 30-Second games
- Pattern-based prediction
- User expiry system (1 Day / Unlimited)
- Win sticker
- Full Admin Panel (Ban/Unban, User List, Broadcast)

## Deploy on Railway / Render

### 1. Required Environment Variables

Go to your Railway/Render dashboard → Variables and add:

| Variable        | Example Value              | Required |
|-----------------|----------------------------|----------|
| `BOT_TOKEN`     | `8707027344:AAF...`        | ✅ Yes   |
| `OWNER_ID`      | `7308292609`               | ✅ Yes   |
| `OWNER_USERNAME`| `@kiki20251`               | ✅ Yes   |
| `ADMIN_IDS`     | `7308292609`               | ✅ Yes   |

> Multiple admins: `ADMIN_IDS=7308292609,123456789`

### 2. Railway Deploy Steps

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select the repository
4. Add the Environment Variables above
5. Set **Start Command**:
   ```
   python lottery_pro_bot.py
   ```
6. Deploy

### 3. Render Deploy Steps

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Background Worker
3. Connect the repository
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `python lottery_pro_bot.py`
6. Add Environment Variables
7. Deploy

## Local Run

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values
python lottery_pro_bot.py
```

## Admin Commands

- `/admin` or press **🔐 Admin Panel**
- `/broadcast Your message`
- `/addchannel -100xxxxxxxxxx`

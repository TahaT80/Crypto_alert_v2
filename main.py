import asyncio
import json
import os
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests

# تنظیمات
TELEGRAM_TOKEN = "XXXXXXXXXX:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # توکن تلگرام خود را اینجا قرار دهید
ALERTS_FILE = "alerts.json"
sent_alerts = set()

# بارگذاری هشدارها
def load_alerts():
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, "r") as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
            except:
                pass
    return {}

# ذخیره هشدارها
def save_alerts(data):
    with open(ALERTS_FILE, "w") as f:
        json.dump(data, f)

# گرفتن قیمت
def get_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        return float(res.json()["price"])
    except:
        return None

# دستورات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"سلام! Chat ID شما: `{update.effective_chat.id}`", parse_mode="Markdown")

async def add_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("فرمت: /add SYMBOL TARGET D|U")
        return
    symbol, target_str, direction = args
    try:
        target = float(target_str)
    except:
        await update.message.reply_text("قیمت نامعتبر.")
        return
    direction = direction.upper()
    if direction not in ["U", "D"]:
        await update.message.reply_text('باید جهت "U" یا "D" باشد.')
        return
    alerts = load_alerts()
    alerts.setdefault(chat_id, [])
    new_id = max([a["ID"] for a in alerts[chat_id]], default=0) + 1
    alerts[chat_id].append({"ID": new_id, "symbol": symbol.upper(), "target": target, "Goal": direction})
    save_alerts(alerts)
    await update.message.reply_text("✅ هشدار افزوده شد.")

async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    alerts = load_alerts()
    if chat_id not in alerts or not alerts[chat_id]:
        await update.message.reply_text("هیچ هشداری ثبت نشده.")
        return
    msg = "📋 هشدارهای شما:\n"
    for a in alerts[chat_id]:
        arrow = "⬆️" if a["Goal"] == "U" else "⬇️"
        msg += f"{a['ID']}. {a['symbol']} {a['target']} {arrow}\n"
    await update.message.reply_text(msg)

async def delete_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("فرمت: /delete ID")
        return
    del_id = int(args[0])
    alerts = load_alerts()
    if chat_id in alerts:
        alerts[chat_id] = [a for a in alerts[chat_id] if a["ID"] != del_id]
        save_alerts(alerts)
        await update.message.reply_text("✅ هشدار حذف شد.")
    else:
        await update.message.reply_text("هیچ هشداری یافت نشد.")

# بررسی هشدارها
async def check_alerts(bot: Bot):
    while True:
        alerts = load_alerts()
        updated_alerts = {}

        for chat_id, user_alerts in alerts.items():
            remaining_alerts = []
            for alert in user_alerts:
                price = get_price(alert["symbol"])
                if price is None:
                    remaining_alerts.append(alert)
                    continue

                condition = (alert["Goal"] == "U" and price >= alert["target"]) or \
                            (alert["Goal"] == "D" and price <= alert["target"])

                if condition:
                    msg = f"🎯 {alert['symbol']} رسید به {price} (هدف: {alert['target']})"
                    await bot.send_message(chat_id=int(chat_id), text=msg)
                    # هشدار فرستاده شد و حذف میشه
                else:
                    remaining_alerts.append(alert)  # هشدار هنوز معتبره

            if remaining_alerts:
                updated_alerts[chat_id] = remaining_alerts

        save_alerts(updated_alerts)
        await asyncio.sleep(15)

# اجرای اصلی بدون asyncio.run()
def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_alert))
    app.add_handler(CommandHandler("list", list_alerts))
    app.add_handler(CommandHandler("delete", delete_alert))

    # شروع تسک هشدارها
    app.job_queue.run_once(lambda _: asyncio.create_task(check_alerts(bot)), 0)
    app.run_polling()

if __name__ == "__main__":
    main()

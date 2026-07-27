import os
import threading
import psycopg2
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask
import telebot
from telebot import types

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

if not TOKEN or not DB_URL:
    raise ValueError("Помилка: відсутній BOT_TOKEN або DATABASE_URL у змінних оточення!")

bot = telebot.TeleBot(TOKEN)

def get_db_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    amount FLOAT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
init_db()

def save_to_db(user_id, amount, desc):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO expenses(user_id, amount, description) VALUES (%s, %s, %s)",
                (user_id, amount, desc)
            )

def read_monthly_stats(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT amount, description, created_at
                FROM expenses 
                WHERE user_id = %s
                  AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                ORDER BY created_at DESC
            """, (user_id,))
            rows = cur.fetchall()
            return [{'amount': row[0], 'desc': row[1], 'date': row[2]} for row in rows]

def generate_chart(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT description, SUM(ABS(amount))
                FROM expenses
                WHERE user_id = %s
                  AND amount < 0
                  AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                GROUP BY description
            """, (user_id,))
            rows = cur.fetchall()

    if not rows:
        return None

    categories = [row[0] for row in rows]
    amounts = [row[1] for row in rows]

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        amounts,
        labels=categories,
        autopct='%1.1f%%',
        startangle=140,
        colors=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c1f0', '#ffb3e6']
    )
    ax.axis('equal')
    plt.title("Розподіл витрат за цей місяць", fontsize=14)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    return buf

@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda message: message.text == "🏠/start")
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("🏠/start"),
        types.KeyboardButton("📊 /stats"),
        types.KeyboardButton("📈 /chart"),
        types.KeyboardButton("🗑 /clear")
    )
    bot.send_message(
        message.chat.id,
        "💰 **Бот-баланс готовий!**\n\nПросто пиши суму та опис:\n`+1000 зарплата` або `-50 кава`",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text in ["📊 /stats", "/stats"])
def show_stats(message):
    this_month_data = read_monthly_stats(message.chat.id)
    if not this_month_data:
        bot.send_message(message.chat.id, "📅 У цьому місяці записів ще немає.")
        return

    now = datetime.now()
    months_ua = {
        1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
        5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
        9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень"
    }

    income = sum(item['amount'] for item in this_month_data if item['amount'] > 0)
    expenses = sum(item['amount'] for item in this_month_data if item['amount'] < 0)
    balance = income + expenses

    report_lines = []
    for item in this_month_data:
        sign = "🟢" if item['amount'] > 0 else "🔴"
        day_month = item['date'].strftime("%d.%m")
        report_lines.append(f"`{day_month}` {sign} {item['amount']} zl - {item['desc']}")

    full_report = "\n".join(report_lines)

    response = (f"📅 **Звіт за {months_ua[now.month]} {now.year}**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{full_report}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"➕ Доходи:  `+{income} zl`\n"
                f"➖ Витрати: `{expenses} zl`\n"
                f"⚖️ Залишок: **{balance} zl**")

    bot.send_message(message.chat.id, response, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text in ["📈 /chart", "/chart"])
def show_chart(message):
    chart_buf = generate_chart(message.chat.id)
    if chart_buf:
        bot.send_photo(message.chat.id, chart_buf, caption="📊 Твої витрати за категоріями")
    else:
        bot.send_message(message.chat.id, "📊 У цьому місяці ще немає витрат для побудови графіка!")

@bot.message_handler(commands=['clear'])
@bot.message_handler(func=lambda message: message.text == "🗑 /clear")
def clear_stats(message):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM expenses WHERE user_id = %s", (message.chat.id,))
    bot.send_message(message.chat.id, "🗑 Історію очищено.")

@bot.message_handler(func=lambda message: True)
def add_expense(message):
    if message.text in ["📊 /stats", "🗑 /clear", "🏠/start", "📈 /chart"]:
        return
    try:
        parts = message.text.strip().split(maxsplit=1)
        amount = float(parts[0].replace(',', '.'))
        description = parts[1] if len(parts) > 1 else "без опису"

        save_to_db(message.chat.id, amount, description)
        status = "✅ Дохід" if amount > 0 else "📉 Витрата"
        bot.send_message(message.chat.id, f"{status} додано!")

    except Exception:
        bot.send_message(message.chat.id, "❌ Помилка! Пиши: сума опис (напр. -100 обід)")

if __name__ == "__main__":
    bot.delete_webhook(drop_pending_updates=True)
    bot.polling(none_stop=True)

import telebot
import os
import psycopg2
from datetime import datetime
from telebot import types

DB_URL = "postgresql://money_db_ujl7_user:Qncte8lVtEfZbNNwcheGMaLKMQ3fpkYd@dpg-d7vss4po3t8c73d8c2n0-a/money_db_ujl7"

Token = '8286392310:AAFQQn1EC7458k47BMhuGCnSvK8pQ7I-Mf0'
bot = telebot.TeleBot(Token)

def get_db_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
            """
        CREATE TABLE IF NOT EXISTS expenses
        (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            amount FLOAT,
            description TEXT,
            date_now TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

def save_to_db(user_id, amount, desc):
    conn = get_db_connection()
    cur = conn.cursor()
    date_now = datetime.now().strftime("%d.%m.%Y %H:%M")
    cur.execute("INSERT INTO expenses (user_id, amount, description, date_now) VALUES (%s, %s, %s, %s)",
                (user_id, amount, desc, date_now))
    conn.commit()
    cur.close()
    conn.close()

def read_status(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT amount, description, date_now FROM expenses WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    user_expenses = []
    for row in rows:
        user_expenses.append({
            'amount': row[0],
            'desc': row[1],
            'date': row[2]
        })
    return user_expenses

@bot.message_handler(commands=['start'])
def start(message):

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_stats = types.KeyboardButton("📊 /stats")
    btn_clear = types.KeyboardButton("🗑 /clear")
    btn_start = types.KeyboardButton("🏠/start")
    markup.add(btn_start, btn_stats, btn_clear)

    bot.send_message(message.chat.id, "Оновлено!", reply_markup=markup)
    
    bot.send_message(message.chat.id,
                     "💰 **Бот-баланс готовий!**\n\n"
                     "Просто пиши суму та опис, наприклад:\n"
                     "`+1000 зарплата` або `-50 кава`",
                     reply_markup=markup,
                     parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
@bot.message_handler(func=lambda message: message.text == "📊 /stats")
def show_stats(message):
    data = read_status(message.chat.id)
    if not data:
        bot.send_message(message.chat.id, "Історія порожня")
        return

    now = datetime.now()

    months_ua ={
        1: "Січень", 2: "Лютий", 3:"Березень", 4: "Квітень",
        5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
        9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень",
    }
    month_name = months_ua[now.month]
    year = now.year

    current_month_year = now.strftime(".%m.%Y")
    this_month_data = [item for item in data if current_month_year in item['date']]

    if not this_month_data:
        bot.send_message(message.chat.id, f"📅 У місяці **{now.strftime('%B')}** записів ще немає.")
        return

    income = sum(item['amount'] for item in data if item['amount'] > 0)
    expenses = sum(item['amount'] for item in data if item['amount'] < 0)
    balance = income + expenses

    report_lines = []
    for item in this_month_data:
        sign = "🟢" if item['amount'] > 0 else "🔴"
        day_month = item['date'][:5]
        report_lines.append(f"`{day_month}` {sign} {item['amount']} zl - {item['desc']}")

    full_report = "\n".join(report_lines)

    response = (f"📅 **Звіт за {month_name} {year}**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{full_report}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"➕ Доходи:  `+{income} zl`\n"
                f"➖ Витрати: `{expenses} zl`\n"
                f"⚖️ Залишок: **{balance} zl**")

    bot.send_message(message.chat.id, response, parse_mode='Markdown')

@bot.message_handler(commands=['clear'])
@bot.message_handler(func=lambda message: message.text == "🗑 /clear")
def clear_stats(message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE user_id = %s", (message.chat.id,))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, "🗑 Історію очищено.")

@bot.message_handler(func=lambda message: True)
def add_expense(message):
    if message.text in ["📊 /stats", "🗑 /clear"]:
        return
    try:
        parts = message.text.strip().split(maxsplit=1)
        amount = float(parts[0].replace(',', '.'))
        description = parts[1] if len(parts) > 1 else "без опису"

        save_to_db(message.chat.id, amount, description)

        status = "✅ Дохід" if amount > 0 else "📉 Витрата"
        bot.send_message(message.chat.id, f"{status} додано!")

    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, "❌ Помилка! Пиши: сума опис напр. -100 обід)")

if __name__ == "__main__":
    bot.remove_webhook(drop_pending_updates=True)
    bot.polling(none_stop=True)
import telebot
import os
import http.server
import socketserver
import threading
import psycopg2
from datetime import datetime
from telebot import types

def run_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_server, daemon=True).start()
DB_URL = "postgresql://money_db_ujl7_user:Qncte8lVtEfZbNNwcheGMaLKMQ3fpkYd@dpg-d7vss4po3t8c73d8c2n0-a/money_db_ujl7"

Token = '8286392310:AAFQQn1EC7458k47BMhuGCnSvK8pQ7I-Mf0'
bot = telebot.TeleBot(Token)

def save_to_file(user_id, amount, desc):
    with open("expenses.txt", "a", encoding="utf-8") as file:
        date_now = datetime.now().strftime("%d.%m.%Y %H.%M")
        file.write(f"{user_id}|{amount}|{desc}|{date_now}\n")
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
    if not os.path.exists("expenses.txt"):
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT amount, description, date_now FROM expenses WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    user_expenses = []
    with open("expenses.txt", "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split("|")
            if len(parts) == 4 and int(parts[0]) == user_id:
                user_expenses.append({
                    'amount': float(parts[1]),
                    'desc': parts[2],
                    'date': parts[3]
                })
    for row in rows:
        user_expenses.append({
            'amount': row[0],
            'desc': row[1],
            'date': row[2]
        })
    return user_expenses

@bot.message_handler(commands=['start'])
@ -43,8 +65,11 @ def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_stats = types.KeyboardButton("📊 /stats")
    btn_clear = types.KeyboardButton("🗑 /clear")
    markup.add(btn_stats, btn_clear)
    btn_start = types.KeyboardButton("🏠/start")
    markup.add(btn_start, btn_stats, btn_clear)

    bot.send_message(message.chat.id, "Оновлено!", reply_markup=markup)
    
    bot.send_message(message.chat.id,
                     "💰 **Бот-баланс готовий!**\n\n"
                     "Просто пиши суму та опис, наприклад:\n"
@ -102,8 +127,12 @ def show_stats(message):
@bot.message_handler(commands=['clear'])
@bot.message_handler(func=lambda message: message.text == "🗑 /clear")
def clear_stats(message):
    if os.path.exists("expenses.txt"):
        os.remove("expenses.txt")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE user_id = %s", (message.chat.id,))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, "🗑 Історію очищено.")

@bot.message_handler(func=lambda message: True)
@ -115,7 +144,7 @ def add_expense(message):
        amount = float(parts[0].replace(',', '.'))
        description = parts[1] if len(parts) > 1 else "без опису"

        save_to_file(message.chat.id, amount, description)
        save_to_db(message.chat.id, amount, description)

        status = "✅ Дохід" if amount > 0 else "📉 Витрата"
        bot.send_message(message.chat.id, f"{status} додано!")
@ -125,4 +154,5 @ def add_expense(message):
        bot.send_message(message.chat.id, "❌ Помилка! Пиши: сума опис напр. -100 обід)")

if __name__ == "__main__":
    bot.remove_webhook(drop_pending_updates=True)
    bot.polling(none_stop=True)

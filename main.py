import telebot
import os
from datetime import datetime
from telebot import types

Token = '8286392310:AAFQQn1EC7458k47BMhuGCnSvK8pQ7I-Mf0'
bot = telebot.TeleBot(Token)

def save_to_file(user_id, amount, desc):
    with open("expenses.txt", "a", encoding="utf-8") as file:
        date_now = datetime.now().strftime("%d.%m.%Y %H.%M")
        file.write(f"{user_id}|{amount}|{desc}|{date_now}\n")

def read_status(user_id):
    if not os.path.exists("expenses.txt"):
        return []
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
    return user_expenses

@bot.message_handler(commands=['start'])
def start(message):

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_stats = types.KeyboardButton("📊 /stats")
    btn_clear = types.KeyboardButton("🗑 /clear")
    markup.add(btn_stats, btn_clear)

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
    if os.path.exists("expenses.txt"):
        os.remove("expenses.txt")
    bot.send_message(message.chat.id, "🗑 Історію очищено.")

@bot.message_handler(func=lambda message: True)
def add_expense(message):
    if message.text in ["📊 /stats", "🗑 /clear"]:
        return
    try:
        parts = message.text.strip().split(maxsplit=1)
        amount = float(parts[0].replace(',', '.'))
        description = parts[1] if len(parts) > 1 else "без опису"

        save_to_file(message.chat.id, amount, description)

        status = "✅ Дохід" if amount > 0 else "📉 Витрата"
        bot.send_message(message.chat.id, f"{status} додано!")

    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, "❌ Помилка! Пиши: сума опис напр. -100 обід)")

if __name__ == "__main__":
    bot.polling(none_stop=True)
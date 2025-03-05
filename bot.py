import os
import telebot
from telebot import types
from dotenv import load_dotenv
from pycoingecko import CoinGeckoAPI
from apscheduler.schedulers.background import BackgroundScheduler

cg = CoinGeckoAPI()

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)


def check_price(coin_id):
    try:
        price = cg.get_price(ids=coin_id, vs_currencies='usd')
        return price[coin_id]['usd']
    except Exception as e:
        return None


def track_price(coin_id, margin):
    try:
        price = cg.get_price(ids=coin_id, vs_currencies='usd')
        current_price = price[coin_id]['usd']
        return current_price == margin
    except Exception as e:
        return False


@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "👋 Hello! Welcome to my Crypto Price Tracker!")


@bot.message_handler(commands=['check_price'])
def check_price_handler(message):
    text = "Which coin price do you want to know?"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

    markup = types.InlineKeyboardMarkup(row_width=2)

    coins = ["bitcoin", "ethereum", "solana", "tron", "binancecoin", "dogecoin", "litecoin", "ripple"]
    buttons = [types.InlineKeyboardButton(coin.capitalize(), callback_data=f"check_{coin}") for coin in coins]
    markup.add(*buttons)

    bot.send_message(message.chat.id, "Select a cryptocurrency:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def get_price(call):
    needed_coin = call.data.replace("check_", "")
    price = check_price(needed_coin)
    if price:
        result_message = f"The price of {needed_coin} is ${price}"
    else:
        result_message = f"❌ Could not retrieve the price of {needed_coin}. Please try again later."
    bot.send_message(call.message.chat.id, result_message, parse_mode="Markdown")


@bot.message_handler(commands=['track_price'])
def track_price_handler(message):
    text = "Which coin do you want to track?"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

    # Create an inline keyboard with cryptocurrency options
    markup = types.InlineKeyboardMarkup(row_width=2)
    coins = ["bitcoin", "ethereum", "solana", "tron", "binancecoin", "dogecoin", "litecoin", "ripple"]
    buttons = [types.InlineKeyboardButton(coin.capitalize(), callback_data=f"track_{coin}") for coin in coins]
    markup.add(*buttons)

    # Send the keyboard to the user
    bot.send_message(message.chat.id, "Select a cryptocurrency:", reply_markup=markup)


scheduler = BackgroundScheduler()
scheduler.start()

# Dictionary to store user thresholds
user_thresholds = {}

def check_thresholds():
    for user_id, data in user_thresholds.items():
        coin = data['coin']
        threshold = data['threshold']
        if track_price(coin, threshold):
            bot.send_message(user_id, f"🚨 Alert! {coin} price has exceeded ${threshold}!")

# Schedule the function to run every minute
scheduler.add_job(check_thresholds, 'interval', minutes=10)

@bot.callback_query_handler(func=lambda call: call.data.startswith("track_"))
def set_threshold(call):
    needed_coin = call.data.replace("track_", "")
    text = f"What is the threshold price for {needed_coin}?"
    sent_msg = bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    # Register the next step handler to pass the coin and user input to the `track` function
    bot.register_next_step_handler(sent_msg, lambda msg: track(msg, needed_coin, call.from_user.id))

def track(message, coin, user_id):
    try:
        price_limit = float(message.text.strip())
        user_thresholds[user_id] = {'coin': coin, 'threshold': price_limit}
        result_message = f"✅ Tracking {coin} for price ${price_limit}"
    except ValueError:
        result_message = "❌ Invalid input. Please enter a valid number for the threshold."
    bot.send_message(message.chat.id, result_message, parse_mode="Markdown")


import atexit
atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    print("🤖 Bot is running...")
    bot.polling()
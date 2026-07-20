import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8845512776:AAHDjlsoXLmdmi9TVRYc5DOjrvj1hxIYzow"
bot = telebot.TeleBot(BOT_TOKEN)

# ساختار هر بازی
# { msg_id: { 'hand1': [], 'hand2': [], 'turn': player1, 'last_claim': None, 'pile': [] } }
games = {}

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    # لاجیک کلیک‌ها:
    # 1. اگر کاربر کارت انتخاب کرد، لیست موقت انتخاب‌ها پر شود.
    # 2. وقتی دکمه "تایید پرتاب" را زد، از او بپرسد "چه چیزی ادعا می‌کنی؟" (با منوی ادعا)
    # 3. بعد از انتخاب ادعا، کارت‌ها به pile اضافه شود و نوبت عوض شود.
    # 4. دکمه "بلوف" فقط برای حریف در دور بعدی فعال باشد.
    pass

# منطق اصلی برای زمانی که کسی ادعای بلوف می‌کند:
def check_bluff(game, caller_id):
    # کارت‌های ریخته شده در آخرین نوبت را بررسی می‌کند:
    # اگر ادعا "شاه" بوده و کارت‌های انداخته شده "بیبی" بودند -> بلوف تایید می‌شود.
    # اگر کارت‌ها واقعاً "شاه" بودند -> مچ‌گیر جریمه می‌شود.
    pass

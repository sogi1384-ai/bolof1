import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputTextMessageContent

BOT_TOKEN = "8845512776:AAHDjlsoXLmdmi9TVRYc5DOjrvj1hxIYzow"
bot = telebot.TeleBot(BOT_TOKEN)

# دیتای موقت بازی
games = {}

def get_hand_text(hand):
    return "  ".join([f"{i+1}:{c['display']}" for i, c in enumerate(hand)])

def build_game_keyboard(game, player_id):
    is_p1 = (player_id == game['player1'])
    hand = game['hand1'] if is_p1 else game['hand2']
    selected = game['selected_1'] if is_p1 else game['selected_2']
    
    markup = InlineKeyboardMarkup(row_width=4)
    
    # دکمه نمایش کارت‌ها (اگر در حالت نمایش هستیم)
    if game.get('show_hand', False):
        for i, card in enumerate(hand):
            status = "✅" if i in selected else "🂠"
            markup.add(InlineKeyboardButton(f"{status} {card['display']}", callback_data=f"sel_{i}"))
        markup.add(InlineKeyboardButton("🚀 پرتاب کارت‌های انتخاب شده", callback_data="play_cards"))
        markup.add(InlineKeyboardButton("❌ بستن دست", callback_data="hide_hand"))
    else:
        markup.add(InlineKeyboardButton("👁 مشاهده دست من", callback_data="show_hand"))
        markup.add(InlineKeyboardButton("🚨 بلوف!", callback_data="bluff"))
        markup.add(InlineKeyboardButton("💤 پاس", callback_data="pass"))
    
    return markup

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    msg_id = call.inline_message_id
    if msg_id not in games: return
    game = games[msg_id]
    
    data = call.data
    p_id = call.from_user.id
    
    if data == "show_hand":
        game['show_hand'] = True
    elif data == "hide_hand":
        game['show_hand'] = False
    elif data.startswith("sel_"):
        idx = int(data.split("_")[1])
        selected = game['selected_1'] if p_id == game['player1'] else game['selected_2']
        if idx in selected: selected.remove(idx)
        else: selected.append(idx)
    
    # ویرایش پیام برای نمایش تغییرات
    bot.edit_message_reply_markup(inline_message_id=msg_id, reply_markup=build_game_keyboard(game, p_id))
    bot.answer_callback_query(call.id)

# ... سایر بخش‌های لاجیک بازی را اینجا اضافه کنید ...

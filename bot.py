import telebot
from telebot.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle, InlineKeyboardMarkup, InlineKeyboardButton
import random
import os
from flask import Flask
from threading import Thread

BOT_TOKEN = "8845512776:AAHDjlsoXLmdmi9TVRYc5DOjrvj1hxIYzow"
bot = telebot.TeleBot(BOT_TOKEN)
games = {}

SUITS = ['♠️', '♥️', '♦️', '♣️']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

def create_deck():
    deck = []
    for r in RANKS:
        for s in SUITS:
            deck.append(f"{s}{r}")
    random.shuffle(deck)
    return deck

def get_game_keyboard(game):
    markup = InlineKeyboardMarkup(row_width=4)
    btn_hand = InlineKeyboardButton("🃏 دیدن دست من", callback_data="action_see_hand")
    btn_bluff = InlineKeyboardButton("🚫 بلوف!", callback_data="action_call_bluff")
    markup.add(btn_hand, btn_bluff)
    
    card_buttons = []
    current_player_hand = game['hand1'] if game['turn'] == game['player1'] else game['hand2']
    for i in range(len(current_player_hand)):
        card_buttons.append(InlineKeyboardButton(f"{i+1}", callback_data=f"play_{i}"))
    markup.add(*card_buttons)
    return markup

@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    try:
        switch_btn = InlineQueryResultArticle(
            id='1',
            title="🎮 شروع بازی دونفره بلوف",
            description="برای دعوت دوستت به بازی کلیک کن",
            input_message_content=InputTextMessageContent(
                message_text="🃏 **بازی دونفره بلوف!**\n\nمنتظر بازیکن دوم..."
            ),
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🤝 ورود به بازی", callback_data="game_join")
            )
        )
        bot.answer_inline_query(inline_query.id, [switch_btn], cache_time=1)
    except Exception as e:
        print(f"Error: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    try:
        msg_id = call.inline_message_id
        user_id = call.from_user.id
        user_name = call.from_user.first_name

        if call.data == "game_join":
            if msg_id not in games:
                games[msg_id] = {
                    'player1': user_id, 'player1_name': user_name,
                    'player2': None, 'player2_name': '',
                    'hand1': [], 'hand2': [],
                    'pile': [], 'last_claim': None, 'last_player': None,
                    'turn': None, 'status': 'waiting'
                }
                bot.answer_callback_query(call.id, "شما اتاق بازی را ساختید. منتظر دوستتان بمانید.", show_alert=True)
                return
            
            game = games[msg_id]
            if game['player1'] == user_id:
                bot.answer_callback_query(call.id, "شما خودتان بازیکن اول هستید!", show_alert=True)
                return
            
            if game['player2'] is None:
                game['player2'] = user_id
                game['player2_name'] = user_name
                game['status'] = 'playing'
                
                deck = create_deck()
                game['hand1'] = deck[:10]
                game['hand2'] = deck[10:20]
                game['turn'] = game['player1']
                
                text = f"🎮 **بازی شروع شد!**\n\n👤 بازیکن اول: {game['player1_name']}\n👤 بازیکن دوم: {game['player2_name']}\n\n🟢 نوبت: {game['player1_name']}\n📥 کارت‌های روی میز: ۰"
                bot.edit_message_text(text, inline_message_id=msg_id, reply_markup=get_game_keyboard(game))
                bot.answer_callback_query(call.id, "شما وارد بازی شدید!")

        if msg_id not in games or games[msg_id]['status'] != 'playing':
            return

        game = games[msg_id]

        if call.data == "action_see_hand":
            if user_id == game['player1']:
                hand_str = " . ".join([f"{i+1}: {c}" for i, c in enumerate(game['hand1'])])
                bot.answer_callback_query(call.id, f"📥 دست شما:\n{hand_str}", show_alert=True)
            elif user_id == game['player2']:
                hand_str = " . ".join([f"{i+1}: {c}" for i, c in enumerate(game['hand2'])])
                bot.answer_callback_query(call.id, f"📥 دست شما:\n{hand_str}", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "شما تماشاچی هستید!", show_alert=True)

        elif call.data.startswith("play_"):
            if user_id != game['turn']:
                bot.answer_callback_query(call.id, "نوبت شما نیست!", show_alert=True)
                return
            
            card_idx = int(call.data.split("_")[1])
            current_hand = game['hand1'] if user_id == game['player1'] else game['hand2']
            
            if card_idx >= len(current_hand):
                return
            
            played_card = current_hand.pop(card_idx)
            game['pile'].append(played_card)
            
            card_rank = played_card[2:]
            game['last_claim'] = card_rank
            game['last_player'] = user_id
            
            if len(current_hand) == 0:
                winner_name = game['player1_name'] if user_id == game['player1'] else game['player2_name']
                bot.edit_message_text(f"🏆 **{winner_name} برنده بازی شد!**\nتمام کارت‌هایش تمام شد.", inline_message_id=msg_id)
                del games[msg_id]
                return

            game['turn'] = game['player2'] if user_id == game['player1'] else game['player1']
            next_name = game['player2_name'] if game['turn'] == game['player2'] else game['player1_name']
            text = f"🂠 **کارت گذاشته شد!**\n\n👤 آخرین حرکت: {user_name} یک کارت گذاشت وسط.\n📢 ادعا: کارت رتبه [{card_rank}] است!\n\n🟢 نوبت: {next_name}\n📥 مجموع کارت‌های روی میز: {len(game['pile'])} تا"
            bot.edit_message_text(text, inline_message_id=msg_id, reply_markup=get_game_keyboard(game))

        elif call.data == "action_call_bluff":
            if game['last_player'] is None:
                bot.answer_callback_query(call.id, "هنوز کارتی روی میز نیست!", show_alert=True)
                return
            if user_id == game['last_player']:
                bot.answer_callback_query(call.id, "نمی‌توانید روی کارت خودتان بلوف بزنید!", show_alert=True)
                return
            
            last_card = game['pile'][-1]
            last_card_rank = last_card[2:]
            
            is_bluff = last_card_rank != game['last_claim']
            all_pile = game['pile'].copy()
            game['pile'] = []
            
            loser_id = game['last_player'] if is_bluff else user_id
            loser_name = game['player1_name'] if loser_id == game['player1'] else game['player2_name']
            
            if loser_id == game['player1']:
                game['hand1'].extend(all_pile)
            else:
                game['hand2'].extend(all_pile)
                
            result_text = "🎭 **بلوف بود!**" if is_bluff else "✅ **راست می‌گفت!**"
            detail_text = f"کارت واقعی {last_card} بود. {loser_name} جریمه شد و تمام {len(all_pile)} کارت روی میز را برداشت!"
            
            game['turn'] = user_id if is_bluff else game['last_player']
            next_name = game['player1_name'] if game['turn'] == game['player1'] else game['player2_name']
            
            game['last_player'] = None
            game['last_claim'] = None
            
            text = f"{result_text}\n🔍 {detail_text}\n\n🟢 نوبت جدید: {next_name}\n📥 کارت‌های روی میز: ۰"
            bot.edit_message_text(text, inline_message_id=msg_id, reply_markup=get_game_keyboard(game))
    except Exception as e:
        print(f"Error: {e}")

app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def run_bot():
    print("Bot started...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)

if __name__ == "__main__":
    t = Thread(target=run_web_server)
    t.start()
    run_bot()

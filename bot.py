import telebot
from telebot.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle, InlineKeyboardMarkup, InlineKeyboardButton
import random
import os
from flask import Flask
from threading import Thread

# --- تنظیمات اصلی ربات ---
BOT_TOKEN = "8845512776:AAHDjlsoXLmdmi9TVRYc5DOjrvj1hxIYzow"  # توکن ربات خود را اینجا بگذارید
bot = telebot.TeleBot(BOT_TOKEN)

# دیتابیس حافظه‌ای بازی‌ها
games = {}

SUITS = ['♠️', '♥️', '♦️', '♣️']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
RANK_NAMES = {
    'A': 'تک (A)', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶',
    '7': '۷', '8': '۸', '9': '۹', '10': '۱۰', 'J': 'سرباز (J)', 'Q': 'بی‌بی (Q)', 'K': 'شاه (K)'
}

def create_deck():
    deck = []
    for r in RANKS:
        for s in SUITS:
            deck.append({'suit': s, 'rank': r, 'display': f"{s}{r}"})
    random.shuffle(deck)
    return deck

def build_keyboard(game, user_id):
    markup = InlineKeyboardMarkup(row_width=4)
    is_turn = (user_id == game['turn'])
    
    # دکمه مشاهده دست
    btn_hand = InlineKeyboardButton("🃏 مشاهده کارت‌های من", callback_data="view_hand")
    btn_bluff = InlineKeyboardButton("🚫 بلوف! (افشای کارت‌ها)", callback_data="call_bluff")
    markup.add(btn_hand)
    
    if len(game['pile']) > 0 and user_id != game['last_player']:
        markup.add(btn_bluff)
        
    if is_turn:
        current_hand = game['hand1'] if user_id == game['player1'] else game['hand2']
        selected = game['selected_1'] if user_id == game['player1'] else game['selected_2']
        
        # دکمه‌های کارت‌ها جهت انتخاب
        card_btns = []
        for idx in range(len(current_hand)):
            icon = "✅" if idx in selected else "🂠"
            card_btns.append(InlineKeyboardButton(f"{icon} کارت {idx+1}", callback_data=f"toggle_{idx}"))
        
        # افزودن دکمه کارت‌ها در ردیف‌های ۴ تایی
        for i in range(0, len(card_btns), 4):
            markup.add(*card_btns[i:i+4])
            
        # دکمه‌های تعیین ادعا و بازی کردن
        if len(selected) > 0:
            claim_rank = game['claim_rank'] or 'A'
            btn_claim = InlineKeyboardButton(f"⚙️ ادعا: [{RANK_NAMES[claim_rank]}] (تغییر)", callback_data="change_claim")
            btn_play = InlineKeyboardButton(f"🚀 بازی کردن ({len(selected)} کارت)", callback_data="play_selected")
            markup.add(btn_claim)
            markup.add(btn_play)
            
    return markup

@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    try:
        switch_btn = InlineQueryResultArticle(
            id='1',
            title="🎮 شروع بازی حرفه‌ای بلوف (دونفره)",
            description="برای دعوت دوستت به کلیک کن!",
            input_message_content=InputTextMessageContent(
                message_text="🃏 **اتاق بازی بلوف ساخته شد!**\n\nبرای شروع بازی، دوستتان باید روی دکمه زیر کلیک کند."
            ),
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🤝 ورود و شروع بازی", callback_data="game_join")
            )
        )
        bot.answer_inline_query(inline_query.id, [switch_btn], cache_time=1)
    except Exception as e:
        print(f"Inline Error: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    try:
        msg_id = call.inline_message_id
        user_id = call.from_user.id
        user_name = call.from_user.first_name

        # --- ۱. ورود به بازی ---
        if call.data == "game_join":
            if msg_id not in games:
                games[msg_id] = {
                    'player1': user_id, 'player1_name': user_name,
                    'player2': None, 'player2_name': '',
                    'hand1': [], 'hand2': [],
                    'selected_1': [], 'selected_2': [],
                    'pile': [], 'last_cards': [], 'last_claim': None, 'last_player': None,
                    'turn': None, 'claim_rank': 'A', 'status': 'waiting'
                }
                bot.answer_callback_query(call.id, "اتاق بازی ساخته شد. منتظر بازیکن دوم باشید!", show_alert=True)
                return

            game = games[msg_id]
            if game['player1'] == user_id:
                bot.answer_callback_query(call.id, "شما بازیکن اول هستید! منتظر حریف بمانید.", show_alert=True)
                return

            if game['player2'] is None:
                game['player2'] = user_id
                game['player2_name'] = user_name
                game['status'] = 'playing'
                
                deck = create_deck()
                game['hand1'] = deck[:15]
                game['hand2'] = deck[15:30]
                game['turn'] = game['player1']
                
                text = (
                    f"🎮 **بازی بلوف شروع شد!**\n\n"
                    f"👤 **بازیکن اول:** {game['player1_name']} (۱۵ کارت)\n"
                    f"👤 **بازیکن دوم:** {game['player2_name']} (۱۵ کارت)\n\n"
                    f"🟢 **نوبت:** {game['player1_name']}\n"
                    f"📥 **کارت‌های روی میز:** ۰ کارت"
                )
                bot.edit_message_text(text, inline_message_id=msg_id, reply_markup=build_keyboard(game, game['player1']), parse_mode="Markdown")
                bot.answer_callback_query(call.id, "شما وارد بازی شدید!")
            return

        if msg_id not in games or games[msg_id]['status'] != 'playing':
            bot.answer_callback_query(call.id, "این بازی پایان یافته است.")
            return

        game = games[msg_id]

        # --- ۲. مشاهده دست بازیکن ---
        if call.data == "view_hand":
            if user_id == game['player1']:
                hand = game['hand1']
            elif user_id == game['player2']:
                hand = game['hand2']
            else:
                bot.answer_callback_query(call.id, "شما تماشاچی هستید!", show_alert=True)
                return
            
            cards_str = "\n".join([f"کارت {i+1}:  {c['display']}" for i, c in enumerate(hand)])
            bot.answer_callback_query(call.id, f"📜 **کارت‌های دست شما ({len(hand)} تا):**\n\n{cards_str}", show_alert=True)
            return

        # --- ۳. انتخاب / از حالت انتخاب درآوردن کارت‌ها ---
        if call.data.startswith("toggle_"):
            if user_id != game['turn']:
                bot.answer_callback_query(call.id, "⚠️ نوبت شما نیست!", show_alert=True)
                return
            
            idx = int(call.data.split("_")[1])
            selected = game['selected_1'] if user_id == game['player1'] else game['selected_2']
            
            if idx in selected:
                selected.remove(idx)
            else:
                if len(selected) >= 4:
                    bot.answer_callback_query(call.id, "حداکثر می‌توانید ۴ کارت هم‌زمان انتخاب کنید!", show_alert=True)
                    return
                selected.append(idx)
                
            bot.edit_message_reply_markup(inline_message_id=msg_id, reply_markup=build_keyboard(game, user_id))
            return

        # --- ۴. تغییر رتبه ادعایی ---
        if call.data == "change_claim":
            if user_id != game['turn']:
                return
            
            current_idx = RANKS.index(game['claim_rank'])
            next_idx = (current_idx + 1) % len(RANKS)
            game['claim_rank'] = RANKS[next_idx]
            
            bot.edit_message_reply_markup(inline_message_id=msg_id, reply_markup=build_keyboard(game, user_id))
            bot.answer_callback_query(call.id, f"ادعا تغییر کرد به: {RANK_NAMES[game['claim_rank']]}")
            return

        # --- ۵. بازی کردن کارت‌های انتخاب شده ---
        if call.data == "play_selected":
            if user_id != game['turn']:
                return
            
            is_p1 = (user_id == game['player1'])
            hand = game['hand1'] if is_p1 else game['hand2']
            selected = game['selected_1'] if is_p1 else game['selected_2']
            
            if len(selected) == 0:
                bot.answer_callback_query(call.id, "لطفاً حداقل یک کارت انتخاب کنید!", show_alert=True)
                return
            
            # جدا کردن کارت‌های بازی شده
            selected.sort(reverse=True)
            played_cards = []
            for i in selected:
                played_cards.append(hand.pop(i))
                
            game['pile'].extend(played_cards)
            game['last_cards'] = played_cards
            game['last_claim'] = game['claim_rank']
            game['last_player'] = user_id
            
            # پاک کردن لیست انتخاب‌ها
            if is_p1:
                game['selected_1'] = []
            else:
                game['selected_2'] = []

            # بررسی شرط برد
            if len(hand) == 0:
                winner_name = game['player1_name'] if is_p1 else game['player2_name']
                bot.edit_message_text(f"🏆 **تبریک! {winner_name} برنده بازی شد!**\nتمام کارت‌هایش تمام شد.", inline_message_id=msg_id)
                del games[msg_id]
                return

            # تغییر نوبت
            game['turn'] = game['player2'] if is_p1 else game['player1']
            next_name = game['player2_name'] if is_p1 else game['player1_name']
            
            text = (
                f"🂠 **کارت روی میز گذاشته شد!**\n\n"
                f"👤 **آخرین حرکت:** {user_name} تعداد **{len(played_cards)} کارت** گذاشت.\n"
                f"📢 **ادعا:** {len(played_cards)} تا **[{RANK_NAMES[game['claim_rank']]}]**\n\n"
                f"🟢 **نوبت:** {next_name}\n"
                f"📥 **مجموع کارت‌های روی میز:** {len(game['pile'])} تا"
            )
            bot.edit_message_text(text, inline_message_id=msg_id, reply_markup=build_keyboard(game, game['turn']), parse_mode="Markdown")
            return

        # --- ۶. رو کردن و اعلام بلوف ---
        if call.data == "call_bluff":
            if len(game['pile']) == 0 or game['last_player'] is None:
                bot.answer_callback_query(call.id, "کارتی روی میز نیست!", show_alert=True)
                return
            if user_id == game['last_player']:
                bot.answer_callback_query(call.id, "نمی‌توانید روی حرکت خودتان بلوف بزنید!", show_alert=True)
                return
            
            last_cards = game['last_cards']
            claimed_rank = game['last_claim']
            
            # آیا واقعاً بلوف بوده؟ (اگر حداقل یکی از کارت‌ها مخالف ادعا باشد)
            is_bluff = any(c['rank'] != claimed_rank for c in last_cards)
            
            revealed_str = " , ".join([c['display'] for c in last_cards])
            all_pile = game['pile'].copy()
            game['pile'] = []
            
            liar_id = game['last_player']
            liar_name = game['player1_name'] if liar_id == game['player1'] else game['player2_name']
            challenger_name = game['player1_name'] if user_id == game['player1'] else game['player2_name']
            
            if is_bluff:
                loser_id = liar_id
                loser_name = liar_name
                result_title = "🎭 **بلوف برملا شد!**"
                detail_text = f"کارت‌های واقعی: [{revealed_str}]\n{liar_name} ادعای دروغ کرده بود! او جریمه شد و تمام **{len(all_pile)} کارت** روی میز را برداشت."
            else:
                loser_id = user_id
                loser_name = challenger_name
                result_title = "✅ **راست می‌گفت! (اشتباه کردید)**"
                detail_text = f"کارت‌های واقعی: [{revealed_str}]\n{liar_name} راست گفته بود! {challenger_name} جریمه شد و تمام **{len(all_pile)} کارت** روی میز را برداشت."

            # افزودن کارت‌ها به دست بازنده
            if loser_id == game['player1']:
                game['hand1'].extend(all_pile)
            else:
                game['hand2'].extend(all_pile)
                
            game['turn'] = user_id if is_bluff else liar_id
            next_name = game['player1_name'] if game['turn'] == game['player1'] else game['player2_name']
            
            game['last_player'] = None
            game['last_cards'] = []
            
            text = (
                f"{result_title}\n🔍 {detail_text}\n\n"
                f"🟢 **نوبت جدید:** {next_name}\n"
                f"📥 **کارت‌های روی میز:** ۰"
            )
            bot.edit_message_text(text, inline_message_id=msg_id, reply_markup=build_keyboard(game, game['turn']), parse_mode="Markdown")
            return

    except Exception as e:
        print(f"Callback Error: {e}")

# --- وب سرور زنده نگه داشتن ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is active!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    t = Thread(target=run_web_server)
    t.start()
    print("Bot is polling...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)

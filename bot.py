import telebot
from telebot.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle, InlineKeyboardMarkup, InlineKeyboardButton
import random
import os
from flask import Flask
from threading import Thread

BOT_TOKEN = "8845512776:AAHDjlsoXLmdmi9TVRYc5DOjrvj1hxIYzow"  # توکن ربات خود را اینجا بگذارید
bot = telebot.TeleBot(BOT_TOKEN)

games = {}

SUITS = ['♠️', '♥️', '♦️', '♣️']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
RANK_NAMES = {'A': 'تک (A)', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', '10': '10', 'J': 'سرباز (J)', 'Q': 'بیبی (Q)', 'K': 'شاه (K)'}

def create_deck():
    deck = []
    for r in RANKS:
        for s in SUITS:
            deck.append({'suit': s, 'rank': r, 'display': f"{s}{r}"})
    random.shuffle(deck)
    return deck

def get_game_text(game):
    p1_name = game['player1_name']
    p2_name = game['player2_name']
    p1_cards = len(game['hand1'])
    p2_cards = len(game['hand2'])
    
    turn_name = p1_name if game['turn'] == game['player1'] else p2_name
    
    text = f"🃏 **کازینو بازی بلوف** 🃏\n\n"
    text += f"👤 {p1_name}: `{p1_cards}` کارت\n"
    text += f"👤 {p2_name}: `{p2_cards}` کارت\n"
    text += f"───────────────────\n"
    
    if game['current_claim_rank']:
        text += f"📢 **ادعای این دور:** کارت‌های [{RANK_NAMES[game['current_claim_rank']]}]\n"
        last_action_name = p1_name if game['last_player'] == game['player1'] else p2_name
        text += f"📥 **آخرین حرکت:** {last_action_name} تعداد `{game['last_cards_count']}` کارت گذاشت.\n"
    else:
        text += f"📢 **وضعیت:** شروع دور جدید (تعیین رتبه ادعا با نفر اول)\n"
        
    text += f"📥 **کل کارت‌های وسط زمین:** `{len(game['pile'])}` برگ\n"
    text += f"⏱ **نوبت حرکت:** __{turn_name}__\n"
    
    if game['last_action_text']:
        text += f"───────────────────\n💬 {game['last_action_text']}"
        
    return text

def build_keyboard(game, viewer_id):
    markup = InlineKeyboardMarkup(row_width=4)
    
    is_p1 = (viewer_id == game['player1'])
    show_hand = game['show_hand_p1'] if is_p1 else game['show_hand_p2']
    current_hand = game['hand1'] if is_p1 else game['hand2']
    selected = game['selected_1'] if is_p1 else game['selected_2']
    
    # ۱. دکمه مشاهده/مخفی کردن کارت‌ها
    hand_text = "🙈 مخفی کردن کارت‌ها" if show_hand else "👁 مشاهده کارت‌های من"
    markup.add(InlineKeyboardButton(hand_text, callback_data="toggle_hand_view"))
    
    if show_hand:
        card_btns = []
        for idx in range(len(current_hand)):
            icon = "✅" if idx in selected else "🂠"
            card_btns.append(InlineKeyboardButton(f"{icon} {idx+1}", callback_data=f"select_{idx}"))
        for i in range(0, len(card_btns), 4):
            markup.add(*card_btns[i:i+4])

    # ۲. دکمه‌های اکشن بازی (فقط در نوبت بازیکن)
    if viewer_id == game['turn']:
        if not game['current_claim_rank'] and len(selected) > 0:
            claim_r = game['claim_selection']
            markup.add(InlineKeyboardButton(f"⚙️ تعیین ادعا: [{RANK_NAMES[claim_r]}] 🔄", callback_data="next_rank"))
            markup.add(InlineKeyboardButton(f"🚀 شروع دور با {len(selected)} کارت", callback_data="play_cards"))
        elif game['current_claim_rank']:
            if len(selected) > 0:
                markup.add(InlineKeyboardButton(f"📥 اضافه کردن {len(selected)} کارت روی میز", callback_data="play_cards"))
            
            btn_pass = InlineKeyboardButton("💤 پاس", callback_data="action_pass")
            
            if game['last_player'] and game['last_player'] != viewer_id:
                btn_bluff = InlineKeyboardButton("🚨 ادعای بلوف!", callback_data="action_bluff")
                markup.add(btn_pass, btn_bluff)
            else:
                markup.add(btn_pass)
                
    return markup

@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    try:
        switch_btn = InlineQueryResultArticle(
            id='1',
            title="🎮 شروع بازی مساوی و حرفه‌ای بلوف",
            description="پخش ۱۵ کارت ناشناخته به هر نفر و شروع چالش",
            input_message_content=InputTextMessageContent(
                message_text="🎯 **اتاق بازی بلوف تشکیل شد.**\n\nمنتظر ورود بازیکن دوم برای توزیع کارت‌ها..."
            ),
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🤝 ورود به صندلی بازی", callback_data="join_game")
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

        if call.data == "join_game":
            if msg_id not in games:
                games[msg_id] = {
                    'player1': user_id, 'player1_name': user_name, 'player2': None, 'player2_name': '',
                    'hand1': [], 'hand2': [], 'selected_1': [], 'selected_2': [],
                    'show_hand_p1': False, 'show_hand_p2': False,
                    'pile': [], 'last_cards_count': 0, 'last_actual_cards': [], 'last_claim_rank': None,
                    'current_claim_rank': None, 'last_player': None, 'turn': None, 'claim_selection': 'A',
                    'pass_count': 0, 'last_action_text': "بازی تازه آغاز شده است."
                }
                bot.answer_callback_query(call.id, "شما بازیکن اول شدید. منتظر حریف بمانید.", show_alert=True)
                return
            
            game = games[msg_id]
            if game['player1'] == user_id:
                bot.answer_callback_query(call.id, "شما بازیکن اول هستید!", show_alert=True)
                return
                
            if game['player2'] is None:
                game['player2'] = user_id
                game['player2_name'] = user_name
                
                # تقسیم ۱۵ کارت به هر نفر (۲۲ کارت بیرون می‌مانند تا دست حریف قابل حدس نباشد)
                deck = create_deck()
                game['hand1'] = deck[:15]
                game['hand2'] = deck[15:30]
                game['turn'] = game['player1']
                
                bot.edit_message_text(get_game_text(game), inline_message_id=msg_id, reply_markup=build_keyboard(game, game['player1']), parse_mode="Markdown")
            return

        if msg_id not in games: return
        game = games[msg_id]

        if user_id != game['player1'] and user_id != game['player2']:
            bot.answer_callback_query(call.id, "شما بازیکن این دست نیستید!", show_alert=True)
            return

        is_p1 = (user_id == game['player1'])

        # نمایش/مخفی‌سازی کارت‌ها
        if call.data == "toggle_hand_view":
            if is_p1:
                game['show_hand_p1'] = not game['show_hand_p1']
            else:
                game['show_hand_p2'] = not game['show_hand_p2']
            bot.edit_message_reply_markup(inline_message_id=msg_id, reply_markup=build_keyboard(game, user_id))
            bot.answer_callback_query(call.id)
            return

        # انتخاب کارت‌ها
        if call.data.startswith("select_"):
            idx = int(call.data.split("_")[1])
            selected = game['selected_1'] if is_p1 else game['selected_2']
            if idx in selected: selected.remove(idx)
            else: selected.append(idx)
            bot.edit_message_reply_markup(inline_message_id=msg_id, reply_markup=build_keyboard(game, user_id))
            bot.answer_callback_query(call.id)
            return

        # تغییر رتبه ادعا
        if call.data == "next_rank":
            curr = RANKS.index(game['claim_selection'])
            game['claim_selection'] = RANKS[(curr + 1) % len(RANKS)]
            bot.edit_message_reply_markup(inline_message_id=msg_id, reply_markup=build_keyboard(game, user_id))
            bot.answer_callback_query(call.id)
            return

        # بازی کردن کارت‌ها
        if call.data == "play_cards":
            if user_id != game['turn']: return
            hand = game['hand1'] if is_p1 else game['hand2']
            selected = game['selected_1'] if is_p1 else game['selected_2']
            
            if len(selected) == 0: return
            
            selected.sort(reverse=True)
            played = []
            for i in selected:
                played.append(hand.pop(i))
                
            if not game['current_claim_rank']:
                game['current_claim_rank'] = game['claim_selection']
                
            game['pile'].extend(played)
            game['last_actual_cards'] = played
            game['last_cards_count'] = len(played)
            game['last_player'] = user_id
            game['pass_count'] = 0
            
            if is_p1: game['selected_1'] = []
            else: game['selected_2'] = []
            
            if len(hand) == 0:
                bot.edit_message_text(f"🏆 **بازی به پایان رسید!**\n\nبازیکن {user_name} زودتر کارت‌هایش تمام شد و برنده این نبرد شد!", inline_message_id=msg_id)
                del games[msg_id]
                return

            game['turn'] = game['player2'] if is_p1 else game['player1']
            game['last_action_text'] = f"برگ‌ها اضافه شدند. رتبه ادعا شده: {RANK_NAMES[game['current_claim_rank']]}"
            
            bot.edit_message_text(get_game_text(game), inline_message_id=msg_id, reply_markup=build_keyboard(game, game['turn']), parse_mode="Markdown")
            bot.answer_callback_query(call.id)
            return

        # پاس دادن
        if call.data == "action_pass":
            if user_id != game['turn']: return
            game['pass_count'] += 1
            
            game['turn'] = game['player2'] if is_p1 else game['player1']
            game['last_action_text'] = f"بازیکن {user_name} این دور را پاس داد."
            
            if game['pass_count'] >= 2:
                game['pile'] = []
                game['current_claim_rank'] = None
                game['turn'] = game['last_player']
                game['last_player'] = None
                game['last_action_text'] = "کارت‌های روی زمین سوختند! حاکم قبلی دور جدید را با کارت دلخواه شروع می‌کند."
                
            bot.edit_message_text(get_game_text(game), inline_message_id=msg_id, reply_markup=build_keyboard(game, game['turn']), parse_mode="Markdown")
            bot.answer_callback_query(call.id)
            return

        # اعلام بلوف
        if call.data == "action_bluff":
            if user_id != game['turn'] or not game['last_player']: return
            
            last_cards = game['last_actual_cards']
            target_rank = game['current_claim_rank']
            
            has_bluffed = any(c['rank'] != target_rank for c in last_cards)
            
            all_cards_in_pile = game['pile'].copy()
            game['pile'] = []
            
            liar_name = game['player1_name'] if game['last_player'] == game['player1'] else game['player2_name']
            revealed_str = " , ".join([c['display'] for c in last_cards])
            
            if has_bluffed:
                loser_id = game['last_player']
                game['last_action_text'] = f"💥 **بلوف موفق مچ‌گیری شد!**\n\nکارت‌های رو شده: [ {revealed_str} ]\nبازیکن {liar_name} دروغ گفته بود و جریمه شد! او تمام `{len(all_cards_in_pile)}` کارت زمین را برداشت.\n\nشروع‌کننده بعدی: {user_name}"
                game['turn'] = user_id
            else:
                loser_id = user_id
                game['last_action_text'] = f"🛡 **رکب خوردید! کاملاً راست می‌گفت.**\n\nکارت‌های رو شده: [ {revealed_str} ]\n{liar_name} حقیقت را گفته بود! بازیکن {user_name} جریمه شد و تمام `{len(all_cards_in_pile)}` کارت زمین را برداشت.\n\nشروع‌کننده بعدی: {liar_name}"
                game['turn'] = game['last_player']

            if loser_id == game['player1']:
                game['hand1'].extend(all_cards_in_pile)
            else:
                game['hand2'].extend(all_cards_in_pile)
                
            game['current_claim_rank'] = None
            game['last_player'] = None
            game['last_actual_cards'] = []
            game['pass_count'] = 0
            
            bot.edit_message_text(get_game_text(game), inline_message_id=msg_id, reply_markup=build_keyboard(game, game['turn']), parse_mode="Markdown")
            bot.answer_callback_query(call.id)
            return

    except Exception as e:
        print(f"Global Error: {e}")

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    t = Thread(target=run_web_server)
    t.start()
    bot.infinity_polling(timeout=20, long_polling_timeout=10)

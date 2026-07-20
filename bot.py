import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputTextMessageContent, InlineQueryResultArticle
import random
import os
from flask import Flask
from threading import Thread

BOT_TOKEN = "8845512776:AAHDjlsoXLmdmi9TVRYc5DOjrvj1hxIYzow"  # توکن خود را اینجا بگذارید
bot = telebot.TeleBot(BOT_TOKEN)

games = {}

SUITS = ['♠️', '♥️', '♦️', '♣️']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
RANK_NAMES = {'A': 'تک (A)', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹', '10': '۱۰', 'J': 'سرباز (J)', 'Q': 'بیبی (Q)', 'K': 'شاه (K)'}

def create_deck():
    deck = []
    for r in RANKS:
        for s in SUITS:
            deck.append({'suit': s, 'rank': r, 'display': f"{s}{r}"})
    random.shuffle(deck)
    return deck

def get_game_text(game):
    p1 = game['player1_name']
    p2 = game['player2_name']
    turn_name = p1 if game['turn'] == game['player1'] else p2
    
    text = f"🃏 **میز بازی بلوف** 🃏\n\n"
    text += f"👤 {p1}: `{len(game['hand1'])}` کارت\n"
    text += f"👤 {p2}: `{len(game['hand2'])}` کارت\n"
    text += f"───────────────────\n"
    
    if game['current_claim_rank']:
        last_name = p1 if game['last_player'] == game['player1'] else p2
        text += f"📢 **ادعای جاری روی میز:** کارت‌های [{RANK_NAMES[game['current_claim_rank']]}]\n"
        text += f"📥 **آخرین حرکت:** {last_name} تعداد `{game['last_cards_count']}` کارت گذاشت.\n"
    else:
        text += f"📢 **وضعیت:** شروع دور جدید (نفر اول رتبه ادعا را تعیین می‌کند)\n"
        
    text += f"🎴 **تعداد کل کارت‌های وسط زمین:** `{len(game['pile'])}` برگ\n"
    text += f"⏱ **نوبت حرکت:** __{turn_name}__\n"
    
    if game['status_text']:
        text += f"───────────────────\n💬 {game['status_text']}"
        
    return text

def build_keyboard(game, viewer_id):
    markup = InlineKeyboardMarkup(row_width=4)
    is_p1 = (viewer_id == game['player1'])
    show_hand = game['show_hand_p1'] if is_p1 else game['show_hand_p2']
    hand = game['hand1'] if is_p1 else game['hand2']
    selected = game['selected_1'] if is_p1 else game['selected_2']
    
    # دکمه نمایش/مخفی کردن کارت‌ها
    h_label = "🙈 مخفی کردن کارت‌های دستم" if show_hand else "👁 مشاهده کارت‌های دستم"
    markup.add(InlineKeyboardButton(h_label, callback_data="toggle_hand"))
    
    if show_hand:
        for idx in range(len(hand)):
            ico = "✅" if idx in selected else "🂠"
            markup.add(InlineKeyboardButton(f"{ico} {idx+1}: {hand[idx]['display']}", callback_data=f"sel_{idx}"))
            
    # منوی اکشن در نوبت بازیکن
    if viewer_id == game['turn']:
        if len(selected) > 0:
            if not game['current_claim_rank']:
                # انتخاب رتبه ادعا برای شروع کننده
                claim_r = game['claim_selection']
                markup.add(InlineKeyboardButton(f"⚙️ ادعا می‌کنم این‌ها [{RANK_NAMES[claim_r]}] هستند 🔄", callback_data="change_claim"))
            markup.add(InlineKeyboardButton(f"🚀 پرتاب {len(selected)} کارت انتخاب شده روی میز", callback_data="play_selected"))
            
        if game['current_claim_rank']:
            markup.add(InlineKeyboardButton("💤 پاس دادن", callback_data="action_pass"))
            if game['last_player'] and game['last_player'] != viewer_id:
                markup.add(InlineKeyboardButton("🚨 مچ‌گیری و ادعای بلوف!", callback_data="action_bluff"))
                
    return markup

@bot.inline_handler(lambda query: True)
def inline_query(q):
    try:
        btn = InlineQueryResultArticle(
            id='bluff_game_1',
            title="🎮 شروع بازی دو نفره بلوف واقعی",
            description="کلیک کنید تا میز بازی ساخته شود",
            input_message_content=InputTextMessageContent(message_text="🎯 **میز بازی بلوف آماده شد!**\n\nنفر دوم برای ورود به بازی روی دکمه زیر کلیک کند:"),
            reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🤝 پیوستن به بازی", callback_data="join_game"))
        )
        bot.answer_inline_query(q.id, [btn], cache_time=1)
    except Exception as e:
        print(e)

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    try:
        msg_id = call.inline_message_id
        uid = call.from_user.id
        uname = call.from_user.first_name
        
        if call.data == "join_game":
            if msg_id not in games:
                games[msg_id] = {
                    'player1': uid, 'player1_name': uname, 'player2': None, 'player2_name': '',
                    'hand1': [], 'hand2': [], 'selected_1': [], 'selected_2': [],
                    'show_hand_p1': False, 'show_hand_p2': False,
                    'pile': [], 'last_cards_count': 0, 'last_actual_cards': [],
                    'current_claim_rank': None, 'last_player': None, 'turn': None,
                    'claim_selection': 'A', 'pass_count': 0, 'status_text': "بازی شروع شد!"
                }
                bot.answer_callback_query(call.id, "شما بازیکن اول شدید. منتظر حریف باشید.", show_alert=True)
                return
                
            game = games[msg_id]
            if game['player1'] == uid:
                bot.answer_callback_query(call.id, "شما از قبل صندلی اول را گرفته‌اید!", show_alert=True)
                return
                
            if game['player2'] is None:
                game['player2'] = uid
                game['player2_name'] = uname
                
                # توزیع ۱۵ کارت به هر بازیکن (و باقی ماندن ۲۲ کارت در بیرون)
                deck = create_deck()
                game['hand1'] = deck[:15]
                game['hand2'] = deck[15:30]
                game['turn'] = game['player1']
                
                bot.edit_message_text(get_game_text(game), inline_message_id=msg_id, reply_markup=build_keyboard(game, game['player1']), parse_mode="Markdown")
            return
            
        if msg_id not in games: return
        game = games[msg_id]
        
        if uid != game['player1'] and uid != game['player2']:
            bot.answer_callback_query(call.id, "شما بازیکن این مسابقه نیستید!", show_alert=True)
            return
            
        is_p1 = (uid == game['player1'])
        
        # نمایش / مخفی کردن دست
        if call.data == "toggle_hand":
            if is_p1: game['show_hand_p1'] = not game['show_hand_p1']
            else: game['show_hand_p2'] = not game['show_hand_p2']
            bot.edit_message_reply_markup(inline_message_id=msg_id, reply_markup=build_keyboard(game, uid))
            bot.answer_callback_query(call.id)
            return
            
        # انتخاب کارت‌ها
        if call.data.startswith("sel_"):
            idx = int(call.data.split("_")[1])
            sel = game['selected_1'] if is_p1 else game['selected_2']
            if idx in sel: sel.remove(idx)
            else: sel.append(idx)
            bot.edit_message_reply_markup(inline_message_id=msg_id, reply_markup=build_keyboard(game, uid))
            bot.answer_callback_query(call.id)
            return
            
        # تغییر رتبه ادعا
        if call.data == "change_claim":
            curr = RANKS.index(game['claim_selection'])
            game['claim_selection'] = RANKS[(curr + 1) % len(RANKS)]
            bot.edit_message_reply_markup(inline_message_id=msg_id, reply_markup=build_keyboard(game, uid))
            bot.answer_callback_query(call.id)
            return
            
        # پرتاب کارت‌ها روی میز
        if call.data == "play_selected":
            if uid != game['turn']: return
            hand = game['hand1'] if is_p1 else game['hand2']
            sel = game['selected_1'] if is_p1 else game['selected_2']
            
            if not sel: return
            
            sel.sort(reverse=True)
            played = [hand.pop(i) for i in sel]
            
            if not game['current_claim_rank']:
                game['current_claim_rank'] = game['claim_selection']
                
            game['pile'].extend(played)
            game['last_actual_cards'] = played
            game['last_cards_count'] = len(played)
            game['last_player'] = uid
            game['pass_count'] = 0
            
            if is_p1: game['selected_1'] = []
            else: game['selected_2'] = []
            
            # بررسی برد
            if len(hand) == 0:
                bot.edit_message_text(f"👑 **بازی به پایان رسید!**\n\nبازیکن **{uname}** تمام کارت‌هایش را تمام کرد و برنده شد!", inline_message_id=msg_id)
                del games[msg_id]
                return
                
            game['turn'] = game['player2'] if is_p1 else game['player1']
            game['status_text'] = f"{uname} تعداد `{len(played)}` کارت انداخت. ادعا: [{RANK_NAMES[game['current_claim_rank']]}]"
            
            bot.edit_message_text(get_game_text(game), inline_message_id=msg_id, reply_markup=build_keyboard(game, game['turn']), parse_mode="Markdown")
            bot.answer_callback_query(call.id)
            return
            
        # پاس دادن
        if call.data == "action_pass":
            if uid != game['turn']: return
            game['pass_count'] += 1
            game['turn'] = game['player2'] if is_p1 else game['player1']
            game['status_text'] = f"{uname} پاس داد."
            
            if game['pass_count'] >= 2:
                game['pile'] = []
                game['current_claim_rank'] = None
                game['turn'] = game['last_player']
                game['last_player'] = None
                game['status_text'] = "هر دو پاس دادند! کارت‌های وسط سوختند و حاکم قبلی دور را شروع می‌کند."
                
            bot.edit_message_text(get_game_text(game), inline_message_id=msg_id, reply_markup=build_keyboard(game, game['turn']), parse_mode="Markdown")
            bot.answer_callback_query(call.id)
            return
            
        # مچ‌گیری و بلوف
        if call.data == "action_bluff":
            if uid != game['turn'] or not game['last_player']: return
            
            last_cards = game['last_actual_cards']
            target_rank = game['current_claim_rank']
            
            # آیا کسی بلوف زده؟ (یعنی حتی یکی از کارت‌ها مخالف رتبه ادعا شده باشد)
            has_bluffed = any(c['rank'] != target_rank for c in last_cards)
            
            all_pile = game['pile'].copy()
            game['pile'] = []
            
            liar_name = game['player1_name'] if game['last_player'] == game['player1'] else game['player2_name']
            revealed_str = " , ".join([c['display'] for c in last_cards])
            
            if has_bluffed:
                loser_id = game['last_player']
                game['status_text'] = f"💥 **بلوف مچ‌گیری شد!**\n\nکارت‌های رو شده: [ {revealed_str} ]\n{liar_name} دروغ گفته بود و جریمه شد! او تمام `{len(all_pile)}` کارت زمین را برداشت."
                game['turn'] = uid
            else:
                loser_id = uid
                game['status_text'] = f"🛡 **اشتباه کردید! راست می‌گفت.**\n\nکارت‌های رو شده: [ {revealed_str} ]\n{liar_name} حقیقت را گفته بود! شما جریمه شدید و تمام `{len(all_pile)}` کارت زمین را برداشتید."
                game['turn'] = game['last_player']
                
            if loser_id == game['player1']: game['hand1'].extend(all_pile)
            else: game['hand2'].extend(all_pile)
            
            game['current_claim_rank'] = None
            game['last_player'] = None
            game['last_actual_cards'] = []
            game['pass_count'] = 0
            
            bot.edit_message_text(get_game_text(game), inline_message_id=msg_id, reply_markup=build_keyboard(game, game['turn']), parse_mode="Markdown")
            bot.answer_callback_query(call.id)
            return
            
    except Exception as e:
        print(f"Error: {e}")

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

if __name__ == "__main__":
    t = Thread(target=run_web_server := lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))))
    t.start()
    bot.infinity_polling(timeout=20, long_polling_timeout=10)

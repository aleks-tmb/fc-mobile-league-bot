from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode


from utils.tournament_utils import TournamentUtils
from utils.config_utils import CONFIG
from score_processor import ScoreProcessor
from utils.users_database import UsersDatabaseCSV

import re

def getUsersDatabase():
    return UsersDatabaseCSV(CONFIG.get('database_path'))

def getLeagueDatabase(tag, season):
    db = getUsersDatabase()
    return TournamentUtils(db, CONFIG.get('database_path'), tag, season)


async def is_user_admin(chat, user):
    admins = await chat.get_administrators()
    for admin in admins:
        if admin.user.id == user.id:
            return True
    return False

reactions = {}
draw_in_progress = False

def build_react_counter(like_count=0):
    global draw_in_progress
    draw_in_progress = True
    keyboard = [[InlineKeyboardButton(f"🖕 {like_count}", callback_data='like')]]
    return InlineKeyboardMarkup(keyboard)

def log_user_request(user, module = '-'):
    print(f'[{module.upper()}] You talk with user {user["username"]} and his user ID: {user["id"]}')



async def perform_draw(tag, season):
    league_db = getLeagueDatabase(tag, season)
    stage = league_db.get_stage()
    print(stage)

    if stage == 'NOT-STARTED':
        league_db.make_groups(4)
    elif stage == 'GROUP':          
        league_db.make_playoff(4)

async def show_score_confirmation(db, message, op_id, score, edit_message_id, league_info):
    user_id = message.from_user.id
    tag = league_info['tag']
    season = league_info['season']
    print(tag)

    s = f"{user_id}_{op_id}_{score[0]}_{score[1]}_{edit_message_id}_{tag}_{season}"
    print(s)
    keyboard = [
        [InlineKeyboardButton("Да", callback_data=f'confirm_yes_{s}')],
        [InlineKeyboardButton("Нет", callback_data=f'confirm_no_{s}')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    username = db.get_username_by_id(user_id)
    op_username = db.get_username_by_id(op_id)
    await message.reply_text(
        f'@{username} {score[0]}:{score[1]} @{op_username}', 
        reply_markup=reply_markup
    )

async def score_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user

    callback_data = query.data.split('_')
    action = callback_data[1]
    id_main = int(callback_data[2])
    id1 = int(callback_data[3])
    g0 = int(callback_data[4])
    g1 = int(callback_data[5])
    edit_id = int(callback_data[6])
    tag = callback_data[7]
    season = int(callback_data[8])

    # Check if the user is the initiating user
    if user.id != id_main:
        await query.answer(text="Вы не можете отменить это действие", show_alert=True)
        return

    if action == 'no':
        await query.answer()
        await query.edit_message_text(text="Отменяю!")
        return
    
    if tag not in ['CL', 'EL']:
        respond = "Турнир не идентифицирован"
    else:
        tour_db = getLeagueDatabase(tag, season)
        respond = tour_db.write_score(id_main, id1, (g0, g1))
    
    await query.answer()
    await query.edit_message_text(text=respond)
    
    if respond == 'Результат зафиксирован!':
        await update_post(context.bot, edit_id, tag, season)
        if tour_db.get_stage() == 'GROUP-COMPLETE':
            tour_db.make_playoff(4)
            await make_post(context.bot, tag, season)
            

    


async def make_post(bot, tag, season):
    league_db = getLeagueDatabase(tag, season)
    respond = league_db.get_status()
    CHANNEL_USERNAME = f"@{CONFIG.get('channel_username')}"
    await bot.send_message(chat_id=CHANNEL_USERNAME, text=respond, parse_mode=ParseMode.HTML) 

async def post_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.message.from_user.id
    except:
        return

    if user_id != int(CONFIG.get('owner_id')):
        await update.message.reply_text('Restricted!')  
        return

    
    for tag in ['CL','EL']:
        make_post(context.bot, tag, 9)
        await update.message.reply_text('Posted!')

async def update_post(bot, edit_id, tag, season) -> None:
    CHANNEL_USERNAME = f"@{CONFIG.get('channel_username')}"
    league_db = getLeagueDatabase(tag, season)
    new_text = league_db.get_status()
    try:
        await bot.edit_message_text(chat_id=CHANNEL_USERNAME, message_id=edit_id, text=new_text, parse_mode=ParseMode.HTML)
    except:
        return

def parse_channel_post(from_chat, text):
    if from_chat != CONFIG.get('channel_username'):
        print("[parse_channel_post] wrong chat name") 
        return

    lines = text.splitlines()

    if lines[0] == 'Лига Чемпионов':
        tag = 'CL'
    elif lines[0] == 'Лига Европы':
        tag = 'EL'
    else:
        return None
    
    try:
        _, season = lines[1].split()
        season = int(season)
    except:
        return None
    
    return {
        "tag" : tag,
        "season" : season
    }

def parse_bot_request(text):
    clean_text = re.sub(r'[.,\-]', ' ', text)
    words = clean_text.split()

    BOT_USERNAME = f"@{CONFIG.get('bot_username')}"
    if words[0].lower() == 'бот' or words[0] == BOT_USERNAME:
        return words[1:]
    return None

async def process_replay(message):
   # Ensure the message is a reply and contains text
    if not message.reply_to_message:
        return
    
    clean_text = re.sub(r'[.,?!\-]', ' ', message.text)
    words = clean_text.lower().split()
    print(words)
    # Check if the message text matches 'ник'
    if 'ник' in words:
        try:
            db = getUsersDatabase()
            user_id = message.reply_to_message.from_user.id
            user = db.get_user(user_id)
            respond = (
                f"@{user['username']}\n"
                f"никнейм в FC mobile: {user['nick']}\n"
                f"рейтинг в РИ: {user['rate']}"
            )
            await message.reply_text(respond)
        except KeyError:
            await message.reply_text(f"Пользователя нет в Базе Данных")
        except Exception as e:
            # Log the exception if needed
            print(f"Error fetching user data: {e}")
            return

def check_pattern(words, pattern):
    list = pattern.split()
    print('list')
    print(list)
    print('words')
    print(words)
    for word in list:
        if word not in words:
            return False
    return True
    

async def process_request(message):
    user = message.from_user

    clean_text = re.sub(r'[.,?!\-]', ' ', message.text)
    words = clean_text.lower().split()[1:]
    print(words)
    db = getUsersDatabase()

    if check_pattern(words, 'рейтинг лиги'):
        await message.reply_text(db.get_rating_table())
        return
    
    if check_pattern(words, 'мой рейтинг'):
        for word in words:
            try:
                rating = int(word)        
                respond = db.update_rating(user.id, user.username, rating)
                await message.reply_text(respond)
                return
            except ValueError:
                continue

        await message.reply_text("Не нашел целое число в сообщении")        
        return

    default_respond = (
        f"Привет, {user.username}! Я понимаю следующие команды:\n\n"
        f"'бот, рейтинг лиги' - выведут участников лиги и их рейтинг в РИ\n\n"
        f"'бот, мой рейтинг 1234' - запишу максимальное кол-во кубков в РИ\n\n"
    )

    await message.reply_text(default_respond)
    
    

async def reply_in_common_chat(message):
    if not message.text:
        return
    
    lower_text = message.text.lower()
    if lower_text.startswith('бот'):
        await process_request(message)
        return

    if message.reply_to_message:
        await process_replay(message)

async def reply_to_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    channel_post = message.reply_to_message

    print(message.chat.title)
    if message.chat.title == CONFIG.get('group_title'):
        await reply_in_common_chat(message)
        return


    if channel_post and channel_post.forward_origin:
        origin = channel_post.forward_origin
    else:
        return

    league_info = parse_channel_post(origin.chat.username, channel_post.text)
    if not league_info:
        return

    words = parse_bot_request(message.text)
    if words is None:
        return

    score_processor = ScoreProcessor(words)
    result = score_processor.get_report()
    if result:
        op_username, score = result
        print(op_username, score)
        try:
            db = getUsersDatabase()
            op_id = db.get_user(op_username,'username')["ID"]
            await show_score_confirmation(db, message, op_id, score, origin.message_id, league_info)
        except KeyError:
            await message.reply_text(f'Игрок {op_username} не найден в базе данных')

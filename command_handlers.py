from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode


from utils.tournament_utils import TournamentUtils
from utils.config_utils import CONFIG
from score_processor import ScoreProcessor
from utils.users_database import UsersDatabaseCSV
from utils.super_league_registrator import SuperLeagueRegistrator

import re
import random

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

        stage = tour_db.get_stage()
        if stage == 'GROUP-COMPLETE':
            tour_db.make_playoff()
            await make_post(context.bot, tour_db.get_status())
        elif stage == 'PLAYOFF-COMPLETE':
            await make_post(context.bot, tour_db.get_summary())

async def make_post(bot, post):
    CHANNEL_USERNAME = f"@{CONFIG.get('channel_username')}"
    await bot.send_message(chat_id=CHANNEL_USERNAME, text=post, parse_mode=ParseMode.HTML)  

async def update_post(bot, edit_id, tag, season) -> None:
    CHANNEL_USERNAME = f"@{CONFIG.get('channel_username')}"
    league_db = getLeagueDatabase(tag, season)
    new_text = league_db.get_status()

    try:
        await bot.edit_message_text(chat_id=CHANNEL_USERNAME, message_id=edit_id, text=new_text, parse_mode=ParseMode.HTML)
    except:
        return
    
def parse_channel_post(text):
    lines = text.splitlines()

    if lines[0] == 'Лига Чемпионов':
        tag = 'CL'
    elif lines[0] == 'Лига Европы':
        tag = 'EL'
    elif lines[0].startswith('Суперлига'):
        tag = 'SL'
    else:
        print(f"[parse_channel_post] Wrong league name {lines[0]}")
        return None
    
    try:
        _, season = lines[1].split()
        season = int(season)
    except:
        return None
    
    print(f"[parse_channel_post] {tag} {season}")
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
    # Check if the message text matches 'ник'
    if 'ник' in words:
        print(words)
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
    lowercased_words = [word.lower() for word in words]
    for word in list:
        if word not in lowercased_words:
            return False
    return True
    

async def process_request(message, is_admin):
    user = message.from_user

    clean_text = re.sub(r'[.,?!\-]', ' ', message.text)
    words = clean_text.split()[1:]
    print(words)
    db = getUsersDatabase()

    if check_pattern(words, 'рейтинг лиги'):
        await message.reply_text(db.get_rating_table())
        return
    
    if check_pattern(words, 'мой рейтинг'):
        for word in words:
            try:
                rating = int(word)        
                respond = db.update_record(user.id, user.username, 'rate', rating)
                await message.reply_text(respond)
                return
            except ValueError:
                continue

        await message.reply_text("Не нашел целое число в сообщении")        
        return
    
    if check_pattern(words, 'мой ник'):
        for word in words:
            if word.lower() == 'мой' or word.lower() == 'ник':
                continue

            respond = db.update_record(user.id, user.username, 'nick',word)
            await message.reply_text(respond)
            return

        await message.reply_text("Не смог записать ник")        
        return
    
    pattern = 'вычеркни рейтинг'
    if check_pattern(words, pattern):
        if not is_admin:
            return

        for word in words:
            if word.lower() in pattern:
                continue
            username = word
            if username[0] == '@':
                username = username[1:]

            try:
                usr = db.get_user(username, 'username')
                db.update_record(usr['ID'], username, 'active',0)
                await message.reply_text(f"Пользователь @{username} вычеркнут из Базы Данных")
            except KeyError:
                await message.reply_text(f"Пользователь @{username} не найден в Базе Данных")
        return
    
    if check_pattern(words, 'статус'):
        await message.reply_text(f"Статус турнира смотри в канале: https://t.me/grandleaguen")
        return
    
    if check_pattern(words, 'кто не участвует'):
        filtered_users = [user for user in db.get_all_users() if user['league'] == '' and user['active'] == 1]
        
        respond = ''.join(f"@{user['username']} [{user['rate']}]\n" for user in filtered_users)
        await message.reply_text(respond)
        return
    


    default_respond = (
        f"Привет, {user.username}! Я понимаю следующие команды:\n\n"
        f"'бот, рейтинг лиги' - выведу участников лиги и их рейтинг в РИ\n\n"
        f"'бот, вычеркни рейтинг @username' - убрать участника из рейтинга лиги (admin)\n\n"
        f"'бот, мой рейтинг 1234' - запишу максимальное кол-во кубков в РИ\n\n"
        f"'бот, мой ник nick' - запишу ник в FC Mobile\n\n"
        f"'бот, кто не участвует' - список игроков, не заявленних ни на один турнир\n\n"
    )

    await message.reply_text(default_respond)
    
    

async def reply_in_common_chat(message, is_admin):
    if not message.text:
        return
    
    lower_text = message.text.lower()
    if lower_text.startswith('бот'):
        await process_request(message, is_admin)
        return

    if message.reply_to_message:
        await process_replay(message)

superleague_lists = {}
registrated_users = []

async def reply_in_superleague_chat(message, is_admin, bot):
    if not message.text:
        return
    user = message.from_user
    
    lower_text = message.text.lower()
    if lower_text.startswith('бот'):
        clean_text = re.sub(r'[.,?!\-]', ' ', message.text)
        words = clean_text.split()[1:]
        print(words)

        if is_admin and check_pattern(words, 'регистрируй'):
            channel_post = message.reply_to_message
            if not channel_post:
                return
            
            print(channel_post)
            sent_message = await bot.send_message(chat_id=message.chat.id, message_thread_id=message.message_thread_id, text=channel_post.text) 
            if sent_message.id not in superleague_lists:
                superleague_lists[sent_message.id] = sent_message.text        
            return
        
        if check_pattern(words, '+1'):
            if len(superleague_lists) == 0:
                await message.reply_text("Регистрация не стартовала")

            if user.username is None:
                await message.reply_text("Установите юзернейм")
                
            if user.username in registrated_users:
                await message.reply_text("Вы уже зарегистрированы!")
                return

            registrator = SuperLeagueRegistrator()
            keys = []
            for key, text in superleague_lists.items():
                if not registrator.get_group_if_registration_complete(text):
                    keys.append(key)

            if len(keys) == 0:
                await message.reply_text("Регистрация завершена!")
                return
            
            key = random.choice(keys) 
            try: 
                lines = registrator.extract_lines_with_teams(superleague_lists[key])
                res = registrator.assign_user_to_random_line(lines, user.username)
                registrated_users.append(user.username)
                await message.reply_text(res)
                respond = '\n'.join(lines)
                superleague_lists[key] = respond
                await bot.edit_message_text(chat_id=message.chat.id, message_id=key, text=respond)

                db = getUsersDatabase()
                db.add_user(user.id, user.username)
            except:
                pass


async def reply_to_private(message, context):
    sender_id = message.from_user.id
    if sender_id != int(CONFIG.get('owner_id')):
        return

    EL = getLeagueDatabase('EL', 10)
    CL = getLeagueDatabase('CL', 10)

    if message.text == 'Го регистрацию':  
        await make_post(context.bot, CL.get_status())
        await make_post(context.bot, EL.get_status())
        await message.reply_text("Posted!")
    elif message.text == 'Го турнир':
        CL.make_groups(6) 
        EL.make_groups(4)
        await make_post(context.bot, CL.get_status())
        await make_post(context.bot, EL.get_status())
        await message.reply_text("Posted!")
    elif 'статус' in message.text:
        try:
            season = int(message.text.split()[2])
            tag = 'CL' if 'лч' in message.text else 'EL'
            CL = getLeagueDatabase(tag, season)
            await message.reply_html(CL.get_status(True))
        except Exception as e:
            # Log the exception if needed
            print(f"Error fetching user data: {e}")

    else:
        await message.reply_text("Го регистрацию, турнир?")

async def reply_to_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    chat_type = message.chat.type
    sender_id = message.from_user.id

    if chat_type == "private":
        await reply_to_private(message, context)
        return
    
    if chat_type not in ["group", "supergroup"]:
        return

    chat_id = update.effective_chat.id
    
    chat_admins = await context.bot.get_chat_administrators(chat_id)
    is_admin = any(admin.user.id == sender_id for admin in chat_admins)
    channel_post = message.reply_to_message

    if message.chat.title == CONFIG.get('superleague_group'):
        print(f"[reply_to_comment] In the superleague group")
        await reply_in_superleague_chat(message, is_admin, context.bot)
        return


    if message.chat.title == CONFIG.get('group_title'):
        print(f"[reply_to_comment] In the main group")
        if channel_post and is_admin and message.text.lower() == 'бан':
            try:
                ban_id = channel_post.from_user.id
                await context.bot.ban_chat_member(chat_id, ban_id)
            except Exception as e:
                # Log the exception if needed
                print(f"Error fetching user data: {e}")
                return
            return

        await reply_in_common_chat(message, is_admin)
        return

    if channel_post and channel_post.forward_origin:
        origin = channel_post.forward_origin
        from_chat = origin.chat.username
        if from_chat != CONFIG.get('channel_username'):
            print("[parse_channel_post] wrong chat name") 
            return
    else:
        return

    league_info = parse_channel_post(channel_post.text)
    if not league_info:
        return

    words = parse_bot_request(message.text)
    if words is None:
        return

    print(f"[reply_to_comment] In the channel comments")
    db = getUsersDatabase()

    if words[0] == '+1':
        if league_info['tag'] == 'CL':
            await message.reply_text(f'Регистрация в ЛЧ недоступна!')
            return
        
        LE = getLeagueDatabase('EL', league_info['season'])
        print(LE.get_stage())
        if LE.get_stage() != 'NOT-STARTED':
            await message.reply_text(f'Регистрация завершена!')
            return           
        
        user = message.from_user
        try:         
            player = db.get_user(user.id)
            if player['league'] == 'CL':
                await message.reply_text(f'@{user.username}, ты учавствуешь в ЛЧ!')
                return
        except KeyError:
            pass

        db.update_record(user.id, user.username, 'league','EL')
        await update_post(context.bot, origin.message_id, league_info['tag'], league_info['season'])
        await message.reply_text(f'@{user.username}, записал тебя в участники ЛЕ!')
        return 


    score_processor = ScoreProcessor(words)
    result = score_processor.get_report()
    if result:
        op_username, score = result
        print(op_username, score)
        try:
            op_id = db.get_user(op_username,'username')["ID"]
            await show_score_confirmation(db, message, op_id, score, origin.message_id, league_info)
        except KeyError:
            await message.reply_text(f'Игрок {op_username} не найден в базе данных')

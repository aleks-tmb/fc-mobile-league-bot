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

def getLeagueDatabase(tag):
    db = getUsersDatabase()
    return TournamentUtils(db, tag, CONFIG.get('database_path'), CONFIG.get('tour_number'))


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

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = getUsersDatabase()
    user_id = None
    tag = None
         
    try:
        player = db.get_user(update.message.from_user["id"])  
        if player['league'] in ['CL', 'EL']:
            user_id = player['ID']
            tag = player['league']
    except KeyError:
        pass  
  
    if tag is None:
        tag = 'CL'

    await show_status(update.message, tag, user_id)

async def get_rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_user_request(user)

    db = getUsersDatabase()
    await update.message.reply_text(db.get_rating_table())


async def perform_draw(message):
    CL_db = getLeagueDatabase('CL')
    LE_db = getLeagueDatabase('EL')
    stage = CL_db.get_stage()
    print(stage)

    if stage == 'NOT-STARTED':
        await message.reply_text(CL_db.make_groups(4))
        await message.reply_text(LE_db.make_groups(4))
    elif stage == 'GROUP':          
        await message.reply_text(CL_db.make_playoff(int(CONFIG.get('playoff_pairs'))))
        await message.reply_text(LE_db.make_playoff(int(CONFIG.get('playoff_pairs'))))
    
    await message.edit_reply_markup(reply_markup=None)
    global draw_in_progress
    draw_in_progress = False


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button presses."""
    query = update.callback_query
    await query.answer()

    user = query.from_user.username
    if not user:
        return

    message_id = query.message.message_id

    # Initialize reactions for this message if not present
    if message_id not in reactions:
        reactions[message_id] = set()

    # Add the reaction to the user's set for this message
    reactions[message_id].add(user)

    # Calculate the count of each reaction for this message
    like_count = len(reactions[message_id])

    if like_count >= int(CONFIG.get('reactions_count')):
        await perform_draw(query.message)
        return 

    new_reply_markup = build_react_counter(like_count)
    # Only update the message if the reply markup has changed
    if query.message.reply_markup != new_reply_markup:
        await query.edit_message_reply_markup(reply_markup=new_reply_markup)


async def reply_to_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    
    chat_type = update.message.chat.type
    message_text = update.message.text

    # Ensure the bot responds only in group chats
    if chat_type in ['group', 'supergroup']:
        # Respond to tagged messages
        BOT_USERNAME = CONFIG.get('bot_username')
        if f'@{BOT_USERNAME}' in message_text:
            await process_request(update.message, context)
    else:
        await update.message.reply_text('Я отвечаю только в групповом чате')

 
async def process_request(message, context):
    username = message.from_user.username

    words = message.text.split()
    if words[0][1:] != CONFIG.get('bot_username'):
        return
    words = words[1:]
    message_text = ' '.join(words)
    message_text = message_text.lower()
    print(message_text)

    if '@' in message_text:
        score_processor = ScoreProcessor(words)
        result = score_processor.get_report()
        if result:
            op_username, score = result
            print(op_username, score)
            try:
                db = getUsersDatabase()
                op_id = db.get_user(op_username,'username')["ID"]
                await show_score_confirmation(db, context, message, op_id, score)
            except KeyError:
                await message.reply_text(f'Игрок {op_username} не найден в базе данных')

        else:
            respond = f'Я не смог разобрать результат матча, {username}\n'
            respond += "Я понимаю следующие форматы:\n"
            respond += "1) я проиграл @username 0:1\n"
            respond += "2) я выиграл у @username 1:0\n"
            respond += "3) я сыграл вничью с @username 1:0"
            await message.reply_text(respond)
    elif 'статус ле' == message_text or 'статус лч' == message_text:
        tag = 'CL' if 'ле' not in message_text else 'EL'
        await show_status(message, tag)        
    elif 'жереб' in message_text:
        await init_draw(message)
    elif ('мой' in message_text) and ('рейт' in message_text):
        await set_rating(message)
    # elif 'истори' in message_text:
    #     await show_history(message)
    else:
        default_respond = f'Привет, {username}! Я понимаю следующие команды, которые ты мне можешь написать:\n\n'
        default_respond += "'статус ЛЕ' - результаты Лиги Европы\n\n"
        default_respond += "'статус ЛЧ' - результаты Лиги Чемпионов\n\n"
        default_respond += "'мой рейтинг 1234' - запишу максимальное кол-во кубков в РИ\n\n"
        default_respond += "'жеребьевка' - проведу жеребьевку турнира по РИ\n\n"
        # default_respond += "'история' - покажу призеров предыдущих турниров\n\n"
        default_respond += "'я выиграл/проиграл/ничья с @username 2:0' - внесу результат матча в таблицу\n\n"
        await message.reply_text(default_respond)



async def show_status(message, tag, user_id = None):
    log_user_request(message.from_user, 'show_status')

    league_db = getLeagueDatabase(tag)
    respond = league_db.get_status(user_id)
    await message.reply_html(f'<pre>{respond}</pre>')

async def init_draw(message):
    user = message.from_user
    chat = message.chat
    log_user_request(user)

    if draw_in_progress:
        return

    if chat.type not in ['group', 'supergroup']:
        await message.reply_text('Доступно только для группового чата')
        return

    if await is_user_admin(chat, user):
        CL_db = getLeagueDatabase('CL')
        LE_db = getLeagueDatabase('EL')
        stage = CL_db.get_stage()
        print(stage)

        N = CONFIG.get('reactions_count')

        if CL_db.get_stage() == 'NOT-STARTED':
            await message.reply_text(f'Проведу жеребьевку турнира на {N} реакций 😎', reply_markup=build_react_counter())
        elif CL_db.get_stage() == 'GROUP-COMPLETE' and LE_db.get_stage() == 'GROUP-COMPLETE':  
            await message.reply_text(f'Проведу жеребьевку плей-офф на {N} реакций 😎', reply_markup=build_react_counter())
        else:
            await message.reply_text('Не все мачти сыграны')
    else:
        await message.reply_text('Доступно только для админов')

async def set_rating(message):
    user = message.from_user

    if user.username is None:
        message.reply_text("Братишка, установи username в Телеге, пожалуйста :)")
        return

    db = getUsersDatabase()

    for word in message.text.split():
        try:
            rating = int(word)        
            respond = db.update_rating(user.id, user.username, rating)
            await message.reply_text(respond)
            return
        except ValueError:
            continue

    await message.reply_text("Не нашел целое число в сообщении :(")

async def show_score_confirmation(db, context, message, op_id, score, edit_message_id, tag):
    user_id = message.from_user.id
    s = f"{user_id}_{op_id}_{score[0]}_{score[1]}_{edit_message_id}_{tag}"
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
        tour_db = getLeagueDatabase(tag)
        respond = tour_db.write_score(id_main, id1, (g0, g1))
    
    await query.answer()
    await query.edit_message_text(text=respond)
    
    # if tour_db.get_stage() == 'PLAYOFF-COMPLETE':
    #     if respond == 'Результат зафиксирован!':
    #         await query.message.reply_text(tour_db.get_summary())

    if respond == 'Результат зафиксирован!':
        await update_post(context.bot, edit_id, tag)


async def post_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.message.from_user.id
    except:
        return

    if user_id != int(CONFIG.get('owner_id')):
        await update.message.reply_text('Restricted!')  
        return

    CHANNEL_USERNAME = f"@{CONFIG.get('channel_username')}"
    for tag in ['CL','EL']:
        league_db = getLeagueDatabase(tag)
        respond = f'{league_db.get_name()}. Групповой этап.\n\n'
        respond += f'<pre>{league_db.get_status()}</pre>'
        await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=respond, parse_mode=ParseMode.HTML) 
        await update.message.reply_text('Posted!')  

async def update_post(bot, edit_id, tag) -> None:
    CHANNEL_USERNAME = f"@{CONFIG.get('channel_username')}"
    league_db = getLeagueDatabase(tag)
    new_text = f'{league_db.get_name()}. Групповой этап.\n\n'
    new_text += f'<pre>{league_db.get_status()}</pre>'
    await bot.edit_message_text(chat_id=CHANNEL_USERNAME, message_id=edit_id, text=new_text, parse_mode=ParseMode.HTML)

def parse_bot_request(text):
    clean_text = re.sub(r'[.,\-]', ' ', text)
    words = clean_text.split()

    BOT_USERNAME = f"@{CONFIG.get('bot_username')}"
    if words[0].lower() == 'бот' or words[0] == BOT_USERNAME:
        return words[1:]
    return None

async def reply_to_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    channel_post = message.reply_to_message

    if channel_post and channel_post.forward_origin:
        origin = channel_post.forward_origin
    else:
        return

    if origin.chat.username != CONFIG.get('channel_username'):
        print(CONFIG.get('channel_username'))
        print(origin)
        return

    if channel_post.text.startswith('Лига Чемпионов.'):
        tag = 'CL'
    elif channel_post.text.startswith('Лига Европы.'):
        tag = 'EL'
    else:
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
            await show_score_confirmation(db, context, message, op_id, score, origin.message_id, tag)
        except KeyError:
            await message.reply_text(f'Игрок {op_username} не найден в базе данных')

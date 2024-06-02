from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.tournament_utils import TournamentUtils
from utils.spreadsheet_utils import SpreadsheetUtils
from utils.users_database_utils import UsersDatabaseUtils
from utils.config_utils import CONFIG
from score_processor import ScoreProcessor

async def is_user_admin(chat, user):
    admins = await chat.get_administrators()
    for admin in admins:
        if admin.user.id == user.id:
            return True
    return False

def make_results_respond(stage, full):
    try:
        # Initialize the spreadsheet utility and scheduler
        spreadsheet_utils = SpreadsheetUtils(CONFIG.get('key_path'))
        worksheet = spreadsheet_utils.get_worksheet(CONFIG.get('tournament_db'))
        scheduler = TournamentUtils(worksheet)
    except Exception as e:
        return f"Error: {e}"

    if stage not in ['GROUP', 'PLAY-OFF']:
        return "unknown stage"
    
    try:
        if stage == 'GROUP':
            groups = scheduler.get_groups_schedule()
            return [group.compute_table(full) for group in groups.values()]
        elif stage == 'PLAY-OFF':
            return scheduler.get_playoff_schedule()
    except Exception as e:
        return f"Error processing stage {stage}: {e}"

def group_stage_finished():
    try:
        spreadsheet_utils = SpreadsheetUtils(CONFIG.get('key_path'))
        worksheet = spreadsheet_utils.get_worksheet(CONFIG.get('tournament_db'))
        scheduler = TournamentUtils(worksheet)
        groups = scheduler.get_groups_schedule()
    except Exception as e:
        return False
    
    return all(group.all_matches_played() for group in groups.values())

def make_palyoff_draw_respond():
    try:
        spreadsheet_utils = SpreadsheetUtils(CONFIG.get('key_path'))
        worksheet = spreadsheet_utils.get_worksheet(CONFIG.get('tournament_db'))
        scheduler = TournamentUtils(worksheet)
        groups = scheduler.get_groups_schedule()
    except Exception as e:
        return f"Error: {e}"

    potA = []
    potB = []

    for group_id, group in groups.items():
        group.compute_table()
        potA.append(group.items[0].id)
        potB.append(group.items[1].id)

    drawer = Drawer()
    pairs = drawer.make_playoff_draw(potA, potB)

    semis = []
    result = "1/4 финала:\n\n"
    for pair in pairs:
        result += "@{} - @{}\n".format(pair[0], pair[1])
        semis.append("@{}/@{}".format(pair[0], pair[1]))

    result += "\n1/2 финала:\n\n"
    result += "{} - {}\n".format(semis[0], semis[1])
    result += "{} - {}\n".format(semis[2], semis[3])

    result += "\nУдачи!"
    return result

def build_react_counter(like_count=0):
    keyboard = [[InlineKeyboardButton(f"🖕 {like_count}", callback_data='like')]]
    return InlineKeyboardMarkup(keyboard)

def log_user_request(user, module = '-'):
    print(f'[{module.upper()}] You talk with user {user["username"]} and his user ID: {user["id"]}')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_status(update.message)

async def set_rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_user_request(user)

    db = UsersDatabaseUtils(CONFIG.get('key_path'), CONFIG.get('users_db'))
    await update.message.reply_text(db.update_user_rating(user["id"], user["username"], context.args))

async def get_rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_user_request(user)

    db = UsersDatabaseUtils(CONFIG.get('key_path'), CONFIG.get('users_db'))
    await update.message.reply_text(db.get_rating_table())

reactions = {}

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button presses."""
    query = update.callback_query
    await query.answer()

    user = query.from_user.username
    if not user:
        return

    reaction = query.data
    message_id = query.message.message_id

    # Initialize reactions for this message if not present
    if message_id not in reactions:
        reactions[message_id] = set()

    # Add the reaction to the user's set for this message
    reactions[message_id].add(user)

    # Calculate the count of each reaction for this message
    like_count = len(reactions[message_id])

    if like_count >= int(CONFIG.get('reactions_count')):
        await query.message.edit_reply_markup(reply_markup=None)
        db = UsersDatabaseUtils(CONFIG.get('key_path'), CONFIG.get('users_db'))
        participants = db.get_users_list()
        filtered_users = [user for user in participants if user.part == '1']
        usernames = [user.username for user in filtered_users]
        tour_db = TournamentUtils(CONFIG.get('key_path'), CONFIG.get('tournament_db'))
        await query.message.reply_text(tour_db.make_groups(usernames))
        CONFIG['stage'] = 'GROUP'
        return 

    new_reply_markup = build_react_counter(like_count)
    # Only update the message if the reply markup has changed
    if query.message.reply_markup != new_reply_markup:
        await query.edit_message_reply_markup(reply_markup=new_reply_markup)


async def reply_to_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_type = update.message.chat.type
    message_text = update.message.text

    # Ensure the bot responds only in group chats
    if chat_type in ['group', 'supergroup']:
        # Respond to tagged messages
        BOT_USERNAME = CONFIG.get('bot_username')
        if f'@{BOT_USERNAME}' in message_text:
            await process_request(update.message, context)
 
def is_command(words, text):
    return len(words) == 1 and words[0] == text


async def process_request(message, context):
    username = message.from_user.username

    words = message.text.split()
    if words[0][1:] != CONFIG.get('bot_username'):
        return
    words = words[1:]
    message_text = ' '.join(words)
    print(message_text)

    if '@' in message_text:
        score_processor = ScoreProcessor(words)
        result = score_processor.get_report()
        if result:
            op_username, score = result
            print(op_username, score)
            await show_score_confirmation(context, message, username, op_username, score)
        else:
            await message.reply_text(f'Я не смог разобрать результат матча, {username}')
    elif ('статус' in message_text) or ('таблиц' in message_text):
        await show_status(message)
    elif ('зарегай' in message_text) or ('зарегистрируй' in message_text):
        await registrate_user(message)
    elif 'жереб' in message_text:
        await make_draw(message)
    else:
        default_respond = f'Привет, {username}! Я понимаю следующие команды, которые ты мне можешь написать:\n\n'
        default_respond += "'cтатус' - покажу текущие результаты\n\n"
        default_respond += "'полный статус' - покажу текущие результаты с деталями\n\n"
        default_respond += "'зарегистрируй' - внесу в список участников турнира по РИ\n\n"
        default_respond += "'жеребьевка' - проведу жеребьевку турнира по РИ\n\n"
        default_respond += "'я выиграл/проиграл @username 2:0' - внесу результат матча в таблицу\n\n"
        await message.reply_text(default_respond)

async def show_status(message):
    user = message.from_user
    log_user_request(user, 'show_status')

    stage = CONFIG.get('stage')
    if stage == 'REGISTRATION':
        db = UsersDatabaseUtils(CONFIG.get('key_path'), CONFIG.get('users_db'))
        await message.reply_text(db.get_registrated_users())
    elif stage == 'GROUP':
        tour_db = TournamentUtils(CONFIG.get('key_path'), CONFIG.get('tournament_db'))
        groups = tour_db.get_groups_schedule()
        full = 'полн' in message.text.lower()
        messages = [group.compute_table(full) for group in groups.values()]
        respond = '\n\n'.join(messages)
        await message.reply_html(f'<pre>{respond}</pre>')
    else:
        await message.reply_text("----")

async def make_draw(message):
    user = message.from_user
    chat = message.chat
    log_user_request(user)

    if chat.type not in ['group', 'supergroup']:
        await message.reply_text('Доступно только для группового чата')
        return

    if await is_user_admin(chat, user):
        stage = CONFIG.get('stage')
        if stage == 'REGISTRATION':
            users_limit = int(CONFIG.get('users_limit'))
            db = UsersDatabaseUtils(CONFIG.get('key_path'), CONFIG.get('users_db')) 
            if not db.is_registration_finished(users_limit):
                await message.reply_text(f'Регистрация не завершена, нам нужно {users_limit} участников')
            else:
                CONFIG['stage'] = 'WAIT-DRAW'
                N = CONFIG.get('reactions_count')
                await message.reply_text(f'Проведу жеребьевку на {N} реакций 😎', reply_markup=build_react_counter())
        elif stage == 'WAIT-DRAW':
            await message.reply_text('Погоди, ждем жеребьевку')
        elif stage == 'GROUP':
            await message.reply_text('Погоди, идет групповой этап')

    else:
        await message.reply_text('Доступно только для админов')

async def registrate_user(message):
    user = message.from_user
    log_user_request(user)

    db = UsersDatabaseUtils(CONFIG.get('key_path'), CONFIG.get('users_db'))
    users_limit = int(CONFIG.get('users_limit'))
    await message.reply_text(db.registrate_user(user["id"], user["username"], users_limit))

async def show_score_confirmation(context, message, username, op_username, score):
        keyboard = [
            [InlineKeyboardButton("Да", callback_data='button1')],
            [InlineKeyboardButton("Нет", callback_data='button2')]
        ]
        context.user_data['init_user_id'] = message.from_user.id
        context.user_data['record'] = (username, op_username, score)
        context.user_data['clicked'] = False
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text(f'@{username} {score[0]}:{score[1]} @{op_username}', reply_markup=reply_markup)

async def button1_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    init_user_id = context.user_data.get('init_user_id')
    # Check if the user is the initiating user
    if user.id != init_user_id:
        await query.answer(text=f"Вы не можете подтвердить это действие", show_alert=True)
        return

    (username, op_username, score) =  context.user_data.get('record')
    if context.user_data.get('clicked'):
        return
    context.user_data['clicked'] = True

    tour_db = TournamentUtils(CONFIG.get('key_path'), CONFIG.get('tournament_db'))
    respond = tour_db.write_score(username, op_username, score)
    
    # Handle the button click for the initiating user
    await query.answer()
    await query.edit_message_text(text=respond)

async def button2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    init_user_id = context.user_data.get('init_user_id')

    # Check if the user is the initiating user
    if user.id != init_user_id:
        await query.answer(text=f"Вы не можете отменить это действие", show_alert=True)
        return

    # Handle the button click for the initiating user
    await query.answer()
    await query.edit_message_text(text="Отменяю!")


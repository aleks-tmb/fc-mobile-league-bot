from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.tournament_utils import TournamentUtils
from utils.spreadsheet_utils import SpreadsheetUtils
from utils.users_database_utils import UsersDatabaseUtils
from utils.drawer import Drawer
from utils.config_utils import CONFIG

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

def log_user_request(user):
    print(f'[register] You talk with user {user["username"]} and his user ID: {user["id"]}')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_user_request(user)

    db = UsersDatabaseUtils(CONFIG.get('key_path'), CONFIG.get('users_db'))
    await update.message.reply_text(db.get_registrated_users())

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_user_request(user)

    db = UsersDatabaseUtils(CONFIG.get('key_path'), CONFIG.get('users_db'))
    users_limit = int(CONFIG.get('users_limit'))
    await update.message.reply_text(db.registrate_user(user["id"], user["username"], users_limit))

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

async def next_stage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat = update.message.chat
    print(f'[register] You talk with user {user["username"]} and his user ID: {user["id"]}')

    if chat.type in ['group', 'supergroup']:
        if await is_user_admin(chat, user):
            stage = CONFIG.get('stage')
            if stage == 'PLAY-OFF':
                await update.message.reply_text('Погоди, идет плей-офф')
            elif stage == 'WAIT-DRAW':
                await update.message.reply_text('Погоди, ждем жеребьевку')
            elif stage == 'GROUP':
                if group_stage_finished():
                    CONFIG['stage'] = 'WAIT-DRAW'
                    await update.message.reply_text('Проведу жеребьевку на 7 реакций 😎', reply_markup=build_react_counter())
                else:
                    await update.message.reply_text('Групповой этап не завершен - не все матчи сыграны')
        else:
            await update.message.reply_text('Доступно только для админов')
    else:
        await update.message.reply_text('Доступно только для группового чата')

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

    if like_count >= 7:
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.reply_text(make_palyoff_draw_respond())
        CONFIG['stage'] = 'PLAY-OFF'
        return 

    new_reply_markup = build_react_counter(like_count)
    # Only update the message if the reply markup has changed
    if query.message.reply_markup != new_reply_markup:
        await query.edit_message_reply_markup(reply_markup=new_reply_markup)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.schedule_io_utils import ScheduleIOUtils
from utils.spreadsheet_utils import SpreadsheetUtils
from utils.users_database_utils import UsersDatabaseUtils
from utils.drawer import Drawer
from utils.config_utils import CONFIG

def make_group_table_respond(Full = False):
    try:
        spreadsheet_utils = SpreadsheetUtils(CONFIG.get('key_path'))
        spreadsheet = spreadsheet_utils.get_spreadsheet_by_id(CONFIG.get('tournament_db'))
        worksheet = spreadsheet.get_worksheet(0)  # For the first worksheet
        scheduler = ScheduleIOUtils(worksheet)
        groups = scheduler.get_groups_schedule()
        messages = []
        for group in groups.values():
            messages.append(group.compute_table(Full))
        return messages
    except Exception as e:
        return f"Error: {e}"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    print(f'[start] You talk with user {user["username"]} and his user ID: {user["id"]}')

    full = len(context.args) == 1 and context.args[0] == 'full'
    if full:
        for message in make_group_table_respond(full):
            await update.message.reply_html(f'<pre>{message}</pre>')
    else:
        res = '\n\n'.join(make_group_table_respond(full))
        await update.message.reply_html(f'<pre>{res}</pre>')

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    print(f'[register] You talk with user {user["username"]} and his user ID: {user["id"]}')
    await update.message.reply_text(register_user_respond(user["id"], user["username"]))

async def set_rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    print(f'[set_rating] You talk with user {user["username"]} and his user ID: {user["id"]}')
    if len(context.args) != 1:
        await update.message.reply_text("Необходимо указать свой рейтинг, например: '/setrating 123'")
        return
    await update.message.reply_text(set_user_rating_respond(user["id"], user["username"], context.args[0]))

async def next_stage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

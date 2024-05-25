import os
import argparse
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from utils.spreadsheet_utils import SpreadsheetUtils
from utils.users_database_utils import UsersDatabaseUtils

CONFIG = {}

def read_config():
    file_path = 'config.txt'
    if not os.path.exists(file_path):
        print("Config does not exist.")
        return False

    try:
        with open(file_path, 'r') as file:
            for line in file.readlines():
                key, value = line.strip().split('=')
                CONFIG[key] = value
    except Exception as e:
        print(f"Error reading config: {e}")
        return False
    return True

def read_table(keyfile_path, spreadsheet_id):
    try:
        spreadsheet_utils = SpreadsheetUtils(keyfile_path)
        spreadsheet = spreadsheet_utils.get_spreadsheet_by_id(spreadsheet_id)
        worksheet = spreadsheet.get_worksheet(0)  # For the first worksheet
        scheduler = ScheduleIOUtils(worksheet)
        return scheduler.get_playoff_schedule()
    except Exception as e:
        return f"Error: {e}"

def register_user_respond(user_id, username):
    if username is None:
        return "Братишка, установи username в Телеге, пожалуйста :)"

    db = UsersDatabaseUtils()
    if not db.connect(CONFIG.get('key_path'), CONFIG.get('users_db')):
        return "Failed to connect to the database."

    row_id = db.get_row_by_user_id(user_id)
    if row_id is not None:
        if db.get_user_info(user_id, 'part') == '1':
            return f"{username}, ты УЖЕ зарегистрирован!"

    db.add_user(user_id, username)
    db.set_user_info(user_id, 'part', '1')
    return f"Спасибо за регистрацию в турнире, {username}! Удачи!"

def participants_respond():
    db = UsersDatabaseUtils()
    if not db.connect(CONFIG.get('key_path'), CONFIG.get('users_db')):
        return "Failed to connect to the database."

    participants = db.get_participants_list()
    sorted_participants = sorted(participants, key=lambda x: x.rate, reverse=True)

    result = "Участники и их рейтинг в РИ:\n\n"
    for i, participant in enumerate(sorted_participants, start=1):
        result += f"{i}. {participant.username} [{participant.rate}]\n"
    return result

def set_user_rating_respond(user_id, username, rating):
    if username is None:
        return "Братишка, установи username в Телеге, пожалуйста :)"

    db = UsersDatabaseUtils()
    if not db.connect(CONFIG.get('key_path'), CONFIG.get('users_db')):
        return "Failed to connect to the database."

    db.add_user(user_id, username)
    try:
        rating = int(rating)
        if db.set_user_info(user_id, 'fcrate', rating):
            return f"Рейтинг обновлен: {rating}"
        else:
            return "Failed to update rating"
    except ValueError:
        return "Рейтинг должен быть целым числом!"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    print(f'[start] You talk with user {user["username"]} and his user ID: {user["id"]}')
    await update.message.reply_text(participants_respond())

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

def init_bot(token):
    print("Starting bot...")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("showstatus", start_command))
    application.add_handler(CommandHandler("register", register_command))
    application.add_handler(CommandHandler("setrating", set_rating_command))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    if not read_config():
        print("Failed to read the config.")
        return
    print(CONFIG)
    init_bot(CONFIG.get('bot_token'))

if __name__ == "__main__":
    main()

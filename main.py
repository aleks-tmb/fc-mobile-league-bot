import os
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters, 
    ContextTypes)
from command_handlers import (
    status_command,
    button_callback,
    score_confirm_callback,
    get_rating_command,
    reply_to_message)
from utils.config_utils import read_config
from utils.config_utils import CONFIG
from utils.tournament_utils import TournamentUtils
from utils.spreadsheet_utils import SpreadsheetUtils

from utils.users_database import UsersDatabaseCSV

def init_bot(token):
    print("Starting bot...")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("getrating", get_rating_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), reply_to_message))
    application.add_handler(CallbackQueryHandler(score_confirm_callback, pattern=r'^confirm_(yes|no)_\d+_\d+_\d_\d$'))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    read_config()
    print(CONFIG) 
    init_bot(CONFIG.get('bot_token'))




if __name__ == "__main__":
    main()
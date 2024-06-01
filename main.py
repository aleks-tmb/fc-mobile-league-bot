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
    start_command,
    register_command,
    next_stage_command,
    button_callback,
    set_rating_command,
    get_rating_command,
    reply_to_message)
from utils.config_utils import read_config
from utils.config_utils import CONFIG
from utils.users_database_utils import UsersDatabaseUtils
from utils.tournament_utils import TournamentUtils

def init_bot(token):
    print("Starting bot...")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("status", start_command))
    application.add_handler(CommandHandler("nextstage", next_stage_command))
    application.add_handler(CommandHandler("registrate", register_command))
    application.add_handler(CommandHandler("setrate", set_rating_command))
    application.add_handler(CommandHandler("getrate", get_rating_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), reply_to_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    read_config()
    print(CONFIG)
    init_bot(CONFIG.get('bot_token'))


if __name__ == "__main__":
    main()
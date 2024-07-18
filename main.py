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
    post_to_channel,
    score_confirm_callback,
    reply_to_comment)
from utils.config_utils import read_config
from utils.config_utils import CONFIG
from utils.tournament_utils import TournamentUtils
from utils.users_database import UsersDatabaseCSV

from command_handlers import getLeagueDatabase
from command_handlers import getUsersDatabase


def init_bot(token):
    print("Starting bot...")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler('post', post_to_channel))
    application.add_handler(CallbackQueryHandler(score_confirm_callback, pattern=r'^confirm_(yes|no)_\d+_\d+_\d_\d_\d+_(CL|EL)_\d+$')) 
    application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), reply_to_comment))

    application.run_polling(allowed_updates=Update.ALL_TYPES)



def main():
    read_config()
    print(CONFIG) 
    init_bot(CONFIG.get('bot_token'))

if __name__ == "__main__":
    main()

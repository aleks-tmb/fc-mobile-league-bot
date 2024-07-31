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
    application.add_handler(CallbackQueryHandler(score_confirm_callback, pattern=r'^confirm_(yes|no)_\d+_\d+_\d+_\d+_\d+_(CL|EL|SL)_\d+$')) 
    application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), reply_to_comment))

    application.run_polling(allowed_updates=Update.ALL_TYPES)



def main():
    read_config()
    print(CONFIG) 
    init_bot(CONFIG.get('bot_token'))
    # CL = getLeagueDatabase('CL', 2)
    # print(CL.get_status() + CL.get_summary(False))

if __name__ == "__main__":
    main()

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
    post_to_channel,
    button_callback,
    score_confirm_callback,
    get_rating_command,
    reply_to_message,
    reply_to_comment)
from utils.config_utils import read_config
from utils.config_utils import CONFIG
from utils.tournament_utils import TournamentUtils
from utils.users_database import UsersDatabaseCSV


def init_bot(token):
    print("Starting bot...")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler('post', post_to_channel))
    application.add_handler(CallbackQueryHandler(score_confirm_callback, pattern=r'^confirm_(yes|no)_\d+_\d+_\d_\d_\d+_(CL|EL)$'))
    application.add_handler(CallbackQueryHandler(button_callback))   
    application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), reply_to_comment))

    application.run_polling(allowed_updates=Update.ALL_TYPES)



def main():
    read_config()
    print(CONFIG) 
    init_bot(CONFIG.get('bot_token'))



if __name__ == "__main__":
    main()

import argparse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, CallbackContext
from utils.spreadsheet_utils import SpreadsheetUtils
from utils.schedule_io_utils import ScheduleIOUtils


SPREADSHEET_ID = ""
KEYFILE = ""

def read_table(keyfile_path, spreadsheet_id):
    try:
        spreadsheet_utils = SpreadsheetUtils(keyfile_path)
        spreadsheet = spreadsheet_utils.get_spreadsheet_by_id(spreadsheet_id)
        worksheet = spreadsheet.get_worksheet(0)  # For the first worksheet
        scheduler = ScheduleIOUtils(worksheet)
        return scheduler.get_playoff_schedule()
    except FileNotFoundError as e:
        return f"Error: Keyfile not found at {keyfile_path}. Exception: {e}"
    except PermissionError as e:
        return f"Error: Permission denied when accessing keyfile at {keyfile_path}. Exception: {e}"
    except ConnectionError as e:
        return f"Error: Failed to connect to the spreadsheet with ID {spreadsheet_id}. Exception: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def read_args():
    parser = argparse.ArgumentParser(description='Telegram Bot Options for FC Mobile League Tournament')
    parser.add_argument('--spreadsheet_id', required=True, help='The ID of the Google Spreadsheet')
    parser.add_argument('--bot_token', required=True, help='The ID of the Telegram Bot Token')
    parser.add_argument('--key_file', required=True, help='The ID of the json keyfile')
    args = parser.parse_args()
    return args

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    print(f'You talk with user {user["username"]} and his user ID: {user["id"]}')
    res = read_table(KEYFILE, SPREADSHEET_ID)
    await update.message.reply_text(res)


def init_bot(token):
    print("Starting bot...")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("showresults", start_command))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    args = read_args()
    global SPREADSHEET_ID
    global KEYFILE
    SPREADSHEET_ID = args.spreadsheet_id
    KEYFILE = args.key_file
    init_bot(args.bot_token)

if __name__ == "__main__":
    main()

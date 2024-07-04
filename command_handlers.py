from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.tournament_utils import TournamentUtils
from utils.spreadsheet_utils import SpreadsheetUtils
from utils.config_utils import CONFIG
from score_processor import ScoreProcessor
from utils.users_database import UsersDatabaseCSV

async def is_user_admin(chat, user):
    admins = await chat.get_administrators()
    for admin in admins:
        if admin.user.id == user.id:
            return True
    return False

def build_react_counter(like_count=0):
    keyboard = [[InlineKeyboardButton(f"🖕 {like_count}", callback_data='like')]]
    return InlineKeyboardMarkup(keyboard)

def log_user_request(user, module = '-'):
    print(f'[{module.upper()}] You talk with user {user["username"]} and his user ID: {user["id"]}')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_status(update.message, False)

async def get_rating_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_user_request(user)

    db = UsersDatabaseCSV(CONFIG.get('users_db'))
    await update.message.reply_text(db.get_rating_table())

reactions = {}

async def draw_group_stage(message):
    db = UsersDatabaseCSV(CONFIG.get('users_db'))
    CL_db = TournamentUtils(db, 'CL')
    LE_db = TournamentUtils(db, 'EL')

    await message.edit_reply_markup(reply_markup=None)
    await message.reply_text(CL_db.make_groups(4))
    await message.reply_text(LE_db.make_groups(4))
    CONFIG['stage'] = 'GROUP'

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
        stage = CONFIG.get('stage')
        if stage == 'WAIT-DRAW':
            await draw_group_stage(query.message)
        elif stage == 'WAIT-PLAYOFF-DRAW':
            db = UsersDatabaseCSV(CONFIG.get('users_db'))
            CL_db = TournamentUtils(db, 'CL')
            LE_db = TournamentUtils(db, 'EL')            
            cl_respond = CL_db.make_playoff(int(CONFIG.get('playoff_pairs')))
            le_respond = LE_db.make_playoff(int(CONFIG.get('playoff_pairs')))
            CONFIG['stage'] = 'PLAY-OFF'
            await query.message.reply_text(cl_respond)
            await query.message.reply_text(le_respond)
            
        return 

    new_reply_markup = build_react_counter(like_count)
    # Only update the message if the reply markup has changed
    if query.message.reply_markup != new_reply_markup:
        await query.edit_message_reply_markup(reply_markup=new_reply_markup)


async def reply_to_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    
    chat_type = update.message.chat.type
    message_text = update.message.text

    # Ensure the bot responds only in group chats
    if chat_type in ['group', 'supergroup']:
        # Respond to tagged messages
        BOT_USERNAME = CONFIG.get('bot_username')
        if f'@{BOT_USERNAME}' in message_text:
            await process_request(update.message, context)
    else:
        await update.message.reply_text('Я отвечаю только в групповом чате')

 
async def process_request(message, context):
    username = message.from_user.username

    words = message.text.split()
    if words[0][1:] != CONFIG.get('bot_username'):
        return
    words = words[1:]
    message_text = ' '.join(words)
    message_text = message_text.lower()
    print(message_text)

    if '@' in message_text:
        score_processor = ScoreProcessor(words)
        result = score_processor.get_report()
        if result:
            op_username, score = result
            print(op_username, score)
            try:
                db = UsersDatabaseCSV(CONFIG.get('users_db'))
                op_id = db.get_user(op_username,'username')["ID"]
                await show_score_confirmation(db, context, message, op_id, score)
            except KeyError:
                await message.reply_text(f'Игрок {op_username} не найден в базе данных')

        else:
            respond = f'Я не смог разобрать результат матча, {username}\n'
            respond += "Я понимаю следующие форматы:\n"
            respond += "1) я проиграл @username 0:1\n"
            respond += "2) я выиграл у @username 1:0\n"
            respond += "3) я сыграл вничью с @username 1:0"
            await message.reply_text(respond)
    elif 'статус ле' == message_text or 'статус лч' == message_text:
        await show_status(message)
    elif ('новый турнир' == message_text):
        await make_draw(message)
    elif 'жереб' in message_text:
        await make_draw(message)
    elif ('мой' in message_text) and ('рейт' in message_text):
        await set_rating(message)
    # elif 'истори' in message_text:
    #     await show_history(message)
    else:
        default_respond = f'Привет, {username}! Я понимаю следующие команды, которые ты мне можешь написать:\n\n'
        default_respond += "'статус ЛЕ' - результаты Лиги Европы\n\n"
        default_respond += "'статус ЛЧ' - результаты Лиги Чемпионов\n\n"
        default_respond += "'мой рейтинг 1234' - запишу максимальное кол-во кубков в РИ\n\n"
        default_respond += "'жеребьевка' - проведу жеребьевку турнира по РИ\n\n"
        default_respond += "'новый турнир' - создам групповой этап нового турнира РИ\n\n"
        # default_respond += "'история' - покажу призеров предыдущих турниров\n\n"
        default_respond += "'я выиграл/проиграл/ничья с @username 2:0' - внесу результат матча в таблицу\n\n"
        await message.reply_text(default_respond)

async def show_status(message, full = True):
    log_user_request(message.from_user, 'show_status')

    db = UsersDatabaseCSV(CONFIG.get('users_db'))
    try:
        player = db.get_user(message.from_user["id"])
    except KeyError:
        await message.reply_text("Вас нет в базе данных Лиги!")
        return

    if full:
        if 'ле' in message.text:
            user_league = 'EL'
        else:
            user_league = 'CL'
    else:
        user_league = player['league']
        if user_league != 'CL' and user_league != 'EL':
            await message.reply_text("На нашел вас в списке участников турниров!")
            return
    
    league_db = TournamentUtils(db, user_league)
    stage = CONFIG.get('stage')

    if stage == 'NEW':
        CL_db = TournamentUtils(db, 'CL')
        EL_db = TournamentUtils(db, 'EL')
        await message.reply_text(CL_db.get_participants())
        await message.reply_text(EL_db.get_participants())
    elif stage == 'GROUP':      
        if full:
            respond = league_db.show_all_tables(False)
        else:
            respond = league_db.show_user_table(player['ID'])
        await message.reply_html(f'<pre>{respond}</pre>')
    elif stage == 'PLAY-OFF':
        respond = league_db.get_playoff_schedule()
        await message.reply_text(respond)
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
        print(stage)
        if stage == 'NEW':
            CONFIG['stage'] = 'WAIT-DRAW'
            N = CONFIG.get('reactions_count')
            await message.reply_text(f'Проведу жеребьевку турнира на {N} реакций 😎', reply_markup=build_react_counter())
        elif stage == 'GROUP':
            db = UsersDatabaseCSV(CONFIG.get('users_db'))
            CL_db = TournamentUtils(db, 'CL')
            LE_db = TournamentUtils(db, 'EL')   
            if CL_db.group_stage_finished() and LE_db.group_stage_finished():
                CONFIG['stage'] = 'WAIT-PLAYOFF-DRAW'
                N = CONFIG.get('reactions_count')
                await message.reply_text(f'Проведу жеребьевку плей-офф на {N} реакций 😎', reply_markup=build_react_counter())
            else:
                await message.reply_text(f'Групповой турнир не завершен - не все матчи отыграны')
        elif stage == 'WAIT-DRAW' or stage == 'WAIT-PLAYOFF-DRAW':
            await message.reply_text('Ждем жеребьевку')
        elif stage == 'PLAY-OFF':
            await message.reply_text('Идет плей-офф')
    else:
        await message.reply_text('Доступно только для админов')

async def set_rating(message):
    user = message.from_user

    if user.username is None:
        message.reply_text("Братишка, установи username в Телеге, пожалуйста :)")

    db = UsersDatabaseCSV(CONFIG.get('users_db'))

    for word in message.text.split():
        try:
            rating = int(word)        
            respond = db.update_rating(user.id, user.username, rating)
            await message.reply_text(respond)
            return
        except ValueError:
            continue

    await message.reply_text("Не нашел целое число в сообщении :(")

async def show_score_confirmation(db, context, message, op_id, score):
    user_id = message.from_user.id
    s = f"{user_id}_{op_id}_{score[0]}_{score[1]}"
    print(s)
    keyboard = [
        [InlineKeyboardButton("Да", callback_data=f'confirm_yes_{s}')],
        [InlineKeyboardButton("Нет", callback_data=f'confirm_no_{s}')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    username = db.get_username_by_id(user_id)
    op_username = db.get_username_by_id(op_id)
    await message.reply_text(
        f'@{username} {score[0]}:{score[1]} @{op_username}', 
        reply_markup=reply_markup
    )

async def score_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user

    callback_data = query.data.split('_')
    action = callback_data[1]
    id_main = int(callback_data[2])
    id1 = int(callback_data[3])
    g0 = int(callback_data[4])
    g1 = int(callback_data[5])

    # Check if the user is the initiating user
    if user.id != id_main:
        await query.answer(text="Вы не можете отменить это действие", show_alert=True)
        return

    if action == 'no':
        await query.answer()
        await query.edit_message_text(text="Отменяю!")
        return
    
    # Assuming you have a configuration variable CONFIG defined somewhere
    db = UsersDatabaseCSV(CONFIG.get('users_db'))
    user2 = db.get_user(id1)
    user_league = user2.get('league', '')

    if user_league not in ['CL', 'EL']:
        respond = "Игрок не участвует в турнирах"
    else:
        tour_db = TournamentUtils(db, user_league)
        respond = tour_db.write_score(id_main, id1, (g0, g1))
        if CONFIG['stage'] == 'PLAY-OFF':
            tour_db.update_playoff_path(id_main, id1)
    
    await query.answer()
    await query.edit_message_text(text=respond)
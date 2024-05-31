import logging
from typing import List, Optional, Union
from utils.spreadsheet_utils import SpreadsheetUtils

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Participant:
    def __init__(self, username: str, fc_name: str, rate: int, champ: str, part: str):
        self.username = username
        self.fc_name = fc_name
        self.rate = rate
        self.champ = champ
        self.part = part

class UsersDatabaseUtils:
    UPDATE_RATING_MESSAGE = """
Необходимо указать свой рейтинг целым числом.
Например, если максимальное количество кубков за РИ у тебя 111.8K, то напиши команду: /setrate 111
"""

    COLUMN_MAP = {
        'id': 1,
        'username': 2,
        'fcname': 3,
        'fcrate': 4,
        'part': 5,
        'champ': 6
    }

    def __init__(self, keyfile_path: str, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet_utils = SpreadsheetUtils(keyfile_path)
        self.worksheet = self._get_worksheet()

    def _get_worksheet(self):
        """Get the worksheet object."""
        worksheet = self.spreadsheet_utils.get_worksheet(self.spreadsheet_id)
        if not worksheet:
            logger.error("Problem with accessing the worksheet")
        return worksheet

    def _get_data(self, row: List[str], column_name: str) -> Optional[str]:
        """Get data from a specific column in a row."""
        col_num = self.COLUMN_MAP.get(column_name)
        return row[col_num - 1] if col_num is not None else None

    def add_user(self, user_id: Union[int, str], username: str):
        """Add a new user to the database."""
        if not self.worksheet:
            logger.error("Problem with accessing the database")
            return

        user_id = str(user_id)
        if self._get_row_by_user_id(user_id) is None:
            self.worksheet.append_row([user_id, username, "", 0, '', ''])
            logger.info(f"New user {username} with ID {user_id} added")
        else:
            logger.info(f"User {username} with ID {user_id} already exists")

    def set_user_info(self, user_id: Union[int, str], column_name: str, new_value: str) -> bool:
        """Set user information in the database."""
        if not self.worksheet:
            logger.error("Problem with accessing the database")
            return False

        row_number = self._get_row_by_user_id(user_id)
        if row_number is None:
            logger.error(f"User with ID {user_id} not found")
            return False

        col_num = self.COLUMN_MAP.get(column_name)
        if col_num is None:
            logger.error(f"Column with name {column_name} not found")
            return False

        self.worksheet.update_cell(row_number, col_num, new_value)
        logger.info(f"Set {column_name} as {new_value} for user with ID {user_id}")
        return True

    def get_user_info(self, user_id: Union[int, str], column_name: str) -> Optional[str]:
        """Get user information from the database."""
        if not self.worksheet:
            logger.error("Problem with accessing the database")
            return None

        row_number = self._get_row_by_user_id(user_id)
        if row_number is None:
            logger.error(f"User with ID {user_id} not found")
            return None

        col_num = self.COLUMN_MAP.get(column_name)
        if col_num is None:
            logger.error(f"Column with name {column_name} not found")
            return None

        return self.worksheet.cell(row_number, col_num).value

    def _get_row_by_user_id(self, user_id: Union[int, str]) -> Optional[int]:
        """Get the row number of a user by their ID."""
        if not self.worksheet:
            logger.error("Problem with accessing the database")
            return None

        user_id = str(user_id)
        id_col = self.COLUMN_MAP.get('id')
        users = self.worksheet.col_values(id_col)
        if user_id in users:
            return users.index(user_id) + 1
        else:
            logger.error(f"User with ID {user_id} not found")
            return None

    def get_users_list(self) -> List[Participant]:
        """Get a list of all users."""
        if not self.worksheet:
            logger.error("Problem with accessing the database")
            return []

        participants = []
        for row in self.worksheet.get_all_values()[1:]:  # Skip the header row
            try:
                participant = Participant(
                    self._get_data(row, 'username'),
                    self._get_data(row, 'fcname'),
                    int(self._get_data(row, 'fcrate')),
                    self._get_data(row, 'champ'),
                    self._get_data(row, 'part')
                )
                participants.append(participant)
            except Exception as e:
                logger.error(f"Error processing row {row}: {e}")

        return participants

    def get_rating_table(self) -> str:
        """Get the league rating table."""
        users = self.get_users_list()
        sorted_users = sorted(users, key=lambda x: x.rate, reverse=True)

        respond = "Рейтинг Лиги\n\n"
        for i, participant in enumerate(sorted_users, start=1):
            respond += f"{i}. {participant.username} [{participant.rate}]\n"
        return respond

    def get_registrated_users(self) -> str:
        """Get a list of registered users."""
        users = self.get_users_list()
        filtered_users = [user for user in users if user.part == '1']
        sorted_users = sorted(filtered_users, key=lambda x: x.rate, reverse=True)

        respond = "Зарегистрированные участники\n\n"
        for i, participant in enumerate(sorted_users, start=1):
            respond += f"{i}. {participant.username} [{participant.rate}]\n"
        return respond

    def registrate_user(self, user_id: Union[int, str], username: str, limit: int) -> str:
        if username is None:
            return "Братишка, установи username в Телеге, пожалуйста :)"

        logger.info(f"Registrate user with ID {user_id}")
        users = self.get_users_list()
        filtered_users = [user for user in users if user.part == '1']
        if len(filtered_users) >= limit:
            return "Регистрация на турнир закончена - место больше нет :("

        self.add_user(user_id, username)
        self.set_user_info(user_id, 'part', 1)
        return f"Спасибо за регистрацию, @{username}! Удачи в турнире!"

    def update_user_rating(self, user_id: Union[int, str], username: str, args: List[str]):
        if username is None:
            return "Братишка, установи username в Телеге, пожалуйста :)"

        if len(args) != 1:
            return self.UPDATE_RATING_MESSAGE

        try:
            rating = int(args[0])
        except ValueError:
            return "Рейтинг должен быть целым числом!"

        self.add_user(user_id, username)
        self.set_user_info(user_id, 'fcrate', str(rating))
        return f"Рейтинг обновлен! Новое значение: {rating}"

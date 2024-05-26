from utils.spreadsheet_utils import SpreadsheetUtils

class Participant:
    def __init__(self, username, fc_name, rate, champ):
        self.username = username
        self.fc_name = fc_name
        self.rate = int(rate)
        self.champ = champ

class UsersDatabaseUtils:
    COLUMN_MAP = {
        'id': 1,
        'username': 2,
        'fcname': 3,
        'fcrate': 4,
        'part': 5,
        'champ': 6
    }

    def __init__(self):
        self.connected = False
        self.worksheet = None

    def get_data(self, row, column_name):
        col_num = self.COLUMN_MAP.get(column_name)
        return row[col_num - 1] if col_num is not None else None

    def connect(self, keyfile_path, spreadsheet_id):
        try:
            spreadsheet_utils = SpreadsheetUtils(keyfile_path)
            spreadsheet = spreadsheet_utils.get_spreadsheet_by_id(spreadsheet_id)
            self.worksheet = spreadsheet.get_worksheet(0)
            self.connected = True
            return True
        except Exception as e:
            print(f"Failed to connect to spreadsheet: {e}")
            return False

    def add_user(self, user_id, username):
        if not self.connected:
            print("Not connected to a spreadsheet. Please connect first.")
            return

        if self.get_row_by_user_id(user_id) is None:
            self.worksheet.append_row([user_id, username, "", 0])
            print(f"New user {username} with ID {user_id} added")

    def set_user_info(self, user_id, column_name, new_value):
        if not self.connected:
            print("Not connected to a spreadsheet. Please connect first.")
            return False

        row_number = self.get_row_by_user_id(user_id)
        if row_number is None:
            print(f"User with ID {user_id} not found")
            return False

        col_num = self.COLUMN_MAP.get(column_name)
        if col_num is None:
            print(f"Column with name {column_name} not found")
            return False

        self.worksheet.update_cell(row_number, col_num, new_value)
        print(f"Set {column_name} as {new_value} for user with ID {user_id}")
        return True

    def get_user_info(self, user_id, column_name):
        if not self.connected:
            print("Not connected to a spreadsheet. Please connect first.")
            return None

        row_number = self.get_row_by_user_id(user_id)
        if row_number is None:
            print(f"User with ID {user_id} not found")
            return None

        col_num = self.COLUMN_MAP.get(column_name)
        if col_num is None:
            print(f"Column with name {column_name} not found")
            return None

        return self.worksheet.cell(row_number, col_num).value

    def get_row_by_user_id(self, user_id):
        if not self.connected:
            print("Not connected to a spreadsheet. Please connect first.")
            return None

        user_id = str(user_id)
        id_col = self.COLUMN_MAP.get('id')
        users = self.worksheet.col_values(id_col)
        if user_id in users:
            return users.index(user_id) + 1
        else:
            print(f"User with ID {user_id} not found")
            return None

    def get_participants_list(self):
        if not self.connected:
            print("Not connected to a spreadsheet. Please connect first.")
            return []

        participants = []
        for row in self.worksheet.get_all_values():
            if self.get_data(row, 'part') == '1':
                participants.append(Participant(
                    self.get_data(row, 'username'),
                    self.get_data(row, 'fcname'),
                    self.get_data(row, 'fcrate'),
                    self.get_data(row, 'champ')
                ))
        return participants

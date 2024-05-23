import gspread
from oauth2client.service_account import ServiceAccountCredentials

class SpreadsheetUtils:
    def __init__(self, keyfile_path):
        self.keyfile_path = keyfile_path
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]

    def authenticate(self):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.keyfile_path, self.scope)
            return gspread.authorize(creds)
        except Exception as e:
            print(f"Authentication failed: {e}")
            return None

    def create_and_share_spreadsheet(self, spreadsheet_title):
        client = self.authenticate()
        if client:
            try:
                spreadsheet = client.create(spreadsheet_title)
                spreadsheet.share('', perm_type='anyone', role='writer')
                print(f"New spreadsheet '{spreadsheet.title}' created and shared for writing successfully!")
                return spreadsheet
            except Exception as e:
                print(f"Failed to create and share spreadsheet: {e}")
                return None

    def get_spreadsheet_by_id(self, spreadsheet_id):
        client = self.authenticate()
        if client:
            try:
                spreadsheet = client.open_by_key(spreadsheet_id)
                print(f"Spreadsheet '{spreadsheet.title}' retrieved successfully!")
                return spreadsheet
            except Exception as e:
                print(f"Failed to retrieve spreadsheet: {e}")
                return None

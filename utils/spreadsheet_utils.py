import gspread
from oauth2client.service_account import ServiceAccountCredentials

class SpreadsheetUtils:
    def __init__(self, keyfile_path):
        self.keyfile_path = keyfile_path
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        self.client = self.authenticate()

    def authenticate(self):
        try:
            print("SpreadsheetUtils - authenticate")
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.keyfile_path, self.scope)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            print(f"Authentication failed: {e}")
            return None

    def _ensure_authenticated(self):
        if not self.client:
            self.client = self.authenticate()

    def create_new_spreadsheet(self, spreadsheet_title):
        self._ensure_authenticated()
        if self.client:
            try:
                spreadsheet = self.client.create(spreadsheet_title)
                spreadsheet.share('', perm_type='anyone', role='writer')
                print(f"New spreadsheet '{spreadsheet.title}' created and shared for writing successfully!")
                return spreadsheet
            except Exception as e:
                print(f"Failed to create and share spreadsheet: {e}")
        else:
            print("Client not authenticated. Cannot create and share spreadsheet.")
        return None

    def get_worksheet(self, spreadsheet_id):
        self._ensure_authenticated()
        if self.client:
            try:
                spreadsheet = self.client.open_by_key(spreadsheet_id)
                print(f"Spreadsheet '{spreadsheet.title}' retrieved successfully!")
                return spreadsheet.get_worksheet(0) 
            except Exception as e:
                print(f"Failed to retrieve spreadsheet: {e}")
        else:
            print("Client not authenticated. Cannot retrieve spreadsheet.")
        return None

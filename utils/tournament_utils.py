from utils.group_handler import *
from utils.spreadsheet_utils import SpreadsheetUtils
from utils.drawer import Drawer

class TournamentUtils:
    def __init__(self, keyfile_path: str, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet_utils = SpreadsheetUtils(keyfile_path)
        self.worksheet = self._get_worksheet()

    def _get_worksheet(self):
        """Get the worksheet object."""
        worksheet = self.spreadsheet_utils.get_worksheet(self.spreadsheet_id)
        if not worksheet:
            print("Problem with accessing the worksheet")
        return worksheet

    def make_groups(self, participants):
        print(participants)
        groups_num = len(participants) // 4
        drawer = Drawer()
        groups = drawer.make_group_draw(participants, groups_num)

        self.write_group_schedule(groups)
        return self.make_draw_respond(groups)

    def make_draw_respond(self, groups):
        respond = 'Результаты жеребьевки\n'
        letter = 'A'
        for group in groups:
            respond += f'\nGroup {letter}\n'
            for p in group:
                respond += f"@{p}\n"
            letter = chr(ord(letter) + 1)
        return respond

    def write_group_schedule(self, groups):
        letter = 'A'
        rows = []
        for group in groups:
            for i in range(len(group)):
                for j in range(i+1,len(group)):
                    rows.append([f'group{letter}',group[i],group[j]])
                    rows.append([f'group{letter}',group[i],group[j]])
            letter = chr(ord(letter) + 1)
        self.worksheet.append_rows(rows)

    def write_playoff_schedule(self, stage_id, pairs):
        all_rows = []
        for pair in pairs:
            self.append_row_multiple_times(all_rows, [stage_id, pair[0], pair[1]], 3)
        self.worksheet.append_rows(all_rows)

    def append_row_multiple_times(self, all_rows, row, n):
        for _ in range(n):
            all_rows.append(row)

    def parse_score(self, score):
        try:
            g0, g1 = score.split(":")
            return g0, g1
        except ValueError:
            return None

    def parse_row(self, row):
        player1, player2 = row[1], row[2]
        score = self.parse_score(row[3])
        if score:
            return f"{player1} {score[0]}:{score[1]} {player2}"
        return f"{player1} - {player2}"

    def get_playoff_schedule(self):
        rounds = {'quarter': [], 'semi': [], 'final': [], 'third': []}
        for row in self.worksheet.get_all_values():
            round_type = row[0]
            if round_type in rounds:
                rounds[round_type].append(self.parse_row(row))

        result = "1/4 финала\n\n" + '\n'.join(rounds['quarter'])

        if rounds['semi']:
            result += "\n\n1/2 финала\n\n" + '\n'.join(rounds['semi'])

        if rounds['third']:
            result += "\n\nМатч за 3е место\n\n" + '\n'.join(rounds['third'])

        if rounds['final']:
            result += "\n\nФинал\n\n" + '\n'.join(rounds['final'])

        return result

    def get_groups_schedule(self):
        groups = {}
        for row in self.worksheet.get_all_values():
            if 'group' in row[0]:
                if groups.get(row[0]) == None:
                    groups[row[0]] = Group(row[0]) 
                groups[row[0]].append_match(*row[1:])
        return groups

    def write_score(self, player1, player2, score):
        print('[write_score]',player1, player2, score)
        found_row = None
        for row_number, row in enumerate(self.worksheet.get_all_values(), start=1):
            if len(row) < 3:
                continue
            if row[1] == player1 and row[2] == player2 and (len(row) == 3 or not row[3]):
                found_row = row_number
                break
            if row[1] == player2 and row[2] == player1  and (len(row) == 3 or not row[3]):
                score = score[1],score[0]
                found_row = row_number
                break
    
        if found_row is not None:
            cell = self.worksheet.cell(found_row, 4)  # Assuming score is in the 4th column
            cell.value = f"{score[0]}:{score[1]}"
            self.worksheet.update_cells([cell])
            return "Peзультат зафиксирован!"
        
        return "Матч для записи не найден"

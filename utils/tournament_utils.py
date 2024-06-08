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

    def make_playoff(self, pairs_count):
        users = self.get_rated_list()

        seed = [user.id for user in users[0:pairs_count]]
        non_seed = [user.id for user in users[pairs_count:2*pairs_count]]


        drawer = Drawer()
        pairs = drawer.make_playoff_draw(seed, non_seed)
        self.write_playoff_schedule('quarter', pairs)
        return self.make_playoff_draw_respond(pairs)

    
    def make_playoff_draw_respond(self, pairs):
        semis = []
        result = "Жеребьевка плей-офф\n\n"
        num = 1
        for pair in pairs:
            result += f"{num}. @{pair[0]} - @{pair[1]}\n"
            semis.append("@{}/@{}".format(pair[0], pair[1]))
            num+=1

        result += "\nУдачи!"
        return result

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

    def group_stage_finished(self):
        groups = self.get_groups_schedule()
        return all(group.all_matches_played() for group in groups.values())

    def get_rated_list(self):
        groups = self.get_groups_schedule()
        place = 0
        for group in groups.values():
            group.compute_table()

        result = list()
        group_size = 4
        for place in range(group_size):
            items = list()
            for group in groups.values():
                items.append(group.items[place])
            result += sorted(items, key=lambda x: (x.points, x.scores), reverse=True)
        return result
            





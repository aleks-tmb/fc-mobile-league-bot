import random
import csv

from utils.group_handler import *
from utils.spreadsheet_utils import SpreadsheetUtils
from utils.drawer import Drawer

class TournamentUtils:
    def __init__(self, db, league_id):
        self.db = db        
        self.league_id = league_id
        self.file_path = f'database/{league_id}.csv'
        if league_id == 'CL':
            self.name = 'Лига Чемпионов'
        else:
            self.name = 'Лига Европы'

    def _read_data(self):
        rows = []
        with open(self.file_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                rows.append(row)
        return rows

    def _save_data(self, rows):
        with open(self.file_path, mode='w', newline='') as csvfile:            
            writer = csv.writer(csvfile)
            writer.writerows(rows)
#---------------------------------------------------------------------------------#

    def make_groups(self, groups_num):
        users = self.db.get_all_users()
        filtered_users = [user for user in users if user['league'] == self.league_id]        
        sorted_users = sorted(filtered_users, key=lambda x: x['rate'], reverse=True)
        ids = [user['ID'] for user in sorted_users]
        
        drawer = Drawer()
        groups = drawer.make_group_draw(ids, groups_num)
        self.write_group_schedule(groups)
        return self.make_draw_respond(groups)

    def write_group_schedule(self, groups):
        rows = []
        for index, group in enumerate(groups):
            letter = chr(ord('A') + index)
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    user1 = self.db.get_user(group[i])
                    user2 = self.db.get_user(group[j])
                    rows.append([f'group{letter}', user1['ID'], user2['ID'],''])
                    rows.append([f'group{letter}', user1['ID'], user2['ID'],''])

        self._save_data(rows)

    def make_draw_respond(self, groups):
        respond = f'{self.name}\n'
        letter = 'A'
        for group in groups:
            respond += f'\nGroup {letter}\n'
            for id in group:
                user = self.db.get_user(id)
                respond += f"@{user['username']} [{user['rate']}]\n"
            letter = chr(ord(letter) + 1)
        return respond

#---------------------------------------------------------------------------------#
    def get_groups(self):
        groups = {}
        with open(self.file_path, mode='r', newline='') as file: 
            reader = csv.reader(file)
            for row in reader:
                if 'group' in row[0]:
                    if groups.get(row[0]) == None:
                        groups[row[0]] = Group(row[0]) 
                    if len(row) > 3:
                        score = row[3]
                    else:
                        score = "" 
                    groups[row[0]].append_match(int(row[1]), int(row[2]), score)
        return groups
    
    def show_all_tables(self, full = False):
        groups = self.get_groups()
        messages = [group.compute_table(self.db, full) for group in groups.values()]
        return f"{self.name}\n\n" + '\n\n'.join(messages)      

    def show_user_table(self, user_id):
        groups = self.get_groups()
        for group in groups.values():
            print(group.get_users())
            if user_id in group.get_users():
                return f"{self.name}\n\n" + group.compute_table(self.db, False) 
        return 'Группа не найдена'  

    def make_playoff(self, pairs_count):
        users = self.get_rated_list()[:2*pairs_count]
        ids = [user.id for user in users]
        print(ids)
        random.shuffle(ids)
        seed = ids[0:pairs_count]
        non_seed = ids[pairs_count:2*pairs_count]

        drawer = Drawer()
        pairs = drawer.make_playoff_draw(seed, non_seed)
        self.write_playoff_schedule(pairs)
        return self.make_playoff_draw_respond(pairs)

    
    def make_playoff_draw_respond(self, pairs):
        result = f"{self.name} плей-офф\n\n"

        # Initial matches
        for match_num, pair in enumerate(pairs, start=1):
            user1 = self.db.get_username_by_id(pair[0])
            user2 = self.db.get_username_by_id(pair[1])
            result += f"{match_num}. @{user1} - @{user2}\n"
        result += '\n'

        # Generate subsequent rounds
        total_matches = len(pairs)
        match_num = len(pairs) + 1
        previous_round_start = 1

        while total_matches > 1:
            total_matches //= 2
            for i in range(total_matches):
                result += f"{match_num}. Победитель {previous_round_start + 2*i} - Победитель {previous_round_start + 2*i + 1}\n"
                match_num += 1
            result += '\n'
            previous_round_start += total_matches*2

        return result

    def write_playoff_schedule(self, pairs):
        rows = self._read_data()
        N_pairs = len(pairs)
        for i in range(N_pairs):
            pair = pairs[i]
            self.append_row_multiple_times(rows, [f"last-{N_pairs*2}-{i}", pair[0], pair[1], ""], 3)

        while N_pairs >= 2:
            N_pairs = N_pairs//2
            for i in range(N_pairs):
                self.append_row_multiple_times(rows, [f"last-{N_pairs*2}-{i}", "", "", ""], 3)

        self._save_data(rows)

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
        player1 = self.db.get_username_by_id(row[1]) 
        player2 = self.db.get_username_by_id(row[2])
        score = self.parse_score(row[3])
        if score:
            return f"{player1} {score[0]}:{score[1]} {player2}"
        return f"{player1} - {player2}"

    def get_playoff_schedule(self):
        rounds = {'last-8': [], 'last-4': [], 'last-2': []}
        for row in self._read_data():
            round_type = row[0][:-2]
            if round_type in rounds:
                rounds[round_type].append(self.parse_row(row))

        result = f"{self.name}\n"
        result += "1/4 финала\n\n" + '\n'.join(rounds['last-8'])

        if rounds['last-4']:
            result += "\n\nПолуфиналы\n\n" + '\n'.join(rounds['last-4'])

        if rounds['last-2']:
            result += "\n\nФинал\n\n" + '\n'.join(rounds['last-2'])

        return result

    def write_score(self, id1, id2, score):
        print('[write_score]', id1, id2, score)
        rows, found_match = [], False

        try:
            with open(self.file_path, mode='r', newline='') as file:
                reader = csv.reader(file)
                for row in reader:
                    if found_match or row[3] != '':
                        rows.append(row)
                        continue

                    row_id1, row_id2 = int(row[1]), int(row[2])
                    if (row_id1 == id1 and row_id2 == id2):
                        row[3] = f"{score[0]}:{score[1]}"
                        found_match = True
                    elif (row_id1 == id2 and row_id2 == id1):
                        row[3] = f"{score[1]}:{score[0]}"
                        found_match = True
                    rows.append(row)

            if not found_match:
                return "Матч для записи не найден"

            with open(self.file_path, mode='w', newline='') as file:
                csv.writer(file).writerows(rows)

            return "Результат зафиксирован!"
        except FileNotFoundError:
            return "Файл не найден"
        except Exception as e:
            return f"Произошла ошибка: {str(e)}"

    def update_playoff_path(self, player1, player2):
        g0, g1, matches_played = 0, 0, 0
        stage_id = None
        player1, player2 = str(player1), str(player2)

        rows = self._read_data()
        for row in rows:
            if 'last' in row[0] and {row[1], row[2]} == {player1, player2}:
                stage_id, match_id = row[0].split('-')[1:3]
                match = Match(int(row[1]), int(row[2]), row[3])
                if row[1] == player2 and row[2] == player1:
                    player1, player2 = player2, player1

                if match.played:
                    matches_played += 1
                    g0 += match.score[0]
                    g1 += match.score[1]

        if stage_id == '2':
            return

        if matches_played >= 2 and g0 != g1:
            promoted = player1 if g0 > g1 else player2
            match_id = int(match_id)
            next_stage = f"last-{int(stage_id) // 2}-{match_id // 2}"
            print(next_stage, promoted, match_id)
            for row in rows:
                if row[0] == next_stage:
                    row[1 + match_id % 2] = promoted
            self._save_data(rows)
            

    def group_stage_finished(self):
        groups = self.get_groups()
        return all(group.all_matches_played() for group in groups.values())

    def get_rated_list(self):
        groups = self.get_groups()
        place = 0
        for group in groups.values():
            group.compute_table(self.db)

        result = list()
        group_size = 4
        for place in range(group_size):
            items = list()
            for group in groups.values():
                items.append(group.items[place])
            result += sorted(items, key=lambda x: (x.points, (x.scored - x.conceded), x.scored), reverse=True)
        return result

    # def get_history(self):
    #     resp = ""
    #     for row in self.worksheet.get_all_values():
    #         resp += f"{row[1]}-{row[0]}\n"
    #         resp += f"🥇 {row[2]}\n🥈 {row[3]}\n🥉 {row[4]}\n\n"
    #     return resp
            





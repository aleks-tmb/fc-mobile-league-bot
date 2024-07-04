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
        self.data = []
        self._read_data()

    def _read_data(self):
        try:
            with open(self.file_path, mode='r', newline='') as file:
                reader = csv.DictReader(file)
                self.data = [row for row in reader]
                for row in self.data:
                    row['id0'] = int(row['id0'])
                    row['id1'] = int(row['id1'])
        except:
            return

    def _save_data(self):
        """Writes the current data to the CSV file."""
        with open(self.file_path, mode='w', newline='') as file:
            if self.data:
                fieldnames = self.data[0].keys()
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.data)

    def _add_record(self, tag, id0, id1, score = ''):
        self.data.append({
            "tag": tag,
            "id0": int(id0),
            "id1": int(id1),
            "score": score
        })
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
        self.data.clear()
        for index, group in enumerate(groups):
            letter = chr(ord('A') + index)
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    self._add_record(f'group{letter}', group[i], group[j])
                    self._add_record(f'group{letter}', group[i], group[j])
        self._save_data()

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
        for row in self.data:
            tag = row['tag']
            if 'group' in tag:
                if groups.get(tag) == None:
                    groups[tag] = Group(tag)  
                groups[tag].append_match(row['id0'], row['id1'], row['score'])
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

    def write_score(self, id0, id1, score):
        print('[write_score]', id0, id1, score)

        for row in self.data:
            if row['score']:
                continue

            if (row['id0'] == id0 and row['id1'] == id1):
                row['score'] = f"{score[0]}:{score[1]}"
                break
            
            if (row['id0'] == id1 and row['id1'] == id0):
                row['score'] = f"{score[1]}:{score[0]}"
                break        
        else:
            return "Матч для записи не найден"

        self._save_data()
        return "Результат зафиксирован!"

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

    def get_participants(self):
        users = self.db.get_all_users()
        filtered_users = [user for user in users if user['league'] == self.league_id]        
        sorted_users = sorted(filtered_users, key=lambda x: x['rate'], reverse=True)
        respond = f'{self.name}. Список участников\n\n'
        for user in sorted_users:
            respond += f"{user['username']} [{user['rate']}]\n"
        return respond

    # def get_history(self):
    #     resp = ""
    #     for row in self.worksheet.get_all_values():
    #         resp += f"{row[1]}-{row[0]}\n"
    #         resp += f"🥇 {row[2]}\n🥈 {row[3]}\n🥉 {row[4]}\n\n"
    #     return resp
            





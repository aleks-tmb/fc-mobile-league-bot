import random
import csv

from utils.group_handler import *
from utils.drawer import Drawer

class TournamentUtils:
    def __init__(self, db, tag, path, id):
        self.db = db 
        self.league_tag = tag       
        self.file_path = f'{path}/{tag}-{id}.csv'
        print(self.file_path)
        if 'CL' in tag:
            self.name = 'Лига Чемпионов'
        else:
            self.name = 'Лига Европы'
        self.data = []
        self._read_data()

    def _read_data(self):
        print('_read_data')
        try:
            with open(self.file_path, mode='r', newline='') as file:
                reader = csv.DictReader(file)
                self.data = [row for row in reader]
                for row in self.data:
                    try:
                        row['id0'] = int(row['id0'])
                        row['id1'] = int(row['id1'])
                    except:
                        continue
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

    def _add_record(self, tag, id0, id1, index=None):
            new_record = {
                "ID": len(self.data),
                "tag": tag,
                "id0": id0,
                "id1": id1,
                "score": ''
            }
            if index is None:
                self.data.append(new_record)
            else:
                self.data.insert(index + 1, new_record)

#---------------------------------------------------------------------------------#   
    def get_stage(self):
        if not self.data:
            return 'NOT-STARTED'

        if any('last' in row['tag'] for row in self.data):
            return 'PLAY-OFF'

        return 'GROUP'      
#---------------------------------------------------------------------------------#
    def get_status(self, user_id = None):
        stage = self.get_stage()
        
        if stage == 'NOT-STARTED':
            return 'Турнир еще не стартовал'

        if stage == 'PLAY-OFF':
            return self.get_playoff_schedule()

        if user_id is None:
            return self.show_all_tables()
        else:
            return self.show_user_table(user_id)
#---------------------------------------------------------------------------------#
    def make_groups(self, groups_num):
        if self.get_stage() != 'NOT-STARTED':
            return 'Турнир уже стартовал'
                
        users = self.db.get_all_users()
        filtered_users = [user for user in users if user['league'] == self.league_tag]        
        sorted_users = sorted(filtered_users, key=lambda x: x['rate'], reverse=True)
        ids = [user['ID'] for user in sorted_users]
        print(ids)
        
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
        if self.get_stage() == 'PLAY-OFF':
            return 'Плей-офф уже идет'
        
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
        N_pairs = len(pairs)
        for i in range(N_pairs):
            pair = pairs[i]
            self._add_record(f"last-{N_pairs*2}-{i}", pair[0], pair[1])
            self._add_record(f"last-{N_pairs*2}-{i}", pair[0], pair[1])

        while N_pairs >= 2:
            N_pairs = N_pairs//2
            for i in range(N_pairs):
                self._add_record(f"last-{N_pairs*2}-{i}", "", "")
                self._add_record(f"last-{N_pairs*2}-{i}", "", "")

        self._add_record(f"third", "", "")
        self._add_record(f"third", "", "")
        self._save_data()

    def parse_score(self, score):
        try:
            g0, g1 = score.split(":")
            return g0, g1
        except ValueError:
            return None

    def parse_row(self, row):
        player1 = self.db.get_username_by_id(row['id0']) 
        player2 = self.db.get_username_by_id(row['id1'])
        score = self.parse_score(row['score'])
        if score:
            return f"{player1} {score[0]}:{score[1]} {player2}"
        return f"{player1} - {player2}"

    def get_playoff_schedule(self):
        rounds = {'last-8': [], 'last-4': [], 'last-2': [], 'third': []}
        for row in self.data:
            for tag in rounds:
                if tag in row['tag']:
                    rounds[tag].append(self.parse_row(row))
                    break

        result = f"{self.name}\n"
        result += "1/4 финала\n\n" + '\n'.join(rounds['last-8'])

        if rounds['last-4']:
            result += "\n\nПолуфиналы\n\n" + '\n'.join(rounds['last-4'])

        if rounds['last-2']:
            result += "\n\nФинал\n\n" + '\n'.join(rounds['last-2'])

        if rounds['third']:
            result += "\nМатч за третье место\n\n" + '\n'.join(rounds['third'])        

        return result

    def write_score(self, id0, id1, score):
        print('[write_score]', id0, id1, score)
        self._read_data()

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

        if self.get_stage() == 'PLAY-OFF':
            self.update_playoff_path(id0, id1)

        return "Результат зафиксирован!"

    def update_playoff_path(self, id0, id1):
        self._read_data()
        matches_played, g0, g1, last_row = self._analyze_matches(id0, id1)

        if matches_played < 2:
            return
        
        tag = last_row['tag']
        if tag == 'last-2-0' or tag == 'third':
            return 

        try:
            stage_id, match_id = tag.split('-')[1:3]
            stage_id = int(stage_id)
            match_id = int(match_id)
        except:
            return

        if g0 == g1:
            self._handle_tie(last_row)
        else:
            self._handle_winner(stage_id, match_id, last_row['id0'], last_row['id1'], g0, g1)

        self._save_data()

    def _analyze_matches(self, id0, id1):
        g0, g1, matches_played = 0, 0, 0
        last_row = None

        for row in self.data:
            if 'last' in row['tag'] and {row['id0'], row['id1']} == {id0, id1}:
                match = Match(row['id0'], row['id1'], row['score'])

                if match.played:
                    matches_played += 1
                    g0 += match.score[0]
                    g1 += match.score[1]
                    last_row = row

        return matches_played, g0, g1, last_row

    def _adjust_ids(self, row, id0, id1):
        if row['id0'] == id1 and row['id1'] == id0:
            return id1, id0
        return id0, id1

    def _handle_tie(self, last_row):
        index = self.data.index(last_row)
        self._add_record(last_row['tag'], last_row['id0'], last_row['id1'], index)

    def _handle_winner(self, stage_id, match_id, id0, id1, g0, g1):
        promoted, loser = (id0, id1) if g0 > g1 else (id1, id0)
        next_stage = self._next_stage_tag(stage_id, match_id)
        id_key = 'id0' if match_id % 2 == 0 else 'id1'

        for row in self.data:
            if row['tag'] == next_stage:
                row[id_key] = promoted

        if int(stage_id) == 4:
            self._assign_loser_to_third_place(loser, id_key)

    def _next_stage_tag(self, stage_id, match_id):
        stage_id = int(stage_id)
        match_id = int(match_id)
        return f"last-{stage_id // 2}-{match_id // 2}"

    def _assign_loser_to_third_place(self, loser, id_key):
        for row in self.data:
            if row['tag'] == 'third':
                row[id_key] = loser
            
    def group_stage_finished(self):
        groups = self.get_groups()
        return all(group.all_matches_played() for group in groups.values())

    def get_rated_list(self):
        groups = self.get_groups()
        for group in groups.values():
            group.compute_table(self.db)

        result = []

        max_group_size = max(len(group.items) for group in groups.values()) 
        # Collect and sort items from each group
        for place in range(max_group_size):
            items = []
            for group in groups.values():
                if place < len(group.items):
                    items.append(group.items[place])
            sorted_items = sorted(items, key=lambda x: (x.points, x.scored - x.conceded, x.scored), reverse=True)
            result.extend(sorted_items)
        
        return result
        

    def get_participants(self):
        users = self.db.get_all_users()
        filtered_users = [user for user in users if user['league'] == self.league_tag]        
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
            





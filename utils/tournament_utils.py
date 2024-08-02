import random
import csv
import copy
import math

from utils.group_handler import *
from utils.drawer import Drawer

class TournamentUtils:
    def __init__(self, db, path, tag, id):
        self.db = db 
        self.league_tag = tag 
        self.id = id      
        self.file_path = f'{path}/{tag}-{id}.csv'
        print(self.file_path)
        if 'CL' in tag:
            self.name = 'Лига Чемпионов'
        elif 'EL' in tag:
            self.name = 'Лига Европы'
        else:
            self.name = 'Суперлига'
        self.data = []
        self.metainfo = []
        self._read_data()

    def _read_data(self):
        try:
            with open(self.file_path, mode='r', newline='') as file:
                reader = csv.DictReader(file)
                self.data.clear()
                self.metainfo.clear()               
                for row in reader:
                    if row['stage'] == 'metainfo':
                        self.metainfo.append(row)
                    else:
                        row['number'] = int(row['number'])
                        try:
                            row['id0'] = int(row['id0'])
                            row['id1'] = int(row['id1'])
                        except:
                            pass
                        self.data.append(row)
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
                writer.writerows(self.metainfo)

    def _add_record(self, stage, tag, number, id0, id1, index=None):
            new_record = {
                "ID": len(self.data),
                "stage" : stage,
                "tag": tag,
                "number": number,
                "id0": id0,
                "id1": id1,
                "score": ''
            }
            self.data.append(new_record)

    def set_metainfo(self, key, value):
        for row in self.metainfo:
            if row['tag'] == key:
                row['number'] = value
                self._save_data()
                print(f"updated {key} = {value}")
                return

        new_record = {
            "ID": len(self.metainfo),
            "stage" : 'metainfo',
            "tag": key,
            "number": value,
        }
        self.metainfo.append(new_record)
        print(f"added {key} = {value}")
        self._save_data()

    def get_metainfo(self, key):
        self._read_data()
        for row in self.metainfo:
            if row['tag'] == key:
                return row['number']
        return None
        

#---------------------------------------------------------------------------------# 
    def get_name(self):
        return self.name

    def get_stage(self):
        self._read_data()

        if not self.data:
            return 'NOT-STARTED'

        stage = 'PLAYOFF' if any('playoff' in row['stage'] for row in self.data) else 'GROUP'
 
        if all(row['score'] != '' for row in self.data):
            stage += '-COMPLETE'
        
        print(f"[get_stage], {stage}")
        return stage
#---------------------------------------------------------------------------------#
    def get_status(self, full=False):
        stage = self.get_stage()
        
        result = self.get_name() + '\n'
        result += f"сезон {self.id}\n\n"

        if stage == 'NOT-STARTED':
            result += 'Список участников\n\n'
            result += self.get_participants()
            return result


        if 'PLAYOFF' in stage:
            if full:
                result += 'Групповой этап\n'
                table = '\n\n'.join(self.show_all_tables())
                result += f'<pre>\n{table}</pre>\n\n'                

            result += 'Плей-офф\n'
            result += f'<pre>\n{self.get_playoff_schedule()}</pre>\n'
        else:
            result += 'Групповой этап\n'
            table = '\n\n'.join(self.show_all_tables())
            result += f'<pre>\n{table}</pre>\n\n'  

        if full:
            result += f"\n{self.get_summary(False)}\n"

        result += '#results'
        return result
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

    def write_group_schedule(self, groups, matches = 2):
        if self.get_stage() != 'NOT-STARTED':
            return
        self.data.clear()
        for index, group in enumerate(groups):
            letter = chr(ord('A') + index)
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    for m in range(matches):
                        self._add_record('group', letter, 0, group[i], group[j])
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
    def get_prioritized(self, items):
        sorted_items = sorted(items, key=lambda x: (x.points, x.scored - x.conceded, x.scored), reverse=True)
        return sorted_items

    def get_groups(self):
        groups = {}
        for row in self.data:
            if 'group' == row['stage']:
                tag = row['tag']
                if groups.get(tag) == None:
                    groups[tag] = Group(tag)  
                groups[tag].append_match(row['id0'], row['id1'], row['score'])
        return groups
    
    def show_all_tables(self, full = False):
        groups = self.get_groups()
        messages = [group.compute_table(self.db, full) for group in groups.values()]
        
        if self.league_tag == 'CL':
            placed3rd = [group.items[2] for group in groups.values()]
            messages.append('Рейтинг третьих мест')
            messages.append(print_group(self.db, self.get_prioritized(placed3rd), '', 4))
        return messages 
    
    def show_user_table(self, user_id):
        groups = self.get_groups()
        for group in groups.values():
            print(group.get_users())
            if user_id in group.get_users():
                return f"{self.name}\n\n" + group.compute_table(self.db, False) 
        return 'Группа не найдена'  

    def make_playoff(self):
        if 'PLAYOFF' in self.get_stage():
            return 'Плей-офф уже идет'
        
        rated_teams = self.get_rated_list()
        # Find the smallest power of 2 greater than half_teams
        half_teams = len(rated_teams) / 2
        promoted_count = 2 ** math.ceil(math.log2(half_teams))
        promoted_users = rated_teams[:promoted_count]

        ids = [user.id for user in promoted_users]
        print(ids)
        random.shuffle(ids)

        mid = len(ids) // 2
        seed = ids[:mid]
        non_seed = ids[mid:]

        drawer = Drawer()
        pairs = drawer.make_playoff_draw(seed, non_seed)
        self.write_playoff_schedule(pairs)
        return "Жеребьевка успешно проведена!"

    def _get_stage_name(self, N):
        if N >= 8:
            return f"last{N*2}"
        
        stage_name = {
            1: "final",
            2: "semifinal",
            4: "quarter",
        }
        return stage_name[N]

    def _get_next_stage(self, stage):
        print(f'[_get_next_stage] {stage}')
        if stage.startswith('last'):
            number_part = int(stage[4:])
            new_number = number_part // 2
            if new_number == 8:
                return 'quarter'
            return f'last{new_number}'
            
        if stage == 'quarter':
            return 'semifinal'
        if stage == 'semifinal':
            return 'final'
        return None

    def write_playoff_schedule(self, pairs):
        N_pairs = len(pairs)
        for i in range(N_pairs):
            pair = pairs[i]
            self._add_record('playoff', self._get_stage_name(N_pairs), i, pair[0], pair[1])
            self._add_record('playoff', self._get_stage_name(N_pairs), i, pair[0], pair[1])

        while N_pairs >= 2:
            N_pairs = N_pairs//2
            for i in range(N_pairs):
                self._add_record('playoff', self._get_stage_name(N_pairs), i, "", "")
                self._add_record('playoff', self._get_stage_name(N_pairs), i, "", "")

        self._add_record('playoff','third', 0, "", "")
        self._add_record('playoff','third', 0, "", "")
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
        stage_names = {
            'last64': "1/32 финала",
            'last32': "1/16 финала",
            'last16': "1/8 финала",
            'quarter': "1/4 финала",
            'semifinal': "Полуфиналы",
            'final': "Финал",
            'third': "Матч за третье место"
        }
        
        rounds = {stage: [] for stage in stage_names}
        for row in self.data:
            if row['stage'] == 'playoff' and row['tag'] in rounds:
                rounds[row['tag']].append(self.parse_row(row))
        
        result = [
            f"● {stage_names[stage]}\n" + '\n'.join(rounds[stage]) + '\n\n'
            for stage in stage_names if rounds[stage]
        ]
        
        return ''.join(result)

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

        if self.get_stage() == 'PLAYOFF':
            self.update_playoff_path(id0, id1)

        return "Результат зафиксирован!"

    def update_playoff_path(self, id0, id1):
        self._read_data()
        matches_played, winner, loser, last_row = self._analyze_matches(id0, id1)
        print(f"[update_playoff_path] w:{winner}, l:{loser}")

        if matches_played < 2:
            return
        
        if winner is None:
            self._handle_tie(last_row)
        else:
            next_tag = self._get_next_stage(last_row['tag'])
            if next_tag is None:
                return
            self._handle_winner(next_tag, last_row, winner, loser)

        self._save_data()

    def _analyze_matches(self, id0, id1):
        g0, g1, matches_played = 0, 0, 0
        last_row = None

        for row in self.data:
            if row['stage'] == 'playoff':
                if {row['id0'], row['id1']} == {id0, id1}:
                    match = Match(row['id0'], row['id1'], row['score'])

                    if match.played:
                        matches_played += 1
                        g0 += match.score[0]
                        g1 += match.score[1]
                        last_row = row

        winner, loser = None, None
        if g0 != g1:
            winner, loser = (last_row['id0'], last_row['id1']) if g0 > g1 else (last_row['id1'], last_row['id0'])
            print(f"[_analyze_matches], {g0}-{g1}, {winner} > {loser}")

        return matches_played, winner, loser, last_row

    def _handle_tie(self, last_row):
        index = self.data.index(last_row)
        new_row = copy.deepcopy(last_row)
        new_row['ID'] = len(self.data)
        new_row['score'] = ''
        self.data.insert(index + 1, new_row)

    def _handle_winner(self, next_tag, last_row, winner, loser):
        next_num = last_row['number'] // 2

        for row in self.data:
            if row['tag'] == next_tag and row['number'] == next_num:
                id_key = 'id0' if row['id0'] == '' else 'id1'
                row[id_key] = winner

        if next_tag == 'final':
            self._assign_loser_to_third_place(loser)

    def _next_stage_tag(self, stage_id, match_id):
        stage_id = int(stage_id)
        match_id = int(match_id)
        return f"last-{stage_id // 2}-{match_id // 2}"

    def _assign_loser_to_third_place(self, loser):
        for row in self.data:
            if row['tag'] == 'third':
                id_key = 'id0' if row['id0'] == '' else 'id1'
                row[id_key] = loser

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
            result.extend(self.get_prioritized(items))
        
        return result
        

    def get_participants(self):
        users = self.db.get_all_users()
        filtered_users = [user for user in users if user['league'] == self.league_tag]
        sorted_users = sorted(filtered_users, key=lambda x: x['rate'], reverse=True)
        
        respond = ''.join(f"{i+1}. @{user['username']} [{user['rate']}]\n" for i, user in enumerate(sorted_users))
        return respond

    def get_summary(self, with_header=True):
        if self.get_stage() != 'PLAYOFF-COMPLETE':
            return ''

        final_record = next((row for row in self.data if  row['tag'] == 'final'), None)
        third_record = next((row for row in self.data if  row['tag'] == 'third'), None)

        if not final_record or not third_record:
            return 'Final or third-place match data is missing.'

        try:
            _, gold_id, silver_id, _ = self._analyze_matches(final_record['id0'], final_record['id1'])
            _, bronze_id, _, _ = self._analyze_matches(third_record['id0'], third_record['id1'])

            gold = self.db.get_username_by_id(gold_id)
            silver = self.db.get_username_by_id(silver_id)
            bronze = self.db.get_username_by_id(bronze_id)

            if not gold or not silver or not bronze:
                raise ValueError('User data for winners is missing.')
        except Exception as e:
            return str(e)

        header = (
            f'{self.name}, {self.id}-й сезон завершен!\n\n'
            f'Поздравляем @{gold} c победой! 🏆 \n\n')
        
        body = (
            'Призеры турнира:\n'
            f'🥇 @{gold}\n🥈 @{silver}\n🥉 @{bronze}\n\n'
        )

        if with_header:
            body = header + body
        return body

    def get_user_matches_list(self, user_id):
        self._read_data()
        matches = []
        for row in self.data:
            if user_id in [row['id0'], row['id1']]:
                match = Match(row['id0'], row['id1'], row['score'])
                matches.append(match)

        return "\n".join(match.to_string(self.db) for match in matches)




        

    # def get_history(self):
    #     resp = ""
    #     for row in self.worksheet.get_all_values():
    #         resp += f"{row[1]}-{row[0]}\n"
    #         resp += f"🥇 {row[2]}\n🥈 {row[3]}\n🥉 {row[4]}\n\n"
    #     return resp
            





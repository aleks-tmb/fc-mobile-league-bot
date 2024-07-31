def print_group(db, items, title = '', split_after = None):

    delim = '-'*26
    result = f"● {title} [игры,очки,голы]\n{delim}\n"
    for num, item in enumerate(items, start=1):
        diff = f"{item.scored}-{item.conceded}"
        username = db.get_username_by_id(item.id)[:14]
        result += f"{num:2} {username:14}{item.games:2}{item.points:3} {diff}\n" 
        if num == split_after:
            result += f"{delim}\n"

    return result   

class Match:
    def __init__(self, player0, player1, score):
        self.id0 = player0
        self.id1 = player1
        self.played = False
        self.score = score
        self.parse_score(score)

    def parse_score(self, score):
        try:
            g0, g1 = map(int, score.split(':'))
            self.played = True
            self.score = (g0, g1)
        except ValueError:
            pass

    def to_string(self, db): 
        player0 = db.get_username_by_id(self.id0)
        player1 = db.get_username_by_id(self.id1)
        if self.played:
            return f"{player0} {self.score[0]}:{self.score[1]} {player1}"
        return f"{player0} - {player1}"

class Item:
    def __init__(self, id):
        self.id = id
        self.games = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.scored = 0
        self.conceded = 0
        self.points = 0

    def update(self, my_score, opponent_score):
        self.games += 1
        self.scored += my_score
        self.conceded += opponent_score

        if my_score > opponent_score:
            self.wins += 1
            self.points += 3
        elif my_score == opponent_score:
            self.draws += 1
            self.points += 1
        else:            
            self.losses += 1
        
class Group:
    def __init__(self, name):
        self.name = name
        self.matches = []
        self.items = []
        self.users = set()

    def append_match(self, team1, team2, score = ""):
       self.matches.append(Match(team1, team2, score)) 
       self.users.add(team1)
       self.users.add(team2)

    def get_users(self):
        return self.users

    def compute_table(self, db, add_results=True):
        items = {}

        for match in self.matches:
            items.setdefault(match.id0, Item(match.id0))
            items.setdefault(match.id1, Item(match.id1))
            if match.played:
                items[match.id0].update(*match.score)
                items[match.id1].update(*reversed(match.score))

        self.items = sorted(items.values(), key=lambda x: (x.points, (x.scored - x.conceded), x.scored), reverse=True)

        title = f"Group {self.name}"
        result = print_group(db, self.items, title)

        if add_results:
            result += '\n' + self.get_matches_list(db)

        return result

    def get_matches_list(self, db):
        return "\n".join(match.to_string(db) for match in self.matches)
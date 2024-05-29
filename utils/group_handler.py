class Match:
    def __init__(self, player0, player1, score):
        self.player0 = player0
        self.player1 = player1
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

    def __str__(self): 
        if self.played:
            return f"{self.player0} {self.score[0]}:{self.score[1]} {self.player1}"
        return f"{self.player0} - {self.player1}"

class Item:
    def __init__(self, id):
        self.id = id
        self.games = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.scores = 0
        self.points = 0

    def update(self, my_score, opponent_score):
        self.games += 1
        self.scores += my_score - opponent_score

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

    def append_match(self, team1, team2, score):
       self.matches.append(Match(team1, team2, score)) 

    def compute_table(self, add_results=True):
        items = {}

        for match in self.matches:
            items.setdefault(match.player0, Item(match.player0))
            items.setdefault(match.player1, Item(match.player1))
            if match.played:
                items[match.player0].update(*match.score)
                items[match.player1].update(*reversed(match.score))

        self.items = sorted(items.values(), key=lambda x: (x.points, x.scores), reverse=True)

        result = f"{self.name}    [игры,очки,голы]\n"
        result += '-'*27 + '\n'
        for num, item in enumerate(self.items, start=1):
            result += f"{num} {item.id[:16]:16}{item.games:2}{item.points:3}{item.scores:+4d}\n"

        if add_results:
            result += '\n' + self.get_matches_list()

        return result

    def get_matches_list(self):
        return "\n".join(str(match) for match in self.matches)

    def all_matches_played(self):
        return all(match.played for match in self.matches)
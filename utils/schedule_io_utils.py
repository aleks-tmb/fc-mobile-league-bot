class ScheduleIOUtils:
    def __init__(self, worksheet):
        self.worksheet = worksheet

    def write_group_schedule(self, groups):
        all_rows = []
        for group in groups:
            participants = group.participants
            for i in range(len(participants)):
                for j in range(i + 1, len(participants)):
                    participant1 = participants[i]
                    participant2 = participants[j]
                    self.append_row_multiple_times(all_rows, ['gr' + group.id, participant1, participant2], 2)
        self.worksheet.append_rows(all_rows)

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
        rounds = {'quart': [], 'semi': [], 'final': [], 'third': []}
        for row in self.worksheet.get_all_values():
            round_type = row[0]
            if round_type in rounds:
                rounds[round_type].append(self.parse_row(row))

        result = "1/4 финала\n\n" + '\n'.join(rounds['quart'])

        if rounds['semi']:
            result += "\n\n1/2 финала\n\n" + '\n'.join(rounds['semi'])

        if rounds['third']:
            result += "\n\nМатч за 3е место\n\n" + '\n'.join(rounds['third'])

        if rounds['final']:
            result += "\n\nФинал\n\n" + '\n'.join(rounds['final'])

        return result

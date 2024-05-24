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

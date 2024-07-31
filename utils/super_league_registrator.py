import random
import re

class SuperLeagueRegistrator:
    def __init__(self):
        pass

    def _starts_with_number_and_dot(self, line):
        # ^ indicates start of the line, \d+ matches one or more digits, \. matches the dot
        pattern = r'^\d+\.'
        if re.match(pattern, line):
            return True
        else:
            return False

    def extract_username(self, line):
        pattern = r'.*@(.*)'
        obj = re.match(pattern, line)
        if obj:
            return obj.groups()[0]
        return None

    def check_user_already_registrated(self, text, username):
        lines = self.extract_lines_with_teams(text)
        for line in lines:
            name = self.extract_username(line)
            if name == username:
                return True

    def extract_lines_with_teams(self, text):
        split = text.splitlines()
        lines = [line for line in split if self._starts_with_number_and_dot(line)]
        return lines

    def assign_user_to_random_line(self, lines, username):
        available_lines = []
        for num, line in enumerate(lines):
            if not '@' in line:
                available_lines.append(num)

        try:
            n = random.choice(available_lines)
            lines[n] += f' @{username}'
            return f"Участник @{username} успешно зарегистрирован!\n{lines[n]}"
        except Exception as e:
            return f"Ошибка при регистрации: {e}"
        
    def get_all_users(self, text):
        lines = self.extract_lines_with_teams(text)
        users = []
        pattern = r'.*@(.*)'
        for line in lines:
            obj = re.match(pattern, line)
            if obj:
                users.append(obj.groups()[0]) 
        return users




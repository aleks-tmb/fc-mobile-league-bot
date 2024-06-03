class ScoreProcessor:
    def __init__(self, words):
        self.words = words
        self.result = None
        self.username = None
        self.score = None

    def parse_result(self, word):
        """Parses the result word and returns the corresponding result type."""
        if word == 'выиграл':
            return 'WIN'
        elif word == 'проиграл':
            return 'LOSE'
        elif 'ничь' in word:
            return 'DRAW'
        return None

    def parse_username(self, word):
        """Parses the username from the word starting with '@'."""
        if word.startswith('@'):
            return word[1:]
        return None

    def parse_score(self, word):
        """Parses the score from the word containing ':' and returns a tuple of scores."""
        if ':' in word:
            try:
                g0, g1 = map(int, word.split(':'))
                return (g0, g1)
            except ValueError:
                pass
        return None

    def validate_and_adjust_score(self):
        """Validates and adjusts the score based on the result type."""
        if self.result == 'DRAW' and self.score[0] != self.score[1]:
            return None
        if self.result != 'DRAW' and self.score[0] == self.score[1]:
            return None
            
        if self.result == 'WIN' and self.score[0] < self.score[1]:
            self.score = (self.score[1], self.score[0])
        if self.result == 'LOSE' and self.score[0] > self.score[1]:
            self.score = (self.score[1], self.score[0])
        return self.score

    def process_words(self):
        print(self.words)
        """Processes the list of words and updates the class attributes."""
        for word in self.words:
            if not self.result:
                self.result = self.parse_result(word)
            if not self.username:
                self.username = self.parse_username(word)
            if not self.score:
                self.score = self.parse_score(word)

    def get_report(self):
        """Processes the words and returns a tuple of username and score if valid."""
        self.process_words()
        if self.result and self.username and self.score:
            self.score = self.validate_and_adjust_score()
            if self.score:
                return (self.username, self.score)
        return None

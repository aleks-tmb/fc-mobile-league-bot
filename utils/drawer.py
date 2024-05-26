import random

class Drawer:
    def __init__(self):
        pass

    def draw_one_and_remove(self, elems):
        choice = random.choice(list(elems))
        elems.remove(choice)
        return choice

    def split_list(self, lst, n):
        return [lst[i:i + n] for i in range(0, len(lst), n)]

    def make_group_draw(self, participants, number_of_groups):
        pots = self.split_list(participants, number_of_groups)
        pots = [set(pot) for pot in pots]
        groups = [[] for _ in range(number_of_groups)]

        for pot in pots:
            for i in range(len(pot)):
                groups[i % number_of_groups].append(self.draw_one_and_remove(pot))
        return groups

    def make_playoff_draw(self, listA, listB):
        pairs = []
        blockers = dict(zip(listA, listB))
        setA = set(listA)
        setB = set(listB)

        while setA:
            A = self.draw_one_and_remove(setA)
            B = self.draw_one_and_remove(setB)

            if blockers.get(A) == B and setB:
                B = self.draw_one_and_remove(setB)
                setB.add(blockers[A])
            
            pairs.append([A, B])

        if pairs and blockers.get(pairs[-1][0]) == pairs[-1][1]:
            if len(pairs) > 1:
                pairs[-1][1], pairs[-2][1] = pairs[-2][1], pairs[-1][1]

        return pairs

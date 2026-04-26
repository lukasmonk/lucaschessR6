import random


class GenTry:
    def __init__(self, xfrom, xto):
        letra_ini, letra_end = ord(xfrom[0]), ord(xto[0])
        num_ini, num_end = ord(xfrom[1]), ord(xto[1])

        li = []
        for letra in range(letra_ini, letra_end + 1):
            for num in range(num_ini, num_end + 1):
                li.append(chr(letra) + chr(num))
        self.li_base = li
        self.pos = -1
        self.li_current = None
        self.gen_new()

    def gen_new(self):
        self.pos = -1
        self.li_current = self.li_base[:]
        random.shuffle(self.li_current)

    def next(self):
        self.pos += 1
        if self.pos >= len(self.li_current) - 1:
            self.gen_new()
            self.pos += 1
        return self.li_current[self.pos], self.li_current[self.pos + 1]

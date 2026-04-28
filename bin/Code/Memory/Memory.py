import Code
from Code.CompetitionWithTutor import CompetitionWithTutor
from Code.Z import Util


class Memory:
    def __init__(self):

        self.file = Code.configuration.paths.file_train_memory()

        self.dic_data = Util.restore_pickle(self.file)
        if self.dic_data is None:
            self.dic_data = {}
            for x in range(6):
                self.dic_data[x] = [0] * 25

        self.categorias = CompetitionWithTutor.Categorias()

    def name_categoria(self, num_categoria):
        return self.categorias.lista[num_categoria].name()

    def save_category(self, num_cat, num_level, seconds):
        previous = self.dic_data[num_cat][num_level]
        if previous == 0 or previous >= seconds:
            self.dic_data[num_cat][num_level] = seconds
            Util.save_pickle(self.file, self.dic_data)

    @staticmethod
    def get_list_fens(num_piezas):
        li = []

        for path_file in Util.listfiles(Code.path_resource("Trainings", "Checkmates in GM games"), "*.fns"):
            with open(path_file, "rt", encoding="utf-8") as f:
                for fen in f:
                    if fen:
                        pz = 0
                        fen = fen.split("|")[0]
                        for c in fen:
                            if c == " ":
                                break
                            if c in "prnbqkPRNBQK":
                                pz += 1
                        if pz == num_piezas:
                            li.append(fen)

        return list(set(li))

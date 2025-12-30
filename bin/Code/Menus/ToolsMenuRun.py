import os
import random
import stat

import Code
from Code import ManagerSolo, Util
from Code.Base.Constantes import TB_QUIT
from Code.Books import WBooks, WFactory, WPolyglot
from Code.Databases import DBgames, WDB_GUtils, WindowDatabase
from Code.Openings import (
    ManagerOPLEngines,
    ManagerOPLPositions,
    ManagerOPLSequential,
    ManagerOPLStatic,
    OpeningLines,
    WindowOpeningLine,
    WindowOpeningLines,
    WindowOpenings,
)
from Code.QT import Delegados, QTDialogs, QTMessages, QTUtils, ScreenUtils, SelectFiles, WindowManualSave


class ToolsMenuRun:
    def __init__(self, tools_menu):
        self.tools_menu = tools_menu
        self.procesador = tools_menu.procesador
        self.wparent = self.procesador.main_window

    def run(self, resp):
        if resp == "create_own_game":
            self.create_own_game()

        elif resp.startswith("dbase_"):
            comando = resp[6:]
            accion = comando[0]  # R=read database,  N=create new, D=delete, M=direct maintenance
            valor = comando[1:]
            self.database(accion, valor)

        elif resp.startswith("pgn_"):
            if resp == "pgn_visor":
                self.pgn_visor()
            elif resp == "pgn_paste":
                self.pgn_paste()
            elif resp == "pgn_manual_save":
                self.pgn_manual_save()
            elif resp == "pgn_miniatura":
                self.pgn_miniatura()

        elif resp.startswith("openings_"):
            if resp == "openings_lines":
                self.openings_lines()
            elif resp == "openings_custom":
                self.openings_custom()
            elif resp == "openings_polyglot":
                self.openings_polyglot()
            elif resp == "openings_books":
                self.openings_books()

    def create_own_game(self):
        manager = ManagerSolo.ManagerSolo(self.procesador)
        manager.start()

    def database(self, accion, dbpath, is_temporary=False):
        if accion == "M":
            Util.startfile(Code.configuration.paths.folder_databases())
            return

        path_pgn = None
        if accion == "N":
            dbpath, path_pgn = WDB_GUtils.new_database(self.wparent, Code.configuration, with_import_pgn=True)
            if dbpath is None:
                return
            accion = "R"

        if accion == "D":
            resp = QTDialogs.select_db(self.wparent, Code.configuration, True, False)
            if resp:
                if QTMessages.pregunta(self.wparent, "%s\n%s" % (_("Do you want to remove?"), resp)):
                    Util.remove_file(resp)
                    Util.remove_file(resp + ".st1")
                    Util.remove_file(resp[:-5] + ".lcmv")
            return

        if accion == "R":
            Code.configuration.set_last_database(Util.relative_path(dbpath))
            w = WindowDatabase.WBDatabase(self.wparent, self.procesador, dbpath, is_temporary, False)
            if self.wparent:
                with ScreenUtils.EscondeWindow(self.wparent):
                    if path_pgn:
                        w.show()
                        w.wgames.tw_importar_pgn(path_pgn)
                    if w.exec():
                        if w.reiniciar:
                            self.database("R", Code.configuration.get_last_database())
            else:
                Delegados.genera_pm(w.infoMove.board.piezas)
                w.show()

    def pgn_visor(self):
        path = SelectFiles.select_pgn(self.wparent)
        if path:
            self.pgn_read(path)

    def pgn_read(self, fichero_pgn):
        fichero_pgn = os.path.abspath(fichero_pgn)
        cfecha_pgn = str(os.path.getmtime(fichero_pgn))
        path_temp_pgns = Code.configuration.paths.folder_databases_pgn()

        li = list(os.scandir(path_temp_pgns))
        li_ant = []
        for entry in li:
            if entry.name.endswith(".lcdb"):
                li_ant.append(entry)
            else:
                Util.remove_file(entry.path)
        if len(li_ant) > 10:
            li_ant.sort(key=lambda z: z.stat()[stat.ST_ATIME], reverse=True)
            for x in li_ant[10:]:
                Util.remove_file(x.path)

        file_db = Util.opj(path_temp_pgns, os.path.basename(fichero_pgn)[:-3] + "lcdb")

        if Util.exist_file(file_db):
            create = False
            db = DBgames.DBgames(file_db)
            cfecha_pgn_ant = db.read_config("PGN_DATE")
            fichero_pgn_ant = db.read_config("PGN_FILE")
            db.close()
            if cfecha_pgn != cfecha_pgn_ant or fichero_pgn_ant != fichero_pgn:
                create = True
                Util.remove_file(file_db)
        else:
            create = True

        if create:
            db = DBgames.DBgames(file_db)
            dl_tmp = QTDialogs.ImportarFicheroPGN(self.wparent)
            dl_tmp.show()
            db.import_pgns([fichero_pgn], dl_tmp=dl_tmp)
            db.save_config("PGN_DATE", cfecha_pgn)
            db.save_config("PGN_FILE", fichero_pgn)
            db.close()
            dl_tmp.close()

        self.database("R", file_db, is_temporary=True)

    def pgn_paste(self):
        texto = QTUtils.get_txt_clipboard()
        if texto:
            path = Code.configuration.temporary_file("pgn")
            texto = texto.strip()
            if not texto.startswith("["):
                texto = '[Event "%s"]\n\n %s' % (_("Paste PGN"), texto)
            with open(path, "wt", encoding="utf-8", errors="ignore") as q:
                q.write(texto)
            self.pgn_read(path)

    def pgn_manual_save(self):
        WindowManualSave.manual_save(self.procesador)

    def pgn_miniatura(self):
        file_miniatures = Code.path_resource("IntFiles", "Miniatures.lcdb")
        db = DBgames.DBgames(file_miniatures)
        db.all_reccount()
        num_game = random.randint(0, db.reccount() - 1)
        game = db.read_game_recno(num_game)
        db.close()
        dic = {"GAME": game.save()}
        manager = ManagerSolo.ManagerSolo(self.procesador)
        manager.start(dic)

    def openings_lines(self):
        dicline = WindowOpeningLines.openingLines(self.procesador)
        if dicline:
            if "TRAIN" in dicline:
                resp = "tr_%s" % dicline["TRAIN"]
            else:
                resp = WindowOpeningLine.study(dicline["file"])
            if resp is None:
                self.openings_lines()
            else:
                path_fichero = Util.opj(Code.configuration.paths.folder_openings(), dicline["file"])
                if resp == "tr_sequential":
                    self.openings_training_sequential(path_fichero)
                elif resp == "tr_static":
                    self.openings_training_static(path_fichero)
                elif resp == "tr_positions":
                    self.openings_training_positions(path_fichero)
                elif resp == "tr_engines":
                    self.openings_training_engines(path_fichero)

    def openings_custom(self):
        w = WindowOpenings.OpeningsCustom(self.procesador)
        w.exec()

    def openings_training_sequential(self, path_fichero):
        manager = ManagerOPLSequential.ManagerOpeningLinesSequential(self.procesador)
        manager.start(path_fichero)

    def openings_training_engines(self, path_fichero):
        manager = ManagerOPLEngines.ManagerOpeningEngines(self.procesador)
        manager.start(path_fichero)

    def openings_training_static(self, path_fichero):
        dbop = OpeningLines.Opening(path_fichero)
        num_linea = WindowOpeningLines.select_static_line(self.procesador, dbop)
        dbop.close()
        if num_linea is not None:
            manager = ManagerOPLStatic.ManagerOpeningLinesStatic(self.procesador)
            manager.start(path_fichero, "static", num_linea)
        else:
            self.openings_lines()

    def openings_training_positions(self, path_fichero):
        manager = ManagerOPLPositions.ManagerOpeningLinesPositions(self.procesador)
        manager.start(path_fichero)

    def externDatabase(self, file):
        # Code.configuration.ficheroDBgames = file
        self.database("R", file)
        self.procesador.run_action(TB_QUIT)

    def select_1_pgn(self, wparent=None):
        wparent = self.wparent if wparent is None else wparent
        path = SelectFiles.select_pgn(wparent)
        if path:
            fichero_pgn = os.path.abspath(path)
            cfecha_pgn = str(os.path.getmtime(fichero_pgn))
            cdir = Code.configuration.paths.folder_databases_pgn()

            file_db = Util.opj(cdir, os.path.basename(fichero_pgn)[:-4] + ".lcdb")

            if Util.exist_file(file_db):
                create = False
                db = DBgames.DBgames(file_db)
                cfecha_pgn_ant = db.read_config("PGN_DATE")
                fichero_pgn_ant = db.read_config("PGN_FILE")
                db.close()
                if cfecha_pgn != cfecha_pgn_ant or fichero_pgn_ant != fichero_pgn:
                    create = True
                    Util.remove_file(file_db)
            else:
                create = True

            if create:
                db = DBgames.DBgames(file_db)
                dl_tmp = QTDialogs.ImportarFicheroPGN(wparent)
                dl_tmp.show()
                db.import_pgns([fichero_pgn], dl_tmp=dl_tmp)
                db.save_config("PGN_DATE", cfecha_pgn)
                db.save_config("PGN_FILE", fichero_pgn)
                db.close()
                dl_tmp.close()

            db = DBgames.DBgames(file_db)
            if db.all_reccount() == 1:
                game = db.read_game_recno(0)
                db.close()
                return game
            db.close()

            w = WindowDatabase.WBDatabase(self.wparent, self, file_db, True, True)
            if w.exec():
                return w.game

        return None

    def openings_polyglot(self):
        resp = WFactory.polyglots_factory(self.procesador)
        if resp:
            w = WPolyglot.WPolyglot(self.wparent, Code.configuration, resp)
            w.exec()
            self.openings_polyglot()

    def openings_books(self):
        WBooks.registered_books(self.wparent)

import os

from Code import Util
from Code.Analysis import AI
from Code.Base import Game
from Code.Base.Constantes import (
    GT_ALONE,
    GT_GAME,
    GT_VARIATIONS,
)
from Code.Databases import DBgames
from Code.ForcingMoves import ForcingMoves
from Code.Kibitzers import Kibitzers
from Code.ManagerBase import ManagerMenu
from Code.QT import (
    FormLayout,
    Iconos,
    QTDialogs,
    QTMessages,
    QTUtils,
    SelectFiles,
    WindowSavePGN,
)
from Code.Themes import AssignThemes


class ManagerMenuUtilities(ManagerMenu.ManagerMenu):

    def launch(self, li_extra_options=None, with_tree=True):
        menu = QTDialogs.LCMenu(self.main_window)

        si_jugadas = len(self.game) > 0

        # Grabar
        ico_grabar = Iconos.Grabar()
        ico_fichero = Iconos.GrabarFichero()
        ico_camara = Iconos.Camara()
        ico_clip = Iconos.Clipboard()

        tr_fichero = _("Save to a file")
        tr_portapapeles = _("Copy to clipboard")

        menu_save = menu.submenu(_("Save"), ico_grabar)

        key_ctrl = "Ctrl" if self.configuration.x_copy_ctrl else "Alt"
        menu_pgn = menu_save.submenu(_("PGN Format"), Iconos.PGN())
        menu_pgn.opcion("pgnfile", tr_fichero, Iconos.GrabarFichero())
        menu_pgn.separador()
        menu_pgn.opcion("pgnclipboard", tr_portapapeles, ico_clip, shortcut=f"{key_ctrl}+Shift+C")
        menu_save.separador()

        menu_fen = menu_save.submenu(_("FEN Format"), Iconos.Naranja())
        menu_fen.opcion("fenfile", tr_fichero, ico_fichero)
        menu_fen.separador()
        menu_fen.opcion("fenclipboard", tr_portapapeles, ico_clip, shortcut=f'{key_ctrl}+C')

        menu_save.separador()

        menu_save.opcion(
            "lcsbfichero",
            "%s -> %s" % (_("lcsb Format"), _("Create your own game")),
            Iconos.JuegaSolo(),
        )

        menu_save.separador()

        menu_save_db = menu_save.submenu(_("To a database"), Iconos.DatabaseMas())
        QTDialogs.menuDB(menu_save_db, self.configuration, True, indicador_previo="dbf_")  # , remove_autosave=True)
        menu_save.separador()

        menu_save_image = menu_save.submenu(_("Board -> Image"), ico_camara)
        menu_save_image.opcion("volfichero", tr_fichero, ico_fichero)
        menu_save_image.opcion("volportapapeles", tr_portapapeles, ico_clip)

        if len(self.game) > 1:
            menu_save.separador()
            menu_save.opcion("gif", _("As GIF file"), Iconos.GIF())

        menu.separador()

        # Kibitzers
        if self.manager.si_check_kibitzers():
            menu.separador()
            menu_kibitzers = menu.submenu(_("Kibitzers"), Iconos.Kibitzer())

            kibitzers = Kibitzers.Kibitzers()
            for huella, name, ico in kibitzers.lista_menu():
                menu_kibitzers.opcion("kibitzer_%s" % huella, name, ico)
            menu_kibitzers.separador()
            menu_kibitzers.opcion("kibitzer_edit", _("Maintenance"), Iconos.ModificarP())

        # Analizar
        if self.manager.can_be_analysed():
            menu.separador()

            submenu = menu.submenu(_("Analysis"), Iconos.Analizar())

            has_analysis = self.game.has_analisis()
            submenu.opcion("analizar", _("Analyze"), Iconos.Analizar(), shortcut="Alt+A")
            if has_analysis:
                submenu.separador()
                submenu.opcion("analizar_grafico", _("Show graphics"), Iconos.Estadisticas())
            submenu.separador()

            AI.add_submenu(submenu)

            if has_analysis:
                menu.separador()
                label = _("Update themes") if self.game.has_themes() else _("Assign themes")
                menu.opcion("themes_assign", label, Iconos.Themes())

        # Pelicula
        if si_jugadas:
            menu.separador()
            menu.opcion("replay", _("Replay game"), Iconos.Pelicula())

        # Juega por mi + help to move
        if self.manager.active_play_instead_of_me():
            if hasattr(self.manager, "play_instead_of_me"):
                menu.separador()
                menu.opcion(
                    "play_instead_of_me",
                    _("Play instead of me"),
                    Iconos.JuegaPorMi(),
                    shortcut='Ctrl+1',
                )

        if self.manager.active_help_to_move():
            if hasattr(self.manager, "help_to_move"):
                menu.separador()
                menu.opcion(
                    "help_to_move",
                    _("Help to move"),
                    Iconos.BotonAyuda(),
                    shortcut='Ctrl+2',
                )

        # Arbol de movimientos
        if with_tree:
            menu.separador()
            menu.opcion("arbol", _("Moves tree"), Iconos.Arbol(), shortcut='Alt+M')

        menu.separador()
        menu.opcion("play", _("Play current position"), Iconos.MoverJugar(), shortcut='Alt+X')

        # Hints
        menu.separador()
        menu.opcion("forcing_moves", _("Find forcing moves"), Iconos.Thinking())

        # Learn this game
        if len(self.game) > 0:
            menu.separador()
            menu.opcion(
                "learn_mem",
                _("Learn") + " - " + _("Memorizing their moves"),
                Iconos.LearnGame(),
            )

        if si_jugadas:
            menu.separador()
            menu.opcion("borrar", _("Remove"), Iconos.Delete())
            menu.separador()

        # Mas Opciones
        self.add_extra_options(menu, li_extra_options)

        resp = menu.lanza()

        if not resp:
            return None

        if li_extra_options:
            for data in li_extra_options:
                key = data[0]
                if resp == key:
                    return resp

        if resp == "play_instead_of_me":
            getattr(self.manager, "play_instead_of_me")()
            return None

        elif resp == "help_to_move":
            self.manager.check_help_to_move()
            return None

        elif resp == "analizar":
            self.manager.analizar()
            return None

        elif resp == "analizar_grafico":
            self.manager.show_analysis()
            return None

        elif resp == "borrar":
            self.borrar()
            return None

        elif resp == "replay":
            self.manager.replay()
            return None

        elif resp == "play":
            self.manager.play_current_position()
            return None

        elif resp.startswith("kibitzer_"):
            self.manager.kibitzers(resp[9:])
            return None

        elif resp == "arbol":
            self.manager.arbol()
            return None

        elif resp.startswith("vol"):
            accion = resp[3:]
            if accion == "fichero":
                resp = SelectFiles.salvaFichero(
                    self.main_window,
                    _("File to save"),
                    self.configuration.save_folder(),
                    "png",
                    False,
                )
                if resp:
                    self.manager.board.save_as_img(resp, "png")
                    return None
                return None

            else:
                self.manager.board.save_as_img()
                return None

        elif resp == "gif":
            self.save_gif()
            return None

        elif resp == "lcsbfichero":
            self.game.set_extend_tags()
            self.save_lcsb()
            return None

        elif resp == "pgnfile":
            self.game.set_extend_tags()
            self.save_pgn()
            return None

        elif resp == "pgnclipboard":
            self.game.set_extend_tags()
            self.save_pgn_clipboard()
            return None

        elif resp.startswith("dbf_"):
            self.game.set_extend_tags()
            self.save_db(resp[4:])
            return None

        elif resp.startswith("fen"):
            si_fichero = resp.endswith("file")
            self.save_fen(si_fichero)
            return None

        elif resp == "forcing_moves":
            self.forcing_moves()
            return None

        elif resp == "learn_mem":
            self.procesador.learn_game(self.game)
            return None

        elif resp.startswith("ai_"):
            AI.run_menu(self.main_window, resp, self.game)
            return None

        elif resp == "themes_assign":
            self.assign_themes()
            return None

        return None

    def borrar(self):
        form = FormLayout.FormLayout(self.main_window, _("Remove"), Iconos.Delete(), anchoMinimo=300)
        form.apart_np(_("Information"))
        form.checkbox(_("All"), False)
        form.separador()
        form.checkbox(_("Variations"), False)
        form.checkbox(_("Ratings") + " (NAGs)", False)
        form.checkbox(_("Comments"), False)
        form.checkbox(_("Analysis"), False)
        form.checkbox(_("Themes"), False)
        form.checkbox(_("Time used") + " (%emt)", False)
        form.checkbox(_("Pending time") + " (%clk)", False)
        form.separador()

        num_moves, nj, row, is_white = self.manager.current_move()
        with_moves = num_moves > 0 and self.manager.can_be_analysed()
        if with_moves:
            form.apart_np(_("Movements"))
            form.checkbox(_("From the beginning to the active position"), False)
            form.checkbox(_("From the active position to the end"), False)
            form.separador()
        resultado = form.run()
        if resultado:
            (
                is_all,
                variations,
                ratings,
                comments,
                analysis,
                themes,
                time_ms,
                clock_ms,
            ) = resultado[
                1
            ][:8]
            if is_all:
                variations = ratings = comments = analysis = themes = time_ms = clock_ms = True
            self.game.remove_info_moves(variations, ratings, comments, analysis, themes, time_ms, clock_ms)
            if with_moves:
                beginning, ending = resultado[1][8:]
                if beginning:
                    self.game.remove_moves(nj, False)
                    self.manager.goto_firstposition()
                elif ending:
                    self.game.remove_moves(nj, True)
                    self.manager.goto_end()
            self.manager.put_view()
            self.manager.refresh_pgn()
            self.manager.refresh()
            self.manager.check_changed()

    def save_gif(self):
        from Code.QT import WGif

        w = WGif.WGif(self.main_window, self.game)
        w.exec()

    def save_lcsb(self):
        if self.manager.game_type in (GT_ALONE, GT_GAME, GT_VARIATIONS) and hasattr(self, "grabarComo"):
            return getattr(self, "grabarComo")()

        dic = dict(GAME=self.game.save(True))

        extension = "lcsb"
        file = self.configuration.paths.folder_save_lcsb()
        while True:
            file = SelectFiles.salvaFichero(self.main_window, _("File to save"), file, extension, False)
            if file:
                file = str(file)
                if os.path.isfile(file):
                    yn = QTMessages.question_withcancel(
                        self.main_window,
                        _X(
                            _("The file %1 already exists, what do you want to do?"),
                            file,
                        ),
                        si=_("Overwrite"),
                        no=_("Choose another"),
                    )
                    if yn is None:
                        break
                    if not yn:
                        continue
                direc = os.path.dirname(file)
                if direc != self.configuration.paths.folder_save_lcsb():
                    self.configuration.paths.folder_save_lcsb(direc)
                    self.configuration.graba()

                name = os.path.basename(file)
                if Util.save_pickle(file, dic):
                    QTMessages.temporary_message(self.main_window, _X(_("Saved to %1"), name), 0.8)
                    return
                else:
                    QTMessages.message_error(self.main_window, "%s: %s" % (_("Unable to save"), name))

            break

    def save_pgn(self):
        w = WindowSavePGN.WSave(self.main_window, self.game)
        w.exec()

    def save_fen(self, with_file):
        dato = self.manager.listado("fen")
        if with_file:
            extension = "fns"
            resp = SelectFiles.salvaFichero(
                self.main_window,
                _("File to save"),
                self.configuration.save_folder(),
                extension,
                False,
            )
            if resp:
                if "." not in resp:
                    resp += ".fns"
                try:
                    modo = "w"
                    if Util.exist_file(resp):
                        yn = QTMessages.question_withcancel(
                            self.main_window,
                            _X(
                                _("The file %1 already exists, what do you want to do?"),
                                resp,
                            ),
                            si=_("Append"),
                            no=_("Overwrite"),
                        )
                        if yn is None:
                            return
                        if yn:
                            modo = "a"
                            dato = "\n" + dato
                    with open(resp, modo, encoding="utf-8", errors="ignore") as q:
                        q.write(dato)
                    QTMessages.message_bold(self.main_window, _X(_("Saved to %1"), resp))
                    direc = os.path.dirname(resp)
                    if direc != self.configuration.save_folder():
                        self.configuration.set_save_folder(direc)
                except:
                    QTUtils.set_clipboard(dato)
                    QTMessages.message_error(
                        self.main_window,
                        "%s : %s\n\n%s"
                        % (
                            _("Unable to save"),
                            resp,
                            _("It is saved in the clipboard to paste it wherever you want."),
                        ),
                    )

        else:
            QTUtils.set_clipboard(dato)
            QTDialogs.fen_is_in_clipboard(self.main_window)

    def save_pgn_clipboard(self):
        dic = WindowSavePGN.read_config_savepgn()
        if dic.get("SEVENTAGS", False):
            game_tmp = self.game.copia()
            game_tmp.add_seventags()
        else:
            game_tmp = self.game
        QTUtils.set_clipboard(game_tmp.pgn())
        QTMessages.message_bold(self.main_window, _("PGN is in clipboard"))

    def save_db(self, database):
        try:
            pgn = self.manager.listado("pgn")
            li_tags = []
            for linea in pgn.split("\n"):
                if linea.startswith("["):
                    ti = linea.split('"')
                    if len(ti) == 3:
                        key = ti[0][1:].strip()
                        valor = ti[1].strip()
                        li_tags.append([key, valor])
                else:
                    break
        except AttributeError:
            li_tags = []

        pc = Game.Game(li_tags=li_tags)
        pc.assign_other_game(self.game)

        db = DBgames.DBgames(database)
        resp = db.insert(pc)
        db.close()
        if resp:
            QTMessages.message_bold(self.main_window, _("Saved") + ": " + db.path_file)
        else:
            QTMessages.message_error(self.main_window, _("This game already exists."))

    def forcing_moves(self):
        fen = self.manager.board.last_position.fen()
        num_moves, nj, row, is_white = self.manager.current_move()
        if num_moves and num_moves > (nj + 1):
            move = self.game.move(nj + 1)
            fen = self.board.last_position.fen()
            if move.analysis:
                mrm, pos = move.analysis
                forcing_moves = ForcingMoves.ForcingMoves(self.board, mrm, self.main_window)
                forcing_moves.fm_show_checklist()
                return

        self.main_window.pensando_tutor(True)
        mrm = self.manager.manager_analyzer.analiza(fen)
        self.main_window.pensando_tutor(False)
        forcing_moves = ForcingMoves.ForcingMoves(self.board, mrm, self.main_window)
        forcing_moves.fm_show_checklist()

    def assign_themes(self):
        st_themes = set()
        for move in self.game.li_moves:
            if move.has_themes():
                st_themes.update(move.li_themes)
        if st_themes:
            themes = ", ".join(AssignThemes.AssignThemes().liblk80_themes(st_themes))
            if themes:
                delete_previous = QTMessages.pregunta(
                    self.main_window,
                    _("Pre-delete the following themes?") + f"<br><br>{themes}",
                )
            else:
                delete_previous = False
        else:
            delete_previous = False
        at = AssignThemes.AssignThemes()
        at.assign_game(self.game, True, delete_previous)
        self.manager.refresh_pgn()
        QTMessages.temporary_message(self.main_window, _("Done"), 1.4, with_image=False)

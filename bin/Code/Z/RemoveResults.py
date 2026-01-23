
import Code
from Code.Z import Util
from Code.QT import Iconos, QTDialogs, QTMessages


class RemoveResults:
    def __init__(self, wowner):
        self.wowner = wowner
        self.configuration = Code.configuration
        self.list_results = [
            (_("Challenge 101"), Iconos.Wheel(), self.rem_101),
            (
                _("Check your memory on a chessboard"),
                Iconos.Memoria(),
                self.rem_check_your_memory,
            ),
            (
                _("The Washing Machine"),
                Iconos.WashingMachine(),
                self.rem_washing_machine,
            ),
        ]

    def menu(self):
        menu = QTDialogs.LCMenu(self.wowner)

        menu.opcion(None, _("Remove results"), Iconos.Delete(), is_disabled=True)
        menu.separador()

        for label, icon, action in self.list_results:
            menu.opcion((action, label), label, icon)
            menu.separador()

        resp = menu.lanza()
        if resp:
            action, label = resp
            mens = f'{label}\n\n{_("Remove results")}\n\n\n{_("Are you sure?")}'
            if not QTMessages.pregunta(self.wowner, mens):
                return
            action()
            QTMessages.temporary_message(self.wowner, _("Done"), 0.8)

    def rem_101(self):
        self.configuration.write_variables("challenge101", {})

    def rem_check_your_memory(self):
        Util.remove_file(self.configuration.paths.file_train_memory())

    def rem_washing_machine(self):
        Util.remove_file(self.configuration.paths.file_washing_machine())

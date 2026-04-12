from PySide6 import QtCore, QtWidgets

import Code
from Code.About import AboutBase
from Code.QT import Colocacion, Controles, Iconos


class WAbout(QtWidgets.QDialog):
    def __init__(self):
        procesador = Code.procesador
        super(WAbout, self).__init__(procesador.main_window)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # gen_web_bootstrap()

        self.setWindowTitle(_("About"))
        self.setWindowIcon(Iconos.Aplicacion64())
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowMaximizeButtonHint
        )

        self.resize(1100, 700)  # Wider to see more tabs at once

        self.f = Controles.FontTypeNew(point_size=10)

        head = f'<span style="font-size:30pt; font-weight="700"; font-family:arial; >{Code.lucas_chess}</span><br>'
        head += f'<span style="font-size:15pt;">{_X(_("version %1"), Code.VERSION)}</span><br>'
        head += (
            f'<span style="font-size:10pt;>{_("Author")}: <a href="mailto:lukasmonk@gmail.com">Lucas Monge</a></span>'
        )
        head += f' - <a style="font-size:10pt;" href="{Code.web}">{Code.web}</a>'
        head += f' - <a style="font-size:10pt;" href="{Code.blog}">Blog : Fresh news</a>'
        head += f' - <a style="font-size:10pt;" href="{Code.github}">Sources: github</a>'
        head += (
            f'<br>{_("License")} <a style="font-size:10pt;" '
            f'href="https://www.gnu.org/licenses/gpl-3.0.html">GPL 3.0</a>'
        )

        lb_ico = Controles.LB(self).put_image(Iconos.pmAplicacion64())
        lb_titulo = Controles.LB(self, head)

        # Tabs setup
        self.tab = Controles.Tab()
        self.tab.set_font(self.f)
        self.tab.currentChanged.connect(self.on_tab_changed)

        self.ib = AboutBase.ThanksTo()
        self.tab_metadata = {}  # index -> (key, sa)
        self.subtab_metadata = {}  # index -> (key, num, sa)
        self.loaded_tabs = set()
        self.loaded_subtabs = set()

        self.sub_tab = None
        self.engines_main_idx = -1

        for k, titulo in self.ib.dic.items():
            if "-" in k:
                base, num = k.split("-")
                if num == "1":
                    self.sub_tab = Controles.Tab()
                    self.sub_tab.set_font(self.f)
                    self.sub_tab.currentChanged.connect(self.on_subtab_changed)
                    self.engines_main_idx = self.tab.addTab(self.sub_tab, _("Engines"))

                # Create scroll area placeholder
                sa = QtWidgets.QScrollArea(self)
                sa.setWidgetResizable(True)

                # Need title for subtabs (e.g. "Abrok - Cheng")
                # This is relatively fast compared to generating the whole HTML
                lm = self.ib.list_engines(num)
                titulo_sub = f"{lm[0][0].split(' ')[1]} - {lm[-1][0].split(' ')[1]}"

                idx = self.sub_tab.addTab(sa, titulo_sub)
                self.subtab_metadata[idx] = (k, sa)
            else:
                sa = QtWidgets.QScrollArea(self)
                sa.setWidgetResizable(True)
                idx = self.tab.addTab(sa, titulo)
                self.tab_metadata[idx] = (k, sa)

        ly_v1 = Colocacion.H().control(lb_ico).espacio(15).control(lb_titulo).relleno()
        layout = Colocacion.V().otro(ly_v1).espacio(10).control(self.tab).margen(10)

        self.setLayout(layout)

        # Trigger load for the first tab
        self.on_tab_changed(0)

    def on_tab_changed(self, index):
        if index == self.engines_main_idx:
            # Ensure the current subtab is loaded
            self.on_subtab_changed(self.sub_tab.currentIndex())
            return

        if index in self.tab_metadata and index not in self.loaded_tabs:
            key, sa = self.tab_metadata[index]
            self._fill_sa(key, sa)
            self.loaded_tabs.add(index)

    def on_subtab_changed(self, index):
        if index in self.subtab_metadata and index not in self.loaded_subtabs:
            key, sa = self.subtab_metadata[index]
            self._fill_sa(key, sa)
            self.loaded_subtabs.add(index)

    def _fill_sa(self, key, sa):
        txt = self.ib.texto(key)
        lb = Controles.LB(self, txt)
        lb.set_font(self.f)
        lb.set_wrap()
        sa.setWidget(lb)



# def gen_web_bootstrap():
#     """
#     <nav>
#   <div class="nav nav-tabs" id="nav-tab" role="tablist">
#     <a class="nav-link active" id="nav-home-tab" data-bs-toggle="tab" href="#nav-home" role="tab" aria-controls="nav-home" aria-selected="true">Home</a>
#     <a class="nav-link" id="nav-profile-tab" data-bs-toggle="tab" href="#nav-profile" role="tab" aria-controls="nav-profile" aria-selected="false">Profile</a>
#     <a class="nav-link" id="nav-contact-tab" data-bs-toggle="tab" href="#nav-contact" role="tab" aria-controls="nav-contact" aria-selected="false">Contact</a>
#   </div>
# </nav>
# <div class="tab-content" id="nav-tabContent">
#   <div class="tab-pane fade show active" id="nav-home" role="tabpanel" aria-labelledby="nav-home-tab">...</div>
#   <div class="tab-pane fade" id="nav-profile" role="tabpanel" aria-labelledby="nav-profile-tab">...</div>
#   <div class="tab-pane fade" id="nav-contact" role="tabpanel" aria-labelledby="nav-contact-tab">...</div>
# </div>
#     """
#     ib = AboutBase.ThanksTo()
#
#     dic = ib.dic
#
#     with open(r"h:\lucaschess\WEB\mysite\templates\Thanksto.html", "wt", encoding="utf-8") as q:
#
#         li = ['{% extends "base.html" %}',
#               '{% block contenido %}',
#               "<nav>",
#               '<div class="nav nav-tabs" id="nav-tab" role="tablist">'
#               ]
#         first = True
#         for clave, rotulo in dic.items():
#             if first:
#                 first = False
#                 active = " active"
#                 selected = "true"
#             else:
#                 active = ""
#                 selected = "false"
#
#             # engines
#             if "-" in clave:
#                 if not clave.endswith("-1"):
#                     continue
#                 clave = clave[:-2]
#                 rotulo = rotulo[:-2]
#             html = (
#                 '<a class="nav-link%s" id="nav-%s-tab" '
#                 'data-bs-toggle="tab" href="#nav-%s" role="tab" '
#                 'aria-controls="nav-%s" aria-selected="%s"><h5 class="mb-0 text-secondary">{{_("%s")}}</h5></a>' % (active, clave, clave, clave, selected, rotulo)
#             )
#             li.append(html)
#
#         li.extend(["</div>", "</nav>", "<br>"])
#
#         li.append('<div class="tab-content" id="nav-tabContent">')
#         first = True
#         for clave, rotulo in dic.items():
#             if first:
#                 first = False
#                 active = " show active"
#             else:
#                 active = ""
#
#             # engines
#             if "-" in clave:
#                 if not clave.endswith("-1"):
#                     continue
#                 clave = clave[:-2]
#                 li_eng_txt = []
#                 li_eng_txt.append('<table class="table table-bordered">')
#                 li_eng_txt.append('<tr>')
#                 li_eng_txt.append('<th>{{_("Engine")}}</th>')
#                 li_eng_txt.append('<th>OS</th>')
#                 li_eng_txt.append('<th>{{_("Author")}}</th>')
#                 li_eng_txt.append('<th>{{_("Web")}}</th>')
#                 li_eng_txt.append('</tr>')
#
#                 li_eng = Code.configuration.engines.list_internal_name_author_url()
#
#                 lix = []
#                 so = "Windows"
#                 for (name, autor, url) in li_eng:
#                     if name == "Maia-1100":
#                         name = "Maia-1100/2200"
#                     elif name.startswith("Maia"):
#                         continue
#                     if "-bmi2" in name:
#                         name = name.replace("-bmi2", "")
#                     if name.endswith("64"):
#                         name = name.replace("64", "")
#                     if name == "Komodo Dragon 1":
#                         name = "Dragon-1"
#                     lix.append((name, autor, url, so))
#                 li_eng = lix
#
#                 with open(r".\OS\linux\OSEngines.py", "rt", encoding="utf-8") as flnx:
#                     cod_linux = flnx.read()
#
#                     # Crear un namespace para ejecutar
#                     namespace = {}
#                     exec(cod_linux, namespace)
#
#                     # Ejecutar la función
#                     dic = namespace['read_engines'](".")
#                     for key, engine in dic.items():
#                         name = engine.name
#                         autor = engine.autor
#                         url = engine.url
#                         so = "Linux"
#                         if name == "Maia-1100":
#                             name = "Maia-1100/2200"
#                         elif name.startswith("Maia"):
#                             continue
#                         if "-bmi2" in name:
#                             name = name.replace("-bmi2", "")
#                         if name.endswith("64"):
#                             name = name.replace("64", "")
#                         li_eng.append((name, autor, url, so))
#
#                 li_eng.sort(key=lambda xt: xt[0].upper())
#
#                 for pos, (name, autor, url, so) in enumerate(li_eng, 1):
#                     li_eng_txt.append("<tr>")
#                     li_eng_txt.append("<td>%s</td>" % name)
#                     li_eng_txt.append("<td>%s</td>" % so)
#                     li_eng_txt.append("<td>%s</td>" % autor)
#                     li_eng_txt.append('<td><a href="%s">%s</a></td>' % (url, url))
#                     li_eng_txt.append("</tr>")
#                 li_eng_txt.append('</table>')
#                 txt = "\n".join(li_eng_txt)
#             else:
#                 txt = ib.texto(clave)
#                 if clave == "contributors":
#                     txt = txt.replace("<br>", "")
#
#             html = '<div class="tab-pane fade%s" id="nav-%s" role="tabpanel" aria-labelledby="nav-%s-tab">%s</div>' % (active, clave, clave, txt)
#             li.append(html)
#
#         li.append("</div>")
#         li.append("{% endblock contenido %}")
#
#         txt = "\n".join(li)
#
#         dic = Code.translations.dic_translate
#
#         for k in dic:
#             if f">{k}<" in txt:
#                 txt = txt.replace(f">{k}<", '>{{ _("%s") }}<' % k)
#
#         q.write(txt)

from Code.Base.Constantes import (
    ALLGAME,
    BLUNDER,
    ENDGAME,
    GOOD_MOVE,
    INACCURACY,
    INTERESTING_MOVE,
    MIDDLEGAME,
    MISTAKE,
    OPENING,
    VERY_GOOD_MOVE,
)
from Code.Nags import Nags


class ShowHtml:
    def __init__(self, nmoves_analyzed):
        self.html = []
        self.white_analyzed, self.black_analyzed = (
            nmoves_analyzed[True],
            nmoves_analyzed[False],
        )
        self.total_analyzed = self.white_analyzed + self.black_analyzed
        self.li_body = []
        self.maxlabel6 = 0

    @staticmethod
    def pvar(x, tt):
        return f"{x * 100.0 / tt:.01f}%" if tt and x else "-"

    def check_maxlabel(self, txt):
        if len(txt) >= self.maxlabel6:
            self.maxlabel6 = len(txt)
        return "|SP|"

    def add_group6(self, group, *moves):
        sp = self.check_maxlabel(group)
        tw = tb = 0
        for wb in moves:
            tw += wb[True]
            tb += wb[False]
        tt = tw + tb
        if tt == 0:
            return False
        pw = self.pvar(tw, self.white_analyzed)
        pb = self.pvar(tb, self.black_analyzed)
        pt = self.pvar(tt, self.total_analyzed)

        self.li_body.append(
            f"""<tr class="group"><td>{group}{sp}</td>
              <td class="val">{tw}</td>
              <td class="val">{tb}</td>
              <td class="val">{tt}</td>
              <td class="val">{pw}</td>
              <td class="val">{pb}</td>
              <td class="val">{pt}</td>
            </tr>"""
        )
        return True

    def add_label6(self, name_class, label, moves, sym=None):
        sp = self.check_maxlabel(label)
        w, b = moves[True], moves[False]
        t = w + b
        # if t == 0:
        #     return
        pw = self.pvar(w, self.white_analyzed)
        pb = self.pvar(b, self.black_analyzed)
        pt = self.pvar(t, self.total_analyzed)
        rest = f"""<td class="val"><small>{sym}</small></td>""" if sym else ""
        self.li_body.append(
            f"""<tr class="{name_class}"><td class="label">{sp}{label}</td>
              <td class="val">{w}</td>
              <td class="val">{b}</td>
              <td class="val">{t}</td>
              <td class="val">{pw}</td>
              <td class="val">{pb}</td>
              <td class="val">{pt}</td>{rest}
            </tr>"""
        )

    def add_total6(self):
        label = _("Moves analyzed")
        sp = self.check_maxlabel(label)
        self.li_body.append(
            f"""<tr class="total"><td class="val">{sp}{label}{sp}</td>
              <td class="val">{self.white_analyzed}</td>
              <td class="val">{self.black_analyzed}</td>
              <td class="val">{self.total_analyzed}</td>
            </tr>"""
        )

    def moves_html(
        self,
        moves_very_good,
        moves_good,
        moves_good_no,
        moves_interestings,
        moves_gray,
        moves_inaccuracies,
        moves_mistakes,
        moves_blunders,
    ):
        if self.total_analyzed == 0:
            return _("There are no analyzed moves.")

        if self.add_group6(
            _("Best moves"),
            moves_very_good,
            moves_good,
            moves_interestings,
            moves_good_no,
        ):
            self.add_label6("brilliant", _("Brilliant moves"), moves_very_good, "‼")
            self.add_label6("good", _("Good moves"), moves_good, "!")
            self.add_label6("interesting", _("Interesting moves"), moves_interestings, "⁉")
            self.add_label6("easy-good", _("Other best moves"), moves_good_no)

        if self.add_group6(_("Acceptable moves"), moves_gray):
            pass
            # self.add_label6("normal", _("Acceptable moves"), moves_gray)

        if self.add_group6(_("Bad moves"), moves_inaccuracies, moves_mistakes, moves_blunders):
            self.add_label6("inaccuracy", _("Dubious moves"), moves_inaccuracies, "⁈")
            self.add_label6("mistake", _("Mistakes"), moves_mistakes, "?")
            self.add_label6("blunder", _("Blunders"), moves_blunders, "⁇")

        self.add_total6()

        resp = self.xhtml("".join(self.li_body), True)
        sp = "&nbsp;" * (self.maxlabel6 // 2)
        resp = resp.replace("|SP|", sp)

        self.li_body = []
        return resp

    def elo_html(self, elos_form):
        if self.total_analyzed == 0:
            return _("There are no analyzed moves.")

        def add_label(name_class, tipo, label):
            w, b = (
                elos_form[True][tipo],
                elos_form[False][tipo],
            )
            t = w + b
            if t == 0:
                return
            mt = t // 2 if w and b else t
            self.li_body.append(
                f"""<tr class="{name_class}"><td class="label">{label}</td>
                  <td class="val">{w or ""}</td>
                  <td class="val">{b or ""}</td>
                  <td class="val">{mt}</td>
                </tr>"""
            )

        add_label("total", ALLGAME, _("Elo performance"))
        for std, tit in (
            (OPENING, _("Opening")),
            (MIDDLEGAME, _("Middlegame")),
            (ENDGAME, _("Endgame")),
        ):
            add_label("normal", std, tit)

        resp = self.xhtml("".join(self.li_body), False)
        self.li_body = []
        return resp

    def indices_html(self, li_indices):
        if self.total_analyzed == 0:
            return _("There are no analyzed moves.")

        for indice in li_indices:
            label, w, b, t = indice
            self.li_body.append(
                f"""<tr class="normal"><td class="label">{label}</td>
                  <td class="val">{w}</td>
                  <td class="val">{b}</td>
                  <td class="val">{t}</td>
                </tr>"""
            )

        resp = self.xhtml("".join(self.li_body), False)
        self.li_body = []
        return resp

    @staticmethod
    def xhtml(body, is_doble):
        single = f"""              <th>{_("White")}</th>
              <th>{_("Black")}</th>
              <th>{_("Total")}</th>
"""
        doble = single if is_doble else ""
        return f"""<head><style>
          body {{
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #333;
            background-color: #fdfdfd;
            margin: 10px;
          }}

          table.stats {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            background-color: #fff;
          }}

          table.stats th, table.stats td {{
            padding: 12px 8px;
            border-bottom: 1px solid #f0f0f0;
            border-right: 1px solid #f0f0f0;
          }}

          table.stats th {{
            background-color: #f8f9fa;
            color: #555;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
          }}

          table.stats tr:last-child td {{
            border-bottom: none;
          }}

          table.stats tr td:last-child, table.stats tr th:last-child {{
            border-right: none;
          }}

          table.stats tr:hover {{
            background-color: #fcfcfc;
          }}

          /* category headers */
          .group {{
            background-color: #f4f6f9 !important;
            color: #2c3e50;
            font-weight: 700;
            text-align: left;
            font-size: 1.05em;
          }}

          /* subcategories */
          .brilliant {{ color:{Nags.nag_color(VERY_GOOD_MOVE)}; font-weight: 600; }}
          .good {{ color:{Nags.nag_color(GOOD_MOVE)}; font-weight: 600; }}
          .easy-good {{ color: #4a90e2; font-weight: 600; }}

          .interesting {{ color:{Nags.nag_color(INTERESTING_MOVE)}; font-weight: 600; }}
          .normal {{ color: #666; }}

          .inaccuracy {{ color:{Nags.nag_color(INACCURACY)}; font-weight: 600; }}
          .mistake {{ color:{Nags.nag_color(MISTAKE)}; font-weight: 600; }}
          .blunder {{ color:{Nags.nag_color(BLUNDER)}; font-weight: 600; }}

          .total {{
            background-color: #f0f2f5 !important;
            font-weight: 800;
            color: #1a1a1a;
          }}

          .val {{
            text-align: center;
          }}

          .label {{
            text-align: right;
            padding-right: 20px !important;
            font-weight: 500;
            color: #444;
          }}

          small {{
            font-weight: bold;
            font-size: 1.1em;
            padding-left: 5px;
          }}
    </style>
    </head>
    <body>
        <table class="stats">
          <thead>
            <tr>
              <th style="width: 30%;"></th>
              {single}
              {doble}
            </tr>
          </thead>
          <tbody>
          {body}
          </tbody>
        </table>
    </body>"""

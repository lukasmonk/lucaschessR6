import builtins
import locale
import os

import polib

import Code
from Code.Z import Util


class Translations:
    def __init__(self, lang):
        self.lang = self.check_lang(lang)
        self.dic_translate = self.read_mo()
        self.dic_openings = self.read_mo_openings()

        for key, routine in (
            ("_X", self.x),
            ("_F", self.f),
            ("_FO", self.translate_opening),
            ("_SP", self.sp),
            ("_", self.translate),
        ):
            setattr(builtins, key, routine)

        Code.lucas_chess = self.translate("Lucas Chess")

    @staticmethod
    def sinonimos(dic):
        def pon(key, keybase):
            if keybase in dic:
                dic[key] = dic[keybase]

        pon("X-ray attack", "X-Ray attack")
        pon("Attacking Defender", "Attacking defender")

    @staticmethod
    def update_dic(dic: dict, path: str, is_mo: bool):
        if Util.exist_file(path):
            try:
                if is_mo:
                    pomofile = polib.mofile(path)
                else:
                    pomofile = polib.pofile(path)

                def lmp(msg):
                    if "||" in msg:
                        msg = msg[msg.index("||"):].strip()
                    return msg

                dicn = {entry.msgid: lmp(entry.msgstr) for entry in pomofile}
                dic.update(dicn)
            except:
                return

    def read_mo(self):
        path_mo = self.get_path(self.lang)
        dic = {}
        self.update_dic(dic, path_mo, is_mo=True)
        if not Code.configuration.x_translation_mode:
            if Code.configuration.x_translator_google:
                path_mo = self.get_path_google_translate(self.lang)
                self.update_dic(dic, path_mo, is_mo=True)
            if Code.configuration.x_translation_local:
                path_po = Util.opj(Code.configuration.paths.folder_userdata(),
                                   "Translations", f"{self.lang}.po")
                self.update_dic(dic, path_po, is_mo=False)

        self.sinonimos(dic)
        return dic

    def read_mo_openings(self):
        path_mo = self.get_path_openings(self.lang)
        dic = {}
        self.update_dic(dic, path_mo, is_mo=True)
        if not Code.configuration.x_translation_mode:
            if Code.configuration.x_translator_google_openings:
                path_mo = self.get_path_google_translate_openings(self.lang)
                self.update_dic(dic, path_mo, is_mo=True)
            if Code.configuration.x_translation_local:
                path_po = Util.opj(Code.configuration.paths.folder_userdata(),
                                   "Translations", f"openings_{self.lang}.po")
                self.update_dic(dic, path_po, is_mo=False)

        return dic

    def translate(self, txt):
        trans = self.dic_translate.get(txt)
        if trans is None:
            trans = txt
            if "||" in txt:
                trans = txt[: txt.index("||")].strip()
            elif txt in self.dic_openings:
                trans = self.dic_openings[txt]
            self.dic_translate[txt] = trans
        return trans

    def is_key(self, key):
        return key in self.dic_translate

    def translate_opening(self, opening):
        return self.dic_openings.get(opening, self.dic_translate.get(opening, opening))

    @staticmethod
    def get_path(lang):
        path_locale = Code.path_resource("Locale")
        return f"{path_locale}/{lang}/LC_MESSAGES/lucaschess.mo"

    @staticmethod
    def get_path_google_translate(lang):
        path_locale = Code.path_resource("Locale")
        return f"{path_locale}/{lang}/LC_MESSAGES/g_lucaschess.mo"

    @staticmethod
    def get_path_google_translate_openings(lang):
        path_locale = Code.path_resource("Locale")
        return f"{path_locale}/{lang}/LC_MESSAGES/g_lcopenings.mo"

    @staticmethod
    def get_path_openings(lang):
        path_locale = Code.path_resource("Locale")
        return f"{path_locale}/{lang}/LC_MESSAGES/lcopenings.mo"

    def check_lang(self, lang):
        if not lang:
            lang = "en"
            li_info = locale.getdefaultlocale()
            if len(li_info) == 2:
                if li_info[0]:
                    lang = li_info[0][:2]
        path = self.get_path(lang)
        return lang if os.path.isfile(path) else "en"

    def f(self, txt):
        return self.translate(txt) if txt else ""

    def sp(self, key):
        if not key:
            return ""
        key = key.strip()
        t = self.f(key)
        if t == key:
            li = []
            for x in key.split(" "):
                if x:
                    li.append(_F(x))
            return " ".join(li)
        else:
            return t

    @staticmethod
    def x(key, op1, op2=None, op3=None):
        if not key:
            return ""
        resp = key.replace("%1", op1)
        if op2:
            resp = resp.replace("%2", op2)
            if op3:
                resp = resp.replace("%3", op3)
        return resp


def install(lang):
    do_install = Code.translations is None
    if not do_install:
        builtins_trans = getattr(builtins, "_")
        do_install = builtins_trans is None or builtins_trans != Code.translations.translate
        if not do_install:
            do_install = Code.translations.lang != lang
    if do_install:
        Code.translations = Translations(lang)

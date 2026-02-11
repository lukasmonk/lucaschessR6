import operator

import OSEngines

import Code
from Code.Z import Util
from Code.Base.Constantes import (
    ENG_FIXED,
)


class ConfigEngines:
    _dic_engines_internal: dict
    _dic_engines_external: dict
    _dic_engines: dict

    def __init__(self, configuration):
        self.configuration = configuration
        self.reset()

    def reset(self):
        self._dic_engines = {}
        self._read_internal()
        self._read_external()
        self._dic_engines.update(self._dic_engines_internal)
        self._dic_engines.update(self._dic_engines_external)

    def _read_internal(self):
        self._dic_engines_internal = OSEngines.read_engines(Code.folder_engines)

    def _read_external(self):
        self._dic_engines_external = {}
        if li := Util.restore_pickle(self.configuration.paths.file_external_engines()):
            from Code.Engines import Engines

            for x in li:
                eng = Engines.Engine()
                if not eng.restore(x):
                    continue

                if eng.exists():
                    key = eng.key
                    n = 0
                    while eng.key in self._dic_engines:
                        n += 1
                        eng.key = "%s-%d" % (key, n)
                    eng.set_extern()
                    self._dic_engines_external[eng.key] = eng

    def dic_engines(self):
        return self._dic_engines

    def search(self, alias, defecto=None):
        if alias in self._dic_engines:
            return self._dic_engines[alias].clone()
        if defecto is None:
            defecto = self.configuration.x_rival_inicial
        return self.search(defecto)

    def search_tutor(self, key):
        if key in self._dic_engines:
            eng = self._dic_engines[key]
            if eng.can_be_tutor_analyzer():
                return eng.clone()
        return self.search_tutor(self.configuration.tutor_default)

    def list_alias_name_multipv(self):
        li = []
        for key, cm in self._dic_engines.items():
            if cm.can_be_tutor_analyzer():
                li.append((key, cm.nombre_ext()))
        li = sorted(li, key=operator.itemgetter(1))
        li.insert(0, self.configuration.x_tutor_clave)
        return li

    def list_name_alias_multipv(self):
        li = []
        for key, cm in self._dic_engines.items():
            if cm.can_be_tutor_analyzer():
                li.append((cm.nombre_ext(), key))
        li.sort(key=operator.itemgetter(1))
        return li

    def list_name_alias(self):
        li = []
        for key, cm in self._dic_engines.items():
            li.append((cm.nombre_ext(), key))
        li.sort(key=lambda x: x[0].upper())
        return li

    def list_name_alias_multipv10(self, minimo=10):
        li_motores = []
        for key, cm in self._dic_engines.items():
            if cm.maxMultiPV >= minimo and not cm.is_maia():
                li_motores.append((cm.nombre_ext(), key))
        li_motores.sort(key=lambda x: x[0])
        return li_motores

    def list_name_internal(self):
        li = [cm for k, cm in self._dic_engines.items() if not cm.is_type_external()]
        li = sorted(li, key=lambda cm: cm.name)
        return li

    def list_name_external(self):
        return [cm for k, cm in self._dic_engines.items() if cm.is_type_external()]

    def reset_external(self):
        self._dic_engines = {}
        self._read_external()
        self._dic_engines.update(self._dic_engines_internal)
        self._dic_engines.update(self._dic_engines_external)

    def list_internal_name_author_url(self):
        li = []
        for k, v in self._dic_engines.items():
            if v.is_type_external():
                continue
            name = v.name
            li.append([name, v.autor, v.url])
        li = sorted(li, key=lambda x: x[0].upper())
        return li

    def list_about(self):
        li = self.list_internal_name_author_url()
        li_resp = []
        maia = True
        for engine in li:
            if engine[0].lower().startswith("maia"):
                if maia:
                    engine[0] = "Maia 1100-2200"
                    maia = False
                else:
                    continue
            li_resp.append(engine)
        return li_resp

    @staticmethod
    def dic_fixed_elo():
        d = OSEngines.dic_engines_fixed_elo(Code.folder_engines)
        for elo, lien in d.items():
            for cm in lien:
                cm.type = ENG_FIXED
                cm.elo = elo
        return d

    def _ensure_exe_exists(self, eng):
        """If the engine exe is missing, run CheckEngines once and recheck."""
        if Util.exist_file(eng.path_exe):
            return True
        from Code.Engines import CheckEngines
        CheckEngines.check_stockfish(check_again=True)
        return Util.exist_file(eng.path_exe)

    def engine_tutor(self):
        alias_tutor = self.configuration.x_tutor_clave
        if alias_tutor in self._dic_engines:
            eng = self._dic_engines[alias_tutor]
            if eng.can_be_tutor_analyzer() and self._ensure_exe_exists(eng):
                eng.reset_uci_options()
                dic = self.configuration.read_variables("TUTOR_ANALYZER")
                for key, value in dic.get("TUTOR", []):
                    eng.set_uci_option(key, value)
                return eng
        default = self.configuration.tutor_default
        if alias_tutor != default:
            self.configuration.x_tutor_clave = default
            return self.engine_tutor()
        return None

    def engine_analyzer(self):
        alias_analyzer = self.configuration.x_analyzer_clave
        if alias_analyzer in self._dic_engines:
            eng = self._dic_engines[alias_analyzer]
            if eng.can_be_tutor_analyzer() and self._ensure_exe_exists(eng):
                eng.reset_uci_options()
                dic = self.configuration.read_variables("TUTOR_ANALYZER")
                for key, value in dic.get("ANALYZER", []):
                    eng.set_uci_option(key, value)
                return eng
        default = self.configuration.analyzer_default
        if alias_analyzer != default:
            self.configuration.x_analyzer_clave = default
            return self.engine_analyzer()
        return None

    def set_logs(self, ok):
        path_log = Util.opj(self.configuration.paths.folder_userdata(), "active_logs.engines")
        if ok:
            with open(path_log, "wt") as q:
                q.write("x")
        else:
            Util.remove_file(path_log)

    def check_logs_active(self):
        path_log = Util.opj(self.configuration.paths.folder_userdata(), "active_logs.engines")
        return Util.exist_file(path_log)

    def formlayout_combo_analyzer(self, only_multipv):
        li = []
        for key, cm in self._dic_engines.items():
            if not only_multipv or cm.can_be_tutor_analyzer():
                li.append((key, cm.nombre_ext()))
        li = sorted(li, key=operator.itemgetter(1))
        li.insert(0, ("default", _("Default analyzer")))
        li.insert(0, "default")
        return li

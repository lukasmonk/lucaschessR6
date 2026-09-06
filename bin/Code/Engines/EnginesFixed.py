import OSEngines

import Code


def dic_engines_fixed_elo(folder_engines):
    d = Code.configuration.engines.dic_engines_internal()
    dic = {}
    li_engines = OSEngines.li_engines_fixed_elo()

    for nm, xfrom, xto in li_engines:
        for elo in range(xfrom, xto + 100, 100):
            cm = d[nm].clone()
            if elo not in dic:
                dic[elo] = []
            cm.set_uci_option("UCI_LimitStrength", "true")
            cm.set_uci_option("UCI_Elo", str(elo))
            cm.name += f" ({elo})"
            cm.key += f" ({elo})"
            cm.elo = elo
            dic[elo].append(cm)
    return dic

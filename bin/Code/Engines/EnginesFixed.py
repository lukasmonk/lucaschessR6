import OSEngines


def dic_engines_fixed_elo(folder_engines):
    d = OSEngines.read_engines(folder_engines)
    dic = {}
    li_engines = OSEngines.li_engines_fixed_elo()

    for nm, xfrom, xto in li_engines:
        for elo in range(xfrom, xto + 100, 100):
            cm = d[nm].clone()
            if elo not in dic:
                dic[elo] = []
            cm.set_uci_option("UCI_LimitStrength", "true")
            cm.set_uci_option("UCI_Elo", str(elo))
            cm.name += " (%d)" % elo
            cm.key += " (%d)" % elo
            cm.elo = elo
            dic[elo].append(cm)
    return dic


def dic_engines_raw_elo():
    return {key: {"min_elo": min_elo, "max_elo": max_elo}
            for key, min_elo, max_elo in OSEngines.li_engines_fixed_elo()}

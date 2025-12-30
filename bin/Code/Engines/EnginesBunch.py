import ast

import Code


def lee_dic_afinidades():
    with open(
        Code.path_resource("IntFiles", "afinidades.dic"),
        "rt",
        encoding="utf-8",
        errors="ignore",
    ) as f:
        return ast.literal_eval(f.read())


def lista(dic_engines):
    dic_relac_total = lee_dic_afinidades()
    li = list(dic_relac_total.keys())
    li.sort()
    return li


def bunch(key_engine, tam_bunch, dic_engines):
    def selecciona(dic_relac, no_incluir):
        minimo = 999
        selec = None
        for key, puntos in dic_relac.items():
            if key not in no_incluir:
                if puntos < minimo:
                    minimo = puntos
                    selec = key

        return selec

    dic_relac_total = lee_dic_afinidades()
    st_no_incluir = set()
    st_no_incluir.add(key_engine)
    li_claves = [key_engine]
    clave_work = key_engine
    if key_engine not in dic_relac_total:
        return li_claves

    for x in range(tam_bunch - 1):
        if clave_work not in dic_relac_total:
            break
        nueva = selecciona(dic_relac_total[clave_work], st_no_incluir)
        if nueva is None:
            break
        st_no_incluir.add(nueva)
        if nueva in dic_engines:
            li_claves.append(nueva)
            clave_work = nueva

    li_claves.sort(key=lambda xr: dic_engines[xr].elo)
    return li_claves

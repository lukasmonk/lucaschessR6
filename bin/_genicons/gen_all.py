import os
import shutil
import sys

from PIL import Image, ImageEnhance, ImageOps

# Importamos las herramientas necesarias de Pillow

# --- CONFIGURACIÓN DE AJUSTES VISUALES ---
# Ajustados para igualar el tono dorado/cálido de ImageMagick

# Valores para 'haz_sepia'
SEPIA_BRIGHTNESS = 0.95  # Un ligero oscurecimiento (IM -10 brillo)
SEPIA_CONTRAST = 1.05  # Un pelín de contraste extra para definición
SEPIA_SATURATION = 1.4  # ¡CLAVE! Alta saturación para que el dorado vibre

# Valores para 'haz_darked' (simulando IM -brightness-contrast -10)
DARK_BRIGHTNESS = 0.90
DARK_CONTRAST = 0.95

# --- LISTAS DE ARCHIVOS ---
COPY_SEPIA = {"Milleniumt.png", "dgt.png", "dgtB.png", "Certabo.png", "Novag.png", "Chessnut.png", "SquareOff.png",
              "Saitek.png", "peon64r.png", "m1.png", "m2.png"}

GREEN_SEPIA = {"icons8_downloads_folder_32px.png", "icons8_checked_checkbox_32px.png", "icons8_close_window_32px_1.png",
               "icons8_home_32px.png", "icons8_filing_cabinet_32px.png", "icons8_file_explorer_32px.png",
               "icons8_add_folder_32px.png", "icons8_delete_folder_32px.png", "icons8_sync_32px.png",
               "icons8_tick_box_32px.png", "icons8_automatic_32px_1.png", "satellites-26.png", "diploma2-32.png",
               "icons8_trophy_32px.png", "icons8_services_30px.png", "icons8_gear_30px.png", "lock-32.png",
               "BSicon_MBAHN.png", "trekking-32.png", "washing_machine-32.png", "icons8_leaderboard_32px.png",
               "add_property-32.png"
               }


# --- FUNCIONES DE PROCESAMIENTO DE IMAGEN (PILLOW) ---


import os
import shutil
import sys
# Importamos las herramientas necesarias de Pillow, incluyendo ImageFilter para el enfoque
from PIL import Image, ImageEnhance, ImageOps, ImageFilter

# --- CONFIGURACIÓN DE AJUSTES VISUALES ---

# Valores para 'haz_sepia' (Tono Chocolate/Arcilla)
# Los colores se definen dentro de la función usando códigos hexadecimales exactos.
SEPIA_POST_CONTRAST = 1.2  # Aumenta la definición de las sombras
SEPIA_POST_SATURATION = 1.1  # Un ligero empujón extra al color

# Valores para 'haz_darked' (Modo oscuro simple)
DARK_BRIGHTNESS = 0.90
DARK_CONTRAST = 0.95

# --- LISTAS DE ARCHIVOS ---
COPY_SEPIA = {"Milleniumt.png", "dgt.png", "dgtB.png", "Certabo.png", "Novag.png", "Chessnut.png", "SquareOff.png",
              "Saitek.png", "peon64r.png", "m1.png", "m2.png"}

GREEN_SEPIA = {"icons8_downloads_folder_32px.png", "icons8_checked_checkbox_32px.png", "icons8_close_window_32px_1.png",
               "icons8_home_32px.png", "icons8_filing_cabinet_32px.png", "icons8_file_explorer_32px.png",
               "icons8_add_folder_32px.png", "icons8_delete_folder_32px.png", "icons8_sync_32px.png",
               "icons8_tick_box_32px.png", "icons8_automatic_32px_1.png", "satellites-26.png", "diploma2-32.png",
               "icons8_trophy_32px.png", "icons8_services_30px.png", "icons8_gear_30px.png", "lock-32.png",
               "BSicon_MBAHN.png", "trekking-32.png", "washing_machine-32.png", "icons8_leaderboard_32px.png",
               "add_property-32.png"
               }
GREEN_SEPIA = {}

# --- FUNCIONES DE PROCESAMIENTO DE IMAGEN (PILLOW) ---

def haz_sepia(origen):
    """
    Replica el tono rojizo/chocolate exacto usando mapeo de color (colorize)
    y aplica un filtro de enfoque final para nitidez.
    """
    img = Image.open(origen).convert("RGBA")
    # Guardamos el canal alfa (transparencia) para el final
    alpha = img.split()[3]

    # 1. Convertimos a escala de grises (L)
    gray = img.convert("L")

    # 2. Mapeo de color exacto (Tono Chocolate/Arcilla)
    # Usamos los códigos de color extraídos de la muestra de referencia.
    img_processed = ImageOps.colorize(
        gray,
        black="#2d1a12",  # Sombras profundas rojizas
        white="#f3d8ca",  # Luces crema
        mid="#8e5a45"  # Medios tonos arcilla
    )

    # 3. Ajustes finales de "fuerza"
    img_processed = ImageEnhance.Contrast(img_processed).enhance(SEPIA_POST_CONTRAST)
    img_processed = ImageEnhance.Color(img_processed).enhance(SEPIA_POST_SATURATION)

    # 4. --- NUEVO PASO: ENFOQUE (SHARPEN) ---
    # Aplica un filtro estándar de enfoque para definir bordes.
    img_processed = img_processed.filter(ImageFilter.SHARPEN)

    # 5. Recombinar con la transparencia original
    img_processed.putalpha(alpha)
    img_processed.save("sepia.png")


def haz_green_pil(origen):
    """
    Recolorea iconos usando la transparencia original como máscara.
    """
    img = Image.open(origen).convert("RGBA")
    a = img.split()[3]
    # Color objetivo del script original: 196, 148, 133
    solid_color_img = Image.new("RGB", img.size, (196, 148, 133))
    img_final = Image.merge("RGBA", (*solid_color_img.split(), a))
    img_final.save("sepia.png")


def haz_darked(origen):
    """
    Modo 'dark' con manejo correcto del canal alfa.
    """
    img = Image.open(origen).convert("RGBA")
    r, g, b, a = img.split()

    # Trabajamos sobre el RGB
    img_rgb = Image.merge("RGB", (r, g, b))
    img_rgb = ImageEnhance.Brightness(img_rgb).enhance(DARK_BRIGHTNESS)
    img_rgb = ImageEnhance.Contrast(img_rgb).enhance(DARK_CONTRAST)

    img_rgb = img_rgb.filter(ImageFilter.SHARPEN)

    # Recomponemos con el alfa
    img_final = Image.merge("RGBA", (*img_rgb.split(), a))
    img_final.save("dark.png")


# --- FUNCIONES PRINCIPALES DE GESTIÓN DE ARCHIVOS ---
# (Estas funciones no han cambiado, solo se aseguran de que existan los directorios)

def funcion_png(qbin, qdic, dic, desde, nom_funcion, nom_dir, nom_fichero):
    c_fich = "%s/%s" % (nom_dir, nom_fichero)
    tt = (nom_dir.lower(), nom_fichero.lower())
    if tt in dic:
        de, a = dic[tt]
    else:
        with open(c_fich, "rb") as f:
            o = f.read()
        qbin.write(o)
        tam = len(o)
        de = desde
        a = de + tam
        desde = a
        dic[tt] = (de, a)
    qdic.write("%s=%d,%d\n" % (nom_funcion, de, a))
    return desde


def funcion_sepia(qbin, qdic, dic, desde, nom_funcion, nom_dir, nom_fichero):
    c_fich = "%s/%s" % (nom_dir, nom_fichero)
    if nom_fichero in COPY_SEPIA:
        shutil.copy(c_fich, "sepia.png")
    elif nom_fichero in GREEN_SEPIA:
        haz_green_pil(c_fich)
    else:
        haz_sepia(c_fich)

    tt = (nom_dir.lower(), nom_fichero.lower())
    if tt in dic:
        de, a = dic[tt]
    else:
        with open("sepia.png", "rb") as f:
            o = f.read()
        qbin.write(o)
        tam = len(o)
        de = desde
        a = de + tam
        desde = a
        dic[tt] = (de, a)
    qdic.write("%s=%d,%d\n" % (nom_funcion, de, a))
    return desde


def funcion_dark(qbin, qdic, dic, desde, nom_funcion, nom_dir, nom_fichero):
    c_fich = "%s/%s" % (nom_dir, nom_fichero)
    haz_darked(c_fich)
    tt = (nom_dir.lower(), nom_fichero.lower())
    if tt in dic:
        de, a = dic[tt]
    else:
        with open("dark.png", "rb") as f:
            o = f.read()
        qbin.write(o)
        tam = len(o)
        de = desde
        a = de + tam
        desde = a
        dic[tt] = (de, a)
    qdic.write("%s=%d,%d\n" % (nom_funcion, de, a))
    return desde


def do_iconos(li_imgs):
    os.makedirs("../Code/QT", exist_ok=True)
    q = open("../Code/QT/Iconos.py", "wt", newline="\n")
    q.write(
        """from Code.QT.IconosBase import iget

def icono(name):
    return iget(name)

def pixmap(name):
    return iget("pm%s" % name)
"""
    )
    for li in li_imgs:
        nom = li[0]
        pixmap = """def pm%s():\n    return iget("pm%s")""" % (nom, nom)
        icono = """def %s():\n    return iget("%s")""" % (nom, nom)
        q.write("\n%s\n\n%s\n" % (pixmap, icono))
    q.close()


def do_normal(li_imgs):
    os.makedirs("../../Resources/IntFiles", exist_ok=True)
    with open("../../Resources/IntFiles/Iconos.bin", "wb") as qbin, \
            open("../../Resources/IntFiles/Iconos.dic", "wt") as qdic:
        print("Normal", len(li_imgs))
        dic = {}
        desde = 0
        for n, li in enumerate(li_imgs, 1):
            print(n, end=" ")
            if n % 20 == 0: sys.stdout.flush()
            previo = desde
            desde = funcion_png(qbin, qdic, dic, previo, li[0], li[1], li[2])
        print()


def do_sepia(li_imgs):
    print("Haciendo SEPIA")
    with open("../../Resources/IntFiles/Iconos_sepia.bin", "wb") as qbin, open(
            "../../Resources/IntFiles/Iconos_sepia.dic", "wt") as qdic:
        dic = {}
        desde = 0
        for n, li in enumerate(li_imgs, 1):
            print(n, end=" ")
            if n % 20 == 0: sys.stdout.flush()
            previo = desde
            desde = funcion_sepia(qbin, qdic, dic, previo, li[0], li[1], li[2])
        print()


def do_dark(li_imgs):
    print("Haciendo DARK")
    with open("../../Resources/IntFiles/Iconos_dark.bin", "wb") as qbin, open(
            "../../Resources/IntFiles/Iconos_dark.dic", "wt") as qdic:
        dic = {}
        desde = 0
        for n, li in enumerate(li_imgs, 1):
            print(n, end=" ")
            if n % 20 == 0: sys.stdout.flush()
            previo = desde
            desde = funcion_dark(qbin, qdic, dic, previo, li[0], li[1], li[2])
        print()


def lee_tema(ctema):
    def error(txt, r_fich):
        print(txt, r_fich)
        sys.exit()

    if not os.path.isfile(ctema):
        error("No se encuentra el archivo del tema", ctema)

    with open(ctema, "r") as f:
        li_imgs = f.read().splitlines()
        li_imgs_fixed = []
        rep = set()
        for x in li_imgs:
            if x.startswith("#"):
                continue
            x = x.strip()
            if not x:
                continue
            li = x.split(" ")
            if len(li) == 3:
                if li[0] in rep:
                    error("error repetido", li[0])
                rep.add(li[0])
                c_fich = "%s/%s" % (li[1], li[2])
                if not os.path.isfile(c_fich):
                    error("No existe la imagen fuente", c_fich)
                li_imgs_fixed.append(li)
            else:
                error("Linea error en el archivo de tema", x)

    do_normal(li_imgs_fixed)
    do_sepia(li_imgs_fixed)
    do_dark(li_imgs_fixed)
    do_iconos(li_imgs_fixed)

    if os.path.exists("sepia.png"): os.remove("sepia.png")
    if os.path.exists("dark.png"): os.remove("dark.png")
    print("\nProceso completado.")


if __name__ == "__main__":
    lee_tema("Formatos.tema")

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from Code.QT import QTDialogs, Iconos
from Code.Translations import TrListas


class FNSanalyzer:
    def __init__(self):
        self.root_paths = []
        self.tree = None
        self.dic_training = {}

    def add_folder(self, path: str):
        self.root_paths.append(Path(path))

    @staticmethod
    def _check_file(file_path: Path) -> bool:
        """Verifica si el archivo es válido (concurrente)."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors="ignore") as f:
                for line in f:
                    if line.count('|') > 1:
                        return True
        except Exception:
            pass
        return False

    def _scan(self, directory: Path) -> list:
        """Escanea recursivamente."""
        content = []

        # Archivos en la carpeta actual
        for file in directory.glob("*.fns"):
            if self._check_file(file):
                content.append(file)

        # Subcarpetas
        for subdir in directory.iterdir():
            if subdir.is_dir():
                sub_content = self._scan(subdir)
                if sub_content:
                    content.append({subdir.name: sub_content})
        return content

    def get_tree(self) -> dict:
        """Lanza el escaneo de cada root-folder en hilos separados."""
        if self.tree:
            return self.tree
        result = {}

        # Usamos un Pool de hilos para procesar las carpetas raíz en paralelo
        with ThreadPoolExecutor() as executor:
            # Mapeamos cada ruta a la función de escaneo
            future_to_path = {executor.submit(self._scan, p): p for p in self.root_paths if p.exists()}

            for future in future_to_path:
                path = future_to_path[future]
                results = future.result()
                if results:
                    result[path.name] = results

        self.tree = result
        return result

    def launch_menu(self, owner):
        menu = QTDialogs.LCMenu(owner)
        tree = self.get_tree()
        dic_training = TrListas.dic_training()

        def translate(txt):
            if txt in dic_training:
                return dic_training[txt]
            if txt.title() in dic_training:
                return dic_training[txt.title()]
            if _F(txt) == txt and _F(txt.title()) != txt.title():
                return _F(txt.title())
            return _F(txt)

        def name(nm):
            if nm.endswith('.fns'):
                nm = nm[:-4]
            if nm[-1] in "0123456789" and nm[-2] not in "0123456789":
                num = nm[-1]
                rest = nm[:-1]
                if rest[-1] == "_":
                    rest = rest[:-1]
                if translate(rest) != rest:
                    return f"{translate(rest)} {num}"
            return translate(nm)

        def add_folder(li_elems, menu_prev):
            for elemento in li_elems:
                if isinstance(elemento, dict):
                    for x in elemento:
                        subfolder = menu_prev.submenu(name(x), Iconos.Carpeta())
                        add_folder(elemento[x], subfolder)
                elif isinstance(elemento, list):
                    for uno in elemento:
                        add_folder(uno, menu_prev)
                else:
                    menu_prev.opcion(elemento, name(elemento.name), Iconos.Azul())

        for key in tree:
            add_folder(tree[key], menu)

        resp = menu.lanza()
        return resp

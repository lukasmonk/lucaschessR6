import pickle
import random
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple, Iterator, Type

import psutil
import sortedcontainers

import Code
from Code import Util


class DictSQL(object):
    def __init__(self, path_db: str, tabla: str = "Data", max_cache: int = 2048):
        self.path_db = path_db
        self.tabla = tabla
        self.max_cache = max_cache
        self.cache: Dict[str, Any] = {}

        self.conexion = sqlite3.connect(path_db)

        self.conexion.execute(f"CREATE TABLE IF NOT EXISTS {tabla}( KEY TEXT PRIMARY KEY, VALUE BLOB );")

        cursor = self.conexion.execute(f"SELECT KEY FROM {self.tabla}")
        self.li_keys: List[str] = [reg[0] for reg in cursor.fetchall()]

        self.normal_save_mode = True
        self.pending_commit = False

        self.li_breplaces_pickle: List[Tuple[bytes, bytes]] = []

    def reset(self) -> None:
        cursor = self.conexion.execute(f"SELECT KEY FROM {self.tabla}")
        self.li_keys = [reg[0] for reg in cursor.fetchall()]

    def set_faster_mode(self) -> None:
        self.normal_save_mode = False

    def set_normal_mode(self) -> None:
        if self.pending_commit:
            self.conexion.commit()
        self.normal_save_mode = True

    def add_cache(self, key: str, obj: Any) -> None:
        if self.max_cache:
            if len(self.cache) > self.max_cache:
                lik = list(self.cache.keys())
                for x in lik[: self.max_cache // 2]:
                    del self.cache[x]
            self.cache[key] = obj

    def __contains__(self, key: str) -> bool:
        return key in self.li_keys

    def __setitem__(self, key: str, obj: Any) -> None:
        if not self.conexion:
            return
        dato = pickle.dumps(obj, protocol=4)
        si_ya_esta = key in self.li_keys
        if si_ya_esta:
            sql = f"UPDATE {self.tabla} SET VALUE=? WHERE KEY = ?"
        else:
            sql = f"INSERT INTO {self.tabla} (VALUE,KEY) values(?,?)"
            self.li_keys.append(key)
        self.conexion.execute(sql, (memoryview(dato), key))

        self.add_cache(key, obj)
        if self.normal_save_mode:
            self.conexion.commit()
        elif not self.pending_commit:
            self.pending_commit = True

    def wrong_pickle(self, bwrong: bytes, bcorrect: bytes) -> None:
        self.li_breplaces_pickle.append((bwrong, bcorrect))

    def __getitem__(self, key: str) -> Any:
        if key in self.li_keys:
            if key in self.cache:
                return self.cache[key]

            sql = f"SELECT VALUE FROM {self.tabla} WHERE KEY= ?"
            row = self.conexion.execute(sql, (key,)).fetchone()
            try:
                obj = pickle.loads(row[0])
            except (pickle.UnpicklingError, TypeError, AttributeError, EOFError, IndexError, ImportError):
                if self.li_breplaces_pickle:
                    btxt = row[0]
                    for btxt_wrong, btxt_correct in self.li_breplaces_pickle:
                        btxt = btxt.replace(btxt_wrong, btxt_correct)
                    try:
                        obj = pickle.loads(btxt)
                        self.__setitem__(key, obj)
                    except (pickle.UnpicklingError, TypeError, AttributeError, EOFError, IndexError, ImportError):
                        obj = None
                else:
                    obj = None

            self.add_cache(key, obj)
            return obj
        return None

    def __delitem__(self, key: str) -> None:
        if key in self.li_keys:
            self.li_keys.remove(key)
            if key in self.cache:
                del self.cache[key]
            sql = f"DELETE FROM {self.tabla} WHERE KEY= ?"
            self.conexion.execute(sql, (key,))
            if self.normal_save_mode:
                self.conexion.commit()
            else:
                self.pending_commit = True

    def __len__(self) -> int:
        return len(self.li_keys)

    def is_closed(self) -> bool:
        return self.conexion is None

    def close(self) -> None:
        if self.conexion:
            if self.pending_commit:
                self.conexion.commit()
            self.conexion.close()
            self.conexion = None

    def keys(self, si_ordenados: bool = False, si_reverse: bool = False) -> List[str]:
        return sorted(self.li_keys, reverse=si_reverse) if si_ordenados else self.li_keys

    def get(self, key: Any, default: Any = None) -> Any:
        key = str(key)
        if key in self.li_keys:
            return self.__getitem__(key)
        else:
            return default

    def as_dictionary(self) -> Dict[str, Any]:
        sql = f"SELECT KEY,VALUE FROM {self.tabla}"
        cursor = self.conexion.execute(sql)
        dic = {}
        for key, dato in cursor.fetchall():
            try:
                dic[key] = pickle.loads(dato)
            except AttributeError:
                if self.li_breplaces_pickle:
                    for btxt_wrong, btxt_correct in self.li_breplaces_pickle:
                        dato = dato.replace(btxt_wrong, btxt_correct)
                    dic[key] = pickle.loads(dato)
        return dic

    def pack(self) -> None:
        self.conexion.execute("VACUUM")
        self.conexion.commit()

    def zap(self) -> None:
        self.conexion.execute(f"DELETE FROM {self.tabla}")
        self.conexion.commit()
        self.conexion.execute("VACUUM")
        self.conexion.commit()
        self.cache = {}
        self.li_keys = []

    def __enter__(self) -> "DictSQL":
        return self

    def __exit__(self, xtype, value, traceback) -> None:
        self.close()

    def copy_from(self, dbdict: Dict[str, Any]) -> None:
        mode = self.normal_save_mode
        self.set_faster_mode()
        for key in dbdict.keys():
            self[key] = dbdict[key]
        self.conexion.commit()
        self.pending_commit = False
        self.normal_save_mode = mode


class DictSQLRawExclusive(object):
    GET_ALL = 1
    GET_ONE = 2
    GET_NONE = 0

    def __init__(self, path_db: str, tabla: str = "Data"):
        self.tabla = tabla
        self.conexion = sqlite3.connect(path_db, isolation_level="EXCLUSIVE")

        self.conexion.execute(f"CREATE TABLE IF NOT EXISTS {tabla}( KEY TEXT PRIMARY KEY, VALUE BLOB );")

        cursor = self.conexion.execute(f"SELECT KEY FROM {self.tabla}")
        self.li_keys: List[str] = [reg[0] for reg in cursor.fetchall()]

    def execute(
        self, sql: str, args: Optional[Tuple] = None, is_all: Optional[int] = None, commit: bool = False
    ) -> Any:
        tries = 10
        while tries:
            try:
                if args:
                    cursor = self.conexion.execute(sql, args)
                else:
                    cursor = self.conexion.execute(sql)
                if is_all == self.GET_ALL:
                    return cursor.fetchall()
                elif is_all == self.GET_ONE:
                    return cursor.fetchone()
                if commit:
                    self.conexion.commit()
                return

            except sqlite3.OperationalError:
                tries -= 1

    def exist(self, key: str) -> bool:
        sql = f"SELECT VALUE FROM {self.tabla} WHERE KEY= ?"
        row = self.execute(sql, (key,), self.GET_ONE)
        return row is not None

    def __contains__(self, key: str) -> bool:
        return self.exist(key)

    def __setitem__(self, key: str, obj: Any) -> None:
        if not self.conexion:
            return
        if self.exist(key):
            sql = f"UPDATE {self.tabla} SET VALUE=? WHERE KEY = ?"
        else:
            sql = f"INSERT INTO {self.tabla} (VALUE,KEY) values(?,?)"
        dato = pickle.dumps(obj, protocol=4)
        self.execute(sql, (memoryview(dato), key), commit=True)

    def __getitem__(self, key: str) -> Any:
        if self.exist(key):
            sql = f"SELECT VALUE FROM {self.tabla} WHERE KEY= ?"

            row = self.execute(sql, (key,), self.GET_ONE)
            if row[0] is not None:
                return pickle.loads(row[0])
        return None

    def __delitem__(self, key: str) -> None:
        sql = f"DELETE FROM {self.tabla} WHERE KEY= ?"
        self.execute(sql, (key,), commit=True)

    def __len__(self) -> int:
        sql = f"SELECT COUNT(*) FROM {self.tabla}"
        row = self.execute(sql, is_all=self.GET_ONE)
        return row[0]

    def close(self) -> None:
        try:
            if self.conexion:
                self.conexion.close()
        except:
            pass
        self.conexion = None

    def get(self, key: Any, default: Any = None) -> Any:
        key = str(key)
        value = self.__getitem__(key)
        if value is None:
            value = default
        return value

    def as_dictionary(self) -> Dict[str, Any]:
        sql = f"SELECT KEY,VALUE FROM {self.tabla}"
        li_all = self.execute(sql, is_all=self.GET_ALL)
        dic = {}
        if li_all:
            for key, dato in li_all:
                dic[key] = pickle.loads(dato)
        return dic

    def keys(self) -> List[str]:
        sql = f"SELECT KEY FROM {self.tabla}"
        li_all = self.execute(sql, is_all=self.GET_ALL)
        return [row[0] for row in li_all]

    def zap(self) -> None:
        self.execute(f"DELETE FROM {self.tabla}", commit=True)
        self.execute("VACUUM", commit=True)

    def __enter__(self) -> "DictSQLRawExclusive":
        return self

    def __exit__(self, xtype: Any, value: Any, traceback: Any) -> None:
        self.close()


class DictObjSQL(DictSQL):
    def __init__(self, path_db: str, class_storage: Type, tabla: str = "Data", max_cache: int = 2048):
        self.class_storage = class_storage
        DictSQL.__init__(self, path_db, tabla, max_cache)

    def __setitem__(self, key: str, obj: Any) -> None:
        dato = Util.save_obj_pickle(obj)
        si_ya_esta = key in self.li_keys
        if si_ya_esta:
            sql = f"UPDATE {self.tabla} SET VALUE=? WHERE KEY = ?"
        else:
            sql = f"INSERT INTO {self.tabla} (VALUE,KEY) values(?,?)"
            self.li_keys.append(key)
        self.conexion.execute(sql, (memoryview(dato), key))
        self.conexion.commit()

        if key in self.cache:
            self.add_cache(key, obj)

    def __getitem__(self, key: str) -> Any:
        if key in self.li_keys:
            if key in self.cache:
                return self.cache[key]

            sql = f"SELECT VALUE FROM {self.tabla} WHERE KEY= ?"
            row = self.conexion.execute(sql, (key,)).fetchone()
            obj = self.class_storage()
            Util.restore_obj_pickle(obj, row[0])
            self.add_cache(key, obj)
            return obj
        else:
            return None

    def __iter__(self) -> Iterator[Any]:
        for key in self.li_keys:
            yield self.__getitem__(key)

    def as_dictionary(self):
        sql = "SELECT KEY,VALUE FROM %s" % self.tabla
        cursor = self.conexion.execute(sql)
        dic = {}
        for key, dato in cursor.fetchall():
            obj = self.class_storage()
            Util.restore_obj_pickle(obj, dato)
            dic[key] = obj
        return dic


class DictRawSQL(DictSQL):
    def __init__(self, path_db: str, tabla: str = "Data"):
        DictSQL.__init__(self, path_db, tabla, max_cache=0)


class ListSQL:
    def __init__(self, path_file: str, tabla: str = "LISTA", max_cache: int = 2048, reversed: bool = False):
        self.path_file = path_file
        self._conexion = sqlite3.connect(path_file)
        self.tabla = tabla
        self.max_cache = max_cache
        self.cache: Dict[int, Any] = {}
        self.reversed = reversed

        self._conexion.execute(f"CREATE TABLE IF NOT EXISTS {tabla}( DATO BLOB );")

        self.li_row_ids: List[int] = self.read_rowids()

    def __enter__(self) -> "ListSQL":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def read_rowids(self) -> List[int]:
        sql = f"SELECT ROWID FROM {self.tabla}"
        if self.reversed:
            sql += " ORDER BY ROWID DESC"
        cursor = self._conexion.execute(sql)
        return [rowid for rowid, in cursor.fetchall()]

    def refresh(self) -> None:
        self.li_row_ids = self.read_rowids()

    def add_cache(self, key: int, obj: Any) -> None:
        if self.max_cache:
            if len(self.cache) > self.max_cache:
                lik = list(self.cache.keys())
                for x in lik[: self.max_cache // 2]:
                    del self.cache[x]
            self.cache[key] = obj

    def append(self, valor: Any, with_cache: bool = False) -> None:
        sql = f"INSERT INTO {self.tabla}( DATO ) VALUES( ? )"
        obj = pickle.dumps(valor, protocol=4)
        cursor = self._conexion.execute(sql, (memoryview(obj),))
        self._conexion.commit()
        lastrowid = cursor.lastrowid
        if self.reversed:
            self.li_row_ids.insert(0, lastrowid)
        else:
            self.li_row_ids.append(lastrowid)
        if with_cache:
            self.add_cache(lastrowid, obj)

    def __getitem__(self, pos: int) -> Any:
        if pos < len(self.li_row_ids):
            rowid = self.li_row_ids[pos]
            if rowid in self.cache:
                return self.cache[rowid]

            sql = f"select DATO from {self.tabla} where ROWID=?"
            cursor = self._conexion.execute(sql, (rowid,))
            row = cursor.fetchone()
            if row is None:
                self.li_row_ids = self.read_rowids()
                return None
            try:
                obj = pickle.loads(row[0])
            except (pickle.UnpicklingError, TypeError, AttributeError, EOFError, IndexError, ImportError):
                obj = None
            self.add_cache(rowid, obj)
            return obj
        else:
            return None

    def __setitem__(self, pos: int, obj: Any) -> None:
        if pos < len(self.li_row_ids):
            dato = pickle.dumps(obj, protocol=4)
            rowid = self.li_row_ids[pos]
            sql = f"UPDATE {self.tabla} SET dato=? WHERE ROWID = ?"
            self._conexion.execute(sql, (memoryview(dato), rowid))
            self._conexion.commit()
            if rowid in self.cache:
                self.add_cache(rowid, obj)

    def __delitem__(self, pos: int) -> None:
        if pos < len(self.li_row_ids):
            rowid = self.li_row_ids[pos]
            sql = f"DELETE FROM {self.tabla} WHERE ROWID= ?"
            self._conexion.execute(sql, (rowid,))
            self._conexion.commit()
            del self.li_row_ids[pos]

            if rowid in self.cache:
                del self.cache[rowid]

    def __len__(self) -> int:
        return len(self.li_row_ids)

    def close(self) -> None:
        if self._conexion:
            self._conexion.close()
            self._conexion = None

    def __iter__(self) -> Iterator[Any]:
        for pos in range(len(self.li_row_ids)):
            yield self.__getitem__(pos)

    def pack(self) -> None:
        self._conexion.execute("VACUUM")
        self._conexion.commit()

    def zap(self) -> None:
        self._conexion.execute(f"DELETE FROM {self.tabla}")
        self._conexion.commit()
        self.pack()
        self.li_row_ids = []
        self.cache = {}

    def rowid(self, pos: int) -> int:
        return self.li_row_ids[pos]

    def pos_rowid(self, rowid: int) -> int:
        try:
            return self.li_row_ids.index(rowid)
        except:
            return -1


class ListSQLBig(object):
    def __init__(self, path_file: str, tabla: str = "LIST"):
        self.path_file = path_file
        self._conexion = sqlite3.connect(path_file)
        self.tabla = tabla
        self.insert = f"INSERT INTO {self.tabla}( DATA ) VALUES( ? )"

        self._conexion.execute(f"CREATE TABLE IF NOT EXISTS {tabla}( DATA TEXT );")

    def __enter__(self) -> "ListSQLBig":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def append(self, valor: str) -> None:
        self._conexion.execute(self.insert, (valor,))

    def close(self) -> None:
        if self._conexion:
            self._conexion.commit()
            self._conexion.close()
            self._conexion = None

    def lista(self, rev: bool) -> Iterator[str]:
        self._conexion.commit()
        cursor = self._conexion.execute(f"SELECT DATA FROM {self.tabla} ORDER BY DATA" + " DESC;" if rev else ";")
        while True:
            row = cursor.fetchone()
            if row:
                yield row[0]
            else:
                break


class ListObjSQL(ListSQL):
    def __init__(
        self, path_file: str, class_storage: Type, tabla: str = "datos", max_cache: int = 2048, reversed: bool = False
    ):
        self.class_storage = class_storage
        ListSQL.__init__(self, path_file, tabla, max_cache, reversed)

    def append(self, obj: Any, with_cache: bool = False, with_commit: bool = True) -> None:
        sql = f"INSERT INTO {self.tabla}( DATO ) VALUES( ? )"
        dato = Util.save_obj_pickle(obj)
        cursor = self._conexion.execute(sql, (memoryview(dato),))
        if with_commit:
            self._conexion.commit()
        lastrowid = cursor.lastrowid
        if self.reversed:
            self.li_row_ids.insert(0, lastrowid)
        else:
            self.li_row_ids.append(lastrowid)
        if with_cache:
            self.add_cache(lastrowid, obj)

    def commit(self) -> None:
        self._conexion.commit()

    def __getitem__(self, pos: int) -> Any:
        if pos < len(self.li_row_ids):
            rowid = self.li_row_ids[pos]
            if rowid in self.cache:
                return self.cache[rowid]

            sql = f"select DATO from {self.tabla} where ROWID=?"
            cursor = self._conexion.execute(sql, (rowid,))
            obj = self.class_storage()
            x = cursor.fetchone()
            try:
                if x:
                    Util.restore_obj_pickle(obj, x[0])
            except (pickle.UnpicklingError, TypeError, AttributeError, EOFError, IndexError, ImportError):
                pass
            self.add_cache(rowid, obj)
            return obj

    def __setitem__(self, pos: int, obj: Any) -> None:
        if pos < len(self.li_row_ids):
            rowid = self.li_row_ids[pos]
            sql = f"UPDATE {self.tabla} SET dato=? WHERE ROWID = ?"
            dato = Util.save_obj_pickle(obj)
            self._conexion.execute(sql, (memoryview(dato), rowid))
            self._conexion.commit()

            if rowid in self.cache:
                self.add_cache(rowid, obj)


class IPC(object):
    def __init__(self, path_file: str, si_crear: bool):
        if si_crear:
            Util.remove_file(path_file)

        self._conexion = sqlite3.connect(path_file)
        self.path_file = path_file

        if si_crear:
            sql = "CREATE TABLE DATOS( DATO BLOB );"
            self._conexion.execute(sql)
            self._conexion.commit()

        self.key = 0

    def pop(self) -> Any:
        nk = self.key + 1
        sql = f"SELECT dato FROM DATOS WHERE ROWID = {nk}"
        cursor = self._conexion.execute(sql)
        reg = cursor.fetchone()
        if reg:
            valor = pickle.loads(reg[0])
            self.key = nk
        else:
            valor = None
        return valor

    def read_again(self) -> None:
        self.key -= 1

    def has_more_data(self) -> bool:
        nk = self.key + 1
        sql = f"SELECT dato FROM DATOS WHERE ROWID = {nk}"
        cursor = self._conexion.execute(sql)
        reg = cursor.fetchone()
        return reg is not None

    def push(self, valor: Any) -> None:
        dato = sqlite3.Binary(pickle.dumps(valor, protocol=4))
        sql = "INSERT INTO DATOS (dato) values(?)"
        self._conexion.execute(sql, [dato])
        self._conexion.commit()

    def close(self) -> None:
        if self._conexion:
            self._conexion.close()
            self._conexion = None


class DictBig(object):
    def __init__(self) -> None:
        self.dict: Dict[Any, Any] = sortedcontainers.SortedDict()
        self.db: Optional[DictBigDB] = None
        self.test_mem = 100_000

    def __contains__(self, key: Any) -> bool:
        if key in self.dict:
            return True
        elif self.db is not None:
            return key in self.db
        return False

    def __getitem__(self, key: Any) -> Any:
        if key in self.dict:
            return self.dict[key]
        elif self.db is not None:
            return self.db[key]
        return None

    def test_memory(self) -> None:
        ps = psutil.virtual_memory()
        if ps.available < (512 * 1024 * 1024) or Util.memory_python() > (512 * 1024 * 1024):
            self.db = DictBigDB()
        else:
            self.test_mem = 50_000

    def __setitem__(self, key: Any, value: Any) -> None:
        if key in self.dict:
            self.dict[key] = value
        elif self.db is not None:
            self.db[key] = value
        else:
            self.dict[key] = value
            self.test_mem -= 1
            if self.test_mem == 0:
                self.test_memory()

    def __delitem__(self, key: Any) -> None:
        if key in self.dict:
            del self.dict[key]
        elif self.db is not None:
            del self.db[key]

    def __len__(self) -> int:
        tam = len(self.dict)
        if self.db is not None:
            tam += len(self.db)
        return tam

    def close(self) -> None:
        if self.dict:
            del self.dict
            if self.db is not None:
                self.db.close()
                self.db = None
            self.dict = None

    def get(self, key: Any, default: Any) -> Any:
        valor = self.__getitem__(key)
        if valor is None:
            return default
        return valor

    def __enter__(self) -> "DictBig":
        return self

    def __exit__(self, xtype: Any, value: Any, traceback: Any) -> None:
        self.close()

    def items(self) -> Iterator[Tuple[Any, Any]]:
        if self.db is None:
            for k, v in self.dict.items():
                yield k, v
            return

        g_db = iter(self.db)

        kg = vg = None

        for k, v in self.dict.items():
            while g_db is not None:
                if kg is None:
                    try:
                        kg, vg = next(g_db)
                        if kg < k:
                            yield kg, vg
                            kg = None
                        else:
                            break
                    except StopIteration:
                        g_db = None
                        break
                else:
                    if kg < k:
                        yield kg, vg
                        kg = None
                    else:
                        break
            yield k, v

        while g_db is not None:
            try:
                kg, vg = next(g_db)
                yield kg, vg
            except StopIteration:
                g_db = None


class DictBigDB(object):
    def __init__(self) -> None:
        self.conexion = sqlite3.connect(Code.configuration.temporary_file("dbdb"))
        self.conexion.execute("CREATE TABLE IF NOT EXISTS DATA( KEY TEXT PRIMARY KEY, VALUE BLOB );")
        self.conexion.execute("PRAGMA journal_mode=REPLACE")
        self.conexion.execute("PRAGMA synchronous=OFF")
        self.conexion.execute("PRAGMA locking_mode=EXCLUSIVE")
        self.conexion.commit()

    def __contains__(self, key: str) -> bool:
        cursor = self.conexion.execute("SELECT KEY FROM DATA WHERE key=?;", (key,))
        return cursor.fetchone() is not None

    def __getitem__(self, key: str) -> Any:
        cursor = self.conexion.execute("SELECT VALUE FROM DATA WHERE key=?;", (key,))
        row = cursor.fetchone()
        if row is not None:
            return pickle.loads(row[0])
        else:
            return None

    def __setitem__(self, key: str, value: Any) -> None:
        xvalue = pickle.dumps(value, protocol=4)
        self.conexion.execute("REPLACE INTO DATA (KEY, VALUE) VALUES (?,?)", (key, xvalue))

    def __delitem__(self, key: str) -> None:
        sql = "DELETE FROM DATA WHERE KEY= ?"
        self.conexion.execute(sql, (key,))

    def __len__(self) -> int:
        cursor = self.conexion.execute("SELECT COUNT(*) FROM DATA")
        row = cursor.fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        if self.conexion:
            self.conexion.close()
            self.conexion = None

    def get(self, key: str, default: Any) -> Any:
        valor = self.__getitem__(key)
        if valor is None:
            return default
        return valor

    def __enter__(self) -> "DictBigDB":
        return self

    def __exit__(self, xtype: Any, value: Any, traceback: Any) -> None:
        self.close()

    def __iter__(self) -> Iterator[Tuple[str, Any]]:
        self.cursor_iter = self.conexion.execute("SELECT KEY,VALUE FROM DATA ORDER BY KEY")
        self.pos_iter = 0
        self.max_iter = 0
        return self

    def __next__(self) -> Tuple[str, Any]:
        if self.pos_iter >= self.max_iter:
            self.rows_iter = self.cursor_iter.fetchmany(10000)
            self.max_iter = len(self.rows_iter) if self.rows_iter else 0
            if self.max_iter == 0:
                raise StopIteration
            self.pos_iter = 0
        k, v = self.rows_iter[self.pos_iter]
        self.pos_iter += 1
        return k, pickle.loads(v)


def check_table_in_db(path_db: str, table: str) -> bool:
    conexion = sqlite3.connect(path_db)
    cursor = conexion.cursor()
    cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table,))
    resp = cursor.fetchone()[0] == 1
    conexion.close()
    return resp


def list_tables(path_db: str) -> List[str]:
    conexion = sqlite3.connect(path_db)
    cursor = conexion.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    li_resp = cursor.fetchall()
    if li_resp:
        return [row[0] for row in li_resp]
    return []


def remove_table(path_db: str, table: str) -> None:
    conexion = sqlite3.connect(path_db)
    cursor = conexion.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table}")
    conexion.execute("VACUUM")
    conexion.commit()
    conexion.close()


class DictTextSQL(object):
    def __init__(self, path_db: str, tabla: str = "DataText", max_cache: int = 2048):
        self.tabla = tabla
        self.max_cache = max_cache
        self.cache: Dict[str, str] = {}

        self.conexion = sqlite3.connect(path_db)

        self.conexion.execute(f"CREATE TABLE IF NOT EXISTS {tabla}( KEY TEXT PRIMARY KEY, VALUE TEXT );")

        cursor = self.conexion.execute(f"SELECT KEY FROM {self.tabla}")
        self.li_keys: List[str] = [reg[0] for reg in cursor.fetchall()]

        self.normal_save_mode = True
        self.pending_commit = False

    def set_faster_mode(self) -> None:
        self.normal_save_mode = False

    def set_normal_mode(self) -> None:
        if self.pending_commit:
            self.conexion.commit()
        self.normal_save_mode = True

    def add_cache(self, key: str, txt: str) -> None:
        if self.max_cache:
            if len(self.cache) > self.max_cache:
                lik = list(self.cache.keys())
                for x in lik[: self.max_cache // 2]:
                    del self.cache[x]
            self.cache[key] = txt

    def __contains__(self, key: str) -> bool:
        return key in self.li_keys

    def __setitem__(self, key: str, txt: str) -> None:
        if not self.conexion:
            return
        si_ya_esta = key in self.li_keys
        if si_ya_esta:
            sql = f"UPDATE {self.tabla} SET VALUE=? WHERE KEY = ?"
        else:
            sql = f"INSERT INTO {self.tabla} (VALUE,KEY) values(?,?)"
            self.li_keys.append(key)
        self.conexion.execute(sql, (txt, key))

        self.add_cache(key, txt)
        if self.normal_save_mode:
            self.conexion.commit()
        elif not self.pending_commit:
            self.pending_commit = True

    def __getitem__(self, key: str) -> Optional[str]:
        if key in self.li_keys:
            if key in self.cache:
                return self.cache[key]

            sql = f"SELECT VALUE FROM {self.tabla} WHERE KEY= ?"
            row = self.conexion.execute(sql, (key,)).fetchone()
            txt = row[0]

            self.add_cache(key, txt)
            return txt
        return None

    def __delitem__(self, key: str) -> None:
        if key in self.li_keys:
            self.li_keys.remove(key)
            if key in self.cache:
                del self.cache[key]
            sql = f"DELETE FROM {self.tabla} WHERE KEY= ?"
            self.conexion.execute(sql, (key,))
            if self.normal_save_mode:
                self.conexion.commit()
            else:
                self.pending_commit = True

    def __len__(self) -> int:
        return len(self.li_keys)

    def is_closed(self) -> bool:
        return self.conexion is None

    def close(self) -> None:
        if self.conexion:
            if self.pending_commit:
                self.conexion.commit()
            self.conexion.close()
            self.conexion = None

    def keys(self, si_ordenados: bool = False, si_reverse: bool = False) -> List[str]:
        return sorted(self.li_keys, reverse=si_reverse) if si_ordenados else self.li_keys

    def get(self, key: Any, default: Any = None) -> Any:
        key = str(key)
        if key in self.li_keys:
            return self.__getitem__(key)
        else:
            return default

    def as_dictionary(self) -> Dict[str, str]:
        sql = f"SELECT KEY,VALUE FROM {self.tabla}"
        cursor = self.conexion.execute(sql)
        dic = {}
        for key, dato in cursor.fetchall():
            dic[key] = dato
        return dic

    def pack(self) -> None:
        self.conexion.execute("VACUUM")
        self.conexion.commit()

    def zap(self) -> None:
        self.conexion.execute(f"DELETE FROM {self.tabla}")
        self.conexion.execute("VACUUM")
        self.conexion.commit()
        self.cache = {}
        self.li_keys = []

    def __enter__(self) -> "DictTextSQL":
        return self

    def __exit__(self, xtype: Any, value: Any, traceback: Any) -> None:
        self.close()

    def copy_from(self, dbdict: Dict[str, str]) -> None:
        mode = self.normal_save_mode
        self.set_faster_mode()
        for key in dbdict.keys():
            self[key] = dbdict[key]
        self.conexion.commit()
        self.pending_commit = False
        self.normal_save_mode = mode

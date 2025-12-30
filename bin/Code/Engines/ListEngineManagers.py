import Code


class ListEngineManagers:
    def __init__(self):
        self.lista = []
        self.with_logs = False

    def append(self, engine_manager):
        if __debug__:
            import Code.Debug
            Code.Debug.prln("appending", engine_manager.engine.name, engine_manager.huella, color="green")
        self.lista.append(engine_manager)
        if self.with_logs:
            engine_manager.log_open()

    def close_all(self):
        self.cleanup_closed()
        for engine_manager in self.lista[:]:  # Iterar sobre copia
            engine_manager.close()
        self.lista = []

    def is_logs_active(self):
        return self.with_logs

    def cleanup_closed(self):
        """Elimina motores que ya no están activos."""
        self.lista = [em for em in self.lista if not em.is_closed]

    def active_logs(self, ok: bool):
        self.cleanup_closed()
        if ok != self.with_logs:
            for engine_manager in self.lista[:]:
                if ok:
                    engine_manager.log_open()
                else:
                    engine_manager.log_close()
            self.with_logs = ok

    def set_active_logs(self):
        Code.configuration.engines.set_logs(self.with_logs)

    def check_active_logs(self):
        if Code.configuration.engines.check_logs_active():
            self.with_logs = True

import psutil

from Code.Z import Util


class Priorities:
    def __init__(self):
        self.normal, self.low, self.verylow, self.high, self.veryhigh = range(5)

        if Util.is_linux():
            p_normal = 0
            p_low, p_verylow = 10, 20
            p_high, p_veryhigh = -10, -20
        else:
            p_normal = psutil.NORMAL_PRIORITY_CLASS
            p_low, p_verylow = (
                psutil.BELOW_NORMAL_PRIORITY_CLASS,
                psutil.IDLE_PRIORITY_CLASS,
            )
            p_high, p_veryhigh = (
                psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                psutil.HIGH_PRIORITY_CLASS,
            )

        self.values = [p_normal, p_low, p_verylow, p_high, p_veryhigh]

    def value(self, priority):
        return self.values[priority] if priority in range(5) else self.values[self.normal]

    @staticmethod
    def labels():
        return [_("Normal"), _("Low"), _("Very low"), _("High"), _("Very high")]

    def combo(self):
        labels = self.labels()
        return [(labels[pr], pr) for pr in range(5)]

    def texto(self, prioridad):
        return self.labels()[prioridad]


priorities = Priorities()

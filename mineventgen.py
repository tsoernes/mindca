from enum import Enum, auto

import numpy as np


class CEvent(Enum):
    NEW = auto()  # Incoming call
    END = auto()  # End a current call


class EventGen:
    def __init__(self, rows, cols, call_rates, call_duration,
                 *args, **kwargs):
        self.rows = rows
        self.cols = cols
        if type(call_rates) != np.ndarray:
            # Use uniform call rates through grid
            self.call_rates = np.ones((rows, cols)) * call_rates
        else:
            self.call_rates = call_rates
        # Avg. time between arriving calls
        self.call_intertimes = 1/self.call_rates
        self.call_duration = call_duration

    def event_new(self, t, cell):
        """
        Generate a new call event at the given cell at an
        exponentially distributed time dt from t.
        """
        dt = np.random.exponential(self.call_intertimes[cell])
        return (dt + t, CEvent.NEW, cell)

    def event_end(self, t, cell, ch):
        """
        Generate end event for a call
        """
        e_time = np.random.exponential(self.call_duration) + t
        return (e_time, CEvent.END, cell, ch)

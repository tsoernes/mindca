from mineventgen import CEvent

from heapq import heappush, heappop


class Strat:
    def __init__(self, pp, eventgen, grid, logger,
                 sanity_check=True,
                 *args, **kwargs):
        self.rows = pp['rows']
        self.cols = pp['cols']
        self.n_channels = pp['n_channels']
        self.n_episodes = pp['n_episodes']
        self.grid = grid
        self.cevents = []  # Call events
        self.eventgen = eventgen
        self.sanity_check = sanity_check
        self.logger = logger

    def simulate(self):
        # Generate initial call events; one for each cell
        for r in range(self.rows):
            for c in range(self.cols):
                heappush(self.cevents, self.eventgen.event_new(0, (r, c)))

        n_rejected = 0
        n_incoming = 0
        cevent = heappop(self.cevents)
        ch = self.get_action(cevent)

        # Discrete event simulation
        for i in range(self.n_episodes):

            t, ce_type, cell = cevent[0], cevent[1], cevent[2]
            self.execute_action(cevent, ch)

            if self.sanity_check and not self.grid.validate_reuse_constr():
                self.logger.error(f"Reuse constraint broken: {self.grid}")
                raise Exception

            if ce_type == CEvent.NEW:
                n_incoming += 1
                # Generate next incoming call
                heappush(self.cevents, self.eventgen.event_new(t, cell))
                if ch == -1:
                    n_rejected += 1
                    self.logger.debug(
                            f"Rejected call to {cell}")
                else:
                    # Generate call duration for call and add end event
                    heappush(self.cevents,
                             self.eventgen.event_end(t, cell, ch))

            next_cevent = heappop(self.cevents)
            next_ch = self.get_action(next_cevent)
            ch, cevent = next_ch, next_cevent
        self.logger.info(
                f"Rejected {n_rejected} of {n_incoming} calls")

    def get_action(self):
        raise NotImplementedError()

    def execute_action(self):
        raise NotImplementedError()


class FAStrat(Strat):
    """
    Fixed assignment (FA) channel allocation.
    The set of channels is partitioned, and the partitions are permanently
    assigned to cells so that all cells can use all the channels assigned
    to them simultaneously without interference.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_action(self, next_cevent, *args):
        next_cell = next_cevent[2]
        if next_cevent[1] == CEvent.NEW:
            # When a call arrives in a cell,
            # if any pre-assigned channel is unused;
            # it is assigned, else the call is blocked.
            ch = -1
            for idx, isNom in enumerate(self.grid.nom_chs[next_cell]):
                if isNom and self.grid.state[next_cell][idx] == 0:
                    ch = idx
                    break
            return ch
        else:
            # No rearrangement is done when a call terminates.
            return next_cevent[3]

    def execute_action(self, cevent, ch):
        cell = cevent[2]
        if ch != -1:
            if cevent[1] == CEvent.NEW:
                self.grid.state[cell][ch] = 1
            else:
                self.grid.state[cell][ch] = 0


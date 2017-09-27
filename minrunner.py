from minstrats import FAStrat
from mingrid import FixedGrid
from mineventgen import EventGen

import logging


def def_pparams(
        rows=7,
        cols=7,
        n_channels=70,
        erlangs=8,
        call_rates=None,
        call_duration=3,
        n_episodes=10000,
        ):
    """
    n_hours: If n_episodes is not specified, run simulation for n_hours
        of simulation time
    Call rates in calls per minute
    Call duration in minutes
    gamma:
    """
    # erlangs = call_rate * duration
    # 10 erlangs = 200cr, 3cd
    # 7.5 erlangs = 150cr, 3cd
    # 5 erlangs = 100cr, 3cd
    if not call_rates:
        call_rates = erlangs / call_duration
    return {
            'rows': rows,
            'cols': cols,
            'n_channels': n_channels,
            'call_rates': call_rates,  # Avg. call rate, in calls per minute
            'call_duration': call_duration,  # Avg. call duration in minutes
            'n_episodes': n_episodes,
            'sanity_check': False,
            'profile': True,
            'log_level': logging.INFO
           }


class Runner:
    def __init__(self):
        self.pp = def_pparams()

        logging.basicConfig(
                level=self.pp['log_level'], format='%(message)s')
        self.logger = logging.getLogger('')
        self.logger.info(f"Starting simulation with params {self.pp}")

    def runFA(self):
        grid = FixedGrid(logger=self.logger, **self.pp)
        self.eventgen = EventGen(**self.pp)
        self.strat = FAStrat(
                self.pp, grid=grid,
                eventgen=self.eventgen,
                sanity_check=True, logger=self.logger)
        self.strat.simulate()


if __name__ == '__main__':
    r = Runner()
    r.runFA()

import math
import functools

import numpy as np


class Grid:
    def __init__(self, rows, cols, n_channels, logger,
                 *args, **kwargs):
        self.rows = rows
        self.cols = cols
        self.n_channels = n_channels
        self.logger = logger

        self.state = np.zeros((self.rows, self.cols, self.n_channels),
                              dtype=bool)
        self.labels = np.zeros((self.rows, self.cols), dtype=int)
        self._partition_cells()

    def validate_reuse_constr(self):
        """
        Verify that the channel reuse constraint of 3 is not violated,
        e.g. that a channel in use in a cell is not in use in its neighbors.
        Returns True if valid not violated, False otherwise
        """
        # TODO: It should be possible to do this more efficiently.
        # If no neighbors of a cell violate the channel reuse constraint,
        # then the cell itself does not either, so it should be possible
        # to skip checking some cells.
        for r in range(self.rows):
            for c in range(self.cols):
                neighs = self.neighbors2(r, c, True)
                inuse = np.bitwise_or.reduce(self.state[neighs])
                if np.any(np.bitwise_and(self.state[r][c], inuse)):
                    self.logger.error(
                        "Channel Reuse constraint violated"
                        f" in Cell {r} {c}")
                    return False
        return True

    @staticmethod
    def move_n(row, col):
        return (row-1, col)

    @staticmethod
    def move_ne(row, col):
        if col % 2 == 0:
            return (row, col+1)
        else:
            return (row-1, col+1)

    @staticmethod
    def move_se(row, col):
        if col % 2 == 0:
            return (row+1, col+1)
        else:
            return (row, col+1)

    @staticmethod
    def move_s(row, col):
        return (row+1, col)

    @staticmethod
    def move_sw(row, col):
        if col % 2 == 0:
            return (row+1, col-1)
        else:
            return (row, col-1)

    @staticmethod
    def move_nw(row, col):
        if col % 2 == 0:
            return (row, col-1)
        else:
            return (row-1, col-1)

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def neighbors1sparse(row, col):
        """
        Returns a list with indexes of neighbors within a radius of 1,
        not including self. The indexes may not be within grid.
        In clockwise order starting from up-right.
        """
        idxs = [
            Grid.move_n(row, col),
            Grid.move_ne(row, col),
            Grid.move_se(row, col),
            Grid.move_s(row, col),
            Grid.move_sw(row, col),
            Grid.move_nw(row, col)]
        return idxs

    @functools.lru_cache(maxsize=None)
    def neighbors2(self, row, col, separate=False):
        """
        If 'separate' is True, return ([r1, r2, ...], [c1, c2, ...])
        else return [(r1, c1), (r2, c2), ...]

        Returns a list with indexes of neighbors within a radius of 2,
        not including self
        """
        if separate:
            rs = []
            cs = []
        else:
            idxs = []

        r_low = max(0, row-2)
        r_hi = min(self.rows-1, row+2)
        c_low = max(0, col-2)
        c_hi = min(self.cols-1, col+2)
        if col % 2 == 0:
            cross1 = row-2
            cross2 = row+2
        else:
            cross1 = row+2
            cross2 = row-2
        for r in range(r_low, r_hi+1):
            for c in range(c_low, c_hi+1):
                if not ((r, c) == (row, col) or
                        (r, c) == (cross1, col-2) or
                        (r, c) == (cross1, col-1) or
                        (r, c) == (cross1, col+1) or
                        (r, c) == (cross1, col+2) or
                        (r, c) == (cross2, col-2) or
                        (r, c) == (cross2, col+2)):
                    if separate:
                        rs.append(r)
                        cs.append(c)
                    else:
                        idxs.append((r, c))
        if separate:
            return (rs, cs)
        else:
            return idxs

    def _partition_cells(self):
        """
        Partition cells into 7 lots such that the minimum distance
        between cells with the same label ([0..6]) is at least 2
        (which corresponds to a minimum reuse distance of 3).

        Returns an n*m array with the label for each cell.
        """
        def right_up(x, y):
            x_new = x + 3
            y_new = y
            if x % 2 != 0:
                # Odd column
                y_new = y - 1
            return (x_new, y_new)

        def down_left(x, y):
            x_new = x - 1
            if x % 2 == 0:
                # Even column
                y_new = y + 3
            else:
                # Odd Column
                y_new = y + 2
            return (x_new, y_new)

        def label(l, x, y):
            # A center and some part of its subgrid may be out of bounds.
            if (x >= 0 and x < self.cols
                    and y >= 0 and y < self.rows):
                self.labels[y][x] = l

        # Center of a 'circular' 7-cell subgrid where
        # each cell has a unique label
        center = (0, 0)
        # First center in current row which has neighbors inside grid
        first_row_center = (0, 0)
        # Move center down-left until subgrid goes out of bounds
        while (center[0] >= -1) and (center[1] <= self.rows):
            # Move center right-up until subgrid goes out of bounds
            while (center[0] <= self.cols) and (center[1] >= -1):
                # Label cells 0..6 with given center as 0
                label(0, *center)
                for i, neigh in enumerate(
                        self.neighbors1sparse(center[1], center[0])):
                    label(i+1, neigh[1], neigh[0])
                center = right_up(*center)
            center = down_left(*first_row_center)
            # Move right until x >= -1
            while center[0] < -1:
                center = right_up(*center)
            first_row_center = center


class FixedGrid(Grid):
    def __init__(self, n_nom_channels=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Nominal channels for each cell
        self.nom_chs = np.zeros((self.rows, self.cols, self.n_channels),
                                dtype=bool)
        self.assign_chs(n_nom_channels)

    def assign_chs(self, n_nom_channels=0):
        """
        Partition the cells and channels up to and including 'n_channels'
        into 7 lots, and assign
        the channels to cells such that they will not interfere with each
        other within a channel reuse constraint of 3.
        The channels assigned to a cell are its nominal channels.

        Returns a (rows*cols*n_channels) array
        where a channel for a cell has value 1 if nominal, 0 otherwise.
        """
        if n_nom_channels == 0:
            n_channels = self.n_channels
        channels_per_subgrid_cell = []
        channels_per_subgrid_cell_accu = [0]
        channels_per_cell = n_channels/7
        ceil = math.ceil(channels_per_cell)
        floor = math.floor(channels_per_cell)
        tot = 0
        for i in range(7):
            if tot + ceil + (6-i) * floor > n_channels:
                tot += ceil
                cell_channels = ceil
            else:
                tot += floor
                cell_channels = floor
            channels_per_subgrid_cell.append(cell_channels)
            channels_per_subgrid_cell_accu.append(tot)
        for r in range(self.rows):
            for c in range(self.cols):
                label = self.labels[r][c]
                lo = channels_per_subgrid_cell_accu[label]
                hi = channels_per_subgrid_cell_accu[label+1]
                self.nom_chs[r][c][lo:hi] = 1

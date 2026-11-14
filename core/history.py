"""Widget-independent history of validated application transactions.

Commands explain the operation; private mementos preserve raw encodings and
record identities exactly, including noncanonical data that cannot be inverted
by simply applying opposite numeric edits.
"""

from copy import deepcopy
from dataclasses import dataclass


@dataclass
class Entry:
    label: str
    before: object
    after: object


class History:
    def __init__(self):
        self.past = []
        self.future = []

    def record(self, label, before, after):
        self.past.append(Entry(label, deepcopy(before), deepcopy(after)))
        self.future.clear()

    def undo(self):
        entry = self.past.pop()
        self.future.append(entry)
        return deepcopy(entry.before)

    def redo(self):
        entry = self.future.pop()
        self.past.append(entry)
        return deepcopy(entry.after)

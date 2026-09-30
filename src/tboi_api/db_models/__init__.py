"""SQLAlchemy models for the isaacguru.com dataset."""

from .base import Base, create_sqlite_engine
from .entries import (
    ENTRY_CLASSES,
    Character,
    Consumable,
    Curse,
    Entry,
    Item,
    Machine,
    Pickup,
    Room,
    Transformation,
    Trinket,
)
from .links import (
    EntryPool,
    EntryReference,
    EntryTag,
    EntryTransformation,
    Synergy,
    UnlockChallenge,
    UnlockReference,
    UnlockTag,
)
from .lookups import Challenge, Pool, Tag

__all__ = [
    "Base",
    "create_sqlite_engine",
    "ENTRY_CLASSES",
    "Entry",
    "Item",
    "Trinket",
    "Consumable",
    "Pickup",
    "Machine",
    "Character",
    "Transformation",
    "Curse",
    "Room",
    "Pool",
    "Tag",
    "Challenge",
    "EntryPool",
    "EntryTag",
    "EntryTransformation",
    "Synergy",
    "EntryReference",
    "UnlockReference",
    "UnlockTag",
    "UnlockChallenge",
]

"""Join tables connecting entries to lookups and to each other."""

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

ENTRY_FK = "entries.id"


class EntryPool(Base):
    """An entry's membership in an item pool, with its spawn weight."""

    __tablename__ = "entry_pools"

    entry_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)
    pool_id: Mapped[str] = mapped_column(ForeignKey("pools.id"), primary_key=True)
    weight: Mapped[float | None] = mapped_column(Float)

    entry: Mapped["Entry"] = relationship(back_populates="pool_links")
    pool: Mapped["Pool"] = relationship(back_populates="entry_links")


class EntryTag(Base):
    """A tag attached to an entry."""

    __tablename__ = "entry_tags"

    entry_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)
    tag_id: Mapped[str] = mapped_column(ForeignKey("tags.id"), primary_key=True)


class EntryTransformation(Base):
    """An entry that counts toward a transformation."""

    __tablename__ = "entry_transformations"

    entry_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)
    transformation_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)


class Synergy(Base):
    """How one entry interacts with another."""

    __tablename__ = "synergies"

    source_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)
    target_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)

    source: Mapped["Entry"] = relationship(foreign_keys=[source_id], back_populates="synergies")
    target: Mapped["Entry"] = relationship(foreign_keys=[target_id])


class EntryReference(Base):
    """Another entry mentioned inside an entry's description."""

    __tablename__ = "entry_references"

    source_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)
    target_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)


class UnlockReference(Base):
    """An entry mentioned in another entry's unlock condition."""

    __tablename__ = "unlock_references"

    entry_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)
    target_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)


class UnlockTag(Base):
    """A tag mentioned in an entry's unlock condition."""

    __tablename__ = "unlock_tags"

    entry_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)
    tag_id: Mapped[str] = mapped_column(ForeignKey("tags.id"), primary_key=True)


class UnlockChallenge(Base):
    """A challenge that must be completed to unlock an entry."""

    __tablename__ = "unlock_challenges"

    entry_id: Mapped[str] = mapped_column(ForeignKey(ENTRY_FK), primary_key=True)
    challenge_id: Mapped[int] = mapped_column(Integer, ForeignKey("challenges.id"), primary_key=True)

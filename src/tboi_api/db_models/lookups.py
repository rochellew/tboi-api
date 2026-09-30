"""Lookup tables that entries point to: item pools, tags, and challenges."""

from sqlalchemy import LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Pool(Base):
    """An item pool (e.g. Treasure Room) that items can be drawn from."""

    __tablename__ = "pools"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    # Offset (CSS px, negative) into data/isaacguru/spritesheets/main.webp; None if the site has no icon.
    sprite_x: Mapped[int | None]
    sprite_y: Mapped[int | None]
    # 13x13 PNG cropped at seed time. Deferred so pool queries don't load it.
    icon: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)

    entry_links: Mapped[list["EntryPool"]] = relationship(back_populates="pool")


class Tag(Base):
    """A gameplay tag (e.g. `angel`, `summonable`) attached to entries."""

    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)

    entries: Mapped[list["Entry"]] = relationship(secondary="entry_tags", back_populates="tags", viewonly=True)


class Challenge(Base):
    """A challenge run, referenced by name in unlock conditions."""

    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)

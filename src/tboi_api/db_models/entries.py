"""Game entries (items, trinkets, characters, ...) stored in one `entries` table.

Every category shares the same id space, so entries use single-table
inheritance: one table, one subclass per category, discriminated by `category`.
"""

from sqlalchemy import JSON, Boolean, ForeignKey, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Entry(Base):
    """Any entry on the site; fields shared by every category."""

    __tablename__ = "entries"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    mod: Mapped[str] = mapped_column(String(32))
    type: Mapped[str | None] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(128), index=True)
    clean_name: Mapped[str] = mapped_column(String(128))
    number: Mapped[str | None] = mapped_column(String(16))
    quality: Mapped[int | None]
    pickup_quote: Mapped[str | None] = mapped_column(Text)
    type_label: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    unlock: Mapped[str | None] = mapped_column(Text)
    unlock_text: Mapped[str | None] = mapped_column(Text)
    stat_changes: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    added_in: Mapped[str | None] = mapped_column(String(32))
    animated: Mapped[bool] = mapped_column(Boolean, default=False)
    wti_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    youtube_id: Mapped[str | None] = mapped_column(String(32))
    costume_url: Mapped[str | None] = mapped_column(Text)
    guru_url: Mapped[str | None] = mapped_column(Text)
    wiki_url: Mapped[str | None] = mapped_column(Text)

    pool_links: Mapped[list["EntryPool"]] = relationship(back_populates="entry")
    tags: Mapped[list["Tag"]] = relationship(secondary="entry_tags", back_populates="entries", viewonly=True)
    transformations: Mapped[list["Transformation"]] = relationship(
        secondary="entry_transformations",
        primaryjoin="Entry.id == EntryTransformation.entry_id",
        secondaryjoin="Transformation.id == EntryTransformation.transformation_id",
        back_populates="members",
        viewonly=True,
    )
    synergies: Mapped[list["Synergy"]] = relationship(foreign_keys="Synergy.source_id", back_populates="source")

    __mapper_args__ = {"polymorphic_on": "category"}

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.id} {self.name!r}>"


class Item(Entry):
    """A collectible item (passive, active, or familiar)."""

    # x offset (CSS px, negative) into data/isaacguru/spritesheets/isaac.png; None for animated items.
    sprite_x: Mapped[int | None]
    # The item's icon image, cropped at seed time. Deferred so item queries don't load it.
    icon: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    icon_mime: Mapped[str | None] = mapped_column(String(16))

    __mapper_args__ = {"polymorphic_identity": "item"}


class Trinket(Entry):
    """A trinket."""

    __mapper_args__ = {"polymorphic_identity": "trinket"}


class Consumable(Entry):
    """A card, rune, or pill effect."""

    __mapper_args__ = {"polymorphic_identity": "consumable"}


class Pickup(Entry):
    """A floor pickup such as a heart, coin, or chest."""

    __mapper_args__ = {"polymorphic_identity": "pickup"}


class Machine(Entry):
    """A machine or beggar."""

    __mapper_args__ = {"polymorphic_identity": "machine"}


class Character(Entry):
    """A playable character, with base stats."""

    speed: Mapped[float | None]
    tears: Mapped[float | None]
    damage: Mapped[float | None]
    range: Mapped[float | None]
    shot_speed: Mapped[float | None]
    luck: Mapped[float | None]

    __mapper_args__ = {"polymorphic_identity": "character"}


class Transformation(Entry):
    """A transformation, granted by collecting tagged or specific entries."""

    tag_id: Mapped[str | None] = mapped_column(ForeignKey("tags.id"))

    tag: Mapped["Tag | None"] = relationship()
    members: Mapped[list["Entry"]] = relationship(
        secondary="entry_transformations",
        primaryjoin="Transformation.id == EntryTransformation.transformation_id",
        secondaryjoin="Entry.id == EntryTransformation.entry_id",
        back_populates="transformations",
        viewonly=True,
    )

    __mapper_args__ = {"polymorphic_identity": "transformation"}


class Curse(Entry):
    """A floor curse."""

    __mapper_args__ = {"polymorphic_identity": "curse"}


class Room(Entry):
    """A special room type."""

    __mapper_args__ = {"polymorphic_identity": "room"}


# Category name (the `category` column) -> model class.
ENTRY_CLASSES: dict[str, type[Entry]] = {
    cls.__mapper_args__["polymorphic_identity"]: cls
    for cls in (Item, Trinket, Consumable, Pickup, Machine, Character, Transformation, Curse, Room)
}

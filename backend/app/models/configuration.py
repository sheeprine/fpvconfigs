import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Configuration(Base):
    __tablename__ = "configurations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    board_name: Mapped[str] = mapped_column(String(64), nullable=True)
    manufacturer_id: Mapped[str] = mapped_column(String(64), nullable=True)
    craft_name: Mapped[str] = mapped_column(String(255), nullable=True)
    pilot_name: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="configurations")
    revisions: Mapped[list["Revision"]] = relationship(
        "Revision", back_populates="configuration", cascade="all, delete-orphan",
        order_by="Revision.revision_number"
    )


class Revision(Base):
    __tablename__ = "revisions"
    __table_args__ = (
        UniqueConstraint("config_id", "revision_number", name="uq_config_revision_number"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("configurations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    betaflight_version: Mapped[str] = mapped_column(String(64), nullable=True)
    msp_api_version: Mapped[str] = mapped_column(String(16), nullable=True)
    config_revision: Mapped[str] = mapped_column(String(64), nullable=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    configuration: Mapped["Configuration"] = relationship(
        "Configuration", back_populates="revisions"
    )

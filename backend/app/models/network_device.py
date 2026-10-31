"""Network Device ORM Model (Simulated Campus Digital Twin)."""

import enum
import uuid
from typing import Any
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DeviceType(str, enum.Enum):
    ACCESS_POINT = "access_point"
    SWITCH = "switch"
    ROUTER = "router"
    SERVER = "server"


class DeviceStatus(str, enum.Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class NetworkDevice(Base):
    """Network device in the campus digital twin.
    
    NOTE: All device telemetries and health metrics in this table are
    SIMULATED representations for the hackathon prototype.
    """

    __tablename__ = "network_devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    device_type: Mapped[DeviceType] = mapped_column(
        SQLEnum(DeviceType, name="device_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    location: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
    )
    mac_address: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    status: Mapped[DeviceStatus] = mapped_column(
        SQLEnum(DeviceStatus, name="device_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=DeviceStatus.ONLINE,
        nullable=False,
        index=True,
    )
    health_metrics: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    is_simulated: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    last_seen: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_network_devices_type_status", "device_type", "status"),
    )


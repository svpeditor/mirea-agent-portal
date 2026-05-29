"""ORM-модели: общая база данных для агентов (datasets + dataset_records).

Один агент наполняет датасет (задачи/решения в LaTeX, классификаторы), другие
агенты его читают. Доступ агента к конкретному датасету объявляется в манифесте
(`runtime.datasets`), а здесь хранятся сами данные. Датасет создаётся лениво при
первой записи.
"""
# ruff: noqa: RUF002
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from portal_api.models.base import Base


class Dataset(Base):
    """Именованная общая база (каталог записей), доступная нескольким агентам."""

    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DatasetRecord(Base):
    """Одна запись в датасете: ключ + JSON-значение и/или текст (например LaTeX).

    Уникальность (dataset_id, record_key) даёт upsert-семантику: повторная
    запись по тому же ключу обновляет значение.
    """

    __tablename__ = "dataset_records"
    __table_args__ = (
        UniqueConstraint("dataset_id", "record_key", name="dataset_records_key_uq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Индексы по dataset_id создаёт миграция 0013 (ix_dataset_records_dataset
    # + составной), поэтому index=True здесь не ставим — иначе autogenerate
    # будет дёргать дублирующий ix_dataset_records_dataset_id.
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    record_key: Mapped[str] = mapped_column(Text, nullable=False)
    # content_format: как трактовать содержимое — 'json' | 'latex' | 'text'.
    content_format: Mapped[str] = mapped_column(Text, nullable=False, default="json")
    value_jsonb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Кто записал. SET NULL — чтобы удаление агента/джоба не ломало данные.
    created_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    created_by_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

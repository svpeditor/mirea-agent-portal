"""Pydantic-модели для manifest.yaml — паспорта агента."""
from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryStrict(StrEnum):
    """Вкладки портала. Должно совпадать с tab.slug в БД портала."""  # noqa: RUF002

    SCIENCE = "научная-работа"
    EDUCATION = "учебная"
    ORGANIZATION = "организационная"


class InputType(StrEnum):
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    CHECKBOX = "checkbox"
    SELECT = "select"
    RADIO = "radio"
    DATE = "date"


class FileType(StrEnum):
    SINGLE_FILE = "single_file"
    MULTI_FILES = "multi_files"
    FOLDER = "folder"
    ZIP = "zip"


class OutputType(StrEnum):
    DOCX = "docx"
    PDF = "pdf"
    XLSX = "xlsx"
    ZIP = "zip"
    HTML = "html"
    JSON = "json"
    ANY = "any"


# --- Поля формы (inputs) ---


class _BaseField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    help: str | None = None
    required: bool = False


class TextField(_BaseField):
    type: Literal[InputType.TEXT]
    placeholder: str | None = None
    default: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None


class TextareaField(_BaseField):
    type: Literal[InputType.TEXTAREA]
    placeholder: str | None = None
    default: str | None = None
    rows: int = 4


class NumberField(_BaseField):
    type: Literal[InputType.NUMBER]
    default: float | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None


class CheckboxField(_BaseField):
    type: Literal[InputType.CHECKBOX]
    default: bool = False


class SelectOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str
    label: str


class SelectField(_BaseField):
    type: Literal[InputType.SELECT]
    options: list[SelectOption] = Field(min_length=1)
    default: str | None = None


class RadioField(_BaseField):
    type: Literal[InputType.RADIO]
    options: list[SelectOption] = Field(min_length=1)
    default: str | None = None


class DateField(_BaseField):
    type: Literal[InputType.DATE]
    default: str | None = None


InputField = Annotated[
    TextField | TextareaField | NumberField | CheckboxField | SelectField | RadioField | DateField,
    Field(discriminator="type"),
]


# --- Файловые поля (files) ---


class _BaseFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    help: str | None = None
    required: bool = False
    accept: list[str] = Field(default_factory=list)
    max_total_size_mb: int = 100


class SingleFileField(_BaseFile):
    type: Literal[FileType.SINGLE_FILE]


class MultiFilesField(_BaseFile):
    type: Literal[FileType.MULTI_FILES]
    max_files: int = 50


class FolderFile(_BaseFile):
    type: Literal[FileType.FOLDER]


class ZipFile(_BaseFile):
    type: Literal[FileType.ZIP]


FileField = Annotated[
    SingleFileField | MultiFilesField | FolderFile | ZipFile,
    Field(discriminator="type"),
]


# --- Выходные артефакты ---


class OutputField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    type: OutputType
    label: str
    filename: str
    primary: bool = False


# --- Runtime ---


class DockerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_image: str
    setup: list[str] = Field(default_factory=list)
    entrypoint: list[str] = Field(min_length=1)


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["openrouter"] = "openrouter"
    models: list[str] = Field(default_factory=list)


class LimitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_runtime_minutes: int = 30
    max_memory_mb: int = 512
    max_cpu_cores: float = 1.0


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    docker: DockerConfig
    llm: LLMConfig = Field(default_factory=LLMConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)


# --- Корневой манифест ---


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    category: CategoryStrict | str  # допускаем кастомные категории сверху
    icon: str | None = None
    short_description: str = Field(min_length=1)
    about: str | None = None

    inputs: dict[str, InputField] = Field(default_factory=dict)
    files: dict[str, FileField] = Field(default_factory=dict)
    outputs: list[OutputField] = Field(min_length=1)
    runtime: RuntimeConfig

    @field_validator("category", mode="before")
    @classmethod
    def _coerce_category(cls, v: object) -> object:
        if isinstance(v, str):
            try:
                return CategoryStrict(v)
            except ValueError:
                return v  # кастомное значение остаётся строкой
        return v

    @field_validator("outputs")
    @classmethod
    def _validate_outputs(cls, v: list[OutputField]) -> list[OutputField]:
        # Проверка дублей id
        ids = [o.id for o in v]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Дубли output.id: {ids}")
        # At most one primary
        primaries = sum(1 for o in v if o.primary)
        if primaries > 1:
            raise ValueError("Только один output может быть primary=true")
        return v

    @classmethod
    def from_yaml(cls, path: Path | str) -> Manifest:
        text = Path(path).read_text(encoding="utf-8")
        data: dict[str, Any] = yaml.safe_load(text)
        return cls.model_validate(data)

"""Источники данных о зависимостях пакетов.

Источник возвращает описание релиза в одном формате, поэтому обход
графа не зависит от того, откуда взяты данные: из JSON API PyPI или
из файла описания тестового репозитория.
"""

from typing import Protocol

from src.pypi import fetch_latest, fetch_release

COMMENT_START = "#"
NAME_END = ":"
DEPENDENCY_SEPARATOR = ","


class Repository(Protocol):
    """Источник описаний релизов."""

    def release(
        self, name: str, version: str
    ) -> tuple[dict | None, str | None]:
        """Возвращает описание релиза и текст ошибки."""
        ...


class RealRepository:
    """Зависимости из JSON API репозитория PyPI."""

    def __init__(self, base: str) -> None:
        self.base = base

    def release(
        self, name: str, version: str
    ) -> tuple[dict | None, str | None]:
        """Берёт заданную версию или последний релиз пакета."""
        if version:
            return fetch_release(self.base, name, version)
        return fetch_latest(self.base, name)


class FileRepository:
    """Зависимости из файла описания тестового репозитория."""

    def __init__(self, packages: dict[str, list[str]]) -> None:
        self.packages = packages

    def release(
        self, name: str, version: str
    ) -> tuple[dict | None, str | None]:
        """Возвращает зависимости пакета из файла."""
        if name not in self.packages:
            return None, f"package is missing in test repository: {name!r}"
        return {
            "name": name,
            "version": version,
            "requires": self.packages[name],
        }, None


def split_dependencies(tail: str) -> list[str]:
    """Делит правую часть строки на имена зависимостей."""
    return tail.replace(DEPENDENCY_SEPARATOR, " ").split()


def parse_test_repository(
    text: str,
) -> tuple[dict[str, list[str]] | None, str | None]:
    """Разбирает файл тестового репозитория.

    Формат строки: «ПАКЕТ: ЗАВИСИМОСТЬ ЗАВИСИМОСТЬ». Пустая правая
    часть означает пакет без зависимостей. Пустые строки и строки,
    начинающиеся с #, пропускаются.
    """
    packages: dict[str, list[str]] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if line == "" or line.startswith(COMMENT_START):
            continue
        name, separator, tail = line.partition(NAME_END)
        name = name.strip()
        if separator == "" or name == "":
            return None, f"invalid test repository line {number}: {raw!r}"
        if name in packages:
            return None, f"package is described twice: {name!r}"
        packages[name] = split_dependencies(tail)
    return packages, None


def load_test_repository(
    path: str,
) -> tuple[dict[str, list[str]] | None, str | None]:
    """Читает файл тестового репозитория с диска."""
    try:
        with open(path, encoding="utf-8") as file:
            text = file.read()
    except OSError as error:
        return None, f"cannot read test repository: {path}: {error.strerror}"
    return parse_test_repository(text)

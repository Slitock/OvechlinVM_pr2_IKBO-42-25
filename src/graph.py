"""Построение графа зависимостей.

Граф хранится словарём: ключ — имя пакета, значение — список имён
пакетов, от которых он зависит. Обход идёт по уровням: сначала
зависимости первого уровня, потом второго и так далее. Один шаг
рекурсии раскрывает ровно один уровень.
"""

import re

from src.pypi import split_requirement
from src.repository import Repository

NAME_SEPARATOR = re.compile(r"[-_.]+")


def build_graph(
    repository: Repository,
    package: str,
    version: str,
    filter_text: str = "",
) -> tuple[dict[str, list[str]] | None, str | None]:
    """Строит граф зависимостей и возвращает (граф, ошибка)."""
    graph: dict[str, list[str]] = {package: []}
    level = [(package, version)]
    error = expand_level(repository, level, graph, filter_text)
    if error:
        return None, error
    return graph, None


def expand_level(
    repository: Repository,
    level: list[tuple[str, str]],
    graph: dict[str, list[str]],
    filter_text: str,
) -> str | None:
    """Раскрывает один уровень графа и вызывает себя для следующего."""
    next_level = []
    for name, version in level:
        dependencies, error = read_dependencies(repository, name, version)
        if error:
            return error
        for dependency in dependencies:
            if is_filtered(dependency, filter_text):
                continue
            key = find_node(graph, dependency)
            if key is None:
                graph[dependency] = []
                key = dependency
                next_level.append((key, ""))
            if key not in graph[name]:
                graph[name].append(key)
    if next_level:
        return expand_level(repository, next_level, graph, filter_text)
    return None


def read_dependencies(
    repository: Repository, name: str, version: str
) -> tuple[list[str], str | None]:
    """Возвращает имена зависимостей без маркеров и повторов.

    Что делать с версией, решает источник: для корневого пакета она
    задана пользователем, для остальных запрашивается последний
    релиз.
    """
    data, error = repository.release(name, version)
    if error:
        return [], error
    names = []
    for text in data["requires"]:
        dependency, _, marker = split_requirement(text)
        if marker:
            continue
        if dependency not in names:
            names.append(dependency)
    return names, None


def normalize_name(name: str) -> str:
    """Приводит имя пакета к нормализованному виду PEP 503."""
    return NAME_SEPARATOR.sub("-", name.lower())


def find_node(graph: dict[str, list[str]], name: str) -> str | None:
    """Ищет пакет в графе по нормализованному имени."""
    target = normalize_name(name)
    for existing in graph:
        if normalize_name(existing) == target:
            return existing
    return None


def is_filtered(dependency: str, filter_text: str) -> bool:
    """Проверяет, содержит ли имя пакета подстроку фильтра."""
    if filter_text == "":
        return False
    return filter_text.lower() in dependency.lower()

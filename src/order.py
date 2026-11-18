"""Порядок загрузки зависимостей.

Зависимость должна загружаться раньше пакета, который от неё зависит.
Такой порядок даёт обход в глубину: пакет попадает в результат после
всех своих зависимостей.
"""


def load_order(graph: dict[str, list[str]], start: str) -> list[str]:
    """Возвращает порядок загрузки пакетов, начиная с зависимостей."""
    order: list[str] = []
    visited: set[str] = set()
    visit(graph, start, visited, order)
    return order


def visit(
    graph: dict[str, list[str]],
    name: str,
    visited: set[str],
    order: list[str],
) -> None:
    """Добавляет пакет в результат после всех его зависимостей."""
    if name in visited:
        return
    visited.add(name)
    for dependency in graph.get(name, []):
        visit(graph, dependency, visited, order)
    order.append(name)

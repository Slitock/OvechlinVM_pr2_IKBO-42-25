"""Представление графа на языке диаграмм Graphviz."""

import os
import subprocess

IMAGE_PATH = "out/graph.png"
DOT_PROGRAM = "dot"
IMAGE_FORMAT = "png"
SUCCESS = 0
OPEN_PROGRAM = "xdg-open"
DISPLAY_VARIABLES = ("DISPLAY", "WAYLAND_DISPLAY")


def quote_name(name: str) -> str:
    """Заключает имя пакета в кавычки для DOT."""
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def build_dot(graph: dict[str, list[str]]) -> str:
    """Собирает описание графа на языке DOT."""
    lines = ["digraph dependencies {", "    rankdir=LR;"]
    for name in graph:
        lines.append(f"    {quote_name(name)};")
        for dependency in graph[name]:
            lines.append(
                f"    {quote_name(name)} -> {quote_name(dependency)};"
            )
    lines.append("}")
    return "\n".join(lines)


def render_image(source: str, path: str = IMAGE_PATH) -> str | None:
    """Рисует картинку из описания DOT и возвращает ошибку."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    command = [DOT_PROGRAM, f"-T{IMAGE_FORMAT}", "-o", path]
    try:
        result = subprocess.run(
            command, input=source, text=True, capture_output=True
        )
    except OSError as error:
        return f"cannot run {DOT_PROGRAM}: {error.strerror}"
    if result.returncode != SUCCESS:
        return f"{DOT_PROGRAM} failed: {result.stderr.strip()}"
    return None


def has_display() -> bool:
    """Проверяет, задана ли графическая среда."""
    for name in DISPLAY_VARIABLES:
        if os.environ.get(name):
            return True
    return False


def open_image(path: str) -> None:
    """Открывает картинку просмотрщиком, если есть графическая среда."""
    if not has_display():
        return
    try:
        subprocess.Popen(
            [OPEN_PROGRAM, path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return

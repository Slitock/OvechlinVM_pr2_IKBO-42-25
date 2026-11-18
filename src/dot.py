"""Представление графа на языке диаграмм Graphviz."""

import os
import subprocess

IMAGE_PATH = "out/graph.png"
DOT_PROGRAM = "dot"
IMAGE_FORMAT = "png"
SUCCESS = 0


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

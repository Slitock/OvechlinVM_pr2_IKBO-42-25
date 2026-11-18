# depviz — визуализатор графа зависимостей пакетов Python

Учебный проект по дисциплине «Конфигурационное управление» (ПР №2,
вариант 21). Программа читает метаданные пакета из репозитория,
строит граф зависимостей, печатает его, порядок загрузки и описание
Graphviz, а также рисует картинку с графом.

Менеджеры пакетов и сторонние библиотеки для получения зависимостей
не используются: нужные данные читаются стандартными средствами
Python.

## Требования

* Python 3.10 или выше.
* Утилита `dot` из пакета Graphviz — только для отрисовки картинки.

## Структура проекта

```
src/main.py        интерфейс командной строки и проверки
src/pypi.py        запрос к PyPI и разбор зависимостей
src/graph.py       обход графа зависимостей
src/order.py       порядок загрузки зависимостей
src/dot.py         представление графа в DOT и отрисовка
src/repository.py  источники данных: PyPI и тестовый файл
examples/          файлы тестового репозитория
tests/             модульные тесты
run.sh             запуск приложения
test.sh            запуск тестов
```

## Запуск

```bash
./run.sh -p <пакет> -r <репозиторий> -V <версия> [опции]
```

## Запуск тестов

```bash
./test.sh
```

## Параметры

| Опция | Длинная форма | Назначение |
| :--- | :--- | :--- |
| `-p` | `--package` | имя анализируемого пакета (обязательный) |
| `-r` | `--repository` | корень API репозитория или файл тестового репозитория (обязательный) |
| `-m` | `--mode` | режим работы: `real` или `test` |
| `-V` | `--version` | версия анализируемого пакета (обязательный) |
| `-f` | `--filter` | подстрока, исключающая пакеты из анализа |
| `-o` | `--output` | режим вывода: `graph`, `order`, `dot` или `all` (по умолчанию `graph`) |

Параметры читаются вручную из `sys.argv`: программа идёт по списку
аргументов парами «флаг — значение». Для каждого флага есть короткая
и длинная форма.

## Правила проверки параметров

* имя пакета: начинается и заканчивается буквой или цифрой, внутри
  допустимы точка, подчёркивание и дефис, длина не больше 128;
* версия: цифры и точки, например `2.31.0`; буквенные метки вроде
  `latest` отклоняются;
* репозиторий: в режиме `real` адрес должен начинаться с `http://`
  или `https://` и содержать хост, в режиме `test` путь должен
  указывать на существующий файл;
* фильтр: не должен содержать пробелов и запятых;
* режим: только `real` или `test`;
* режим вывода: только `graph`, `order`, `dot` или `all`.

## Обработка ошибок

Сообщение об ошибке печатается в поток ошибок, программа завершается
с кодом `2`:

```bash
$ ./run.sh -p "requests extra" -r https://pypi.org/pypi -V 2.31.0
error: invalid package name: 'requests extra'
```

```bash
$ ./run.sh -p requests -r ftp://mirror -V 2.31.0
error: repository URL must use http or https: 'ftp://mirror'
```

```bash
$ ./run.sh -p requests -r https://pypi.org/pypi -V latest
error: invalid version: 'latest'
```

```bash
$ ./run.sh -p requests -r https://pypi.org/pypi -V 2.31.0 -f "a b"
error: filter must not contain whitespace or commas: 'a b'
```

```bash
$ ./run.sh -p requests -r graph.txt -m test -V 2.31.0
error: test repository file not found: 'graph.txt'
```

```bash
$ ./run.sh --colour red
error: unknown option: --colour
```

```bash
$ ./run.sh -p
error: missing value for -p
```

```bash
$ ./run.sh -p requests -r https://pypi.org/pypi -V 2.31.0 -m broken
error: invalid mode: 'broken'
```

```bash
$ ./run.sh -p requests -r https://pypi.org/pypi -V 2.31.0 -o picture
error: invalid output mode: 'picture'
```

```bash
$ ./run.sh -p requests -r "https://pypi.org/pypi extra" -V 2.31.0
error: repository URL must not contain whitespace: \
'https://pypi.org/pypi extra'
```

## Пример использования

Примеры этапов показывают только тот вывод, который относится к
этому этапу. Текущая версия после параметров печатает ещё прямые
зависимости и граф.

Первый этап печатает все настраиваемые параметры:

```bash
$ ./run.sh -p requests -r https://pypi.org/pypi -V 2.31.0 -f tests
package:    requests
repository: https://pypi.org/pypi
mode:       real
version:    2.31.0
filter:     tests
output:     graph
```

Пустой фильтр печатается как `(none)`, чтобы было видно, что параметр
задан и пуст.

## Коды возврата

| Код | Когда |
| :--- | :--- |
| `0` | данные получены и напечатаны |
| `1` | репозиторий не ответил, версия не найдена, ответ broken, пакет отсутствует в тестовом репозитории |
| `2` | параметры командной строки заданы неверно |

Ошибка репозитория выглядит так:

```bash
$ ./run.sh -p ghost-package-xyz -r https://pypi.org/pypi -V 1.0
error: repository answered 404: \
https://pypi.org/pypi/ghost-package-xyz/1.0/json
```

## Этап 2. Сбор данных

Для заданной версии пакета программа запрашивает у репозитория JSON с
метаданными:

```
https://pypi.org/pypi/<пакет>/<версия>/json
```

Из ответа берётся поле `info.requires_dist` — список прямых
зависимостей. Каждая строка делится на три части: имя, условие версии
и маркер окружения. Например, `idna (<4,>=2.5)` даёт имя `idna` и
условие `<4,>=2.5`, а
`PySocks (!=1.5.7,>=1.5.6) ; extra == "socks"` дополнительно содержит
маркер `extra == "socks"`.

Маркеры на втором этапе только печатаются: видно, какие зависимости
необязательные (`extra == ...`) и какие зависят от платформы
(`python_version < '3.10'`). Фильтрация по маркерам появится на
третьем этапе вместе с обходом графа.

```bash
$ ./run.sh -p requests -r https://pypi.org/pypi -V 2.31.0
package:    requests
repository: https://pypi.org/pypi
mode:       real
version:    2.31.0
filter:     (none)
output:     graph

requests 2.31.0: direct dependencies (6)
  - charset-normalizer <4,>=2
  - idna <4,>=2.5
  - urllib3 <3,>=1.21.1
  - certifi >=2017.4.17
  - PySocks !=1.5.7,>=1.5.6  ; extra == 'socks'
  - chardet <6,>=3.0.2  ; extra == 'use_chardet_on_py3'
```

Пакет с зависимостями от версии Python:

```bash
$ ./run.sh -p flask -r https://pypi.org/pypi -V 2.3.3
...
Flask 2.3.3: direct dependencies (8)
  - Werkzeug >=2.3.7
  - Jinja2 >=3.1.2
  - itsdangerous >=2.1.2
  - click >=8.1.3
  - blinker >=1.6.2
  - importlib-metadata >=3.6.0  ; python_version < '3.10'
  - asgiref >=3.2  ; extra == "async"
  - python-dotenv  ; extra == "dotenv"
```

## Этап 3. Граф зависимостей

Программа обходит зависимости транзитивно: узел графа — пакет, ребро —
«пакет зависит от пакета».

Обход выполнен алгоритмом BFS (breadth-first search, обход в ширину)
с рекурсией: `expand_level` раскрывает ровно один уровень и вызывает
себя для следующего. Очередь уровня хранится в списке `next_level`.

* версия корневого пакета берётся из `-V`, для остальных пакетов
  запрашивается последний релиз;
* зависимости с маркерами (`extra == ...`, `python_version < ...`)
  в граф не включаются;
* имена пакетов сравниваются по правилам PEP 503 (нормализация
  имён): регистр, точки, подчёркивания и дефисы не различаются,
  поэтому `typing_extensions` и `typing-extensions` — один узел;
* циклы не зацикливают обход: пакет попадает в граф до раскрытия и
  повторно в следующий уровень не добавляется.

### Фильтрация

Параметр `-f` задаёт подстроку: пакеты, в имени которых она есть,
исключаются из анализа вместе со своими зависимостями. Регистр не
учитывается. Корневой пакет фильтр не отсекает: иначе анализировать
было бы нечего.

### Тестовый репозиторий

В режиме `-m test` вместо URL указывается путь к файлу с описанием
графа. Формат строки: имя пакета, двоеточие и список зависимостей.

```
A: B C
B: D
C: D
D:
```

Правила:

* одна строка — один пакет;
* зависимости разделяются пробелами или запятыми;
* пустая правая часть означает пакет без зависимостей;
* пустые строки и строки, начинающиеся с `#`, пропускаются;
* все достижимые пакеты должны быть описаны в файле, иначе программа
  сообщит об ошибке.

Готовые файлы лежат в каталоге `examples/`.

Цепочка:

```bash
$ ./run.sh -p A -r examples/chain.txt -m test -V 1.0
...
graph: 3 packages, 2 edges
  A
    -> B
  B
    -> C
  C
```

Ромб, в котором `D` — общая зависимость `B` и `C`:

```bash
$ ./run.sh -p A -r examples/diamond.txt -m test -V 1.0
...
graph: 4 packages, 4 edges
```

Цикл `A -> B -> C -> A`:

```bash
$ ./run.sh -p A -r examples/cycle.txt -m test -V 1.0
...
graph: 3 packages, 3 edges
  A
    -> B
  B
    -> C
  C
    -> A
```

Фильтр `-f D` убирает пакет `D` и рёбра к нему:

```bash
$ ./run.sh -p A -r examples/diamond.txt -m test -V 1.0 -f D
...
graph: 3 packages, 2 edges
```

Ошибки тестового режима:

```bash
$ ./run.sh -p A -r missing.txt -m test -V 1.0
error: test repository file not found: 'missing.txt'
```

```bash
$ ./run.sh -p A -r bad.txt -m test -V 1.0
error: invalid test repository line 1: 'A B'
```

Если в файле описана строка `A: Z`, а пакет `Z` отсутствует:

```bash
error: package is missing in test repository: 'Z'
```

## Этап 4. Порядок загрузки

Режим `-o order` печатает порядок, в котором пакеты нужно загружать:
сначала зависимости, затем пакет, который от них зависит. Порядок
строится обходом в глубину: пакет добавляется в результат после всех
своих зависимостей, поэтому любое ребро графа идёт от более раннего
пакета к более позднему.

```bash
$ ./run.sh -p requests -r https://pypi.org/pypi -V 2.31.0 -o order
...
loading order (5)
  1. charset-normalizer
  2. idna
  3. urllib3
  4. certifi
  5. requests
```

Если в графе есть цикл, строгого порядка не существует. Обход всё
равно завершается: посещённый пакет повторно не раскрывается, а ребро
цикла остаётся в графе.

```bash
$ ./run.sh -p A -r examples/cycle.txt -m test -V 1.0 -o order
...
loading order (3)
  1. C
  2. B
  3. A
```

Ромб и фильтр:

```bash
$ ./run.sh -p A -r examples/diamond.txt -m test -V 1.0 -o order
...
loading order (4)
  1. D
  2. B
  3. C
  4. A
```

```bash
$ ./run.sh -p A -r examples/diamond.txt -m test -V 1.0 -f D -o order
...
loading order (3)
  1. B
  2. C
  3. A
```

Режим `-o all` печатает и граф, и порядок загрузки.

### Сравнение с pip

Порядок установки pip выводит в строке `Installing collected packages`.
Проверка выполнена в чистом виртуальном окружении:

```bash
$ python3 -m venv /tmp/venv
$ /tmp/venv/bin/pip install requests==2.31.0
Installing collected packages: urllib3, idna, charset-normalizer, certifi, requests
```

```
наш порядок:  charset-normalizer, idna, urllib3, certifi, requests
порядок pip:  urllib3, idna, charset-normalizer, certifi, requests
```

Наборы пакетов совпадают. Порядок различается только у независимых
пакетов: между ними нет рёбер, поэтому оба порядка корректны.
Второй пример:

```bash
$ python3 -m venv /tmp/venv-flask
$ /tmp/venv-flask/bin/pip install flask==2.3.3
Installing collected packages: MarkupSafe, itsdangerous, click, blinker, Werkzeug, Jinja2, flask
```

```
наш порядок:  markupsafe, Werkzeug, Jinja2, itsdangerous, click, blinker, flask
порядок pip:  MarkupSafe, itsdangerous, click, blinker, Werkzeug, Jinja2, flask
```

Здесь тоже совпадают и набор пакетов, и свойство «зависимость раньше
зависимого». Отличия:

* у независимых пакетов порядок не определён однозначно, pip
  сортирует их по своим весам;
* регистр имени: pip печатает имя проекта (`MarkupSafe`), программа —
  имя из `requires_dist` (`markupsafe`), для pip это один пакет;
* версии: pip разрешает ограничения из `requires_dist`, программа
  берёт последний релиз каждой транзитивной зависимости.

## Этап 5. Визуализация

Режим `-o dot` печатает описание графа на языке Graphviz DOT и рисует
картинку `out/graph.png` утилитой `dot`.

```bash
$ ./run.sh -p requests -r https://pypi.org/pypi -V 2.31.0 -o dot
...
digraph dependencies {
    rankdir=LR;
    "requests";
    "requests" -> "charset-normalizer";
    "requests" -> "idna";
    "requests" -> "urllib3";
    "requests" -> "certifi";
    "charset-normalizer";
    "idna";
    "urllib3";
    "certifi";
}

image: out/graph.png
```

После отрисовки программа открывает `out/graph.png` просмотрщиком
через `xdg-open`, если задана графическая среда (`DISPLAY` или
`WAYLAND_DISPLAY`). Если среды нет или `xdg-open` недоступен, файл
просто остаётся на диске. Каталог `out/` исключён из репозитория.
Если утилиты `dot` нет, программа сообщает об ошибке и завершается
с кодом `1`.

Примеры для трёх пакетов:

| Пакет | Версия | Пакетов | Рёбер | Картинка |
| :--- | :--- | :--- | :--- | :--- |
| requests | 2.31.0 | 5 | 4 | 383x275 |
| flask | 2.3.3 | 7 | 7 | 482x347 |
| httpx | 0.27.0 | 7 | 8 | 384x304 |

### Сравнение с pipdeptree

`pipdeptree` — стандартный инструмент визуализации зависимостей
установленного окружения pip. Для requests он выводит:

```bash
$ pipdeptree -p requests -o graphviz-dot
digraph {
	"charset-normalizer" [label="charset-normalizer\n3.5.2"]
	certifi [label="certifi\n2026.10.23"]
	idna [label="idna\n3.20"]
	requests -> "charset-normalizer" [label=">=2,<4"]
	requests -> certifi [label=">=2017.4.17"]
	requests -> idna [label=">=2.5,<4"]
	requests -> urllib3 [label=">=1.21.1,<3"]
	requests [label="requests\n2.31.0"]
	urllib3 [label="urllib3\n2.8.0"]
}
```

Наборы узлов и рёбер совпадают с нашим графом для той же версии.
Отличия:

* `pipdeptree` подписывает узлы версиями, а рёбра — ограничениями
  версий; программа версии не отслеживает;
* `pipdeptree` описывает только установленные пакеты, то есть у него
  маркеры и extras уже вычислены; программа отбрасывает все
  зависимости с маркерами;
* `pipdeptree` печатает имя проекта (`MarkupSafe`), программа — имя
  из `requires_dist` (`markupsafe`); для pip это один пакет;
* оформление: у программы есть имя графа и `rankdir=LR`, у
  `pipdeptree` — подписи и другой набор атрибутов.

## Ограничения

* Поддерживаются версии из цифр и точек. Предрелизы вида `1.0rc1`
  не принимаются: для демонстрации они не нужны.
* Ограничения версий из `requires_dist` не разрешаются: для
  транзитивных пакетов берётся последний релиз.
* Зависимости с маркерами окружения в граф не включаются, поэтому он
  может быть меньше, чем результат pip.
* Глубина обхода ограничена пределом рекурсии Python; для реальных
  графов это несущественно.
* Картинка всегда сохраняется в `out/graph.png`, путь не настраивается;
  в графической среде она открывается просмотрщиком.

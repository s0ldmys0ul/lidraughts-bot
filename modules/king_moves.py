from logger import logger
from modules.timing import timer

# Кэш координат (поля 1..50 -> (col, row))
_field_to_coord_cache = {}
_coord_to_field_cache = {}


def _build_coord_cache():
    for field in range(1, 51):
        row = (field - 1) // 5
        col_in_row = (field - 1) % 5
        col = col_in_row * 2 + (1 if row % 2 == 0 else 0)
        _field_to_coord_cache[field] = (col, row)
        _coord_to_field_cache[(col, row)] = field


_build_coord_cache()


def _field_to_coord(field: int):
    return _field_to_coord_cache.get(field)


def _coord_to_field(col: int, row: int):
    return _coord_to_field_cache.get((col, row))


def _is_on_diagonal(f1: int, f2: int) -> bool:
    """Проверяет, лежат ли поля на одной диагонали (любое расстояние)."""
    c1, r1 = _field_to_coord(f1)
    c2, r2 = _field_to_coord(f2)
    return abs(c1 - c2) == abs(r1 - r2) and (c1 != c2 or r1 != r2)


def _line_is_clear_between(f1: int, f2: int, board: list, exclude: set = None) -> bool:
    """
    Проверяет, что на линии между f1 и f2 (исключая сами поля) нет других фигур.
    Если задано множество exclude, поля из него считаются пустыми (уже сбиты).
    """
    c1, r1 = _field_to_coord(f1)
    c2, r2 = _field_to_coord(f2)
    dc = (c2 - c1) // max(1, abs(c2 - c1))  # шаг по столбцу: -1, 0, 1
    dr = (r2 - r1) // max(1, abs(r2 - r1))  # шаг по строке: -1, 0, 1
    steps = max(abs(c2 - c1), abs(r2 - r1))
    for i in range(1, steps):
        c = c1 + i * dc
        r = r1 + i * dr
        field = _coord_to_field(c, r)
        if field is None:
            continue  # не должно произойти, если линия корректна
        if board[field - 1] != 'e' and (exclude is None or field not in exclude):
            return False
    return True


def _possible_landings(current: int, captured: int, board: list, exclude: set = None) -> list:
    """
    Возвращает список полей, на которые может приземлиться дамка,
    взяв captured из current.
    Все поля должны быть пустыми (или уже сбитыми в exclude).
    """
    c_cur, r_cur = _field_to_coord(current)
    c_cap, r_cap = _field_to_coord(captured)
    dc = c_cap - c_cur
    dr = r_cap - r_cur
    # Шаг должен быть ненулевым и диагональным
    if abs(dc) != abs(dr) or (dc == 0 and dr == 0):
        return []
    step_col = dc // abs(dc)  # направление по столбцу: -1 или 1
    step_row = dr // abs(dr)  # направление по строке: -1 или 1
    # Проверяем, что линия от current до captured чиста (кроме самой captured)
    if not _line_is_clear_between(current, captured, board, exclude):
        return []

    landings = []
    k = 1
    while True:
        c_land = c_cap + k * step_col
        r_land = r_cap + k * step_row
        if not (0 <= c_land < 10 and 0 <= r_land < 10):
            break
        land_field = _coord_to_field(c_land, r_land)
        # Если клетка занята (и не в exclude), дальше нельзя
        if board[land_field - 1] != 'e' and (exclude is None or land_field not in exclude):
            break
        landings.append(land_field)
        k += 1
    return landings


def reconstruct_king_path(start: int, end: int, captured: list, board: list) -> list:
    with timer(f"reconstruct_king_path(start={start}, end={end}, captured={captured})"):  # TIMING ADDED
        """
        Рекурсивно восстанавливает траекторию дамочного взятия.
        Возвращает список полей [start, промежуточные..., end] или None.
        """
        captured_set = set(captured)
        visited_states = set()

        def backtrack(current: int, remaining: frozenset, path: list):
            state = (current, tuple(sorted(remaining)))
            if state in visited_states:
                return None
            visited_states.add(state)

            if not remaining:
                if current == end:
                    return path
                return None

            for cap in remaining:
                if not _is_on_diagonal(current, cap):
                    continue
                # Проверяем, что линия от current до cap чиста
                # При этом уже взятые фигуры (captured_set - remaining) игнорируются
                taken = captured_set - remaining
                if not _line_is_clear_between(current, cap, board, taken):
                    continue
                # Получаем все возможные поля приземления за cap
                # Исключаем из проверки уже взятые фигуры (taken)
                landings = _possible_landings(current, cap, board, taken)
                for land in landings:
                    new_remaining = remaining - {cap}
                    result = backtrack(land, new_remaining, path + [land])
                    if result is not None:
                        return result
            return None

        result = backtrack(start, frozenset(captured_set), [start])
        return result
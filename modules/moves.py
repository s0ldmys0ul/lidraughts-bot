# modules/moves.py
import re
from logger import logger
from modules.king_moves import reconstruct_king_path
from modules.timing import timer  # <-- добавить эту строку!

class MoveParser:
    """
    Преобразует строку хода от Scan в последовательность полей для кликов.
    Для взятий восстанавливает правильный хронологический порядок.
    Если на начальном поле стоит дамка и есть несколько сбитых, используется дамочный парсер.
    """

    def __init__(self):
        self._field_to_coord_cache = {}
        self._coord_to_field_cache = {}
        self._build_coord_cache()

    def _build_coord_cache(self):
        for field in range(1, 51):
            row = (field - 1) // 5
            col_in_row = (field - 1) % 5
            col = col_in_row * 2 + (1 if row % 2 == 0 else 0)
            self._field_to_coord_cache[field] = (col, row)
            self._coord_to_field_cache[(col, row)] = field

    def _field_to_coord(self, field: int):
        return self._field_to_coord_cache.get(field)

    def _coord_to_field(self, col: int, row: int):
        return self._coord_to_field_cache.get((col, row))

    def _is_diagonal_neighbor(self, f1: int, f2: int) -> bool:
        """Проверяет, являются ли поля соседними по диагонали (расстояние 1)."""
        c1, r1 = self._field_to_coord(f1)
        c2, r2 = self._field_to_coord(f2)
        return abs(c1 - c2) == 1 and abs(r1 - r2) == 1

    def _get_landing_field(self, from_field: int, captured_field: int) -> int:
        with timer(f"MoveParser._get_landing_field({from_field}, {captured_field})"):  # TIMING ADDED
            if not self._is_diagonal_neighbor(from_field, captured_field):
                return None

            c1, r1 = self._field_to_coord(from_field)
            c2, r2 = self._field_to_coord(captured_field)

            dc = c2 - c1
            dr = r2 - r1

            c3 = c2 + dc
            r3 = r2 + dr

            if not (0 <= c3 < 10 and 0 <= r3 < 10):
                return None

            return self._coord_to_field(c3, r3)

    def _reconstruct_path(self, start: int, end: int, captured: list) -> list:
        with timer(f"MoveParser._reconstruct_path(start={start}, end={end}, captured={captured})"):  # TIMING ADDED
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
                    if not self._is_diagonal_neighbor(current, cap):
                        continue
                    landing = self._get_landing_field(current, cap)
                    if landing is None:
                        continue
                    new_remaining = remaining - {cap}
                    result = backtrack(landing, new_remaining, path + [landing])
                    if result is not None:
                        return result
                return None

            result = backtrack(start, frozenset(captured_set), [start])
            return result

    def parse(self, scan_move: str, board: list, turn: str, white_kings: list, black_kings: list) -> list:
        with timer(f"MoveParser.parse({scan_move})"):  # TIMING ADDED
            logger.debug(f"Парсинг хода: '{scan_move}'")

            # Простой ход
            if '-' in scan_move:
                parts = scan_move.split('-')
                if len(parts) == 2:
                    try:
                        start = int(parts[0].strip())
                        end = int(parts[1].strip())
                        logger.debug(f"Простой ход: {start} → {end}")
                        return [start, end]
                    except ValueError:
                        logger.error(f"Ошибка парсинга простого хода: {scan_move}")
                        return None

            # Взятие
            elif 'x' in scan_move:
                parts = [p.strip() for p in scan_move.split('x') if p.strip()]
                if len(parts) < 2:
                    logger.error(f"Недостаточно компонентов во взятии: {scan_move}")
                    return None

                try:
                    start = int(parts[0])
                    end = int(parts[1])
                    captured = [int(p) for p in parts[2:]] if len(parts) > 2 else []

                    logger.debug(f"Взятие: start={start}, end={end}, captured={captured}")

                    # Определяем тип фигуры на начальном поле
                    is_king = False
                    if turn == 'W' and start in white_kings:
                        is_king = True
                    elif turn == 'B' and start in black_kings:
                        is_king = True

                    # Если это дамка и есть несколько сбитых, используем дамочный парсер
                    if is_king and len(captured) >= 1:
                        logger.debug("Обнаружено дамочное взятие, вызываем king_moves")
                        path = reconstruct_king_path(start, end, captured, board)
                        if path:
                            logger.debug(f"Восстановленная дамочная траектория: {path}")
                            return path
                        else:
                            logger.error(f"Не удалось восстановить траекторию для дамки: {scan_move}")
                            # Fallback на start->end (надеемся, что сайт сам построит путь)
                            return [start, end]

                    # Простое взятие (без явного списка captured или одна сбитая)
                    if not captured:
                        landing = self._get_landing_field(start, end)
                        if landing is None:
                            logger.error(f"Невозможно вычислить конечное поле для {start}x{end}")
                            return None
                        logger.debug(f"Простое взятие: {start} → {landing} через {end}")
                        return [start, landing]

                    # Множественное взятие простой шашкой
                    path = self._reconstruct_path(start, end, captured)
                    if path:
                        logger.debug(f"Восстановленная траектория (простая): {path}")
                        return path
                    else:
                        logger.error(f"Не удалось восстановить траекторию для {scan_move}")
                        return [start, end]

                except ValueError as e:
                    logger.error(f"Ошибка преобразования чисел в '{scan_move}': {e}")
                    return None

            logger.error(f"Неизвестный формат хода: '{scan_move}'")
            return None
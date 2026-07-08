#!/usr/bin/env python3
"""
Конвертер между хаб-строкой Scan и форматом "W:W31,32,...:B1,2,...[:H0:F1]"
Запуск: python converter.py
Введите строку в любом формате, программа выведет результат.
Для выхода введите пустую строку или 'quit'.
"""

import sys
import re

def parse_second_format(s: str):
    """
    Парсит строку вида "W:W31,32,...:B1,2,...[:H0:F1]"
    Возвращает (turn, white_list, black_list, half_moves, f_value)
    white_list и black_list — списки кортежей (номер_поля, is_king)
    """
    # Убираем возможные пробелы
    s = s.strip()
    parts = s.split(':')
    if len(parts) < 3:
        raise ValueError("Недостаточно частей (должно быть минимум 3, разделённых ':')")

    turn = parts[0].strip()
    if turn not in ('W', 'B'):
        raise ValueError(f"Очередь должна быть 'W' или 'B', получено '{turn}'")

    # Белые: ожидается "W31,32,..." или пусто
    white_part = parts[1]
    if not white_part.startswith('W'):
        raise ValueError("Вторая часть должна начинаться с 'W'")
    white_str = white_part[1:]  # убираем 'W'
    black_part = parts[2]
    if not black_part.startswith('B'):
        raise ValueError("Третья часть должна начинаться с 'B'")
    black_str = black_part[1:]

    # Дополнительные части H и F игнорируем
    half_moves = 0
    f_value = 1
    if len(parts) >= 4 and parts[3].startswith('H'):
        try:
            half_moves = int(parts[3][1:])
        except:
            pass
    if len(parts) >= 5 and parts[4].startswith('F'):
        try:
            f_value = int(parts[4][1:])
        except:
            pass

    def parse_list(lst_str):
        if not lst_str:
            return []
        items = lst_str.split(',')
        result = []
        for item in items:
            item = item.strip()
            if not item:
                continue
            if item.endswith('K'):
                field = int(item[:-1])
                is_king = True
            else:
                field = int(item)
                is_king = False
            result.append((field, is_king))
        return result

    white_list = parse_list(white_str)
    black_list = parse_list(black_str)

    return turn, white_list, black_list, half_moves, f_value


def second_to_hub(turn, white_list, black_list):
    """
    Преобразует разобранный второй формат в хаб-строку.
    """
    squares = ['e'] * 50
    for f, king in white_list:
        if 1 <= f <= 50:
            squares[f-1] = 'W' if king else 'w'
    for f, king in black_list:
        if 1 <= f <= 50:
            squares[f-1] = 'B' if king else 'b'
    return turn + ''.join(squares)


def parse_hub(hub_str: str):
    """
    Парсит хаб-строку (длина 51, первый символ W/B, остальные 50 из w,b,W,B,e)
    Возвращает (turn, squares_list) где squares_list — список из 50 символов.
    """
    hub_str = hub_str.strip()
    if len(hub_str) != 51:
        raise ValueError("Хаб-строка должна быть длиной ровно 51 символ")
    turn = hub_str[0]
    if turn not in ('W', 'B'):
        raise ValueError("Первый символ должен быть 'W' или 'B'")
    squares = list(hub_str[1:])
    valid = set('wWbBe')
    for i, ch in enumerate(squares):
        if ch not in valid:
            raise ValueError(f"Недопустимый символ '{ch}' на позиции {i+2}")
    return turn, squares


def hub_to_second(turn, squares, include_hf=False, half_moves=0, f_value=1):
    """
    Преобразует разобранную хаб-строку во второй формат.
    Возвращает строку вида "W:W...:B..." с опциональными :H и :F.
    """
    white = []
    black = []
    for i, ch in enumerate(squares, start=1):
        if ch == 'w':
            white.append(str(i))
        elif ch == 'W':
            white.append(f"{i}K")
        elif ch == 'b':
            black.append(str(i))
        elif ch == 'B':
            black.append(f"{i}K")
        # 'e' игнорируем

    # Сортируем по номеру поля для удобства
    def field_key(item):
        # item может быть "31" или "31K"
        return int(item.rstrip('K'))

    white.sort(key=field_key)
    black.sort(key=field_key)

    white_str = ','.join(white)
    black_str = ','.join(black)

    result = f"{turn}:W{white_str}:B{black_str}"
    if include_hf:
        result += f":H{half_moves}:F{f_value}"
    return result


def detect_format(s: str) -> str:
    """
    Определяет формат строки: 'hub' или 'second'.
    """
    s = s.strip()
    if not s:
        return 'unknown'
    # Если есть двоеточия и первый символ W/B после возможных пробелов
    if ':' in s:
        # Проверим, что первая часть до двоеточия это 'W' или 'B'
        first = s.split(':', 1)[0].strip()
        if first in ('W', 'B'):
            return 'second'
        # Иначе может быть что-то другое
    else:
        # Нет двоеточий — возможно хаб-строка
        if len(s) == 51 and s[0] in ('W', 'B'):
            return 'hub'
    # Если не удалось определить, пробуем по длине
    if len(s) == 51 and s[0] in ('W', 'B'):
        return 'hub'
    if ':' in s:
        return 'second'
    raise ValueError("Не удалось определить формат строки")


def main():
    print("Конвертер нотаций для шашек")
    print("Введите строку в одном из форматов, и получите результат.")
    print("Для выхода оставьте строку пустой или введите 'quit'.")
    print("-" * 50)

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not line or line.lower() == 'quit':
            break

        try:
            fmt = detect_format(line)
            if fmt == 'hub':
                turn, squares = parse_hub(line)
                result = hub_to_second(turn, squares, include_hf=False)
                print("Второй формат:", result)
            elif fmt == 'second':
                turn, white, black, half, fval = parse_second_format(line)
                result = second_to_hub(turn, white, black)
                print("Хаб-строка:", result)
            else:
                print("Неизвестный формат")
        except Exception as e:
            print("Ошибка:", e)

    print("До свидания!")


if __name__ == "__main__":
    main()
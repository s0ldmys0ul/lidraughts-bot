# modules/position.py
from logger import logger

def update_engine_position(bot, fen: str) -> bool:
    """
    Парсит FEN, обновляет bot.board, bot.white_kings, bot.black_kings.
    """
    try:
        fen = fen.strip()
        if not fen:
            return False

        if 'G' in fen:
            logger.debug(f"Пропущен FEN с G: {fen[:50]}...")
            return False

        parts = fen.split(':')
        if parts[0] in ('W', 'B'):
            white_raw = parts[1] if len(parts) > 1 else ''
            black_raw = parts[2] if len(parts) > 2 else ''
        else:
            white_raw = parts[0] if len(parts) > 0 else ''
            black_raw = parts[1] if len(parts) > 1 else ''

        white_raw = white_raw.lstrip('W').split(':')[0]
        black_raw = black_raw.lstrip('B').split(':')[0]

        white_men, white_kings = _parse_side(white_raw)
        black_men, black_kings = _parse_side(black_raw)

        bot.white_kings = sorted(white_kings)
        bot.black_kings = sorted(black_kings)
        bot.board = ['e'] * 50
        for f in white_men:
            if 1 <= f <= 50:
                bot.board[f-1] = 'w'
        for f in white_kings:
            if 1 <= f <= 50:
                bot.board[f-1] = 'W'
        for f in black_men:
            if 1 <= f <= 50:
                bot.board[f-1] = 'b'
        for f in black_kings:
            if 1 <= f <= 50:
                bot.board[f-1] = 'B'

        logger.debug(f"Парсинг FEN: белые простые={sorted(white_men)}, белые дамки={sorted(white_kings)}")
        logger.debug(f"Парсинг FEN: чёрные простые={sorted(black_men)}, чёрные дамки={sorted(black_kings)}")
        return True
    except Exception as e:
        logger.exception(f"Ошибка обновления позиции: {e}")
        return False

def _parse_side(raw: str):
    men = []
    kings = []
    for item in raw.split(','):
        item = item.strip()
        if not item:
            continue
        if item.upper().startswith('K') or (len(item) > 1 and item[1:].upper().startswith('K')):
            num_str = ''.join(filter(str.isdigit, item))
            if num_str:
                try:
                    kings.append(int(num_str))
                except:
                    pass
        else:
            try:
                men.append(int(item))
            except:
                pass
    return men, kings
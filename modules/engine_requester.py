# modules/engine_requester.py
import asyncio
from logger import logger
from config import settings
from modules.time_control import calculate_adaptive_move_time

async def get_best_move_from_engine(bot):
    try:
        turn = bot._color_to_turn()
        hub_pos = turn + ''.join(bot.board)
        logger.info(f"Отправляю в Scan: {hub_pos}")

        if not bot.engine.set_position(hub_pos):
            logger.error("Не удалось установить позицию")
            return None

        move_time = await calculate_adaptive_move_time(bot)
        logger.info(f"⏱️ move_time для этого хода: {move_time:.3f}с")

        loop = asyncio.get_event_loop()
        move = await loop.run_in_executor(None, bot.engine.get_best_move, move_time)
        if move:
            logger.info(f"Движок вернул ход: {move}")
            fields = bot.parser.parse(move, bot.board, turn, bot.white_kings, bot.black_kings)
            if fields:
                bot._last_parsed_fields = fields
            else:
                logger.error(f"Парсер не смог разобрать ход {move}")
                return None
        return move
    except Exception as e:
        logger.exception(f"Ошибка получения хода от движка: {e}")
        return None
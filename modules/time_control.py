import random
import re
from logger import logger
from config import settings

async def calculate_adaptive_move_time(bot) -> float:
    """
    Рассчитывает время поиска на основе номера хода и оставшегося времени.
    """
    original_mt = bot.original_move_time
    if original_mt <= 0.1:
        logger.debug(f"🚀 Оригинальное move_time={original_mt} ≤ 0.1 → адаптация отключена")
        return original_mt

    time_left = await get_my_time_left(bot)
    if time_left is not None and time_left < bot.zeitnot_threshold:
        if not bot.in_zeitnot:
            bot.in_zeitnot = True
            logger.info(f"⚡ ВХОД В ЦЕЙТНОТ: время {time_left:.1f}с < порог {bot.zeitnot_threshold:.1f}с → mt=0.03")
        else:
            logger.debug(f"⚡ Время {time_left:.1f}с < {bot.zeitnot_threshold:.1f}с → цейтнот режим (mt=0.03)")
        return 0.03
    else:
        if bot.in_zeitnot:
            bot.in_zeitnot = False
            logger.info(f"✅ ВЫХОД ИЗ ЦЕЙТНОТА: время {time_left:.1f}с ≥ порог {bot.zeitnot_threshold:.1f}с → возврат к mt={original_mt}")

    logger.debug(f"📊 Возвращаем оригинальное move_time={original_mt}")
    return original_mt

async def get_my_time_left(bot) -> float | None:
    try:
        selector = '.rclock-bottom .time' if bot.my_color == 'white' else '.rclock-top .time'
        elem = await bot.browser.page.query_selector(selector)
        if not elem:
            return None
        html = await elem.inner_html()
        text = re.sub(r'<[^>]+>', '', html).strip()
        if ':' in text:
            m, s = text.split(':')
            return float(m) * 60 + float(s)
        return float(text)
    except Exception as e:
        logger.debug(f"Не удалось получить время: {e}")
        return None
import asyncio
import json
import random
from logger import logger
from config import settings
from modules.time_control import get_my_time_left

async def send_move(bot, scan_move: str) -> bool:
    logger.info(f"Выполняем ход: {scan_move} (ход #{bot.move_counter + 1} в игре)")

    capture_count = scan_move.count('x')
    is_multi_capture = capture_count > 1
    time_left = await get_my_time_left(bot)

    need_think_delay = True
    delay_reason = []
    delay_applied = False

    # Если MOVE_TIME < 0.1 — режим супербыстрый, но задержку всё равно будем делать (свою)
    if settings.move_time < 0.1:
        delay_reason.append("MOVE_TIME < 0.1 (режим супербыстрый)")
        # need_think_delay не сбрасываем, чтобы позже применить быструю задержку

    # Цейтнот — если время мало, но в супербыстром режиме задержку оставляем
    if time_left is not None and time_left < settings.urgent_time_threshold and need_think_delay:
        if settings.move_time > 0.1:
            need_think_delay = False
            delay_reason.append(f"Время мало ({time_left:.1f}с < {settings.urgent_time_threshold}с) – задержка отключена")
        else:
            delay_reason.append(f"Время мало, но супербыстрый режим – задержка сохраняется")

    # --- Задержка для супербыстрого режима (mt ≤ 0.1) ---
    if settings.move_time <= 0.1 and not is_multi_capture and need_think_delay:
        think_time = random.uniform(settings.think_time_fast_min, settings.think_time_fast_max)
        await asyncio.sleep(think_time)
        logger.info(f"⏱️ Задержка перед ходом: {think_time:.3f}с (супербыстрый режим mt≤0.1, ход #{bot.move_counter + 1})")
        need_think_delay = False
        delay_applied = True
        delay_reason.append("Супербыстрый режим")

    # --- Обычная задержка (для mt > 0.1) ---
    if settings.move_time > 0.1 and not is_multi_capture and need_think_delay:
        think_time = random.uniform(settings.think_time_min, settings.think_time_max)
        await asyncio.sleep(think_time)
        logger.info(f"⏱️ Задержка перед ходом: {think_time:.3f}с (обычный ход #{bot.move_counter + 1})")
        need_think_delay = False
        delay_applied = True
        delay_reason.append("Обычный ход")

    # --- Задержка для множественных взятий ---
    if need_think_delay:
        think_time = random.uniform(settings.capture_delay_min, settings.capture_delay_max)
        await asyncio.sleep(think_time)
        logger.info(f"⏱️ Задержка перед ходом: {think_time:.3f}с (множественное взятие, причины: {', '.join(delay_reason)})")
        delay_applied = True

    # Если ни одна задержка не была применена — логируем 0
    if not delay_applied:
        logger.info(f"⏱️ Задержка перед ходом: 0.000с (причины: {'; '.join(delay_reason)})")

    if not bot._last_parsed_fields:
        logger.error("Нет распарсенных полей для хода")
        return False

    fields = bot._last_parsed_fields
    bot._last_parsed_fields = None
    bot.move_counter += 1

    try:
        moves = []
        for i in range(len(fields) - 1):
            click_delay = random.randint(30, 150) if is_multi_capture else random.randint(20, 80)
            moves.append({
                'from': str(fields[i]),
                'to': str(fields[i+1]),
                'delay': click_delay
            })

        total_delay = sum(m['delay'] for m in moves)
        logger.info(f"🖱️ Кликов: {len(moves)}, задержки: {[m['delay'] for m in moves]}мс, всего: {total_delay}мс")
        logger.debug(f"Поля для кликов: {fields}")

        js_code = f"""
            (function() {{
                if (!window.lidraughts || !window.lidraughts.socket) return;
                const moves = {json.dumps(moves)};
                let cumulativeDelay = 0;
                moves.forEach((move, index) => {{
                    setTimeout(() => {{
                        window.lidraughts.socket.send('move', {{
                            from: move.from,
                            to: move.to
                        }});
                    }}, cumulativeDelay);
                    cumulativeDelay += move.delay;
                }});
            }})();
        """
        await bot.browser.page.evaluate(js_code)
        logger.info(f"✅ Ход отправлен успешно (ход #{bot.move_counter})")
        return True
    except Exception as e:
        logger.exception(f"Ошибка отправки хода: {e}")
        return False
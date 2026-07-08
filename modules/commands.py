# modules/commands.py
import asyncio
import os
from config import settings
from logger import logger

async def async_input(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)

async def handle_command(cmd: str) -> bool:
    """Обрабатывает команду, возвращает True если команда распознана."""
    cmd = cmd.strip().lower()
    
    # Очистка консоли
    if cmd in ['cls', 'clear']:
        os.system('cls' if os.name == 'nt' else 'clear')
        return True
    
    if cmd.startswith('mt=') or cmd.startswith('move_time='):
        try:
            val = float(cmd.split('=')[1])
            settings.move_time = val
            logger.info(f"MOVE_TIME изменён на {val}")
            print(f"✅ MOVE_TIME теперь {val} с")
        except:
            print("❌ Неверный формат. Используйте mt=0.1")
        return True
    elif cmd.startswith('mt '):
        try:
            val = float(cmd.split()[1])
            settings.move_time = val
            logger.info(f"MOVE_TIME изменён на {val}")
            print(f"✅ MOVE_TIME теперь {val} с")
        except:
            print("❌ Неверный формат. Используйте mt 0.1")
        return True
    elif cmd == 'status':
        print("📊 Текущие настройки:")
        print(f"  MOVE_TIME          = {settings.move_time}")
        print(f"  DELAY_AFTER_MOVE   = {settings.delay_after_move}")
        print(f"  LOG_LEVEL          = {settings.log_level}")
        print(f"  HEADLESS           = {settings.headless}")
        return True
    elif cmd == 'help':
        print("📖 Доступные команды:")
        print("  mt=0.1  или mt 0.1   - установить MOVE_TIME (сек)")
        print("  status                - показать настройки")
        print("  help                  - это сообщение")
        print("  cls или clear         - очистить консоль")
        print("  back                  - вернуться (только в режиме команд)")
        return True
    elif cmd == 'back':
        return True
    else:
        return False
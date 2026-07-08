import sys
from pathlib import Path
from loguru import logger
from config import settings

# Удаляем стандартный обработчик loguru (чтобы настроить свои)
logger.remove()

# Создаём папку для логов, если её нет
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# Формат сообщения: время | уровень | имя_файла:функция:строка | сообщение
log_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}"

# Добавляем вывод в консоль с цветом (уровень из настроек)
logger.add(
    sys.stdout,
    format=log_format,
    level=settings.log_level,
    colorize=True,
    backtrace=True,
    diagnose=True
)

# Добавляем вывод в файл (все уровни, с ротацией)
logger.add(
    log_dir / "bot_{time:YYYY-MM-DD}.log",
    format=log_format,
    level="DEBUG",          # в файл пишем всё, даже DEBUG
    rotation="10 MB",       # новый файл после 10 МБ
    retention="7 days",     # храним логи 7 дней
    compression="zip",      # сжимаем старые
    backtrace=True,
    diagnose=True
)


# Тестовый блок: если файл запущен напрямую, покажем примеры логов
if __name__ == '__main__':
    logger.debug("Это сообщение уровня DEBUG")
    logger.info("Это сообщение уровня INFO")
    logger.warning("Это сообщение уровня WARNING")
    logger.error("Это сообщение уровня ERROR")
    logger.critical("Это сообщение уровня CRITICAL")
    
    # Демонстрация логирования исключения
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Поймали исключение")

    print("\n✅ Логи работают. Проверь консоль и папку 'logs'.")
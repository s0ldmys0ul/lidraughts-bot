# modules/ui.py
import asyncio
from modules.commands import async_input, handle_command
from logger import logger

async def choose_color_with_exit() -> str | None:
    """
    Меню выбора цвета для игры. Возвращает 'white' или 'black', если пользователь выбрал цвет.
    Возвращает None, если пользователь выбрал "Это не моя доска" (т.е. нужно искать другую).
    """
    while True:
        choice = await async_input("\n📋 Выберите:\n  1) Играть за белых\n  2) Играть за чёрных\n  3) Это не моя доска (искать другую)\nВаш выбор (1/2/3) или команда (help для справки): ")
        choice = choice.strip().lower()
        if choice == '3':
            return None
        elif choice == '1':
            return 'white'
        elif choice == '2':
            return 'black'
        else:
            # Если ввели команду (mt, status и т.п.) – обработаем
            if await handle_command(choice):
                continue
            else:
                print("Неверный ввод. Введите 1, 2 или 3.")
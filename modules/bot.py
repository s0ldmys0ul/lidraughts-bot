import asyncio
import json
import random
from logger import logger
from config import settings
from modules.browser import BrowserController
from modules.engine import ScanEngine
from modules.moves import MoveParser
from modules.commands import async_input, handle_command
from modules.ui import choose_color_with_exit
from modules.position import update_engine_position
from modules.time_control import calculate_adaptive_move_time, get_my_time_left
from modules.move_sender import send_move
from modules.engine_requester import get_best_move_from_engine

class DraughtsBot:
    def __init__(self):
        self.browser = BrowserController()
        self.engine = ScanEngine()
        self.parser = MoveParser()
        self.my_color = None
        self.running = True
        self.manual_mode = False
        self.consecutive_errors = 0
        self.last_move = None
        self.same_move_counter = 0
        self._last_parsed_fields = None
        self.current_game_id = None
        self.current_color = None
        self._move_in_progress = False
        self.last_fen = None
        self.board = ['e'] * 50
        self.white_kings = []
        self.black_kings = []
        self.move_counter = 0
        self.game_number = 0
        self.original_move_time = settings.move_time
        self.fast_mode_active = False
        self.zeitnot_threshold = 13.0
        self.in_zeitnot = False

    def _color_to_turn(self):
        return 'W' if self.my_color == 'white' else 'B'

    async def on_move(self, data_json: str):
        if not self.running:
            return
        try:
            data = json.loads(data_json)
            fen = data['fen']
            color = data['color']
            san = data['san']
            ply = data['ply']

            logger.debug(f"on_move: color={color}, san={san}, ply={ply}, FEN={fen}")

            if 'G' in fen:
                logger.debug("Пропущен FEN с G")
                return

            self.last_fen = fen
            logger.debug(f"✅ last_fen обновлён: {fen[:50]}...")

            if not update_engine_position(self, fen):
                logger.error("Не удалось обновить позицию в движке")
                return

            if color == 'unknown':
                logger.info("Получена стартовая позиция")
                return

            if color == self.my_color:
                logger.debug("Это наш ход (эхо), игнорируем")
                return

            if color != self.my_color and self.my_color is not None:
                logger.info(f"Ход противника: {san}")
                if self.manual_mode:
                    logger.info("Ручной режим: автоматический ответ отключён")
                    return

                if await self._is_game_over():
                    logger.info("Игра завершена")
                    return

                await self._make_my_move()

        except Exception as e:
            logger.exception(f"Ошибка в on_move: {e}")

    async def _is_game_over(self) -> bool:
        try:
            status_elem = await self.browser.page.query_selector('.status')
            if status_elem:
                text = await status_elem.text_content()
                return bool(text and text.strip())
            return False
        except Exception:
            return False

    async def _make_my_move(self):
        if self._move_in_progress:
            logger.warning("Ход уже выполняется, пропускаем")
            return
        self._move_in_progress = True
        try:
            move = await get_best_move_from_engine(self)
            if not move:
                self.consecutive_errors += 1
                if self.consecutive_errors >= settings.max_consecutive_errors:
                    logger.error("Слишком много ошибок, включаем ручной режим")
                    self.manual_mode = True
                return

            self.consecutive_errors = 0
            success = await send_move(self, move)
            if success:
                self.last_move = move
            else:
                self.consecutive_errors += 1
        finally:
            self._move_in_progress = False

    async def _get_fen_from_page(self) -> str | None:
        try:
            js_code = """
                (function() {
                    if (window.lidraughts && window.lidraughts.data && window.lidraughts.data.game) {
                        return window.lidraughts.data.game.fen;
                    }
                    return null;
                })();
            """
            fen = await self.browser.page.evaluate(js_code)
            if fen:
                logger.info(f"🔄 FEN получен напрямую со страницы: {fen[:50]}...")
                return fen
            return None
        except Exception as e:
            logger.debug(f"Не удалось получить FEN со страницы: {e}")
            return None

    async def play_game(self):
        self.game_number += 1
        logger.info(f"🎮 Начинаем партию #{self.game_number} за {self.my_color.upper()}ми")
        self.current_game_id = self.browser.get_game_id_from_url()
        self.current_color = self.my_color
        self.consecutive_errors = 0
        self.same_move_counter = 0
        self.last_move = None
        self.original_move_time = settings.move_time
        self.move_counter = 0
        self.zeitnot_threshold = random.uniform(6.0, 11.0)
        self.in_zeitnot = False

        if self.original_move_time > 0.1:
            self.fast_mode_active = True
            logger.info(f"🚀 АДАПТИВНЫЙ РЕЖИМ АКТИВИРОВАН (оригинальное mt={self.original_move_time} > 0.1)")
            logger.info(f"   • Первые {settings.fast_moves_count} ходов: mt=0.01 + задержка 0.10-0.30с")
            logger.info(f"   • При времени < {self.zeitnot_threshold:.1f}с: mt=0.03")
            logger.info(f"   • Остальные ходы: mt={self.original_move_time}")
        else:
            self.fast_mode_active = False
            logger.info(f"⚡ АДАПТИВНЫЙ РЕЖИМ ОТКЛЮЧЕН (оригинальное mt={self.original_move_time} ≤ 0.1)")

        logger.info(f"🔄 move_counter сброшен в 0 для новой игры #{self.game_number}")

        try:
            if self.my_color == 'white':
                await self._make_my_move()
            else:
                logger.info("Ожидание первого хода белых...")
                start_time = asyncio.get_event_loop().time()
                fen_received = False
                while self.running and asyncio.get_event_loop().time() - start_time < 15:
                    if await self.browser.has_last_move() and self.last_fen:
                        logger.info("✅ Ход белых обнаружен! FEN получен через мостик")
                        fen_received = True
                        break
                    await asyncio.sleep(0.2)

                if not fen_received:
                    logger.warning("⚠️ Мостик не сработал, пробуем получить FEN напрямую...")
                    fen = await self._get_fen_from_page()
                    if fen:
                        self.last_fen = fen
                        fen_received = True
                        logger.info("✅ FEN получен через fallback!")
                    else:
                        logger.error("❌ Не удалось получить FEN")

                if not fen_received:
                    logger.error("Не удалось получить позицию после хода белых")
                    return

                logger.debug(f"Использую last_fen: {self.last_fen}")
                update_engine_position(self, self.last_fen)
                await self._make_my_move()

            while self.running:
                if self.browser.page.is_closed():
                    logger.warning("Страница закрыта")
                    break
                if await self._is_game_over():
                    logger.info("Игра завершена")
                    break
                await asyncio.sleep(1)

        except Exception as e:
            logger.exception(f"Ошибка в игровом цикле: {e}")
        finally:
            logger.info(f"🏁 Выход из игры #{self.game_number}")
            self.current_game_id = None
            self.current_color = None

    async def run(self):
        self.current_color = None
        try:
            if not self.engine.start():
                logger.error("Не удалось запустить Scan")
                return

            await self.browser.start()
            self.browser.set_move_callback(self.on_move)
            await self.browser.goto_site()

            logger.info(f"📊 Текущие настройки:")
            logger.info(f"   move_time = {settings.move_time}с")
            logger.info(f"   fast_moves_count = {settings.fast_moves_count}")
            logger.info(f"   urgent_time_threshold = {settings.urgent_time_threshold}с")

            async def command_reader():
                loop = asyncio.get_event_loop()
                while self.running:
                    try:
                        cmd = await loop.run_in_executor(None, input, "> ")
                        if cmd.lower() == 'quit':
                            self.running = False
                            break
                        elif not await handle_command(cmd):
                            print("Неизвестная команда. Введите help.")
                    except Exception:
                        break

            reader_task = asyncio.create_task(command_reader())

            while self.running:
                print("📌 Ожидание доски. Вводите команды (help для справки).")
                board_found = await self.browser.wait_for_live_board(timeout=120)
                if not board_found:
                    logger.error("Доска не появилась")
                    await self.browser.goto_site()
                    continue

                print("✅ Доска обнаружена!")

                if self.current_color:
                    self.my_color = self.current_color
                    logger.info(f"Продолжение игры за {self.my_color}")
                    await self.play_game()
                else:
                    while True:
                        color = await choose_color_with_exit()
                        if color is None:
                            break
                        else:
                            self.my_color = color
                            await self.play_game()
                            logger.info("Партия завершена. Готов к следующей.")
                            self.my_color = None
                            self.manual_mode = False
                            self.consecutive_errors = 0
                            self.last_move = None
                            self.same_move_counter = 0
                            self.engine.new_game()
                            break

                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Бот остановлен")
        except Exception as e:
            logger.exception(f"Критическая ошибка: {e}")
        finally:
            self.running = False
            self.engine.stop()
            await self.browser.close()
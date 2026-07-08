import asyncio
import re
from playwright.async_api import async_playwright, Page
from logger import logger
from config import settings
from modules.timing import async_timer

class BrowserController:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page: Page = None
        self.board_element = None
        self.cell_size = None
        self.board_offset = None
        self._move_callback = None

    def set_move_callback(self, callback):
        self._move_callback = callback

    async def _on_move_from_js(self, data_json: str):
        logger.debug(f"_on_move_from_js получил данные: {data_json[:100]}...")
        if self._move_callback:
            await self._move_callback(data_json)
        else:
            logger.warning("_move_callback не установлен")

    async def start(self):
        async with async_timer("Browser.start"):
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=settings.headless,
                args=['--start-maximized']
            )
            self.page = await self.browser.new_page()
            await self.page.expose_function("onMove", self._on_move_from_js)
            self.page.on("framenavigated", lambda frame: asyncio.create_task(self._on_frame_navigated(frame)))
            self.page.on("console", lambda msg: logger.debug(f"🖥️ BROWSER CONSOLE: {msg.text}"))
            await self.page.set_viewport_size({"width": 1920, "height": 1080})
            logger.info("Браузер запущен 1920x1080")
            
            # 🆕 Внедряем мостик СРАЗУ после запуска
            await self._inject_bridge()

    async def _on_frame_navigated(self, frame):
        if frame == self.page.main_frame:
            logger.debug("Главный фрейм перезагружен, перевнедряем мостик")
            await asyncio.sleep(0.5)  # Даём странице немного загрузиться
            await self._inject_bridge()

    async def _inject_bridge(self):
        # 🆕 Улучшенный мостик с надёжным получением начальной позиции
        bridge_js = """
        (function() {
            if (window.lidraughtsBridgeInjected) return;
            window.lidraughtsBridgeInjected = true;

            const originalParse = JSON.parse;
            JSON.parse = function(text) {
                const data = originalParse.call(this, text);
                
                if (data?.d?.fen && data.t === 'move') {
                    const fen = data.d.fen;
                    const san = data.d.san || '';
                    const uci = data.d.uci || data.d.u || '';
                    const ply = data.d.ply || 0;
                    const movedColor = (ply % 2 === 1) ? 'white' : 'black';
                    
                    window.onMove(JSON.stringify({
                        color: movedColor,
                        san: san,
                        uci: uci,
                        ply: ply,
                        fen: fen
                    }));
                } 
                
                return data;
            };
            
            // 🆕 Функция для отправки начальной позиции
            function sendInitialPosition() {
                // Способ 1: Через window.lidraughts.data.game.fen
                if (window.lidraughts && window.lidraughts.data && window.lidraughts.data.game) {
                    const fen = window.lidraughts.data.game.fen;
                    if (fen) {
                        console.log('📍 Начальная позиция из window.lidraughts.', fen.substring(0, 50));
                        window.onMove(JSON.stringify({
                            color: 'unknown',
                            san: 'start',
                            uci: '',
                            ply: 0,
                            fen: fen
                        }));
                        return true;
                    }
                }
                
                // Способ 2: Парсинг script тегов
                for (let s of document.querySelectorAll('script')) {
                    const m = s.textContent.match(/"fen":\\s*"([^"]+)"/);
                    if (m) {
                        console.log('📍 Начальная позиция из script тега:', m[1].substring(0, 50));
                        window.onMove(JSON.stringify({
                            color: 'unknown',
                            san: 'start',
                            uci: '',
                            ply: 0,
                            fen: m[1]
                        }));
                        return true;
                    }
                }
                
                return false;
            }
            
            // 🆕 Пробуем получить позицию СРАЗУ
            if (!sendInitialPosition()) {
                // 🆕 Если не получилось — пробуем через 1с и 2с
                setTimeout(() => {
                    if (!sendInitialPosition()) {
                        setTimeout(() => {
                            sendInitialPosition();
                        }, 1000);
                    }
                }, 1000);
            }
        })();
        """
        try:
            await self.page.evaluate(bridge_js)
            logger.debug("JS-мостик внедрён")
        except Exception as e:
            logger.error(f"Не удалось внедрить мостик: {e}")

    async def goto_site(self, url: str = "https://lidraughts.org/"):
        async with async_timer(f"Browser.goto_site({url})"):
            await self.page.goto(url, wait_until="networkidle")
            await asyncio.sleep(1)
            logger.info(f"Перешли на {url}")

    async def wait_for_live_board(self, timeout: float = 120, min_size: int = 200) -> bool:
        async with async_timer(f"Browser.wait_for_live_board(timeout={timeout})"):
            logger.info(f"Ожидание доски в течение {timeout}с...")
            logger.info("👉 Откройте игру на сайте (Играть → С компьютером → Играть)")
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    current_url = self.page.url
                    if current_url.rstrip('/') == 'https://lidraughts.org':
                        await asyncio.sleep(1)
                        continue
                    boards = await self.page.query_selector_all('cg-board')
                    for board in boards:
                        bbox = await board.bounding_box()
                        if bbox and bbox['width'] >= min_size:
                            self.board_element = board
                            await self._update_board_geometry()
                            logger.info(f"✅ Доска обнаружена! {bbox['width']:.0f}x{bbox['height']:.0f}")
                            return True
                except Exception:
                    pass
                await asyncio.sleep(1)
            logger.error("❌ Доска не появилась")
            return False

    async def has_live_board(self, min_size: int = 200) -> bool:
        try:
            boards = await self.page.query_selector_all('cg-board')
            for board in boards:
                bbox = await board.bounding_box()
                if bbox and bbox['width'] >= min_size:
                    return True
        except Exception:
            pass
        return False

    async def _update_board_geometry(self):
        if not self.board_element:
            return
        bbox = await self.board_element.bounding_box()
        if bbox:
            self.board_offset = (bbox['x'], bbox['y'])
            self.cell_size = bbox['width'] / 10

    async def click_field(self, field_num: int):
        if not self.cell_size or not self.board_offset:
            raise RuntimeError("Геометрия доски не определена")
        row = (field_num - 1) // 5
        col_in_row = (field_num - 1) % 5
        col = col_in_row * 2 + (1 if row % 2 == 0 else 0)
        x = self.board_offset[0] + col * self.cell_size + self.cell_size / 2
        y = self.board_offset[1] + row * self.cell_size + self.cell_size / 2
        await self.page.mouse.click(x, y)

    async def click_sequence(self, fields: list):
        delay = 0.015 if len(fields) <= 2 else 0.03
        for field in fields:
            await self.click_field(field)
            await asyncio.sleep(delay)

    async def send_uci_move(self, uci: str):
        if len(uci) == 4:
            from_field = uci[:2]
            to_field = uci[2:]
            js_code = f"""
                if (window.lidraughts && window.lidraughts.socket) {{
                    window.lidraughts.socket.send('move', {{ from: '{from_field}', to: '{to_field}' }});
                }}
            """
            await self.page.evaluate(js_code)

    async def has_last_move(self) -> bool:
        """Проверяет, есть ли на доске элементы с классом last-move (признак только что сделанного хода)."""
        try:
            last_move = await self.page.query_selector('square.last-move')
            return last_move is not None
        except Exception:
            return False

    async def close(self):
        async with async_timer("Browser.close"):
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Браузер закрыт")

    def get_game_id_from_url(self) -> str | None:
        try:
            url = self.page.url
            match = re.search(r'/([a-zA-Z0-9]+)(?:/|$)', url)
            if match:
                return match.group(1)
        except Exception:
            pass
        return None
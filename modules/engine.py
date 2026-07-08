# modules/engine.py
import subprocess
import threading
import queue
import time
import re
from typing import Optional
from logger import logger
from config import settings
from modules.timing import timer  # <-- важно!

class ScanEngine:
    def __init__(self):
        self.proc = None
        self.stdout_queue = queue.Queue()
        self.stderr_queue = queue.Queue()
        self.stop_reader = False
        self.reader_thread = None
        self.stderr_thread = None
        self.initialized = False
        self._lock = threading.Lock()

    def start(self) -> bool:
        with timer("ScanEngine.start"):  # TIMING ADDED
            logger.info(f"Запуск Scan из {settings.scan_path}")
            try:
                self.proc = subprocess.Popen(
                    [settings.scan_path, "hub"],
                    cwd=settings.scan_dir,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    encoding='utf-8'
                )
            except Exception as e:
                logger.error(f"Не удалось запустить Scan: {e}")
                return False

            self.stop_reader = False
            self.reader_thread = threading.Thread(target=self._reader_worker, daemon=True)
            self.reader_thread.start()
            self.stderr_thread = threading.Thread(target=self._stderr_worker, daemon=True)
            self.stderr_thread.start()

            self.proc.stdin.write("hub\n")
            self.proc.stdin.flush()
            logger.debug("Отправлено: hub")

            if not self._wait_for_prompt("wait", timeout=10):
                logger.error("Не получен ответ 'wait' от Scan")
                self.stop()
                return False

            if not self._send_and_wait("init\n", "ready", timeout=10):
                logger.error("Не получен ответ 'ready' от Scan")
                self.stop()
                return False

            self._clear_queue()
            self.initialized = True
            logger.info("Scan успешно инициализирован")
            return True

    def stop(self):
        with timer("ScanEngine.stop"):  # TIMING ADDED
            self.initialized = False
            self.stop_reader = True
            if self.proc:
                logger.info("Остановка Scan")
                try:
                    if self.proc.stdin and not self.proc.stdin.closed:
                        self.proc.stdin.write("quit\n")
                        self.proc.stdin.flush()
                except Exception as e:
                    logger.error(f"Ошибка при отправке quit: {e}")
                time.sleep(0.5)
                if self.proc.poll() is None:
                    self.proc.kill()
                self.proc = None
            if self.reader_thread:
                self.reader_thread.join(timeout=1)
            if self.stderr_thread:
                self.stderr_thread.join(timeout=1)

    def _check_process_alive(self) -> bool:
        if self.proc is None:
            return False
        if self.proc.poll() is not None:
            logger.error(f"Процесс Scan умер с кодом {self.proc.poll()}")
            return False
        return True

    def _reader_worker(self):
        try:
            for line in iter(self.proc.stdout.readline, ''):
                if self.stop_reader:
                    break
                if line.strip():
                    self.stdout_queue.put(line.strip())
        except Exception as e:
            logger.error(f"Ошибка в reader_worker: {e}")
        finally:
            if self.proc and self.proc.stdout:
                try:
                    self.proc.stdout.close()
                except:
                    pass

    def _stderr_worker(self):
        try:
            for line in iter(self.proc.stderr.readline, ''):
                if self.stop_reader:
                    break
                if line.strip():
                    logger.error(f"Scan stderr: {line.strip()}")
        except Exception as e:
            logger.error(f"Ошибка в stderr_worker: {e}")
        finally:
            if self.proc and self.proc.stderr:
                try:
                    self.proc.stderr.close()
                except:
                    pass

    def _clear_queue(self):
        while not self.stdout_queue.empty():
            try:
                self.stdout_queue.get_nowait()
            except queue.Empty:
                break

    def _read_line(self, timeout: float) -> Optional[str]:
        try:
            return self.stdout_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _wait_for_prompt(self, expected: str, timeout: float) -> bool:
        with timer(f"ScanEngine._wait_for_prompt(expected={expected}, timeout={timeout})"):  # TIMING ADDED
            start = time.time()
            while time.time() - start < timeout:
                line = self._read_line(1.0)
                if line is None:
                    continue
                logger.debug(f"Получено: {line}")
                if expected in line:
                    return True
            return False

    def _send_and_wait(self, command: str, expected: str, timeout: float) -> bool:
        with timer(f"ScanEngine._send_and_wait(command={command.strip()}, expected={expected})"):  # TIMING ADDED
            if not self._check_process_alive():
                return False
            self.proc.stdin.write(command)
            self.proc.stdin.flush()
            logger.debug(f"Отправлено: {command.strip()}")
            return self._wait_for_prompt(expected, timeout)

    def _write_command(self, command: str) -> bool:
        with timer(f"ScanEngine._write_command({command.strip()})"):  # TIMING ADDED
            if not self._check_process_alive():
                return False
            try:
                self.proc.stdin.write(command)
                self.proc.stdin.flush()
                return True
            except Exception as e:
                logger.error(f"Ошибка записи в stdin: {e}")
                return False

    def set_position(self, hub_pos: str) -> bool:
        with timer(f"ScanEngine.set_position({hub_pos})"):  # TIMING ADDED
            if not self.initialized:
                logger.error("Движок не инициализирован")
                return False

            if not self._check_process_alive():
                logger.warning("Процесс умер, пытаемся перезапустить...")
                self.stop()
                time.sleep(0.5)
                if not self.start():
                    logger.error("Не удалось перезапустить Scan")
                    return False

            self._write_command("stop\n")
            time.sleep(0.05)
            self._clear_queue()

            if not self._write_command(f"pos pos={hub_pos}\n"):
                logger.error("Не удалось отправить позицию")
                return False

            logger.debug(f"Установлена позиция: {hub_pos}")
            return True

    def get_best_move(self, move_time: Optional[float] = None) -> Optional[str]:
        with timer(f"ScanEngine.get_best_move(time={move_time})"):  # TIMING ADDED
            if not self.initialized:
                logger.error("Движок не инициализирован")
                return None

            if not self._check_process_alive():
                logger.error("Процесс умер во время get_best_move")
                return None

            self._clear_queue()

            time_val = move_time if move_time is not None else settings.move_time
            self._write_command(f"level move-time={time_val}\n")
            logger.debug(f"Установлено время: {time_val}")

            self._write_command("go think\n")
            logger.debug("Запущен поиск хода")

            timeout = time_val + 0.3

            start_time = time.time()
            while True:
                elapsed = time.time() - start_time
                remaining_timeout = max(0.05, timeout - elapsed)

                line = self._read_line(timeout=remaining_timeout)
                if line is None:
                    logger.error(f"Таймаут при ожидании хода от Scan ({elapsed:.1f}с)")
                    return None

                logger.debug(f"Scan: {line}")

                if line.startswith("done"):
                    match = re.search(r'move=([\d\-x]+)', line)
                    if match:
                        move = match.group(1)
                        logger.info(f"Получен ход: {move}")
                        return move
                    else:
                        logger.warning(f"Строка 'done' не содержит ход: {line}")
                        return None

                if not self._check_process_alive():
                    logger.error("Процесс Scan умер во время поиска")
                    return None

            return None

    def new_game(self) -> bool:
        with timer("ScanEngine.new_game"):  # TIMING ADDED
            if not self.initialized:
                return False
            if not self._check_process_alive():
                return False
            self._write_command("new-game\n")
            self._clear_queue()
            logger.debug("Отправлено: new-game")
            return True
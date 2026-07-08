# modules/timing.py
import time
from contextlib import contextmanager, asynccontextmanager
from logger import logger

@contextmanager
def timer(name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.debug(f"[TIMING] {name} took {elapsed:.4f}s")

@asynccontextmanager
async def async_timer(name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.debug(f"[TIMING] {name} took {elapsed:.4f}s")
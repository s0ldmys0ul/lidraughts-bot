from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    scan_path: str = Field(..., validation_alias='SCAN_PATH')
    scan_dir: str = Field(..., validation_alias='SCAN_DIR')
    move_time: float = Field(0.3, validation_alias='MOVE_TIME')
    delay_after_move: float = Field(0.1, validation_alias='DELAY_AFTER_MOVE')
    max_consecutive_errors: int = Field(2, validation_alias='MAX_CONSECUTIVE_ERRORS')
    log_level: str = Field('INFO', validation_alias='LOG_LEVEL')
    headless: bool = Field(False, validation_alias='HEADLESS')
    time_think_threshold: float = Field(8.0, validation_alias='TIME_THINK_THRESHOLD')
    think_time_min: float = Field(0.05, validation_alias='THINK_TIME_MIN')
    think_time_max: float = Field(0.35, validation_alias='THINK_TIME_MAX')
    
    # 🆕 Новые настройки для человеческих задержек
    fast_moves_count: int = Field(10, validation_alias='FAST_MOVES_COUNT')
    urgent_time_threshold: float = Field(13.0, validation_alias='URGENT_TIME_THRESHOLD')
    capture_delay_min: float = Field(0.05, validation_alias='CAPTURE_DELAY_MIN')
    capture_delay_max: float = Field(0.20, validation_alias='CAPTURE_DELAY_MAX')
        # 🆕🆕 Диапазон задержки для режима mt ≤ 0.1
    think_time_fast_min: float = Field(0, validation_alias='THINK_TIME_FAST_MIN')
    think_time_fast_max: float = Field(0, validation_alias='THINK_TIME_FAST_MAX')
    
    model_config = {
        'env_file': '.env',
        'env_file_encoding': 'utf-8',
        'case_sensitive': False,
        'extra': 'ignore'
    }

settings = Settings()

if __name__ == '__main__':
    print('Текущие настройки:')
    print(f'  scan_path = {settings.scan_path}')
    print(f'  scan_dir = {settings.scan_dir}')
    print(f'  move_time = {settings.move_time}')
    print(f'  delay_after_move = {settings.delay_after_move}')
    print(f'  max_consecutive_errors = {settings.max_consecutive_errors}')
    print(f'  log_level = {settings.log_level}')
    print(f'  headless = {settings.headless}')
    print(f'  time_think_threshold = {settings.time_think_threshold}')
    print(f'  think_time_min = {settings.think_time_min}')
    print(f'  think_time_max = {settings.think_time_max}')
    print(f'  fast_moves_count = {settings.fast_moves_count}')
    print(f'  urgent_time_threshold = {settings.urgent_time_threshold}')
    print(f'  capture_delay_min = {settings.capture_delay_min}')
    print(f'  capture_delay_max = {settings.capture_delay_max}')
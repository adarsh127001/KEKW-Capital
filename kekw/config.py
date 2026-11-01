from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    twitch_bot_token: str = ""
    twitch_client_id: str = ""
    twitch_bot_username: str = ""
    openai_api_key: str = ""
    db_path: str = "kekw.sqlite3"
    candle_bucket_seconds: int = 5
    ema_fast_alpha: float = 0.3
    ema_slow_alpha: float = 0.01
    k1: float = 0.05
    k2: float = 0.14
    k1_min: float = 0.0
    k1_max: float = 0.25
    k2_min: float = 0.0
    k2_max: float = 0.25
    earn_tendies_per_minute: int = 1
    earn_cap_per_stream: int = 20
    trade_limit_seconds: int = 5
    settle_key: str = ""

    @classmethod
    def from_env(cls):
        from pathlib import Path
        file_values={}
        env_file=Path(".env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line=line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key,value=line.split("=",1); file_values[key.strip()]=value.strip().strip('"').strip("'")
        def setting(key,default=""): return os.getenv(key,file_values.get(key,default))
        def val(key, default, cast):
            raw = setting("KEKW_" + key.upper())
            return cast(raw) if raw else default
        return cls(
            twitch_bot_token=setting("TWITCH_BOT_TOKEN"),
            twitch_client_id=setting("TWITCH_CLIENT_ID"),
            twitch_bot_username=setting("TWITCH_BOT_USERNAME"),
            openai_api_key=setting("OPENAI_API_KEY"),
            settle_key=setting("KEKW_SETTLE_KEY"),
            db_path=setting("KEKW_DB_PATH","kekw.sqlite3"),
            candle_bucket_seconds=val("candle_bucket_seconds", 5, int),
            ema_fast_alpha=val("ema_fast_alpha", .3, float),
            ema_slow_alpha=val("ema_slow_alpha", .01, float),
            k1=val("k1", .05, float), k2=val("k2", .14, float),
            k1_min=val("k1_min", 0., float), k1_max=val("k1_max", .25, float),
            k2_min=val("k2_min", 0., float), k2_max=val("k2_max", .25, float),
            earn_tendies_per_minute=val("earn_tendies_per_minute", 1, int),
            earn_cap_per_stream=val("earn_cap_per_stream", 20, int),
            trade_limit_seconds=val("trade_limit_seconds", 5, int))

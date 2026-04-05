import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    elevenlabs_api_key: str = ""
    elevenlabs_model: str = "eleven_v3"
    elevenlabs_speaker_a_voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
    elevenlabs_speaker_b_voice_id: str = "Aw4FAjKCGjjNkVhN1Xmq"
    upload_dir: str = "backend/data/uploads"
    audio_dir: str = "backend/storage/audio"
    transcript_dir: str = "backend/data/transcripts"
    events_db_path: str = "backend/data/events.db"
    app_state_path: str = "backend/data/app_state.json"
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

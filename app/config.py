from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:8b"

    # app/prompts/rag/<versiyon>.yaml
    rag_prompt_version: str = "v2"

    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    chroma_dir: str = "data/chroma"
    chroma_collection: str = "kurumsal_docs"

    chunk_size: int = 1000
    chunk_overlap: int = 150

    top_k: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()

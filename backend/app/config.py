from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    minimax_token_plan_key: str = ""
    minimax_api_key: str = ""
    minimax_group_id: str = ""
    minimax_base_url: str = "https://api.minimaxi.com"
    frontend_origin: str = "http://localhost:5173"

    @property
    def minimax_effective_api_key(self) -> str:
        return self.minimax_token_plan_key or self.minimax_api_key

    @property
    def minimax_key_source(self) -> str:
        if self.minimax_token_plan_key:
            return "MINIMAX_TOKEN_PLAN_KEY"
        if self.minimax_api_key:
            return "MINIMAX_API_KEY"
        return ""


settings = Settings()

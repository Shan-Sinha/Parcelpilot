from typing import Optional
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_deployment_name: str = "gpt-4o"
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    secret_key: str = "parcelpilot-jwt-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Directories — all overridable via env vars for Render/Docker deployment
    base_dir: Path = Path(__file__).parent.parent
    docs_dir: Optional[str] = None   # env DOCS_DIR overrides; defaults to parent of backend/
    data_dir: Optional[str] = None   # env DATA_DIR overrides
    chroma_persist_dir: Optional[str] = None   # env CHROMA_DIR overrides
    sqlite_db_path: Optional[str] = None   # env SQLITE_DB_PATH overrides

    @property
    def resolved_docs_dir(self) -> Path:
        return Path(self.docs_dir) if self.docs_dir else self.base_dir.parent

    @property
    def resolved_data_dir(self) -> Path:
        return Path(self.data_dir) if self.data_dir else (self.base_dir / "data")

    @property
    def resolved_chroma_dir(self) -> str:
        return self.chroma_persist_dir if self.chroma_persist_dir else str(self.base_dir / "data" / "chroma")

    @property
    def resolved_sqlite_path(self) -> str:
        return self.sqlite_db_path if self.sqlite_db_path else str(self.base_dir / "data" / "parcelpilot.db")

    model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Source reliability metadata — lower number = higher authority
SOURCE_RELIABILITY = {
    "05_Northstar_Logistics_Enterprise_Agreement.pdf": {
        "priority": 1,
        "label": "Enterprise Agreement",
        "badge": "contract",
        "customer_scope": "northstar",
        "is_deprecated": False,
        "trust": "high",
    },
    "06_LumenWorks_Service_Agreement.pdf": {
        "priority": 1,
        "label": "Service Agreement",
        "badge": "contract",
        "customer_scope": "lumenworks",
        "is_deprecated": False,
        "trust": "high",
    },
    "01_Support_Policy_v3_CURRENT.pdf": {
        "priority": 2,
        "label": "Support Policy v3 (Current)",
        "badge": "policy",
        "customer_scope": None,
        "is_deprecated": False,
        "trust": "high",
    },
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf": {
        "priority": 3,
        "label": "Cancellation & Credit SOP v4",
        "badge": "sop",
        "customer_scope": None,
        "is_deprecated": False,
        "trust": "high",
    },
    "04_Product_Operations_Guide_and_Known_Issues.pdf": {
        "priority": 4,
        "label": "Product Operations Guide",
        "badge": "guide",
        "customer_scope": None,
        "is_deprecated": False,
        "trust": "medium",
    },
    "02_Support_Policy_v2_DEPRECATED.pdf": {
        "priority": 5,
        "label": "Support Policy v2 (DEPRECATED)",
        "badge": "deprecated",
        "customer_scope": None,
        "is_deprecated": True,
        "trust": "low",
    },
}

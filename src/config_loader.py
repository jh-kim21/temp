import yaml
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ColumnMapping:
    excel_name: str
    dto_field: str


@dataclass
class ExcelConfig:
    sheet_name: Optional[str]
    text_columns: List[ColumnMapping]


@dataclass
class ApiConfig:
    base_url: str
    endpoint: str
    timeout: int
    stop_on_error: bool


@dataclass
class AppConfig:
    excel: ExcelConfig
    api: ApiConfig


def load_config(config_path: str = "config/config.yaml") -> AppConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    excel_raw = raw["excel"]
    text_columns = [
        ColumnMapping(excel_name=col["excel_name"], dto_field=col["dto_field"])
        for col in excel_raw.get("text_columns", [])
    ]
    excel = ExcelConfig(
        sheet_name=excel_raw.get("sheet_name"),
        text_columns=text_columns,
    )

    api_raw = raw["api"]
    api = ApiConfig(
        base_url=api_raw["base_url"],
        endpoint=api_raw["endpoint"],
        timeout=api_raw.get("timeout", 30),
        stop_on_error=api_raw.get("stop_on_error", False),
    )

    return AppConfig(excel=excel, api=api)

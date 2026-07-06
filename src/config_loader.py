import yaml
from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass
class ColumnMapping:
    excel_name: str
    dto_field: str


@dataclass
class ExcelConfig:
    sheet_name: Optional[str]
    text_columns: List[ColumnMapping]


@dataclass
class AuthConfig:
    login_endpoint: str
    username: str
    password: str
    token_json_path: str  # 응답 JSON 내 토큰 키 경로 (점으로 중첩 접근)


@dataclass
class ApiConfig:
    base_url: str
    endpoint: str
    timeout: int
    stop_on_error: bool
    ssl_verify: Union[bool, str]  # True / False / CA 인증서 파일 경로
    auth: Optional[AuthConfig]    # None이면 인증 없이 전송


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

    auth: Optional[AuthConfig] = None
    if "auth" in api_raw:
        a = api_raw["auth"]
        auth = AuthConfig(
            login_endpoint=a["login_endpoint"],
            username=a["username"],
            password=a["password"],
            token_json_path=a.get("token_json_path", "token"),
        )

    api = ApiConfig(
        base_url=api_raw["base_url"],
        endpoint=api_raw["endpoint"],
        timeout=api_raw.get("timeout", 30),
        stop_on_error=api_raw.get("stop_on_error", False),
        ssl_verify=api_raw.get("ssl_verify", True),
        auth=auth,
    )

    return AppConfig(excel=excel, api=api)

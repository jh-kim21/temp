import yaml
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union


@dataclass
class ColumnMapping:
    excel_name: str
    dto_field: str
    col_type: str = "string"  # "string" | "json_array"


@dataclass
class ExcelConfig:
    sheet_name: Optional[str]
    text_columns: List[ColumnMapping]


@dataclass
class AuthConfig:
    login_endpoint: str
    username: str
    password: str
    token_json_path: str


@dataclass
class ApiConfig:
    base_url: str
    endpoint: str
    timeout: int
    stop_on_error: bool
    ssl_verify: Union[bool, str]
    auth: Optional[AuthConfig]


@dataclass
class ProfileConfig:
    name: str
    endpoint: str
    excel: ExcelConfig


@dataclass
class AppConfig:
    api: ApiConfig          # endpoint는 프로파일 선택 전 placeholder
    profiles: List[ProfileConfig]

    def resolve(self, profile_name: str) -> Tuple[ExcelConfig, ApiConfig]:
        """프로파일 이름으로 (ExcelConfig, ApiConfig)를 반환한다."""
        profile = next((p for p in self.profiles if p.name == profile_name), None)
        if profile is None:
            available = [p.name for p in self.profiles]
            raise ValueError(
                f"프로파일 '{profile_name}'을 찾을 수 없습니다. "
                f"사용 가능: {available}"
            )
        resolved_api = ApiConfig(
            base_url=self.api.base_url,
            endpoint=profile.endpoint,
            timeout=self.api.timeout,
            stop_on_error=self.api.stop_on_error,
            ssl_verify=self.api.ssl_verify,
            auth=self.api.auth,
        )
        return profile.excel, resolved_api

    @property
    def profile_names(self) -> List[str]:
        return [p.name for p in self.profiles]


def load_config(config_path: str = "config/config.yaml") -> AppConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

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

    # endpoint는 프로파일에서 덮어쓰므로 여기서는 빈값으로 둔다
    api = ApiConfig(
        base_url=api_raw["base_url"],
        endpoint="",
        timeout=api_raw.get("timeout", 30),
        stop_on_error=api_raw.get("stop_on_error", False),
        ssl_verify=api_raw.get("ssl_verify", True),
        auth=auth,
    )

    profiles = [_parse_profile(p) for p in raw.get("profiles", [])]

    return AppConfig(api=api, profiles=profiles)


def _parse_profile(raw: dict) -> ProfileConfig:
    excel_raw = raw["excel"]
    text_columns = [
        ColumnMapping(
            excel_name=col["excel_name"],
            dto_field=col["dto_field"],
            col_type=col.get("type", "string"),
        )
        for col in excel_raw.get("text_columns", [])
    ]
    excel = ExcelConfig(
        sheet_name=excel_raw.get("sheet_name"),
        text_columns=text_columns,
    )
    return ProfileConfig(
        name=raw["name"],
        endpoint=raw["endpoint"],
        excel=excel,
    )

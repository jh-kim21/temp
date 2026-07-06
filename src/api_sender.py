import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config_loader import ApiConfig, AuthConfig
from .image_extractor import detect_mime_type

logger = logging.getLogger(__name__)


def send_rows(rows: List[Dict[str, Any]], api_config: ApiConfig) -> None:
    """각 행 데이터를 multipart/form-data 형식으로 Spring Boot API에 전송한다."""
    url = f"{api_config.base_url.rstrip('/')}{api_config.endpoint}"
    logger.info(f"{len(rows)}개 행을 {url} 에 전송합니다.")

    if api_config.ssl_verify is False:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logger.warning("SSL 인증서 검증이 비활성화되어 있습니다.")

    # JWT 로그인 (설정된 경우)
    token: Optional[str] = None
    if api_config.auth:
        token = _login(api_config)
        logger.info("JWT 토큰 획득 완료")

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    success = 0
    errors = 0

    for i, row in enumerate(rows, start=1):
        logger.info(f"[{i}/{len(rows)}] 전송 중...")
        try:
            _send_single_row(url, row, api_config.timeout, api_config.ssl_verify, headers)
            success += 1
            logger.info(f"[{i}/{len(rows)}] 성공")
        except requests.HTTPError as e:
            errors += 1
            logger.error(
                f"[{i}/{len(rows)}] HTTP 오류 {e.response.status_code}: "
                f"{e.response.text[:200]}"
            )
            if api_config.stop_on_error:
                raise
        except Exception as e:
            errors += 1
            logger.error(f"[{i}/{len(rows)}] 오류: {e}")
            if api_config.stop_on_error:
                raise

    logger.info(f"전송 완료 | 성공: {success} / 실패: {errors} / 전체: {len(rows)}")


def _login(api_config: ApiConfig) -> str:
    """로그인 API를 호출하여 JWT 토큰을 반환한다."""
    auth = api_config.auth
    login_url = f"{api_config.base_url.rstrip('/')}{auth.login_endpoint}"
    logger.info(f"로그인 요청: {login_url}")

    response = requests.post(
        login_url,
        json={"username": auth.username, "password": auth.password},
        timeout=api_config.timeout,
        verify=api_config.ssl_verify,
    )
    response.raise_for_status()

    return _extract_token(response.json(), auth.token_json_path)


def _extract_token(data: dict, json_path: str) -> str:
    """점(.) 구분 경로로 중첩 JSON에서 토큰 값을 추출한다.
    예) token_json_path="data.accessToken" → data["data"]["accessToken"]
    """
    value = data
    for key in json_path.split("."):
        if not isinstance(value, dict) or key not in value:
            raise KeyError(
                f"로그인 응답에서 토큰 경로 '{json_path}'를 찾을 수 없습니다. "
                f"응답: {data}"
            )
        value = value[key]
    return str(value)


def _send_single_row(
    url: str,
    row: Dict[str, Any],
    timeout: int,
    ssl_verify,
    headers: Dict[str, str],
) -> None:
    """단일 행을 multipart/form-data로 전송한다."""
    data: Dict[str, str] = {k: v for k, v in row.items() if k != "files"}

    image_entries: List[Tuple[str, bytes]] = row.get("files", [])
    multipart_files = [
        ("files", (filename, img_bytes, detect_mime_type(img_bytes)))
        for filename, img_bytes in image_entries
    ]

    response = requests.post(
        url,
        data=data,
        files=multipart_files if multipart_files else None,
        headers=headers,
        timeout=timeout,
        verify=ssl_verify,
    )
    response.raise_for_status()

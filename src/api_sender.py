import logging
from typing import Any, Dict, List, Tuple

import requests

from .config_loader import ApiConfig
from .image_extractor import detect_mime_type

logger = logging.getLogger(__name__)


def send_rows(rows: List[Dict[str, Any]], api_config: ApiConfig) -> None:
    """각 행 데이터를 multipart/form-data 형식으로 Spring Boot API에 전송한다."""
    url = f"{api_config.base_url.rstrip('/')}{api_config.endpoint}"
    logger.info(f"{len(rows)}개 행을 {url} 에 전송합니다.")

    success = 0
    errors = 0

    for i, row in enumerate(rows, start=1):
        logger.info(f"[{i}/{len(rows)}] 전송 중...")
        try:
            _send_single_row(url, row, api_config.timeout)
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


def _send_single_row(url: str, row: Dict[str, Any], timeout: int) -> None:
    """단일 행을 multipart/form-data로 전송한다."""
    # 텍스트 필드
    data: Dict[str, str] = {k: v for k, v in row.items() if k != "files"}

    # 이미지 파일 — 동일한 필드명 'files'로 복수 파일 전송
    image_entries: List[Tuple[str, bytes]] = row.get("files", [])
    multipart_files = [
        ("files", (_rename_for_row(filename, i), img_bytes, detect_mime_type(img_bytes)))
        for i, (filename, img_bytes) in enumerate(image_entries)
    ]

    response = requests.post(
        url,
        data=data,
        files=multipart_files if multipart_files else None,
        timeout=timeout,
    )
    response.raise_for_status()


def _rename_for_row(original_filename: str, index: int) -> str:
    """같은 이름의 이미지가 여러 행에 걸쳐 존재할 경우를 위해 인덱스를 부여한다."""
    # Excel 내부 미디어 파일명(예: image1.png)이 행마다 달라지지 않으므로
    # 원본 파일명을 그대로 사용한다 (Spring Boot가 파일명을 기준으로 처리할 경우 대비).
    return original_filename

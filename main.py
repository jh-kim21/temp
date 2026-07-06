import argparse
import logging
import sys
from pathlib import Path

from src.config_loader import load_config
from src.excel_parser import parse_excel
from src.api_sender import send_rows


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Excel 파일을 파싱하여 Spring Boot API로 전송합니다."
    )
    parser.add_argument("excel_file", help="처리할 Excel(.xlsx) 파일 경로")
    parser.add_argument(
        "--profile", "-p",
        required=True,
        help="사용할 프로파일 이름 (config.yaml의 profiles[].name)",
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="설정 파일 경로 (기본값: config/config.yaml)",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="사용 가능한 프로파일 목록을 출력하고 종료합니다.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파싱만 수행하고 API 전송은 건너뜁니다.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )
    return parser


def main() -> None:
    # --list-profiles는 --profile 없이도 동작해야 하므로 먼저 처리
    if "--list-profiles" in sys.argv:
        _handle_list_profiles()
        return

    args = build_parser().parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    excel_path = Path(args.excel_file)
    if not excel_path.exists():
        logger.error(f"Excel 파일을 찾을 수 없습니다: {excel_path}")
        sys.exit(1)

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)

    logger.info(f"설정 로드: {config_path}")
    app_config = load_config(str(config_path))

    try:
        excel_config, api_config = app_config.resolve(args.profile)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info(f"프로파일: {args.profile} → endpoint: {api_config.endpoint}")

    logger.info(f"Excel 파싱: {excel_path}")
    rows = parse_excel(str(excel_path), excel_config, api_config)

    if not rows:
        logger.warning("처리할 데이터 행이 없습니다.")
        return

    logger.info(f"파싱된 행 수: {len(rows)}")

    if args.dry_run:
        logger.info("=== Dry-run 모드: API 전송을 건너뜁니다 ===")
        for i, row in enumerate(rows, start=1):
            files_info = [name for name, _ in row.get("files", [])]
            text_fields = {k: v for k, v in row.items() if k != "files"}
            logger.info(f"  행 {i}: {text_fields} | 이미지: {files_info}")
        return

    send_rows(rows, api_config)


def _handle_list_profiles() -> None:
    """--list-profiles 전용 처리: --profile 없이 실행 가능."""
    import argparse as _ap
    p = _ap.ArgumentParser(add_help=False)
    p.add_argument("excel_file", nargs="?")
    p.add_argument("--config", default="config/config.yaml")
    p.add_argument("--list-profiles", action="store_true")
    p.add_argument("--profile", "-p", default=None)
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    setup_logging(args.verbose)
    app_config = load_config(args.config)
    print("사용 가능한 프로파일:")
    for name in app_config.profile_names:
        print(f"  - {name}")


if __name__ == "__main__":
    main()

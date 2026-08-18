from __future__ import annotations

import os
import sys

from ipost.settings import get_settings


def main() -> None:
    live = os.getenv("IPOST_LIVE", "").lower() in {"1", "true", "yes"}
    settings = get_settings()
    if not live or settings.ipost_mock_bedrock:
        print("test_full skipped: set IPOST_LIVE=1 and IPOST_MOCK_BEDROCK=false to call Bedrock.")
        print("That uses your existing Bedrock access; it does not create AWS resources.")
        sys.exit(0)

    from ipost.agents.test_simple import test_story_handler

    print("Testing iPost agents against Bedrock (Nova Pro + Nova Canvas)")
    print("=" * 60)
    test_story_handler()
    print("=" * 60)
    print("test_full passed")


if __name__ == "__main__":
    main()

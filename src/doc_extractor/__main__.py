"""Allow ``python -m doc_extractor`` without an installed console wrapper."""

from .cli import main

raise SystemExit(main())

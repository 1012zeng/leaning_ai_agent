"""Allow `python -m rag_lab` execution without installation."""

from rag_lab.cli import main

raise SystemExit(main())

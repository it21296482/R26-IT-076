from __future__ import annotations

import sys
from pathlib import Path


COMPONENT_ROOT = Path(__file__).resolve().parent.parent
if str(COMPONENT_ROOT) not in sys.path:
    sys.path.insert(0, str(COMPONENT_ROOT))

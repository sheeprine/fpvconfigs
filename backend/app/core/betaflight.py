import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class BetaflightConfig:
    betaflight_version: Optional[str]
    msp_api: Optional[str]
    config_revision: Optional[str]
    board_name: Optional[str]
    manufacturer_id: Optional[str]
    craft_name: Optional[str]
    pilot_name: Optional[str]


# Pattern for the Betaflight version header line
# e.g.: # Betaflight / STM32H743 (H743) 2026.6.1 Aug  3 2026 / 08:48:14 (6dbc4218f) MSP API: 1.48
VERSION_HEADER_RE = re.compile(
    r"#\s+Betaflight\s*/\s*\S+\s+\([^)]+\)\s+(\d+\.\d+(?:\.\d+)?)"
    r".*?MSP API:\s*(\S+)",
    re.IGNORECASE,
)

# Alternative: older format without parenthesized target
VERSION_HEADER_ALT_RE = re.compile(
    r"#\s+Betaflight\s*/\s*\S+\s+(\d+\.\d+(?:\.\d+)?)"
    r".*?MSP API:\s*(\S+)",
    re.IGNORECASE,
)

CONFIG_REVISION_RE = re.compile(r"#\s+config rev:\s*(\S+)", re.IGNORECASE)
BOARD_NAME_RE = re.compile(r"^board_name\s+(\S+)", re.MULTILINE)
MANUFACTURER_ID_RE = re.compile(r"^manufacturer_id\s+(\S+)", re.MULTILINE)

# craft_name can appear as:
#   set craft_name = ERA5
#   name ERA5   (older format)
#   # name: ERA5
CRAFT_NAME_SET_RE = re.compile(r"^set\s+craft_name\s*=\s*(.+)$", re.MULTILINE)
CRAFT_NAME_COMMENT_RE = re.compile(r"^#\s+name:\s*(.+)$", re.MULTILINE)
CRAFT_NAME_CMD_RE = re.compile(r"^name\s+(.+)$", re.MULTILINE)

# pilot_name: set pilot_name = UBR
PILOT_NAME_RE = re.compile(r"^set\s+pilot_name\s*=\s*(.+)$", re.MULTILINE)


def _extract_craft_name(text: str) -> Optional[str]:
    """Try multiple patterns to extract craft name."""
    for pattern in (CRAFT_NAME_SET_RE, CRAFT_NAME_COMMENT_RE, CRAFT_NAME_CMD_RE):
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    return None


def parse_betaflight_config(content: str) -> Optional[BetaflightConfig]:
    """
    Parse a Betaflight CLI backup config file.

    Returns a BetaflightConfig dataclass or None if the content is not a valid
    Betaflight config (missing the version header line).

    Validation rules:
    - Must contain the Betaflight version header line starting with '# Betaflight'
    - Must contain either 'batch start' or 'board_name' to confirm it's a CLI dump
    """
    # Primary validation: must have the version header
    version_match = VERSION_HEADER_RE.search(content)
    if version_match is None:
        version_match = VERSION_HEADER_ALT_RE.search(content)
    if version_match is None:
        return None

    # Secondary validation: must look like a CLI dump
    has_batch_start = "batch start" in content
    has_board_name = bool(BOARD_NAME_RE.search(content))
    if not (has_batch_start or has_board_name):
        return None

    betaflight_version = version_match.group(1).strip()
    msp_api = version_match.group(2).strip() if version_match.lastindex >= 2 else None

    config_rev_match = CONFIG_REVISION_RE.search(content)
    config_revision = config_rev_match.group(1).strip() if config_rev_match else None

    board_match = BOARD_NAME_RE.search(content)
    board_name = board_match.group(1).strip() if board_match else None

    mfr_match = MANUFACTURER_ID_RE.search(content)
    manufacturer_id = mfr_match.group(1).strip() if mfr_match else None

    craft_name = _extract_craft_name(content)

    pilot_match = PILOT_NAME_RE.search(content)
    pilot_name = pilot_match.group(1).strip() if pilot_match else None

    return BetaflightConfig(
        betaflight_version=betaflight_version,
        msp_api=msp_api,
        config_revision=config_revision,
        board_name=board_name,
        manufacturer_id=manufacturer_id,
        craft_name=craft_name,
        pilot_name=pilot_name,
    )


def is_valid_betaflight_config(content: str) -> bool:
    """Return True if the content appears to be a valid Betaflight config."""
    return parse_betaflight_config(content) is not None

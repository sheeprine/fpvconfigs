import pytest
from app.core.betaflight import BetaflightConfig, is_valid_betaflight_config, parse_betaflight_config

# ---------------------------------------------------------------------------
# Fixtures / constants
# ---------------------------------------------------------------------------

FULL_CONFIG = """\

# version
# Betaflight / STM32H743 (H743) 2026.6.1 Aug  3 2026 / 08:48:14 (6dbc4218f) MSP API: 1.48
# config rev: 749fff1

# start the command batch
batch start

# reset configuration to default settings
defaults nosave

board_name MATEKH743
manufacturer_id MTKS
mcu_id 0023003b3230510131303832

# name: ERA5

set craft_name = ERA5
set pilot_name = UBR

# save configuration
save
"""

MINIMAL_CONFIG = """\
# Betaflight / STM32H743 (H743) 4.4.3 / MSP API: 1.45
batch start
board_name TESTBOARD
"""


# ---------------------------------------------------------------------------
# parse_betaflight_config – valid inputs
# ---------------------------------------------------------------------------


class TestParseValidConfig:
    def test_extracts_betaflight_version(self):
        result = parse_betaflight_config(FULL_CONFIG)
        assert result is not None
        assert result.betaflight_version == "2026.6.1"

    def test_extracts_msp_api(self):
        result = parse_betaflight_config(FULL_CONFIG)
        assert result is not None
        assert result.msp_api == "1.48"

    def test_extracts_config_revision(self):
        result = parse_betaflight_config(FULL_CONFIG)
        assert result is not None
        assert result.config_revision == "749fff1"

    def test_extracts_board_name(self):
        result = parse_betaflight_config(FULL_CONFIG)
        assert result is not None
        assert result.board_name == "MATEKH743"

    def test_extracts_manufacturer_id(self):
        result = parse_betaflight_config(FULL_CONFIG)
        assert result is not None
        assert result.manufacturer_id == "MTKS"

    def test_extracts_craft_name_from_set_command(self):
        result = parse_betaflight_config(FULL_CONFIG)
        assert result is not None
        assert result.craft_name == "ERA5"

    def test_extracts_pilot_name(self):
        result = parse_betaflight_config(FULL_CONFIG)
        assert result is not None
        assert result.pilot_name == "UBR"

    def test_returns_betaflight_config_dataclass(self):
        result = parse_betaflight_config(FULL_CONFIG)
        assert isinstance(result, BetaflightConfig)

    def test_minimal_config_accepted(self):
        result = parse_betaflight_config(MINIMAL_CONFIG)
        assert result is not None
        assert result.board_name == "TESTBOARD"

    def test_minimal_config_missing_fields_are_none(self):
        result = parse_betaflight_config(MINIMAL_CONFIG)
        assert result is not None
        assert result.config_revision is None
        assert result.manufacturer_id is None
        assert result.craft_name is None
        assert result.pilot_name is None

    def test_batch_start_without_board_name_is_accepted(self):
        content = (
            "# Betaflight / STM32H743 (H743) 4.4.0 / MSP API: 1.44\n"
            "batch start\n"
        )
        assert parse_betaflight_config(content) is not None

    def test_board_name_without_batch_start_is_accepted(self):
        content = (
            "# Betaflight / STM32H743 (H743) 4.4.0 / MSP API: 1.44\n"
            "board_name SOMEBOARD\n"
        )
        assert parse_betaflight_config(content) is not None

    def test_version_without_parenthesized_target(self):
        content = (
            "# Betaflight / STM32F405 4.3.0 Aug 25 2021 / MSP API: 1.44\n"
            "batch start\n"
        )
        result = parse_betaflight_config(content)
        assert result is not None
        assert result.betaflight_version == "4.3.0"


# ---------------------------------------------------------------------------
# craft_name extraction – alternative patterns
# ---------------------------------------------------------------------------


class TestCraftNameExtraction:
    def _base(self, extra: str) -> str:
        return (
            "# Betaflight / STM32H743 (H743) 4.4.3 / MSP API: 1.45\n"
            "batch start\n"
            + extra
        )

    def test_craft_name_from_set_command(self):
        config = self._base("set craft_name = MYQUAD\n")
        result = parse_betaflight_config(config)
        assert result is not None
        assert result.craft_name == "MYQUAD"

    def test_craft_name_from_comment_name(self):
        config = self._base("# name: COMMENTCRAFT\n")
        result = parse_betaflight_config(config)
        assert result is not None
        assert result.craft_name == "COMMENTCRAFT"

    def test_craft_name_from_bare_name_command(self):
        config = self._base("name BARECRAFT\n")
        result = parse_betaflight_config(config)
        assert result is not None
        assert result.craft_name == "BARECRAFT"

    def test_set_craft_name_takes_priority_over_comment(self):
        config = self._base("# name: COMMENT\nset craft_name = SETNAME\n")
        result = parse_betaflight_config(config)
        assert result is not None
        assert result.craft_name == "SETNAME"

    def test_craft_name_with_spaces_trimmed(self):
        config = self._base("set craft_name =   SPACED   \n")
        result = parse_betaflight_config(config)
        assert result is not None
        assert result.craft_name == "SPACED"


# ---------------------------------------------------------------------------
# parse_betaflight_config – invalid inputs
# ---------------------------------------------------------------------------


class TestParseInvalidConfig:
    def test_empty_string_returns_none(self):
        assert parse_betaflight_config("") is None

    def test_no_betaflight_header_returns_none(self):
        content = "batch start\nboard_name TESTBOARD\n"
        assert parse_betaflight_config(content) is None

    def test_random_text_returns_none(self):
        assert parse_betaflight_config("hello world\nthis is not a config\n") is None

    def test_betaflight_header_without_batch_or_board_returns_none(self):
        content = "# Betaflight / STM32H743 (H743) 4.4.3 / MSP API: 1.45\n# just a comment\n"
        assert parse_betaflight_config(content) is None

    def test_partial_header_without_msp_api(self):
        content = "# Betaflight / STM32H743 (H743) 4.4.3\nbatch start\n"
        result = parse_betaflight_config(content)
        # Must at least have batch start; alt regex without MSP API shouldn't match version+msp
        # behavior: either None or parsed without msp_api – both acceptable; just no crash
        # The important thing is it doesn't raise
        assert result is None or isinstance(result, BetaflightConfig)


# ---------------------------------------------------------------------------
# is_valid_betaflight_config
# ---------------------------------------------------------------------------


class TestIsValid:
    def test_valid_config_returns_true(self):
        assert is_valid_betaflight_config(FULL_CONFIG) is True

    def test_invalid_config_returns_false(self):
        assert is_valid_betaflight_config("not a config") is False

    def test_empty_string_returns_false(self):
        assert is_valid_betaflight_config("") is False

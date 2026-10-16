"""Build the printable fixture so tests work in a fresh source checkout."""
import pytest

from calib_board.common import DEFAULT_SPEC
from calib_board.generate import generate


@pytest.fixture(scope='session', autouse=True)
def printable_board():
    generate(DEFAULT_SPEC, 'build/board_v1_1_A3.pdf', preview=False)

"""parse_route / format_route: conversão do texto digitado em geometria."""

import pytest

from app.core import MAX_ROUTE_POINTS, format_route, parse_route

POINTS = [[-10.7001, -37.4101], [-10.7012942, -37.4131006]]


def test_one_point_per_line():
    assert parse_route("-10.7001, -37.4101\n-10.7012942, -37.4131006") == POINTS


@pytest.mark.parametrize(
    "text",
    [
        "-10.7001 -37.4101\n-10.7012942 -37.4131006",        # espaço
        "-10.7001;-37.4101\r\n-10.7012942;-37.4131006\r\n",  # ponto e vírgula, CRLF
        "\n  -10.7001,-37.4101  \n\n-10.7012942,-37.4131006\n\n",  # linhas em branco
    ],
    ids=["spaces", "semicolon-crlf", "blank-lines"],
)
def test_separators_and_blank_lines_are_tolerated(text):
    assert parse_route(text) == POINTS


def test_json_array():
    assert parse_route("[[-10.7001, -37.4101], [-10.7012942, -37.4131006]]") == POINTS
    assert parse_route('[["-10.7001", "-37.4101"], [-10.7012942, -37.4131006]]') == POINTS


@pytest.mark.parametrize("empty", ["", "   ", "\n\n", None])
def test_empty_means_no_route(empty):
    assert parse_route(empty) == []


@pytest.mark.parametrize(
    "bad",
    ["1, 1", "1, 1\n2", "a, b\nc, d", "1, 2, 3\n4, 5, 6", "91, 0\n1, 1", "[[1, 2]]",
     "[[1, 2], [3, 4, 5]]", "[1, 2]", "[[1, 2], [3", "[[null, 1], [2, 3]]"],
)
def test_invalid_input_raises_value_error(bad):
    with pytest.raises(ValueError):
        parse_route(bad)


def test_point_limit():
    at_limit = "\n".join("1, 1" for _ in range(MAX_ROUTE_POINTS))
    assert len(parse_route(at_limit)) == MAX_ROUTE_POINTS
    with pytest.raises(ValueError):
        parse_route(at_limit + "\n1, 1")


def test_error_messages_point_at_the_problem():
    with pytest.raises(ValueError, match="Linha 2"):
        parse_route("1, 1\nsó-uma-coisa")
    with pytest.raises(ValueError, match="Ponto 2"):
        parse_route("1, 1\n200, 1")


def test_format_is_the_inverse_of_parse():
    import json

    assert format_route(json.dumps(POINTS)) == "-10.7001, -37.4101\n-10.7012942, -37.4131006"
    assert parse_route(format_route(json.dumps(POINTS))) == POINTS


@pytest.mark.parametrize("stored", [None, "", "isto nao e json", "{}", '"texto"', "123"])
def test_format_tolerates_broken_stored_values(stored):
    assert format_route(stored) == ""

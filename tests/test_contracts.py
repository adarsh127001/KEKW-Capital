import pytest

from kekw.market.contracts import PrimeTime, Wager


@pytest.mark.parametrize("winning_size", range(26))
@pytest.mark.parametrize("losing_size", range(26))
def test_settlement_math_pays_winners_and_burns_loser_tax(winning_size, losing_size):
    bets = [
        Wager("winner", "DUEL_YES", winning_size),
        Wager("loser", "DUEL_NO", losing_size),
    ]

    result = PrimeTime.settlement_math(bets, "DUEL_YES", "DUEL_NO", "DUEL_YES")

    assert result["payouts"] == {"winner": pytest.approx(winning_size * 1.9)}
    assert result["losing_stake"] == pytest.approx(losing_size)
    assert result["burned"] == pytest.approx(losing_size * 0.10)

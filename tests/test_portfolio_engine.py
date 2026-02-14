import unittest
from decimal import Decimal

from engines.portfolio_config import BALANCED_CONFIG, CONSERVATIVE_CONFIG
from engines.portfolio_engine import allocate_weights, filter_signals_for_portfolio, score_and_rank


class MockSignal:
    def __init__(self, symbol, action, consensus, agent_votes, sector, entry=100, stop=90, target=120, is_egx30=True):
        self.stock_symbol = symbol
        self.stock_name_ar = symbol
        self.action = action
        self.consensus_score = consensus
        self.agent_votes = agent_votes
        self.sector = sector
        self.entry_price = Decimal(str(entry))
        self.stop_loss_price = Decimal(str(stop))
        self.target_price = Decimal(str(target))
        self.is_egx30 = is_egx30


class TestConstraintValidation(unittest.TestCase):
    def test_single_stock_never_exceeds_max(self):
        config = CONSERVATIVE_CONFIG
        signals = [
            MockSignal("COMI.CA", "strong_buy", 0.9, {"a": "buy", "b": "buy", "c": "buy"}, "Banking"),
            MockSignal("HRHO.CA", "strong_buy", 0.85, {"a": "buy", "b": "buy", "c": "buy"}, "Banking"),
        ]
        filtered = filter_signals_for_portfolio(signals, config)
        scored = score_and_rank(filtered)
        allocation = allocate_weights(scored, config)
        for alloc in allocation.allocations:
            self.assertLessEqual(float(alloc["allocation"]), config.max_single_stock_pct)

    def test_allocations_sum_to_100(self):
        config = BALANCED_CONFIG
        signals = [
            MockSignal("COMI.CA", "strong_buy", 0.8, {"a": "buy", "b": "buy"}, "Banking"),
            MockSignal("HRHO.CA", "buy", 0.7, {"a": "buy", "b": "hold"}, "Banking"),
            MockSignal("SWDY.CA", "buy", 0.75, {"a": "buy", "b": "buy"}, "Energy"),
        ]
        filtered = filter_signals_for_portfolio(signals, config)
        scored = score_and_rank(filtered)
        allocation = allocate_weights(scored, config)
        total = sum(a["allocation"] for a in allocation.allocations) + allocation.cash_pct
        self.assertAlmostEqual(float(total), 100.0, places=1)

    def test_cash_floor_enforced(self):
        config = CONSERVATIVE_CONFIG
        signals = [MockSignal("COMI.CA", "strong_buy", 0.9, {"a": "buy", "b": "buy", "c": "buy"}, "Banking")]
        filtered = filter_signals_for_portfolio(signals, config)
        scored = score_and_rank(filtered)
        allocation = allocate_weights(scored, config)
        self.assertGreaterEqual(float(allocation.cash_pct), config.min_cash_pct)


class TestEdgeCases(unittest.TestCase):
    def test_no_active_signals(self):
        config = CONSERVATIVE_CONFIG
        allocation = allocate_weights([], config)
        self.assertEqual(len(allocation.allocations), 0)
        self.assertEqual(float(allocation.cash_pct), 100.0)

    def test_only_one_signal(self):
        config = BALANCED_CONFIG
        signals = [MockSignal("COMI.CA", "strong_buy", 0.9, {"a": "buy", "b": "buy"}, "Banking")]
        filtered = filter_signals_for_portfolio(signals, config)
        scored = score_and_rank(filtered)
        allocation = allocate_weights(scored, config)
        self.assertEqual(len(allocation.allocations), 1)
        self.assertGreater(float(allocation.cash_pct), 0)


if __name__ == "__main__":
    unittest.main()

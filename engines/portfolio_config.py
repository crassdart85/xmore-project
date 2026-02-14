from typing import List, Literal, Tuple

from pydantic import BaseModel


class PortfolioConfig(BaseModel):
    portfolio_type: str
    display_name_ar: str
    display_name_en: str
    max_stocks: Tuple[int, int]  # (min, max)
    min_cash_pct: int
    max_cash_pct: int
    allowed_signals: List[str]
    min_consensus_score: float
    min_agents_agree: int
    stock_universe: Literal["egx30", "egx30+midcap", "all"]
    max_single_stock_pct: int
    max_sector_pct: int
    rebalance_frequency: Literal["weekly", "biweekly", "monthly"]
    stop_loss_threshold_pct: int
    target_annual_return_range: Tuple[int, int]
    target_max_drawdown_pct: int


CONSERVATIVE_CONFIG = PortfolioConfig(
    portfolio_type="conservative",
    display_name_ar="الأمان",
    display_name_en="Al-Aman (The Safe)",
    max_stocks=(5, 8),
    min_cash_pct=30,
    max_cash_pct=50,
    allowed_signals=["strong_buy"],
    min_consensus_score=0.75,
    min_agents_agree=3,
    stock_universe="egx30",
    max_single_stock_pct=15,
    max_sector_pct=40,
    rebalance_frequency="monthly",
    stop_loss_threshold_pct=5,
    target_annual_return_range=(2, 5),
    target_max_drawdown_pct=8,
)

BALANCED_CONFIG = PortfolioConfig(
    portfolio_type="balanced",
    display_name_ar="الميزان",
    display_name_en="Al-Mizan (The Balance)",
    max_stocks=(8, 12),
    min_cash_pct=15,
    max_cash_pct=30,
    allowed_signals=["strong_buy", "buy"],
    min_consensus_score=0.50,
    min_agents_agree=2,
    stock_universe="egx30+midcap",
    max_single_stock_pct=20,
    max_sector_pct=40,
    rebalance_frequency="biweekly",
    stop_loss_threshold_pct=8,
    target_annual_return_range=(5, 12),
    target_max_drawdown_pct=15,
)

AGGRESSIVE_CONFIG = PortfolioConfig(
    portfolio_type="aggressive",
    display_name_ar="النمو",
    display_name_en="Al-Numu (The Growth)",
    max_stocks=(10, 15),
    min_cash_pct=5,
    max_cash_pct=15,
    allowed_signals=["strong_buy", "buy", "watch"],
    min_consensus_score=0.50,
    min_agents_agree=2,
    stock_universe="all",
    max_single_stock_pct=25,
    max_sector_pct=40,
    rebalance_frequency="weekly",
    stop_loss_threshold_pct=12,
    target_annual_return_range=(10, 20),
    target_max_drawdown_pct=22,
)

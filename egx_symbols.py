"""
Egyptian Exchange (EGX) Symbol Mapping and Utilities

This module provides comprehensive mapping for Egyptian stocks across different
data providers (Yahoo Finance, investpy) and utilities for working with EGX symbols.

Symbol Format Reference:
- Yahoo Finance: SYMBOL.CA (e.g., COMI.CA for CIB)
- investpy: Full company name in English
- Reuters: SYMBOL.CA
- Bloomberg: SYMBOL EY Equity

Top 30 EGX Stocks by Market Cap and Liquidity
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class EGXStock:
    """Represents an Egyptian stock with multi-provider symbol mapping."""
    ticker: str           # Local EGX ticker (e.g., COMI)
    yahoo: str            # Yahoo Finance symbol (e.g., COMI.CA)
    name_en: str          # English company name
    name_ar: str          # Arabic company name
    sector: str           # Business sector
    is_egx30: bool        # Part of EGX 30 index

# Comprehensive EGX Symbol Database
EGX_SYMBOL_DATABASE: Dict[str, EGXStock] = {
    # ============ BANKING & FINANCIAL SERVICES ============
    "COMI": EGXStock(
        ticker="COMI",
        yahoo="COMI.CA",
        name_en="Commercial International Bank (CIB)",
        name_ar="البنك التجاري الدولي",
        sector="Banking",
        is_egx30=True
    ),
    "HRHO": EGXStock(
        ticker="HRHO",
        yahoo="HRHO.CA",
        name_en="EFG Holding (Hermes)",
        name_ar="هيرميس القابضة",
        sector="Financial Services",
        is_egx30=True
    ),
    "FWRY": EGXStock(
        ticker="FWRY",
        yahoo="FWRY.CA",
        name_en="Fawry for Banking Technology",
        name_ar="فوري لتكنولوجيا البنوك",
        sector="Fintech",
        is_egx30=True
    ),
    "CIEB": EGXStock(
        ticker="CIEB",
        yahoo="CIEB.CA",
        name_en="Credit Agricole Egypt",
        name_ar="كريدي أجريكول مصر",
        sector="Banking",
        is_egx30=False
    ),

    # ============ REAL ESTATE & CONSTRUCTION ============
    "TMGH": EGXStock(
        ticker="TMGH",
        yahoo="TMGH.CA",
        name_en="Talaat Moustafa Group Holding",
        name_ar="طلعت مصطفى القابضة",
        sector="Real Estate",
        is_egx30=True
    ),
    "ORAS": EGXStock(
        ticker="ORAS",
        yahoo="ORAS.CA",
        name_en="Orascom Construction",
        name_ar="أوراسكوم للإنشاء",
        sector="Construction",
        is_egx30=True
    ),
    "PHDC": EGXStock(
        ticker="PHDC",
        yahoo="PHDC.CA",
        name_en="Palm Hills Development",
        name_ar="بالم هيلز للتعمير",
        sector="Real Estate",
        is_egx30=True
    ),
    "MNHD": EGXStock(
        ticker="MNHD",
        yahoo="MNHD.CA",
        name_en="Madinet Nasr Housing",
        name_ar="مدينة نصر للإسكان",
        sector="Real Estate",
        is_egx30=True
    ),
    "OCDI": EGXStock(
        ticker="OCDI",
        yahoo="OCDI.CA",
        name_en="Orascom Development",
        name_ar="أوراسكوم للتنمية",
        sector="Real Estate",
        is_egx30=True
    ),

    # ============ INDUSTRIAL & MANUFACTURING ============
    "SWDY": EGXStock(
        ticker="SWDY",
        yahoo="SWDY.CA",
        name_en="El Sewedy Electric",
        name_ar="السويدي إليكتريك",
        sector="Electrical Equipment",
        is_egx30=True
    ),
    "EAST": EGXStock(
        ticker="EAST",
        yahoo="EAST.CA",
        name_en="Eastern Company",
        name_ar="الشرقية للدخان",
        sector="Tobacco",
        is_egx30=True
    ),
    "EFIH": EGXStock(
        ticker="EFIH",
        yahoo="EFIH.CA",
        name_en="Egyptian Financial & Industrial",
        name_ar="المصرية المالية والصناعية",
        sector="Industrial",
        is_egx30=True
    ),
    "ESRS": EGXStock(
        ticker="ESRS",
        yahoo="ESRS.CA",
        name_en="Ezz Steel",
        name_ar="حديد عز",
        sector="Steel",
        is_egx30=True
    ),
    "IRON": EGXStock(
        ticker="IRON",
        yahoo="IRON.CA",
        name_en="Egyptian Iron & Steel",
        name_ar="الحديد والصلب المصرية",
        sector="Steel",
        is_egx30=False
    ),

    # ============ TELECOMMUNICATIONS ============
    "ETEL": EGXStock(
        ticker="ETEL",
        yahoo="ETEL.CA",
        name_en="Telecom Egypt",
        name_ar="المصرية للاتصالات",
        sector="Telecommunications",
        is_egx30=True
    ),
    "EMFD": EGXStock(
        ticker="EMFD",
        yahoo="EMFD.CA",
        name_en="E-Finance for Digital",
        name_ar="إي فاينانس",
        sector="Fintech",
        is_egx30=True
    ),

    # ============ PORTS & LOGISTICS ============
    "ALCN": EGXStock(
        ticker="ALCN",
        yahoo="ALCN.CA",
        name_en="Alexandria Container & Cargo Handling",
        name_ar="الإسكندرية لتداول الحاويات",
        sector="Ports & Shipping",
        is_egx30=True
    ),

    # ============ FERTILIZERS & CHEMICALS ============
    "ABUK": EGXStock(
        ticker="ABUK",
        yahoo="ABUK.CA",
        name_en="Abu Qir Fertilizers",
        name_ar="أبو قير للأسمدة",
        sector="Chemicals",
        is_egx30=True
    ),
    "MFPC": EGXStock(
        ticker="MFPC",
        yahoo="MFPC.CA",
        name_en="Misr Fertilizers Production (MOPCO)",
        name_ar="مصر لإنتاج الأسمدة",
        sector="Chemicals",
        is_egx30=True
    ),
    "SKPC": EGXStock(
        ticker="SKPC",
        yahoo="SKPC.CA",
        name_en="Sidi Kerir Petrochemicals",
        name_ar="سيدي كرير للبتروكيماويات",
        sector="Petrochemicals",
        is_egx30=True
    ),

    # ============ FOOD & BEVERAGES ============
    "JUFO": EGXStock(
        ticker="JUFO",
        yahoo="JUFO.CA",
        name_en="Juhayna Food Industries",
        name_ar="جهينة للصناعات الغذائية",
        sector="Food & Beverage",
        is_egx30=True
    ),
    "CCAP": EGXStock(
        ticker="CCAP",
        yahoo="CCAP.CA",
        name_en="Cleopatra Hospital",
        name_ar="مستشفى كليوباترا",
        sector="Healthcare",
        is_egx30=True
    ),
    "DOMTY": EGXStock(
        ticker="DOMTY",
        yahoo="DOMTY.CA",
        name_en="Arabian Food Industries (Domty)",
        name_ar="الصناعات الغذائية العربية دومتي",
        sector="Food & Beverage",
        is_egx30=False
    ),

    # ============ TEXTILES & CONSUMER ============
    "ORWE": EGXStock(
        ticker="ORWE",
        yahoo="ORWE.CA",
        name_en="Oriental Weavers",
        name_ar="السجاد الشرقية",
        sector="Textiles",
        is_egx30=True
    ),

    # ============ ENERGY & UTILITIES ============
    "AMOC": EGXStock(
        ticker="AMOC",
        yahoo="AMOC.CA",
        name_en="Alexandria Mineral Oils",
        name_ar="اسكندرية للزيوت المعدنية",
        sector="Oil & Gas",
        is_egx30=True
    ),

    # ============ TOURISM & HOSPITALITY ============
    "EKHOA": EGXStock(
        ticker="EKHOA",
        yahoo="EKHOA.CA",
        name_en="Egyptian Hotels (EGOTH)",
        name_ar="الفنادق المصرية إيجوث",
        sector="Tourism",
        is_egx30=False
    ),

    # ============ CEMENT ============
    "ARCC": EGXStock(
        ticker="ARCC",
        yahoo="ARCC.CA",
        name_en="Arabian Cement",
        name_ar="الأسمنت العربية",
        sector="Cement",
        is_egx30=False
    ),
}


def get_yahoo_symbols() -> List[str]:
    """
    Get list of all Yahoo Finance formatted symbols.

    Returns:
        List of symbols in SYMBOL.CA format.

    Example:
        >>> symbols = get_yahoo_symbols()
        >>> print(symbols[:3])
        ['COMI.CA', 'HRHO.CA', 'FWRY.CA']
    """
    return [stock.yahoo for stock in EGX_SYMBOL_DATABASE.values()]


def get_egx30_symbols() -> List[str]:
    """
    Get only EGX 30 index constituents (Yahoo Finance format).

    Returns:
        List of EGX 30 symbols in SYMBOL.CA format.
    """
    return [stock.yahoo for stock in EGX_SYMBOL_DATABASE.values() if stock.is_egx30]


def get_symbols_by_sector(sector: str) -> List[str]:
    """
    Get symbols filtered by sector.

    Args:
        sector: Sector name (e.g., 'Banking', 'Real Estate')

    Returns:
        List of Yahoo Finance symbols in that sector.
    """
    return [stock.yahoo for stock in EGX_SYMBOL_DATABASE.values()
            if stock.sector.lower() == sector.lower()]


def get_stock_info(symbol: str) -> Optional[EGXStock]:
    """
    Get full stock information by ticker or Yahoo symbol.

    Args:
        symbol: Either local ticker (COMI) or Yahoo format (COMI.CA)

    Returns:
        EGXStock object or None if not found.
    """
    # Clean symbol
    clean = symbol.upper().replace('.CA', '')
    return EGX_SYMBOL_DATABASE.get(clean)


def get_company_name(symbol: str, lang: str = 'en') -> str:
    """
    Get company name for a symbol.

    Args:
        symbol: Stock symbol (COMI or COMI.CA)
        lang: 'en' for English, 'ar' for Arabic

    Returns:
        Company name or the symbol if not found.
    """
    stock = get_stock_info(symbol)
    if not stock:
        return symbol
    return stock.name_en if lang == 'en' else stock.name_ar


def get_search_keywords(symbol: str) -> List[str]:
    """
    Get search keywords for news queries about a stock.

    Args:
        symbol: Stock symbol

    Returns:
        List of search terms including ticker, company name, and sector.
    """
    stock = get_stock_info(symbol)
    if not stock:
        return [symbol]

    keywords = [
        stock.ticker,
        stock.name_en,
        stock.name_ar,
        f"{stock.ticker} Egypt",
        f"{stock.name_en} stock",
    ]
    return keywords


# ============================================
# MARKET INFORMATION
# ============================================

EGX_MARKET_INFO = {
    "name": "Egyptian Exchange",
    "name_ar": "البورصة المصرية",
    "currency": "EGP",
    "timezone": "Africa/Cairo",
    "trading_hours": {
        "open": "10:00",
        "close": "14:30",
        "pre_open": "09:30",
    },
    "trading_days": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
    "website": "https://www.egx.com.eg",
    "main_indices": ["EGX30", "EGX70", "EGX100"],
}


if __name__ == "__main__":
    print("=" * 60)
    print("Egyptian Exchange (EGX) Symbol Database")
    print("=" * 60)

    print(f"\nTotal stocks: {len(EGX_SYMBOL_DATABASE)}")
    print(f"EGX 30 constituents: {len(get_egx30_symbols())}")

    print("\nStocks by Sector:")
    sectors = set(s.sector for s in EGX_SYMBOL_DATABASE.values())
    for sector in sorted(sectors):
        count = len(get_symbols_by_sector(sector))
        print(f"  {sector}: {count}")

    print("\nYahoo Finance Symbols:")
    for symbol in get_yahoo_symbols():
        stock = get_stock_info(symbol)
        egx30_marker = " [EGX30]" if stock.is_egx30 else ""
        print(f"  {symbol:12} - {stock.name_en}{egx30_marker}")

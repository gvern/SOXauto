"""Build complete SQL query parameters from cutoff date and selected countries/entities."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime
from typing import Any, Dict, Iterable, List, Sequence


COUNTRY_CONFIG: Dict[str, Dict[str, str]] = {
    "NG": {"company_code": "EC_NG", "currency_code": "NGN"},
    "GH": {"company_code": "JD_GH", "currency_code": "GHS"},
    "CI": {"company_code": "EC_IC", "currency_code": "XOF"},
    "SN": {"company_code": "HF_SN", "currency_code": "XOF"},
    "KE": {"company_code": "EC_KE", "currency_code": "KES"},
    "UG": {"company_code": "JD_UG", "currency_code": "UGX"},
    "DZ": {"company_code": "JD_DZ", "currency_code": "DZD"},
    "EG": {"company_code": "JM_EG", "currency_code": "EGP"},
    "MA": {"company_code": "EC_MA", "currency_code": "MAD"},
}

COUNTRY_CURRENCY_MAP: Dict[str, str] = {
    "NG": "NGN",
    "GH": "GHS",
    "CI": "XOF",
    "SN": "XOF",
    "KE": "KES",
    "UG": "UGX",
    "DZ": "DZD",
    "EG": "EGP",
    "MA": "MAD",
    "US": "USD",
}

GL_ACCOUNTS = {
    "voucher_liability": ["18412"],
    "gl_accounts_cr_03": ["15010"],
    "customer_balances": ["13001", "13002", "13003"],
    "prepayments": ["18650", "18397"],
    "all_receivables": ["13001", "13002", "13003", "18412", "18650", "18397"],
}

CUSTOMER_POSTING_GROUPS = [
    "LOAN-REC-NAT", "B2B-NG-NAT", "B2C-NG-NAT", "B2C-NG-INT", "NTR-NG-NAT",
    "B2B-NG-INT", "NTR-NG-INT", "UE", "INL", "EXPORT", "EU", "NATIONAL",
    "OM", "NAT", "AUS", "EXCB2B-NAT", "EMP-NAT",
]


def _to_list(countries: Sequence[str] | str | None) -> List[str]:
    if countries is None:
        return []
    if isinstance(countries, str):
        return [countries]
    return [str(c) for c in countries]


def _short_code(country_or_company: str) -> str:
    token = country_or_company.upper().strip()
    if "_" in token:
        return token.split("_")[-1]
    return token


def _sql_tuple(values: Iterable[str]) -> str:
    items = [str(v) for v in values if str(v)]
    if not items:
        return "('')"
    escaped = [v.replace("'", "''") for v in items]
    return "(" + ",".join(f"'{v}'" for v in escaped) + ")"


def _parse_cutoff(cutoff_date: str | datetime) -> datetime:
    if isinstance(cutoff_date, datetime):
        return cutoff_date
    return datetime.strptime(str(cutoff_date), "%Y-%m-%d")


def build_complete_query_params(
    cutoff_date: str | datetime,
    countries: Sequence[str] | str | None,
    *,
    run_id: str | None = None,
    period: str | None = None,
    overrides: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return a full parameter set compatible with all catalog SQL placeholders."""
    cutoff_dt = _parse_cutoff(cutoff_date)
    cutoff_date_str = cutoff_dt.strftime("%Y-%m-%d")

    cutoff_year = cutoff_dt.year
    cutoff_month = cutoff_dt.month

    year_start = datetime(cutoff_year, 1, 1)
    year_end = datetime(cutoff_year, cutoff_month, monthrange(cutoff_year, cutoff_month)[1])
    period_month_start = datetime(cutoff_year, cutoff_month, 1, 0, 0, 0)
    if cutoff_month == 12:
        subsequent_month_start = datetime(cutoff_year + 1, 1, 1, 0, 0, 0)
    else:
        subsequent_month_start = datetime(cutoff_year, cutoff_month + 1, 1, 0, 0, 0)

    country_tokens = _to_list(countries)
    short_codes = [_short_code(c) for c in country_tokens]

    company_codes: List[str] = []
    currency_codes: List[str] = []
    for idx, token in enumerate(country_tokens):
        short = short_codes[idx]
        if short in COUNTRY_CONFIG:
            company_codes.append(COUNTRY_CONFIG[short]["company_code"])
            currency_codes.append(COUNTRY_CONFIG[short]["currency_code"])
        else:
            # Already a company code or unknown token; keep as company code fallback.
            company_codes.append(token)

    currencies_needed = sorted(
        {
            COUNTRY_CURRENCY_MAP[short]
            for short in short_codes
            if short in COUNTRY_CURRENCY_MAP
        }
    )
    if "USD" not in currencies_needed:
        currencies_needed.append("USD")

    params: Dict[str, Any] = {
        "countries": country_tokens,
        "run_id": run_id,
        "period": period,
        "cutoff_date": cutoff_date_str,
        "cutoff_year": cutoff_year,
        "cutoff_month": cutoff_month,
        "year_start": year_start.strftime("%Y-%m-%d"),
        "year_end": year_end.strftime("%Y-%m-%d"),
        "fx_year": cutoff_year,
        "fx_month": cutoff_month,
        "fx_date": cutoff_date_str,
        "period_month_start": period_month_start.strftime("%Y-%m-%d %H:%M:%S"),
        "subsequent_month_start": subsequent_month_start.strftime("%Y-%m-%d %H:%M:%S"),
        "id_companies_active": _sql_tuple(company_codes),
        "id_companies_active_list": company_codes,
        "currency_code": currency_codes[0] if currency_codes else "USD",
        "company_code": company_codes[0] if company_codes else (country_tokens[0] if country_tokens else ""),
        "gl_accounts_voucher": _sql_tuple(GL_ACCOUNTS["voucher_liability"]),
        "gl_accounts_cr_03": _sql_tuple(GL_ACCOUNTS["gl_accounts_cr_03"]),
        "gl_accounts_customer": _sql_tuple(GL_ACCOUNTS["customer_balances"]),
        "gl_accounts_cr_04": _sql_tuple(GL_ACCOUNTS["prepayments"]),
        "gl_accounts_all": _sql_tuple(GL_ACCOUNTS["all_receivables"]),
        "gl_accounts": _sql_tuple(GL_ACCOUNTS["all_receivables"]),
        "customer_posting_groups": _sql_tuple(CUSTOMER_POSTING_GROUPS),
        "excluded_countries_ipe31": _sql_tuple(["TN", "TZ", "ZA"]),
        "excluded_countries_ipe34": _sql_tuple(["AT_TN", "EC_CM"]),
        "currencies_needed": _sql_tuple(currencies_needed),
    }

    if overrides:
        params.update(overrides)

    # Keep aliases required by legacy queries/comments.
    params.setdefault("company", params["company_code"])
    params.setdefault("year", params["cutoff_year"])
    params.setdefault("month", params["cutoff_month"])

    return params


__all__ = ["build_complete_query_params"]
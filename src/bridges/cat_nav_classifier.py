"""
NAV Classifier Module - Integration Type Detection.

Determines whether a NAV GL entry is Manual or Integration based on the User ID.

Business Rule:
- If User ID contains "NAV" AND ("BATCH" OR "SRVC"), treat as Integration
- Otherwise, treat as Manual

This is a pure function: DataFrame -> DataFrame
No st.session_state or st.cache usage.
"""

from typing import Optional
import pandas as pd


def classify_integration_type(
    df: pd.DataFrame,
    user_id_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Classify NAV GL entries as Manual or Integration based on User ID.

    The integration pattern matches user IDs containing "NAV" AND ("BATCH" OR "SRVC").
    This indicates system/batch processing rather than manual entry.

    Args:
        df: DataFrame containing GL entries with a user ID column.
        user_id_col: Name of the user ID column. If None, auto-detects from
                     common column names: 'User ID', 'user_id', 'User_ID', 'userid'

    Returns:
        DataFrame with added 'Integration_Type' column containing either
        'Integration' or 'Manual'.

    Example:
        >>> df = pd.DataFrame({'User ID': ['JUMIA/NAV13AFR.BATCH.SRVC', 'USER/01']})
        >>> result = classify_integration_type(df)
        >>> print(result['Integration_Type'].tolist())
        ['Integration', 'Manual']
    """
    if df is None or df.empty:
        result = df.copy() if df is not None else pd.DataFrame()
        result["Integration_Type"] = None
        return result

    out = df.copy()
    out["Integration_Type"] = None

    # Auto-detect user ID column if not specified
    if user_id_col is None:
        user_id_candidates = ["User ID", "user_id", "User_ID", "userid", "UserID"]
        for col in user_id_candidates:
            if col in out.columns:
                user_id_col = col
                break

    if user_id_col is None or user_id_col not in out.columns:
        # Cannot classify without user ID column - default to Manual
        out["Integration_Type"] = "Manual"
        return out

    # Apply classification logic for each row
    for idx, row in out.iterrows():
        user_id = (
            str(row[user_id_col]).strip().upper()
            if pd.notna(row[user_id_col])
            else ""
        )
        # Check if user_id matches integration pattern: contains NAV AND (BATCH OR SRVC)
        is_integration = "NAV" in user_id and ("BATCH" in user_id or "SRVC" in user_id)
        out.at[idx, "Integration_Type"] = "Integration" if is_integration else "Manual"

    return out


def is_integration_user(user_id: str) -> bool:
    """
    Check if a user ID represents an integration/batch user.

    Args:
        user_id: The user ID string to check.

    Returns:
        True if the user ID matches the integration pattern, False otherwise.

    Example:
        >>> is_integration_user("JUMIA/NAV13AFR.BATCH.SRVC")
        True
        >>> is_integration_user("USER/01")
        False
    """
    if not user_id or pd.isna(user_id):
        return False
    user_id_upper = str(user_id).strip().upper()
    return "NAV" in user_id_upper and ("BATCH" in user_id_upper or "SRVC" in user_id_upper)


__all__ = ["classify_integration_type", "is_integration_user"]

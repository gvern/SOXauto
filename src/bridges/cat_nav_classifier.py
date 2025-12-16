"""
NAV Classifier Module - Integration Type Detection.

Determines whether a NAV GL entry is Manual or Integration based on the User ID.

Business Rule:
- If User ID == 'JUMIA/NAV31AFR.BATCH.SRVC' (strict match), treat as Integration
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

    The integration type is determined by strict matching against the
    specific user ID 'JUMIA/NAV31AFR.BATCH.SRVC'.

    Args:
        df: DataFrame containing GL entries with a user ID column.
        user_id_col: Name of the user ID column. If None, auto-detects from
                     common column names: 'User ID', 'user_id', 'User_ID', 'userid'

    Returns:
        DataFrame with added 'Integration_Type' column containing either
        'Integration' or 'Manual'.

    Example:
        >>> df = pd.DataFrame({'User ID': ['JUMIA/NAV31AFR.BATCH.SRVC', 'USER/01']})
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
        # Normalize slashes for strict match: treat both / and \ as equivalent
        normalized_user_id = user_id.replace("\\", "/")
        is_integration = normalized_user_id == "JUMIA/NAV31AFR.BATCH.SRVC"
        out.at[idx, "Integration_Type"] = "Integration" if is_integration else "Manual"

    return out


def is_integration_user(user_id: str) -> bool:
    """
    Check if a user ID represents an integration/batch user.

    Args:
        user_id: The user ID string to check.

    Returns:
        True if the user ID matches the integration user (JUMIA/NAV31AFR.BATCH.SRVC), False otherwise.

    Example:
        >>> is_integration_user("JUMIA/NAV31AFR.BATCH.SRVC")
        True
        >>> is_integration_user("JUMIA\\NAV31AFR.BATCH.SRVC")
        True
        >>> is_integration_user("USER/01")
        False
    """
    if not user_id or pd.isna(user_id):
        return False
    user_id_upper = str(user_id).strip().upper()
    # Normalize slashes for strict match: treat both / and \ as equivalent
    normalized_user_id = user_id_upper.replace("\\", "/")
    return normalized_user_id == "JUMIA/NAV31AFR.BATCH.SRVC"


__all__ = ["classify_integration_type", "is_integration_user"]

"""
FX Conversion utilities for SOXauto.

Provides functionality to convert local currency amounts to USD using
monthly FX rates from CR_05 (FX Rates Control Report).
"""

from typing import Optional
import pandas as pd


class FXConverter:
    """
    FX Converter for converting local currency amounts to USD.
    
    Uses monthly "Closing" rates extracted via CR_05 control report.
    The conversion formula is: Amount_USD = Amount_LCY / FX_rate
    
    Attributes:
        rates_dict (dict): Dictionary mapping Company_Code to FX_rate
        default_rate (float): Default rate to use when company not found (1.0)
    """
    
    def __init__(self, cr05_df: pd.DataFrame, default_rate: float = 1.0):
        """
        Initialize the FX Converter with CR_05 FX rates data.
        
        Args:
            cr05_df: DataFrame from CR_05 containing columns:
                - Company_Code: Company identifier
                - FX_rate: Exchange rate (Local Currency / USD)
            default_rate: Rate to use when company not found or rate is invalid.
                         Default is 1.0 (assumes USD when no rate available).
        
        Raises:
            ValueError: If cr05_df is None or missing required columns
        """
        if cr05_df is None or cr05_df.empty:
            raise ValueError("CR_05 DataFrame cannot be None or empty")
        
        # Validate required columns
        required_cols = ["Company_Code", "FX_rate"]
        missing_cols = [col for col in required_cols if col not in cr05_df.columns]
        if missing_cols:
            raise ValueError(f"CR_05 DataFrame missing required columns: {missing_cols}")
        
        self.default_rate = default_rate
        
        # Build lookup dictionary: {Company_Code: FX_rate}
        # Use the first rate if there are duplicates
        self.rates_dict = {}
        for _, row in cr05_df.iterrows():
            company_code = row["Company_Code"]
            fx_rate = row["FX_rate"]
            
            # Only store if company_code is not null
            if pd.notna(company_code):
                # Store the rate if it's valid (not null and not zero)
                if pd.notna(fx_rate) and fx_rate != 0:
                    self.rates_dict[str(company_code)] = float(fx_rate)
    
    def convert_to_usd(self, amount: float, company_code: str) -> float:
        """
        Convert a local currency amount to USD.
        
        Formula: Amount_USD = Amount_LCY / FX_rate
        
        Args:
            amount: Amount in local currency
            company_code: Company code to look up the FX rate
        
        Returns:
            Amount in USD. Returns 0.0 if input amount is None/NaN.
            Returns original amount if company_code not found (assumes rate=1).
        
        Examples:
            >>> converter = FXConverter(cr05_df)
            >>> converter.convert_to_usd(1000.0, "JD_GH")  # If rate is 15.5
            64.52
            >>> converter.convert_to_usd(100.0, "UNKNOWN")  # Company not found
            100.0
            >>> converter.convert_to_usd(None, "JD_GH")
            0.0
        """
        # Handle None/NaN amounts
        if pd.isna(amount):
            return 0.0
        
        amount = float(amount)
        
        # Handle None/NaN company codes
        if pd.isna(company_code):
            # No company code means we can't look up rate, use default
            return amount / self.default_rate
        
        company_code_str = str(company_code)
        
        # Look up FX rate
        fx_rate = self.rates_dict.get(company_code_str)
        
        if fx_rate is None:
            # Company not found, use default rate
            fx_rate = self.default_rate
        
        # Perform conversion: Amount_USD = Amount_LCY / FX_rate
        # The fx_rate is guaranteed to be non-zero from __init__ validation
        return amount / fx_rate
    
    def convert_series_to_usd(
        self, 
        amount_series: pd.Series, 
        company_code_series: pd.Series
    ) -> pd.Series:
        """
        Convert a pandas Series of amounts to USD using corresponding company codes.
        
        This is a vectorized helper for converting entire DataFrame columns.
        
        Args:
            amount_series: Series of amounts in local currency
            company_code_series: Series of company codes (must have same index)
        
        Returns:
            Series of amounts in USD
        
        Examples:
            >>> amounts = pd.Series([1000, 2000, 3000])
            >>> companies = pd.Series(["JD_GH", "EC_NG", "EC_KE"])
            >>> converter.convert_series_to_usd(amounts, companies)
            0    64.52
            1   500.00
            2   100.00
            dtype: float64
        """
        if len(amount_series) != len(company_code_series):
            raise ValueError(
                "amount_series and company_code_series must have the same length"
            )
        
        # Apply conversion element-wise
        result = pd.Series(index=amount_series.index, dtype=float)
        for idx in amount_series.index:
            result[idx] = self.convert_to_usd(
                amount_series[idx], 
                company_code_series[idx]
            )
        
        return result


__all__ = ["FXConverter"]

# Voucher to Cash (VTC) Reconciliation Process

This is a **bridge identification** process. The goal is to find refund vouchers that were canceled in the source system (BOB) but have not yet been booked in the accounting system (NAV), because the cash refund to the customer has not been processed.

The automated workflow is as follows:

1. **Extract Canceled Vouchers from BOB**:

    * Run the query from the "Issuance" tab in the `Voucher TV Extract.xlsx` file.
    * Apply the following filters to get the list of vouchers that were canceled in the source system this month:
        * `business_use_formatted` = **'refund'**
        * `is_active` = **0** (or `FALSE`)
        * Filter by the relevant month and country (e.g., `created_at` in September, `ID_COMPANY` is Nigeria).

2. **Extract and Categorize NAV GL Entries**:

    * Extract all entries for the Voucher Accrual account (`18412`) from the `GL Entries` table in NAV for the same period.
    * From this extract, identify the entries that represent a VTC booking by applying the following four conditions:
        * `GL Account` is **18412**.
        * `Amount` is **positive**.
        * `Balancing Account Type` is **'Bank Account'**.
        * `User ID` is a **manual user** (i.e., does not start with 'NAV/' or 'jumia/').

3. **Compare and Identify the Bridge**:

    * Compare the list of canceled voucher IDs from BOB (Step 1) against the list of VTC-booked voucher IDs from NAV (Step 2).
    * Any `voucher_id` that exists in the BOB list but **does not exist** in the NAV list is considered a "bridge" item. These are the vouchers that need to be sent to the accounting team for booking.

-----

## NAV GL Entry Categorization Rules

This process automates the manual categorization currently done in the "Voucher Accrual Analysis" Excel sheet. The goal is to classify every transaction in the GL Account `18412` based on a clear set of rules.

### **Base Condition for All Rules:**

* The `GL Account` must be **18412** (Voucher Accrual).

Here are the rules for each category:

| Category | Conditions | Voucher Type (Sub-Category) |
| :--- | :--- | :--- |
| **VTC** | **1.** `Amount` is **positive**.<br>**2.** `Balancing Account Type` is **'Bank Account'**.<br>**3.** `User ID` is **manual**. | `Refund` (implied for VTC) |
| **Usage** | **1.** `Amount` is **positive**.<br>**2.** `User ID` is **integrated** (starts with 'NAV/').<br>**3.** `Description` contains `'Item Price Credit'`, `'Item Shipping Fee'`, or `'Voucher Application To'`. | Determined by a **VLOOKUP/Join** using `voucher_id` from this NAV entry against the **BOB Usage extract** to find the `business_use`. |
| **Issuance** | **1.** `Amount` is **negative**. | Determined by `Description` or `Document Type`: <br> - `Description` contains `'refund'` → **Refund**<br> - `Description` is `'Commercial Gesture (CXP)'` → **Apology**<br> - `Description` starts with `'PYT_PF'` → **JForce**<br> - `Description` contains `'_voucher'` or `'Jumia JP app_store credit'` AND `User ID` is manual → **Jumia Pay Store Credit**<br> - `Document Type` is `'Invoice'` AND `User ID` is manual → **Store Credit** |
| **Cancellation** | **1.** `Amount` is **positive**. | Determined by `Document Type` or `Description`: <br> - `Document Type` is `'Credit Memo'` AND `User ID` is manual → **Store Credit**<br> - `Description` is `'Voucher Approval'` AND `User ID` is integrated → **Apology** |
| **Expiration** | **1.** `Amount` is **positive**.<br>**2.** `User ID` is **manual**.<br>**3.** `Description` starts with **'EXPR_'**. | Determined by the text following `EXPR_`. <br> - `EXPR_APOLOGY` → **Apology**<br> - `EXPR_RFN` → **Refund**<br> - `EXPR_STR CREDIT` → **Store Credit** |

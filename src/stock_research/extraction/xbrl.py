from __future__ import annotations

import html
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from stock_research.extraction.earnings_release import _HtmlTableParser, extract_earnings_release_facts
from stock_research.extraction.tencent_reports import extract_tencent_report_facts
from stock_research.sources.document_policy import is_financial_extraction_document


TARGET_TAGS: dict[str, dict[str, Any]] = {
    "revenue": {
        "label": "Revenue",
        "tags": [
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap:Revenues",
        ],
    },
    "cost_of_revenue": {
        "label": "Cost of revenue",
        "tags": ["us-gaap:CostOfRevenue"],
    },
    "sales_and_marketing_expense": {
        "label": "Sales and marketing expense",
        "tags": ["us-gaap:SellingAndMarketingExpense"],
    },
    "research_and_development_expense": {
        "label": "Research and development expense",
        "tags": ["us-gaap:ResearchAndDevelopmentExpense"],
    },
    "general_and_administrative_expense": {
        "label": "General and administrative expense",
        "tags": ["us-gaap:GeneralAndAdministrativeExpense"],
    },
    "advertising_expense": {
        "label": "Advertising expense",
        "tags": ["us-gaap:AdvertisingExpense"],
    },
    "fulfillment_expense": {
        "label": "Fulfillment expense",
        "tags": [],
    },
    "payment_processing_expense": {
        "label": "Payment processing expense",
        "tags": [],
    },
    "server_and_bandwidth_costs": {
        "label": "Server and bandwidth costs",
        "tags": [],
    },
    "merchant_support_costs": {
        "label": "Merchant support costs",
        "tags": [],
    },
    "platform_governance_costs": {
        "label": "Platform governance costs",
        "tags": [],
    },
    "logistics_expense": {
        "label": "Logistics expense",
        "tags": [],
    },
    "gross_profit": {
        "label": "Gross profit",
        "tags": ["us-gaap:GrossProfit"],
    },
    "operating_income": {
        "label": "Operating income",
        "tags": ["us-gaap:OperatingIncomeLoss"],
    },
    "pretax_income": {
        "label": "Pretax income before equity-method results",
        "tags": [
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        ],
    },
    "pretax_income_after_equity_method": {
        "label": "Pretax income after equity-method results",
        "tags": [
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        ],
    },
    "tax_expense": {
        "label": "Income tax expense",
        "tags": ["us-gaap:IncomeTaxExpenseBenefit"],
    },
    "interest_expense": {
        "label": "Interest expense",
        "tags": ["us-gaap:InterestExpenseNonoperating"],
    },
    "interest_income": {
        "label": "Interest income",
        "tags": [
            "us-gaap:InterestIncomeNonOperating",
        ],
    },
    "foreign_exchange_gain_loss": {
        "label": "Foreign exchange gain / loss",
        "tags": [],
    },
    "other_income_net": {
        "label": "Other income, net",
        "tags": ["us-gaap:OtherNonoperatingIncomeExpense"],
    },
    "net_income": {
        "label": "Net income",
        "tags": ["us-gaap:NetIncomeLoss"],
    },
    "operating_cash_flow": {
        "label": "Operating cash flow",
        "tags": ["us-gaap:NetCashProvidedByUsedInOperatingActivities"],
    },
    "capex": {
        "label": "Capital expenditure",
        "tags": [
            "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
            "pdd:PaymentsToAcquirePropertyEquipmentAndSoftwareAndIntangibleAssets",
        ],
    },
    "cash": {
        "label": "Cash and cash equivalents",
        "tags": ["us-gaap:CashAndCashEquivalentsAtCarryingValue"],
    },
    "short_term_investments": {
        "label": "Short-term investments",
        "tags": [
            "us-gaap:ShortTermInvestments",
            "us-gaap:ShortTermInvestmentsAvailableForSale",
            "us-gaap:MarketableSecuritiesCurrent",
        ],
    },
    "long_term_investments": {
        "label": "Long-term investments",
        "tags": [
            "us-gaap:LongTermInvestments",
            "us-gaap:MarketableSecuritiesNoncurrent",
        ],
    },
    "cash_and_short_term_investments": {
        "label": "Cash and short-term investments",
        "tags": [],
    },
    "restricted_cash": {
        "label": "Restricted cash",
        "tags": [
            "us-gaap:RestrictedCashAndCashEquivalentsAtCarryingValue",
            "us-gaap:RestrictedCashCurrent",
            "us-gaap:RestrictedCashNoncurrent",
        ],
    },
    "debt": {
        "label": "Interest-bearing debt",
        "tags": [
            "us-gaap:ConvertibleDebt",
            "us-gaap:ShortTermBorrowings",
        ],
    },
    "debt_current": {
        "label": "Current interest-bearing debt",
        "tags": [
            "us-gaap:ConvertibleDebtCurrent",
            "us-gaap:LongTermDebtAndFinanceLeaseObligationsCurrent",
        ],
    },
    "debt_noncurrent": {
        "label": "Noncurrent interest-bearing debt",
        "tags": [
            "us-gaap:ConvertibleDebtNoncurrent",
            "us-gaap:LongTermDebtAndFinanceLeaseObligationsNoncurrent",
        ],
    },
    "convertible_debt_current": {
        "label": "Convertible debt, current portion",
        "tags": ["us-gaap:ConvertibleDebtCurrent"],
    },
    "convertible_debt_noncurrent": {
        "label": "Convertible debt, noncurrent portion",
        "tags": ["us-gaap:ConvertibleDebtNoncurrent"],
    },
    "lease_liabilities_current": {
        "label": "Lease liabilities, current",
        "tags": ["us-gaap:OperatingLeaseLiabilityCurrent"],
    },
    "lease_liabilities_noncurrent": {
        "label": "Lease liabilities, noncurrent",
        "tags": ["us-gaap:OperatingLeaseLiabilityNoncurrent"],
    },
    "lease_liabilities": {
        "label": "Lease liabilities",
        "tags": ["us-gaap:OperatingLeaseLiability"],
    },
    "stock_based_compensation": {
        "label": "Stock-based compensation cash-flow addback",
        "tags": [
            "us-gaap:ShareBasedCompensation",
        ],
    },
    "depreciation_and_amortization": {
        "label": "Depreciation and amortization",
        "tags": ["us-gaap:DepreciationAndAmortization"],
    },
    "basic_shares": {
        "label": "Basic shares",
        "tags": ["us-gaap:WeightedAverageNumberOfSharesOutstandingBasic"],
    },
    "diluted_shares": {
        "label": "Diluted shares",
        "tags": ["us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"],
    },
    "basic_eps": {
        "label": "Basic EPS",
        "tags": ["us-gaap:EarningsPerShareBasic"],
    },
    "diluted_eps": {
        "label": "Diluted EPS",
        "tags": ["us-gaap:EarningsPerShareDiluted"],
    },
    "ordinary_shares_outstanding": {
        "label": "Ordinary shares outstanding",
        "tags": [],
    },
    "ads_outstanding": {
        "label": "ADS outstanding",
        "tags": [],
    },
    "ordinary_shares_per_ads": {
        "label": "Ordinary shares per ADS",
        "tags": [],
    },
    "share_repurchases": {
        "label": "Share repurchases",
        "tags": ["us-gaap:PaymentsForRepurchaseOfCommonStock"],
    },
    "dividends_paid": {
        "label": "Dividends paid",
        "tags": ["us-gaap:PaymentsOfDividends"],
    },
    "equity_plan_authorized_shares": {
        "label": "Equity plan authorized shares",
        "tags": [],
    },
    "equity_plan_available_shares": {
        "label": "Equity plan available shares",
        "tags": [],
    },
    "current_assets": {
        "label": "Current assets",
        "tags": ["us-gaap:AssetsCurrent"],
    },
    "total_assets": {
        "label": "Total assets",
        "tags": ["us-gaap:Assets"],
    },
    "current_liabilities": {
        "label": "Current liabilities",
        "tags": ["us-gaap:LiabilitiesCurrent"],
    },
    "total_liabilities": {
        "label": "Total liabilities",
        "tags": ["us-gaap:Liabilities"],
    },
    "accounts_receivable": {
        "label": "Accounts receivable",
        "tags": ["us-gaap:AccountsReceivableNetCurrent"],
    },
    "receivables_from_online_payment_platforms": {
        "label": "Receivables from online payment platforms",
        "tags": ["pdd:ReceivablesFromOnlinePaymentPlatformsCurrent"],
    },
    "inventory": {
        "label": "Inventory",
        "tags": ["us-gaap:InventoryNet"],
    },
    "prepayments_and_other_current_assets": {
        "label": "Prepayments and other current assets",
        "tags": ["us-gaap:PrepaidExpenseAndOtherAssetsCurrent"],
    },
    "accounts_payable": {
        "label": "Accounts payable",
        "tags": ["us-gaap:AccountsPayableCurrent"],
    },
    "accounts_payable_and_accrued_expenses": {
        "label": "Accounts payable and accrued liabilities",
        "tags": ["us-gaap:AccountsPayableAndAccruedLiabilitiesCurrent"],
    },
    "payable_to_merchants": {
        "label": "Payable to merchants",
        "tags": ["pdd:PayableToMerchantsCurrent"],
    },
    "accrued_expenses": {
        "label": "Accrued expenses and other current liabilities",
        "tags": [
            "us-gaap:AccruedLiabilitiesCurrent",
            "us-gaap:AccruedIncomeTaxesCurrent",
        ],
    },
    "deferred_revenue": {
        "label": "Deferred revenue / contract liabilities",
        "tags": [
            "us-gaap:ContractWithCustomerLiabilityCurrent",
            "us-gaap:DeferredRevenueCurrent",
            "us-gaap:DeferredRevenueAndCreditsCurrent",
            "pdd:AdvancesToCustomerAndDeferredRevenueCurrent",
        ],
    },
    "customer_advances_and_deferred_revenues": {
        "label": "Customer advances and deferred revenues",
        "tags": ["pdd:AdvancesToCustomerAndDeferredRevenueCurrent"],
    },
    "merchant_deposits": {
        "label": "Merchant / customer deposits",
        "tags": [
            "us-gaap:DepositLiabilityCurrent",
            "pdd:MerchantDepositsCurrent",
        ],
    },
    "change_in_payable_to_merchants": {
        "label": "Change in payables to merchants",
        "tags": ["pdd:IncreaseDecreaseInPayablesToMerchants"],
    },
    "change_in_merchant_deposits": {
        "label": "Change in merchant deposits",
        "tags": ["pdd:IncreaseDecreaseInMerchantDeposits"],
    },
    "change_in_deferred_revenue": {
        "label": "Change in advances to customers and deferred revenue",
        "tags": ["pdd:IncreaseDecreaseInAdvancesToCustomersAndDeferredRevenue"],
    },
    "change_in_receivables_from_online_payment_platforms": {
        "label": "Change in receivables from online payment platforms",
        "tags": [],
    },
    "change_in_prepayments_and_other_current_assets": {
        "label": "Change in prepayments and other current assets",
        "tags": ["us-gaap:IncreaseDecreaseInPrepaidDeferredExpenseAndOtherAssets"],
    },
    "change_in_accrued_expenses_and_other_liabilities": {
        "label": "Change in accrued expenses and other liabilities",
        "tags": ["us-gaap:IncreaseDecreaseInAccruedLiabilitiesAndOtherOperatingLiabilities"],
    },
    "change_in_lease_liabilities": {
        "label": "Change in lease liabilities",
        "tags": ["us-gaap:IncreaseDecreaseInOperatingLeaseLiability"],
    },
    "fair_value_change_of_investments": {
        "label": "Fair value change of investments",
        "tags": [],
    },
    "cash_paid_for_taxes": {
        "label": "Cash paid for income taxes",
        "tags": ["us-gaap:IncomeTaxesPaidNet"],
    },
    "cash_paid_for_interest": {
        "label": "Cash paid for interest",
        "tags": ["us-gaap:InterestPaidNet"],
    },
    "equity_method_income": {
        "label": "Equity-method income / loss",
        "tags": ["us-gaap:IncomeLossFromEquityMethodInvestments"],
    },
    "investment_income": {
        "label": "Investment income",
        "tags": [
            "us-gaap:InvestmentIncomeNet",
            "us-gaap:InvestmentIncomeInterest",
        ],
    },
    "unrecognized_share_based_compensation": {
        "label": "Unrecognized share-based compensation",
        "tags": [
            "us-gaap:EmployeeServiceShareBasedCompensationNonvestedAwardsTotalCompensationCostNotYetRecognizedStockOptions",
            "us-gaap:EmployeeServiceShareBasedCompensationNonvestedAwardsTotalCompensationCostNotYetRecognizedShareBasedAwardsOtherThanOptions",
        ],
    },
    "sbc_remaining_vesting_years": {
        "label": "Remaining weighted-average vesting period for unrecognized SBC",
        "tags": [
            "us-gaap:EmployeeServiceShareBasedCompensationNonvestedAwardsTotalCompensationCostNotYetRecognizedPeriodForRecognition1",
        ],
    },
    "impairment": {
        "label": "Impairment charges",
        "tags": [
            "us-gaap:ImpairmentOfGoodwillAndIndefiniteLivedIntangibleAssets",
            "us-gaap:ImpairmentOfIntangibleAssetsExcludingGoodwill",
        ],
    },
}

TAG_TO_METRIC = {
    tag.lower(): metric
    for metric, config in TARGET_TAGS.items()
    for tag in config["tags"]
}

CORE_PRIORITY_A_METRICS = [
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "pretax_income",
    "tax_expense",
    "net_income",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
    "cash",
    "total_assets",
    "total_liabilities",
    "diluted_shares",
]

CORE_PRIORITY_B_METRICS = [
    "online_marketing_services_revenue",
    "transaction_services_revenue",
    "sales_and_marketing_expense",
    "research_and_development_expense",
    "general_and_administrative_expense",
    "stock_based_compensation",
    "depreciation_and_amortization",
    "short_term_investments",
    "restricted_cash",
    "current_assets",
    "current_liabilities",
    "basic_shares",
    "basic_eps",
    "diluted_eps",
    "debt",
    "debt_current",
    "debt_noncurrent",
    "convertible_debt_current",
    "convertible_debt_noncurrent",
    "lease_liabilities_current",
    "lease_liabilities_noncurrent",
    "lease_liabilities",
    "accounts_receivable",
    "receivables_from_online_payment_platforms",
    "inventory",
    "prepayments_and_other_current_assets",
    "accounts_payable",
    "accounts_payable_and_accrued_expenses",
    "payable_to_merchants",
    "accrued_expenses",
    "deferred_revenue",
    "customer_advances_and_deferred_revenues",
    "merchant_deposits",
    "change_in_payable_to_merchants",
    "change_in_merchant_deposits",
    "change_in_deferred_revenue",
    "change_in_receivables_from_online_payment_platforms",
    "change_in_prepayments_and_other_current_assets",
    "change_in_accrued_expenses_and_other_liabilities",
    "change_in_lease_liabilities",
    "cash_paid_for_taxes",
    "cash_paid_for_interest",
    "investment_income",
    "interest_expense",
    "foreign_exchange_gain_loss",
    "other_income_net",
    "equity_method_income",
    "fair_value_change_of_investments",
    "unrecognized_share_based_compensation",
    "sbc_remaining_vesting_years",
    "impairment",
]

METRIC_METADATA: dict[str, dict[str, str]] = {
    "revenue": {
        "metric_family": "income_statement_core",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "cost_of_revenue": {
        "metric_family": "income_statement_core",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "gross_profit": {
        "metric_family": "income_statement_core",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "sales_and_marketing_expense": {
        "metric_family": "operating_expense_breakdown",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "research_and_development_expense": {
        "metric_family": "operating_expense_breakdown",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "general_and_administrative_expense": {
        "metric_family": "operating_expense_breakdown",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "advertising_expense": {
        "metric_family": "operating_expense_breakdown",
        "financial_statement": "income_statement",
        "source_table": "expense_note",
    },
    "operating_income": {
        "metric_family": "income_statement_core",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "pretax_income": {
        "metric_family": "income_statement_core",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "pretax_income_after_equity_method": {
        "metric_family": "income_statement_core",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "tax_expense": {
        "metric_family": "tax_and_accounting_quality",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "interest_expense": {
        "metric_family": "below_operating_items",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "foreign_exchange_gain_loss": {
        "metric_family": "below_operating_items",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "other_income_net": {
        "metric_family": "below_operating_items",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "net_income": {
        "metric_family": "income_statement_core",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations",
    },
    "operating_cash_flow": {
        "metric_family": "cash_flow_core",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "capex": {
        "metric_family": "cash_flow_core",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "free_cash_flow": {
        "metric_family": "cash_flow_core",
        "financial_statement": "cash_flow_statement",
        "source_table": "derived_from_cash_flow_statement",
    },
    "stock_based_compensation": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "depreciation_and_amortization": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "change_in_payable_to_merchants": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "change_in_merchant_deposits": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "change_in_deferred_revenue": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "cash_paid_for_taxes": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "cash_paid_for_interest": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "cash": {
        "metric_family": "balance_sheet_core",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet",
    },
    "restricted_cash": {
        "metric_family": "balance_sheet_liquidity",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_cash_note",
    },
    "short_term_investments": {
        "metric_family": "balance_sheet_liquidity",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet",
    },
    "current_assets": {
        "metric_family": "balance_sheet_core",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet",
    },
    "total_assets": {
        "metric_family": "balance_sheet_core",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet",
    },
    "current_liabilities": {
        "metric_family": "balance_sheet_core",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet",
    },
    "total_liabilities": {
        "metric_family": "balance_sheet_core",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet",
    },
    "debt": {
        "metric_family": "balance_sheet_debt",
        "financial_statement": "balance_sheet",
        "source_table": "debt_note",
    },
    "debt_current": {
        "metric_family": "balance_sheet_debt",
        "financial_statement": "balance_sheet",
        "source_table": "debt_note",
    },
    "debt_noncurrent": {
        "metric_family": "balance_sheet_debt",
        "financial_statement": "balance_sheet",
        "source_table": "debt_note",
    },
    "convertible_debt_current": {
        "metric_family": "balance_sheet_debt",
        "financial_statement": "balance_sheet",
        "source_table": "debt_note",
    },
    "convertible_debt_noncurrent": {
        "metric_family": "balance_sheet_debt",
        "financial_statement": "balance_sheet",
        "source_table": "debt_note",
    },
    "lease_liabilities_current": {
        "metric_family": "balance_sheet_lease",
        "financial_statement": "balance_sheet",
        "source_table": "lease_note",
    },
    "lease_liabilities_noncurrent": {
        "metric_family": "balance_sheet_lease",
        "financial_statement": "balance_sheet",
        "source_table": "lease_note",
    },
    "lease_liabilities": {
        "metric_family": "balance_sheet_lease",
        "financial_statement": "balance_sheet",
        "source_table": "lease_note",
    },
    "accounts_receivable": {
        "metric_family": "working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_working_capital_note",
    },
    "receivables_from_online_payment_platforms": {
        "metric_family": "working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_working_capital_note",
    },
    "inventory": {
        "metric_family": "working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_working_capital_note",
    },
    "prepayments_and_other_current_assets": {
        "metric_family": "working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_working_capital_note",
    },
    "amounts_due_from_related_parties_current": {
        "metric_family": "related_party_working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_related_party_note",
    },
    "amounts_due_to_related_parties_current": {
        "metric_family": "related_party_working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_related_party_note",
    },
    "accounts_payable": {
        "metric_family": "working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_working_capital_note",
    },
    "accounts_payable_and_accrued_expenses": {
        "metric_family": "working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_working_capital_note",
    },
    "payable_to_merchants": {
        "metric_family": "working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_working_capital_note",
    },
    "accrued_expenses": {
        "metric_family": "working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_working_capital_note",
    },
    "deferred_revenue": {
        "metric_family": "working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_revenue_note",
    },
    "customer_advances_and_deferred_revenues": {
        "metric_family": "working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_revenue_note",
    },
    "merchant_deposits": {
        "metric_family": "working_capital",
        "financial_statement": "balance_sheet",
        "source_table": "balance_sheet_or_deposit_note",
    },
    "change_in_receivables_from_online_payment_platforms": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "change_in_prepayments_and_other_current_assets": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "change_in_accrued_expenses_and_other_liabilities": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "change_in_lease_liabilities": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "fair_value_change_of_investments": {
        "metric_family": "cash_flow_bridge",
        "financial_statement": "cash_flow_statement",
        "source_table": "statement_of_cash_flows",
    },
    "basic_shares": {
        "metric_family": "per_share_and_dilution",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations_or_eps_note",
    },
    "diluted_shares": {
        "metric_family": "per_share_and_dilution",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations_or_eps_note",
    },
    "basic_eps": {
        "metric_family": "per_share_and_dilution",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations_or_eps_note",
    },
    "diluted_eps": {
        "metric_family": "per_share_and_dilution",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations_or_eps_note",
    },
    "online_marketing_services_revenue": {
        "metric_family": "revenue_breakdown",
        "financial_statement": "income_statement",
        "source_table": "official_earnings_release_or_revenue_note",
    },
    "transaction_services_revenue": {
        "metric_family": "revenue_breakdown",
        "financial_statement": "income_statement",
        "source_table": "official_earnings_release_or_revenue_note",
    },
    "investment_income": {
        "metric_family": "below_operating_items",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations_or_investment_note",
    },
    "equity_method_income": {
        "metric_family": "below_operating_items",
        "financial_statement": "income_statement",
        "source_table": "statement_of_operations_or_investment_note",
    },
    "unrecognized_share_based_compensation": {
        "metric_family": "sbc_dilution_bridge",
        "financial_statement": "notes",
        "source_table": "share_based_compensation_note",
    },
    "sbc_remaining_vesting_years": {
        "metric_family": "sbc_dilution_bridge",
        "financial_statement": "notes",
        "source_table": "share_based_compensation_note",
    },
    "impairment": {
        "metric_family": "accounting_quality",
        "financial_statement": "income_statement",
        "source_table": "impairment_note",
    },
}

METRIC_METADATA.update(
    {
        "fulfillment_expense": {
            "metric_family": "cost_subcomponents",
            "financial_statement": "income_statement_or_cost_note",
            "source_table": "cost_of_revenue_note",
        },
        "payment_processing_expense": {
            "metric_family": "cost_subcomponents",
            "financial_statement": "income_statement_or_cost_note",
            "source_table": "cost_of_revenue_note",
        },
        "server_and_bandwidth_costs": {
            "metric_family": "cost_subcomponents",
            "financial_statement": "income_statement_or_cost_note",
            "source_table": "cost_of_revenue_note",
        },
        "merchant_support_costs": {
            "metric_family": "cost_subcomponents",
            "financial_statement": "income_statement_or_cost_note",
            "source_table": "cost_of_revenue_note",
        },
        "platform_governance_costs": {
            "metric_family": "cost_subcomponents",
            "financial_statement": "income_statement_or_cost_note",
            "source_table": "cost_of_revenue_note",
        },
        "logistics_expense": {
            "metric_family": "cost_subcomponents",
            "financial_statement": "income_statement_or_cost_note",
            "source_table": "cost_of_revenue_note",
        },
        "interest_income": {
            "metric_family": "below_operating_items",
            "financial_statement": "income_statement",
            "source_table": "statement_of_operations_or_investment_note",
        },
        "long_term_investments": {
            "metric_family": "balance_sheet_liquidity",
            "financial_statement": "balance_sheet",
            "source_table": "balance_sheet_or_investment_note",
        },
        "cash_and_short_term_investments": {
            "metric_family": "balance_sheet_liquidity",
            "financial_statement": "balance_sheet",
            "source_table": "derived_or_official_liquidity_summary",
        },
        "investment_portfolio": {
            "metric_family": "balance_sheet_liquidity",
            "financial_statement": "balance_sheet",
            "source_table": "investment_note",
        },
        "ordinary_shares_outstanding": {
            "metric_family": "sbc_dilution_bridge",
            "financial_statement": "equity_statement_or_cover_page",
            "source_table": "share_count_or_cover_page",
        },
        "ads_outstanding": {
            "metric_family": "sbc_dilution_bridge",
            "financial_statement": "equity_statement_or_cover_page",
            "source_table": "share_count_or_cover_page",
        },
        "ordinary_shares_per_ads": {
            "metric_family": "sbc_dilution_bridge",
            "financial_statement": "share_structure_note",
            "source_table": "share_structure_note",
        },
        "share_repurchases": {
            "metric_family": "capital_return_bridge",
            "financial_statement": "cash_flow_statement_or_equity_note",
            "source_table": "cash_flow_statement_or_buyback_note",
        },
        "dividends_paid": {
            "metric_family": "capital_return_bridge",
            "financial_statement": "cash_flow_statement_or_equity_note",
            "source_table": "cash_flow_statement_or_dividend_note",
        },
        "equity_plan_authorized_shares": {
            "metric_family": "sbc_dilution_bridge",
            "financial_statement": "share_based_compensation_note",
            "source_table": "equity_plan_note",
        },
        "equity_plan_available_shares": {
            "metric_family": "sbc_dilution_bridge",
            "financial_statement": "share_based_compensation_note",
            "source_table": "equity_plan_note",
        },
    }
)

FACT_QUALITY_GATE_CORE_METRICS = [
    "revenue",
    "operating_income",
    "net_income",
    "operating_cash_flow",
    "cash",
]

STATEMENT_COVERAGE_GROUPS = {
    "income_statement_core": [
        "revenue",
        "cost_of_revenue",
        "gross_profit",
        "operating_income",
        "net_income",
    ],
    "balance_sheet_core": [
        "cash",
        "current_assets",
        "current_liabilities",
        "total_assets",
        "total_liabilities",
    ],
    "cash_flow_core": [
        "operating_cash_flow",
        "capex",
        "free_cash_flow",
    ],
    "revenue_breakdown": [
        "online_marketing_services_revenue",
        "transaction_services_revenue",
    ],
    "expense_bridge": [
        "revenue",
        "cost_of_revenue",
        "gross_profit",
        "sales_and_marketing_expense",
        "research_and_development_expense",
        "general_and_administrative_expense",
        "operating_income",
    ],
    "cost_subcomponents": [
        "fulfillment_expense",
        "payment_processing_expense",
        "server_and_bandwidth_costs",
        "merchant_support_costs",
        "platform_governance_costs",
        "logistics_expense",
    ],
    "working_capital_bridge": [
        "stock_based_compensation",
        "depreciation_and_amortization",
        "change_in_receivables_from_online_payment_platforms",
        "change_in_prepayments_and_other_current_assets",
        "change_in_payable_to_merchants",
        "change_in_accrued_expenses_and_other_liabilities",
        "change_in_merchant_deposits",
        "change_in_deferred_revenue",
    ],
    "below_operating_bridge": [
        "investment_income",
        "interest_expense",
        "foreign_exchange_gain_loss",
        "other_income_net",
        "tax_expense",
        "equity_method_income",
    ],
    "liquidity_and_debt_detail": [
        "cash",
        "restricted_cash",
        "short_term_investments",
        "convertible_debt_current",
        "lease_liabilities_current",
        "lease_liabilities_noncurrent",
    ],
    "non_gaap_bridge": [
        "non_gaap_operating_income",
        "non_gaap_net_income",
        "non_gaap_adjustment_share_based_compensation",
    ],
    "cash_availability": [
        "cash",
        "restricted_cash",
        "short_term_investments",
        "long_term_investments",
        "investment_portfolio",
    ],
    "shares_sbc_capital_return": [
        "stock_based_compensation",
        "basic_shares",
        "diluted_shares",
        "ordinary_shares_outstanding",
        "ads_outstanding",
        "ordinary_shares_per_ads",
        "share_repurchases",
        "dividends_paid",
        "equity_plan_authorized_shares",
        "equity_plan_available_shares",
    ],
}

HARD_FINANCIAL_WORKSHEETS = [
    {
        "worksheet_id": "revenue_component_bridge",
        "question": "收入组件 YoY / QoQ：交易服务、在线营销分别贡献多少增长。",
        "core_metrics": ["revenue"],
        "supporting_metrics": [
            "online_marketing_services_revenue",
            "transaction_services_revenue",
        ],
        "review_note": "Supports revenue source attribution. Segment, product, geography, take-rate and volume facts remain separate optional gaps unless officially disclosed.",
    },
    {
        "worksheet_id": "expense_bridge",
        "question": "费用桥：收入增加 -> 毛利变化 -> S&M/R&D/G&A/成本变化 -> 经营利润变化。",
        "core_metrics": ["revenue", "cost_of_revenue", "gross_profit", "operating_income"],
        "supporting_metrics": [
            "sales_and_marketing_expense",
            "research_and_development_expense",
            "general_and_administrative_expense",
        ],
        "review_note": "Supports operating leverage and margin attribution before valuation work.",
    },
    {
        "worksheet_id": "cost_subcomponents",
        "question": "成本细项：履约、支付处理、服务器带宽、商家支持、平台治理。",
        "core_metrics": [],
        "supporting_metrics": [
            "fulfillment_expense",
            "payment_processing_expense",
            "server_and_bandwidth_costs",
            "merchant_support_costs",
            "platform_governance_costs",
            "logistics_expense",
        ],
        "review_note": "Optional but high-value cost detail. If absent, margin pressure cannot be attributed below broad cost-of-revenue / opex lines.",
    },
    {
        "worksheet_id": "below_operating_bridge",
        "question": "经营利润以下桥：投资收益、利息、其他损益、税项、权益法，解释经营利润和净利润分叉。",
        "core_metrics": ["operating_income", "pretax_income", "tax_expense", "net_income"],
        "supporting_metrics": [
            "investment_income",
            "interest_income",
            "interest_expense",
            "foreign_exchange_gain_loss",
            "other_income_net",
            "equity_method_income",
            "fair_value_change_of_investments",
        ],
        "review_note": "Supports diagnosis of whether reported profit changed because core operations changed or below-operating items moved.",
    },
    {
        "worksheet_id": "working_capital_bridge",
        "question": "营运资本桥：应收、预付、应付商家、应计费用、商家保证金、递延收入。",
        "core_metrics": ["operating_cash_flow"],
        "supporting_metrics": [
            "accounts_receivable",
            "receivables_from_online_payment_platforms",
            "prepayments_and_other_current_assets",
            "accounts_payable",
            "accounts_payable_and_accrued_expenses",
            "payable_to_merchants",
            "accrued_expenses",
            "merchant_deposits",
            "deferred_revenue",
            "change_in_receivables_from_online_payment_platforms",
            "change_in_prepayments_and_other_current_assets",
            "change_in_payable_to_merchants",
            "change_in_accrued_expenses_and_other_liabilities",
            "change_in_merchant_deposits",
            "change_in_deferred_revenue",
        ],
        "review_note": "Supports cash-quality work. Strong CFO must be separated from float, payables, deposits, and deferred-revenue tailwinds.",
    },
    {
        "worksheet_id": "cash_availability",
        "question": "现金可用性：现金、受限现金、短投、长期投资、VIE、资金转移限制。",
        "core_metrics": ["cash"],
        "supporting_metrics": [
            "restricted_cash",
            "short_term_investments",
            "long_term_investments",
            "investment_portfolio",
            "cash_and_short_term_investments",
        ],
        "text_evidence_needed": ["VIE cash-transfer restrictions", "dividend / remittance restrictions", "restricted-cash footnote"],
        "review_note": "Numerical liquidity facts are extractor-owned; VIE and transfer restrictions require official-report text evidence from the evidence agent.",
    },
    {
        "worksheet_id": "shares_sbc_capital_return_bridge",
        "question": "股数/SBC/资本回报桥：SBC、稀释股数、ADS/普通股、回购、分红、股权计划。",
        "core_metrics": ["diluted_shares", "stock_based_compensation"],
        "supporting_metrics": [
            "basic_shares",
            "ordinary_shares_outstanding",
            "ads_outstanding",
            "ordinary_shares_per_ads",
            "share_repurchases",
            "dividends_paid",
            "unrecognized_share_based_compensation",
            "sbc_remaining_vesting_years",
            "equity_plan_authorized_shares",
            "equity_plan_available_shares",
        ],
        "review_note": "Supports per-share dilution and capital-return work. Valuation yield remains outside Financial Evidence.",
    },
]

FINANCIAL_QUESTION_COVERAGE = [
    {
        "question_id": "growth_source",
        "question": "收入增长来自哪里？ / Where does revenue growth come from?",
        "core_metrics": ["revenue"],
        "supporting_metrics": [
            "online_marketing_services_revenue",
            "transaction_services_revenue",
        ],
    },
    {
        "question_id": "margin_change",
        "question": "毛利率、经营利润率有没有变化？ / Are gross and operating margins changing?",
        "core_metrics": ["revenue", "gross_profit", "operating_income"],
        "supporting_metrics": ["cost_of_revenue", "sales_and_marketing_expense"],
    },
    {
        "question_id": "cash_quality",
        "question": "现金流质量好不好？这个公司赚的钱是真钱吗？ / Is cash-flow quality good?",
        "core_metrics": ["net_income", "operating_cash_flow", "free_cash_flow"],
        "supporting_metrics": [
            "stock_based_compensation",
            "depreciation_and_amortization",
            "accounts_receivable",
            "inventory",
            "accounts_payable",
            "deferred_revenue",
        ],
    },
    {
        "question_id": "capital_consumption",
        "question": "增长需要消耗多少资本？ / How much capital does growth consume?",
        "core_metrics": ["capex", "operating_cash_flow", "free_cash_flow"],
        "supporting_metrics": ["current_assets", "current_liabilities", "cash_paid_for_taxes"],
    },
    {
        "question_id": "balance_sheet_risk",
        "question": "资产负债表风险有多大？ / What balance-sheet risks are visible?",
        "core_metrics": ["cash", "total_assets", "total_liabilities"],
        "supporting_metrics": ["short_term_investments", "restricted_cash", "debt", "debt_current", "debt_noncurrent"],
    },
]

CONTEXT_PATTERN = re.compile(
    r"<xbrli:context\b(?P<attrs>[^>]*)>(?P<body>.*?)</xbrli:context>",
    flags=re.IGNORECASE | re.DOTALL,
)
NON_FRACTION_PATTERN = re.compile(
    r"<ix:nonFraction\b(?P<attrs>[^>]*)>(?P<body>.*?)</ix:nonFraction>",
    flags=re.IGNORECASE | re.DOTALL,
)
ATTRIBUTE_PATTERN = re.compile(r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*\"([^\"]*)\"")
TAG_PATTERN = re.compile(r"<[^>]+>")

SKIPPED_CONTEXT_MARKERS = (
    "RelatedParty",
    "CounterpartyNameAxis",
    "StatementEquityComponentsAxis",
    "AwardTypeAxis",
    "PlanNameAxis",
    "FairValueByMeasurementFrequencyAxis",
    "PropertyPlantAndEquipmentByTypeAxis",
    "CumulativeEffectPeriodOfAdoptionAxis",
    "ParentCompanyMember",
    "StatementClassOfStockAxis",
    "VariableInterestEntityPrimaryBeneficiaryMember",
)


def extract_financial_facts_from_documents(documents: list[dict[str, Any]]) -> dict[str, Any]:
    raw_facts: list[dict[str, Any]] = []
    extraction_errors: list[dict[str, str]] = []
    latest_tencent_annual_year = _latest_tencent_annual_year(documents)
    latest_tencent_interim_year = _latest_tencent_interim_year(documents)

    for document in documents:
        if not is_financial_extraction_document(document):
            continue
        path_value = document.get("local_path")
        if not path_value:
            continue
        path = Path(path_value)
        if path.suffix.lower() == ".pdf":
            if (
                document.get("source_id") == "tencent_investor_relations"
                and document.get("report_kind") == "annual"
                and latest_tencent_annual_year is not None
                and int(document.get("fiscal_year") or 0) != latest_tencent_annual_year
            ):
                continue
            if (
                document.get("source_id") == "tencent_investor_relations"
                and document.get("report_kind") == "interim"
                and latest_tencent_interim_year is not None
                and int(document.get("fiscal_year") or 0) != latest_tencent_interim_year
            ):
                continue
            try:
                raw_facts.extend(extract_tencent_report_facts(path, document))
            except Exception as exc:  # noqa: BLE001 - recorded for audit instead of failing the run.
                extraction_errors.append({"path": str(path), "error": str(exc)})
            continue
        if path.suffix.lower() not in {".htm", ".html"}:
            continue
        try:
            raw_facts.extend(_extract_document_facts(path, document))
            raw_facts.extend(extract_earnings_release_facts(path, document))
        except Exception as exc:  # noqa: BLE001 - recorded for audit instead of failing the run.
            extraction_errors.append({"path": str(path), "error": str(exc)})

    selected_facts = _select_best_facts(raw_facts)
    selected_facts = _derive_facts(selected_facts)
    selected_facts = _enrich_fact_metadata(selected_facts)

    counts_by_metric = Counter(fact["metric"] for fact in selected_facts)
    counts_by_period = Counter(fact["period_type"] for fact in selected_facts)
    methods = sorted({fact.get("extraction_method") for fact in selected_facts if fact.get("extraction_method")})
    coverage = _build_extraction_coverage(selected_facts)
    hard_financial_worksheet_coverage = _build_hard_financial_worksheet_coverage(selected_facts)
    annual_statement_coverage = _build_annual_statement_coverage(selected_facts)
    fact_quality_gate = _build_fact_quality_gate(selected_facts, annual_statement_coverage)
    review_flags = _build_extraction_review_flags(selected_facts, coverage)
    disclosure_gap_registry = _build_disclosure_gap_registry(selected_facts, documents)
    if not fact_quality_gate.get("can_generate_full_report"):
        review_flags.insert(
            0,
            {
                "flag_id": "core_fact_quality_gate_failed",
                "severity": "high",
                "missing_metrics": fact_quality_gate.get("missing_core_metrics", []),
                "message": fact_quality_gate.get("message"),
            },
        )
    summary = {
        "raw_fact_count": len(raw_facts),
        "selected_fact_count": len(selected_facts),
        "counts_by_metric": dict(sorted(counts_by_metric.items())),
        "counts_by_period": dict(sorted(counts_by_period.items())),
        "coverage": coverage,
        "hard_financial_worksheet_coverage": hard_financial_worksheet_coverage,
        "annual_statement_coverage": annual_statement_coverage,
        "fact_quality_gate": fact_quality_gate,
        "review_flags": review_flags,
        "disclosure_gap_registry": disclosure_gap_registry,
        "extraction_errors": extraction_errors,
        "method": "official_document_table_extraction",
        "methods_used": methods,
        "canonical_metric_map": _canonical_metric_map(),
        "notes": [
            "Only mapped SEC XBRL tags and controlled official earnings-release table labels are extracted.",
            "Comparative values are deduplicated by metric, unit, and period, preferring the latest official filing.",
            "Gross profit and free cash flow may be derived only from official component tags.",
            "Every selected fact carries canonical metric, statement family, period label, unit, source document, and confidence metadata.",
            "The fact quality gate blocks full report generation when the latest annual core facts are missing.",
            "SEC helper pages and wrapper-only 6-K documents are skipped by the document corpus policy.",
            "Pretax income and stock-based compensation tags are kept to one accounting concept per metric.",
            "Tencent PDF extraction prefers audited statement tables over five-year summary tables for overlapping periods.",
            "Tencent interim PDF extraction is limited to the latest interim report until older PDF scale formats are mapped safely.",
            "Financial extraction is source-gated to SEC/regulator filings and company investor-relations documents; third-party mirrors are rejected.",
            "No number is filled from memory or from non-official sources.",
            "Hard financial worksheet coverage is grouped around revenue, expense, cost-detail, below-operating, working-capital, cash-availability, and dilution/capital-return bridges.",
        ],
}

    return {
        "raw_facts": raw_facts,
        "selected_facts": selected_facts,
        "summary": summary,
    }


def _build_disclosure_gap_registry(
    facts: list[dict[str, Any]],
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not _document_set_looks_like_pdd(documents):
        return []
    present = {str(fact.get("metric")) for fact in facts if fact.get("metric")}
    gap_specs = [
        {
            "gap_id": "temu_standalone_economics",
            "status": "not_disclosed_as_structured_numeric_fact",
            "missing_metrics": ["temu_revenue", "temu_operating_income", "temu_gmv", "temu_fulfillment_cost"],
            "why_it_matters": "Temu/global business may change growth, fulfillment cost, regulation and margin profile.",
        },
        {
            "gap_id": "first_party_brand_unit_economics",
            "status": "not_disclosed_as_structured_numeric_fact",
            "missing_metrics": [
                "first_party_revenue",
                "first_party_inventory_risk",
                "first_party_operating_income",
                "first_party_investment_payback",
            ],
            "why_it_matters": "First-party brand language could make the platform model heavier, but filings do not yet quantify the economics.",
        },
        {
            "gap_id": "cost_of_revenue_subcomponents",
            "status": "narrative_only_unless_future_tables_disclose_amounts",
            "missing_metrics": [
                "fulfillment_expense",
                "payment_processing_expense",
                "server_and_bandwidth_costs",
                "merchant_support_costs",
                "platform_governance_costs",
                "logistics_expense",
            ],
            "why_it_matters": "Cost subcomponents are needed to attribute margin pressure to fulfillment, payment, technology, governance or merchant support.",
        },
        {
            "gap_id": "user_and_transaction_kpis",
            "status": "partially_disclosed",
            "available_metrics": [
                metric
                for metric in [
                    "online_marketing_services_revenue",
                    "transaction_services_revenue",
                ]
                if metric in present
            ],
            "missing_metrics": ["gmv", "active_buyers", "monthly_active_users", "orders", "take_rate"],
            "why_it_matters": "Revenue components are available, but user/volume/take-rate drivers are not stable structured facts.",
        },
        {
            "gap_id": "maintenance_vs_growth_capex",
            "status": "not_disclosed_as_structured_numeric_fact",
            "missing_metrics": ["maintenance_capex", "growth_capex"],
            "why_it_matters": "CapEx split would improve owner-earnings quality, but the filings do not separate it.",
        },
    ]
    return gap_specs


def _document_set_looks_like_pdd(documents: list[dict[str, Any]]) -> bool:
    for document in documents:
        if "pdd" in str(document.get("downloaded_file") or "").lower():
            return True
        if "PDD" in str(document.get("document_id") or ""):
            return True
    return False


def _latest_tencent_annual_year(documents: list[dict[str, Any]]) -> int | None:
    years = [
        int(document.get("fiscal_year"))
        for document in documents
        if document.get("source_id") == "tencent_investor_relations"
        and document.get("report_kind") == "annual"
        and str(document.get("fiscal_year") or "").isdigit()
    ]
    return max(years) if years else None


def _latest_tencent_interim_year(documents: list[dict[str, Any]]) -> int | None:
    years = [
        int(document.get("fiscal_year"))
        for document in documents
        if document.get("source_id") == "tencent_investor_relations"
        and document.get("report_kind") == "interim"
        and str(document.get("fiscal_year") or "").isdigit()
    ]
    return max(years) if years else None


def derive_official_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _derive_facts(facts)


def verify_financial_facts(raw_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for fact in raw_facts:
        key = (
            fact.get("metric"),
            fact.get("unit"),
            fact.get("period_type"),
            fact.get("start_date"),
            fact.get("end_date"),
            fact.get("instant"),
        )
        grouped[key].append(fact)

    results: list[dict[str, Any]] = []
    for key, facts in sorted(grouped.items(), key=lambda item: str(item[0])):
        best_rank = min(_context_rank(fact.get("context_ref") or "") for fact in facts)
        facts = [fact for fact in facts if _context_rank(fact.get("context_ref") or "") == best_rank]
        values = [fact["value"] for fact in facts if fact.get("value") is not None]
        if len(values) <= 1:
            continue
        low = min(values)
        high = max(values)
        denominator = max(abs(high), abs(low), 1.0)
        mismatch_pct = abs(high - low) / denominator
        if mismatch_pct == 0:
            continue
        status = "material_conflict" if mismatch_pct > 0.02 else "accepted_rounding_difference"
        results.append(
            {
                "status": status,
                "severity": "high" if status == "material_conflict" else "info",
                "metric": key[0],
                "unit": key[1],
                "period_type": key[2],
                "start_date": key[3],
                "end_date": key[4],
                "instant": key[5],
                "mismatch_pct": mismatch_pct,
                "min_value": low,
                "max_value": high,
                "sources": sorted(
                    {
                        f"{fact.get('accession_number')}:{fact.get('downloaded_file')}"
                        for fact in facts
                    }
                ),
                "explanation": "Official filing values differ by more than 2%."
                if status == "material_conflict"
                else "Difference is within the 2% rounding tolerance.",
                "context_rank": best_rank,
            }
        )

    if not results:
        results.append(
            {
                "status": "passed_no_material_conflicts",
                "severity": "info",
                "explanation": "No official-to-official extracted fact conflicts exceeded the 2% materiality rule.",
            }
        )
    return results


def _enrich_fact_metadata(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for fact in facts:
        metric = str(fact.get("metric") or "")
        metadata = _metric_metadata(metric)
        unit = fact.get("unit")
        confidence = str(fact.get("confidence") or "medium")
        period_label = _period_label(fact)
        enriched.append(
            {
                **fact,
                "canonical_metric": metric,
                "metric_family": metadata["metric_family"],
                "financial_statement": metadata["financial_statement"],
                "source_table": metadata["source_table"],
                "currency": _currency_from_unit(unit),
                "value_scale": 1,
                "display_unit": _display_unit(unit),
                "period_label": period_label,
                "period_year": _fact_year(fact),
                "confidence_score": _confidence_score(confidence, str(fact.get("extraction_method") or "")),
                "source_document_type": fact.get("document_type"),
                "source_document": fact.get("downloaded_file") or fact.get("document_id"),
                "source_accession_number": fact.get("accession_number"),
            }
        )
    return enriched


def _metric_metadata(metric: str) -> dict[str, str]:
    if metric in METRIC_METADATA:
        return METRIC_METADATA[metric]
    if metric.startswith("non_gaap_"):
        return {
            "metric_family": "non_gaap_bridge",
            "financial_statement": "non_gaap_reconciliation",
            "source_table": "official_non_gaap_reconciliation",
        }
    return {
        "metric_family": "other_official_fact",
        "financial_statement": "unknown",
        "source_table": "unknown",
    }


def _canonical_metric_map() -> dict[str, Any]:
    mapped_metrics = sorted(set(TARGET_TAGS) | set(METRIC_METADATA))
    output: dict[str, Any] = {}
    for metric in mapped_metrics:
        metadata = _metric_metadata(metric)
        output[metric] = {
            "label": (TARGET_TAGS.get(metric) or {}).get("label") or _humanize_metric(metric),
            "tags": (TARGET_TAGS.get(metric) or {}).get("tags", []),
            "metric_family": metadata["metric_family"],
            "financial_statement": metadata["financial_statement"],
            "source_table": metadata["source_table"],
        }
    output["non_gaap_*"] = {
        "label": "Non-GAAP bridge row",
        "tags": [],
        "metric_family": "non_gaap_bridge",
        "financial_statement": "non_gaap_reconciliation",
        "source_table": "official_non_gaap_reconciliation",
    }
    return output


def _humanize_metric(metric: str) -> str:
    return metric.replace("_", " ").title()


def _currency_from_unit(unit: Any) -> str | None:
    unit_text = str(unit or "")
    if unit_text == "CNY":
        return "RMB"
    if unit_text == "USD":
        return "USD"
    return None


def _display_unit(unit: Any) -> str | None:
    unit_text = str(unit or "")
    if unit_text == "CNY":
        return "RMB"
    if unit_text == "USD":
        return "USD"
    if unit_text == "shares":
        return "shares"
    if unit_text == "pure":
        return "ratio"
    return unit_text or None


def _confidence_score(confidence: str, extraction_method: str) -> float:
    if confidence == "high":
        return 0.98
    if confidence == "medium":
        if extraction_method.startswith("official_earnings_release"):
            return 0.90
        if extraction_method.startswith("derived_from"):
            return 0.86
        return 0.80
    return 0.55


def _period_label(fact: dict[str, Any]) -> str | None:
    year = _fact_year(fact)
    if year is None:
        return None
    period_type = fact.get("period_type")
    if period_type == "annual":
        return f"FY{year}"
    if period_type == "quarter":
        end_date = str(fact.get("end_date") or "")
        quarter = {"03": "Q1", "06": "Q2", "09": "Q3", "12": "Q4"}.get(end_date[5:7])
        return f"{year} {quarter}" if quarter else f"{year} quarter"
    if period_type == "half_year":
        return f"H1 {year}"
    if period_type == "nine_month":
        return f"9M {year}"
    if period_type == "instant":
        return f"{year}-end" if str(fact.get("end_date") or "").endswith("-12-31") else str(fact.get("end_date") or "")
    return str(fact.get("end_date") or fact.get("instant") or "")


def _fact_year(fact: dict[str, Any]) -> int | None:
    date_value = str(fact.get("end_date") or fact.get("instant") or "")
    if len(date_value) >= 4 and date_value[:4].isdigit():
        return int(date_value[:4])
    return None


def _build_annual_statement_coverage(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    years = sorted(
        {
            _fact_year(fact)
            for fact in facts
            if _fact_year(fact) is not None and _is_annual_or_year_end_fact(fact)
        }
    )
    output: list[dict[str, Any]] = []
    for year in years[-5:]:
        present_metrics = {
            str(fact.get("metric"))
            for fact in facts
            if _fact_year(fact) == year and _is_annual_or_year_end_fact(fact)
        }
        groups = {
            group: _coverage_group(required, sorted(present_metrics))
            for group, required in STATEMENT_COVERAGE_GROUPS.items()
        }
        output.append(
            {
                "year": year,
                "present_metric_count": len(present_metrics),
                "groups": groups,
            }
        )
    return output


def _is_annual_or_year_end_fact(fact: dict[str, Any]) -> bool:
    if fact.get("period_type") == "annual":
        return True
    if fact.get("period_type") == "instant" and str(fact.get("end_date") or fact.get("instant") or "").endswith("-12-31"):
        return True
    return False


def _build_fact_quality_gate(
    facts: list[dict[str, Any]],
    annual_statement_coverage: list[dict[str, Any]],
) -> dict[str, Any]:
    latest_year = _latest_annual_year(facts)
    if latest_year is None:
        return {
            "status": "failed",
            "can_generate_full_report": False,
            "latest_annual_year": None,
            "required_core_metrics": FACT_QUALITY_GATE_CORE_METRICS,
            "missing_core_metrics": FACT_QUALITY_GATE_CORE_METRICS,
            "message": "No latest annual period with revenue was extracted.",
            "message_zh": "没有抽取到可作为年度锚点的收入事实，不能生成完整财务报告。",
            "annual_statement_coverage": annual_statement_coverage,
        }
    present = {
        str(fact.get("metric"))
        for fact in facts
        if _fact_year(fact) == latest_year and _is_annual_or_year_end_fact(fact)
    }
    missing = [metric for metric in FACT_QUALITY_GATE_CORE_METRICS if metric not in present]
    can_generate = not missing
    return {
        "status": "passed" if can_generate else "failed",
        "can_generate_full_report": can_generate,
        "latest_annual_year": latest_year,
        "required_core_metrics": FACT_QUALITY_GATE_CORE_METRICS,
        "present_core_metrics": [metric for metric in FACT_QUALITY_GATE_CORE_METRICS if metric in present],
        "missing_core_metrics": missing,
        "coverage_level": "full_core" if can_generate else "core_gap",
        "message": "Latest annual core facts are present." if can_generate else "Latest annual core facts are missing.",
        "message_zh": "最新年度核心事实已抽齐，可以生成完整财务报告。"
        if can_generate
        else f"最新年度核心事实缺失：{', '.join(missing)}。不能生成完整财务报告。",
        "annual_statement_coverage": annual_statement_coverage,
    }


def _latest_annual_year(facts: list[dict[str, Any]]) -> int | None:
    revenue_years = sorted(
        {
            _fact_year(fact)
            for fact in facts
            if fact.get("metric") == "revenue"
            and fact.get("period_type") == "annual"
            and _fact_year(fact) is not None
        }
    )
    if revenue_years:
        return revenue_years[-1]
    annual_years = sorted(
        {
            _fact_year(fact)
            for fact in facts
            if fact.get("period_type") == "annual" and _fact_year(fact) is not None
        }
    )
    return annual_years[-1] if annual_years else None


def _build_extraction_coverage(facts: list[dict[str, Any]]) -> dict[str, Any]:
    present_metrics = sorted({str(fact.get("metric")) for fact in facts if fact.get("metric")})
    return {
        "present_metrics": present_metrics,
        "priority_a": _coverage_group(CORE_PRIORITY_A_METRICS, present_metrics),
        "priority_b": _coverage_group(CORE_PRIORITY_B_METRICS, present_metrics),
        "question_coverage": [
            _question_coverage(question, present_metrics) for question in FINANCIAL_QUESTION_COVERAGE
        ],
    }


def _build_hard_financial_worksheet_coverage(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    present_metrics = sorted({str(fact.get("metric")) for fact in facts if fact.get("metric")})
    present = set(present_metrics)
    return [
        _hard_financial_worksheet_row(worksheet, present, facts)
        for worksheet in HARD_FINANCIAL_WORKSHEETS
    ]


def _hard_financial_worksheet_row(
    worksheet: dict[str, Any],
    present: set[str],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    core_metrics = list(worksheet.get("core_metrics") or [])
    supporting_metrics = list(worksheet.get("supporting_metrics") or [])
    available_core = [metric for metric in core_metrics if metric in present]
    missing_core = [metric for metric in core_metrics if metric not in present]
    available_supporting = [metric for metric in supporting_metrics if metric in present]
    missing_supporting = [metric for metric in supporting_metrics if metric not in present]

    if core_metrics:
        if not missing_core and available_supporting:
            status = "supported"
        elif not missing_core:
            status = "core_supported"
        elif available_core or available_supporting:
            status = "partial"
        else:
            status = "missing"
    elif available_supporting:
        status = "optional_detail_supported"
    else:
        status = "optional_detail_missing"

    relevant_metrics = core_metrics + supporting_metrics
    return {
        "worksheet_id": worksheet["worksheet_id"],
        "question": worksheet["question"],
        "status": status,
        "available_core_metrics": available_core,
        "missing_core_metrics": missing_core,
        "available_supporting_metrics": available_supporting,
        "missing_supporting_metrics": missing_supporting,
        "period_coverage": _period_coverage_for_metrics(facts, relevant_metrics),
        "source_fact_ids": _source_fact_ids_for_metrics(facts, relevant_metrics),
        "text_evidence_needed": list(worksheet.get("text_evidence_needed") or []),
        "review_note": worksheet.get("review_note"),
    }


def _period_coverage_for_metrics(
    facts: list[dict[str, Any]],
    metrics: list[str],
) -> dict[str, Any]:
    metric_set = set(metrics)
    annual_years = sorted(
        {
            _fact_year(fact)
            for fact in facts
            if fact.get("metric") in metric_set
            and fact.get("period_type") == "annual"
            and _fact_year(fact) is not None
        }
    )
    quarter_ends = sorted(
        {
            str(fact.get("end_date"))
            for fact in facts
            if fact.get("metric") in metric_set
            and fact.get("period_type") == "quarter"
            and fact.get("end_date")
        }
    )
    instant_dates = sorted(
        {
            str(fact.get("instant") or fact.get("end_date"))
            for fact in facts
            if fact.get("metric") in metric_set
            and fact.get("period_type") == "instant"
            and (fact.get("instant") or fact.get("end_date"))
        }
    )
    return {
        "annual_years": annual_years,
        "latest_annual_year": annual_years[-1] if annual_years else None,
        "quarter_ends": quarter_ends,
        "latest_quarter_end": quarter_ends[-1] if quarter_ends else None,
        "instant_dates": instant_dates,
        "latest_instant_date": instant_dates[-1] if instant_dates else None,
    }


def _source_fact_ids_for_metrics(facts: list[dict[str, Any]], metrics: list[str]) -> list[str]:
    metric_set = set(metrics)
    return sorted(
        {
            str(fact.get("fact_id"))
            for fact in facts
            if fact.get("metric") in metric_set and fact.get("fact_id")
        }
    )


def _coverage_group(required_metrics: list[str], present_metrics: list[str]) -> dict[str, Any]:
    present = set(present_metrics)
    return {
        "present": [metric for metric in required_metrics if metric in present],
        "missing": [metric for metric in required_metrics if metric not in present],
    }


def _question_coverage(question: dict[str, Any], present_metrics: list[str]) -> dict[str, Any]:
    present = set(present_metrics)
    core_metrics = list(question["core_metrics"])
    supporting_metrics = list(question["supporting_metrics"])
    available_core = [metric for metric in core_metrics if metric in present]
    missing_core = [metric for metric in core_metrics if metric not in present]
    available_supporting = [metric for metric in supporting_metrics if metric in present]
    missing_supporting = [metric for metric in supporting_metrics if metric not in present]
    if not missing_core and available_supporting:
        status = "supported"
    elif not missing_core:
        status = "basic_supported"
    elif available_core:
        status = "partial"
    else:
        status = "missing"
    return {
        "question_id": question["question_id"],
        "question": question["question"],
        "status": status,
        "available_core_metrics": available_core,
        "missing_core_metrics": missing_core,
        "available_supporting_metrics": available_supporting,
        "missing_supporting_metrics": missing_supporting,
    }


def _build_extraction_review_flags(
    facts: list[dict[str, Any]],
    coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    present = {str(fact.get("metric")) for fact in facts if fact.get("metric")}
    flags: list[dict[str, Any]] = []
    if not facts:
        return [
            {
                "flag_id": "no_official_financial_facts_extracted",
                "severity": "high",
                "message": "No mapped official financial facts were extracted from the eligible document set.",
            }
        ]

    priority_a_missing = coverage.get("priority_a", {}).get("missing", [])
    if priority_a_missing:
        flags.append(
            {
                "flag_id": "priority_a_metric_gap",
                "severity": "medium",
                "missing_metrics": priority_a_missing,
                "message": "Some core financial-statement facts are still missing from mapped extraction.",
            }
        )

    if {"cash", "total_assets", "total_liabilities"} & present and not ({"debt", "debt_current", "debt_noncurrent"} & present):
        flags.append(
            {
                "flag_id": "interest_bearing_debt_not_explicitly_extracted",
                "severity": "info",
                "message": "No explicit interest-bearing debt fact was extracted. The extractor does not assume debt is zero.",
            }
        )

    working_capital_metrics = {
        "accounts_receivable",
        "inventory",
        "accounts_payable",
        "accounts_payable_and_accrued_expenses",
        "accrued_expenses",
        "deferred_revenue",
    }
    if "operating_cash_flow" in present and not (working_capital_metrics & present):
        flags.append(
            {
                "flag_id": "working_capital_detail_gap",
                "severity": "medium",
                "message": "Operating cash flow was extracted, but working-capital detail was not. Cash-conversion analysis should remain cautious.",
            }
        )

    revenue_breakdown_metrics = {
        "online_marketing_services_revenue",
        "transaction_services_revenue",
    }
    if "revenue" in present and not (revenue_breakdown_metrics & present):
        flags.append(
            {
                "flag_id": "revenue_breakdown_gap",
                "severity": "info",
                "message": "Revenue was extracted, but no controlled revenue breakdown fact was found in the mapped tags/tables.",
            }
        )

    cost_subcomponent_metrics = {
        "fulfillment_expense",
        "payment_processing_expense",
        "server_and_bandwidth_costs",
        "merchant_support_costs",
        "platform_governance_costs",
        "logistics_expense",
    }
    if "cost_of_revenue" in present and not (cost_subcomponent_metrics & present):
        flags.append(
            {
                "flag_id": "cost_subcomponent_detail_gap",
                "severity": "info",
                "message": "Cost of revenue was extracted, but no fulfillment/payment/server/merchant-support/platform-governance cost subcomponent was found in controlled official tables.",
            }
        )

    has_earnings_release_table = any(
        str(fact.get("extraction_method") or "").startswith("official_earnings_release")
        for fact in facts
    )
    has_non_gaap_bridge = any(str(fact.get("metric") or "").startswith("non_gaap_") for fact in facts)
    if has_earnings_release_table and not has_non_gaap_bridge:
        flags.append(
            {
                "flag_id": "non_gaap_bridge_not_extracted",
                "severity": "info",
                "message": "Official earnings-release facts were extracted, but no non-GAAP bridge rows were found by the controlled parser.",
            }
        )

    return flags


def _extract_document_facts(path: Path, document: dict[str, Any]) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    contexts = _parse_contexts(text)
    facts = []
    for match in NON_FRACTION_PATTERN.finditer(text):
        attrs = _parse_attrs(match.group("attrs"))
        name = attrs.get("name")
        if not name:
            continue
        metric = TAG_TO_METRIC.get(name.lower())
        if not metric:
            continue
        context_ref = attrs.get("contextRef") or attrs.get("contextref")
        if not context_ref:
            continue
        context = contexts.get(context_ref, {"context_id": context_ref})
        if _skip_context(context_ref):
            continue
        unit = attrs.get("unitRef") or attrs.get("unitref")
        value = _parse_number(match.group("body"), attrs)
        if value is None:
            continue
        adjustment_note = None
        if metric in {"basic_shares", "diluted_shares"} and value and value < 100_000_000:
            value *= 1000
            adjustment_note = "Applied share-count scale normalization: values below 100 million are treated as thousands."
        period = _period_fields(context)
        fact_id = (
            f"{document.get('document_id')}:{metric}:"
            f"{period.get('start_date') or ''}:{period.get('end_date') or period.get('instant') or ''}:"
            f"{unit or ''}:{len(facts)}"
        )
        facts.append(
            {
                "fact_id": fact_id,
                "metric": metric,
                "label": TARGET_TAGS[metric]["label"],
                "xbrl_tag": name,
                "context_ref": context_ref,
                "context_rank": _context_rank(context_ref),
                "value": value,
                "unit": _normalize_unit(unit),
                "period_type": period["period_type"],
                "start_date": period.get("start_date"),
                "end_date": period.get("end_date"),
                "instant": period.get("instant"),
                "source_id": document.get("source_id"),
                "source_url": document.get("source_url"),
                "local_path": document.get("local_path"),
                "document_id": document.get("document_id"),
                "document_type": document.get("document_type"),
                "accession_number": _accession_from_document(document),
                "downloaded_file": document.get("downloaded_file"),
                "filing_date": document.get("filing_date"),
                "report_date": document.get("report_date"),
                "confidence": "high",
                "extraction_method": "inline_xbrl_tag",
                "adjustment_note": adjustment_note,
            }
        )
    facts.extend(_extract_controlled_html_table_facts(text, document))
    return facts


ANNUAL_DURATION_TABLE_ROWS: list[tuple[str, tuple[str, ...], str]] = [
    ("online_marketing_services_revenue", ("online marketing services and others",), "signed"),
    ("transaction_services_revenue", ("transaction services",), "signed"),
    ("revenue", ("revenues",), "signed"),
    ("cost_of_revenue", ("costs of revenues",), "expense_abs"),
    ("sales_and_marketing_expense", ("sales and marketing",), "expense_abs"),
    ("general_and_administrative_expense", ("general and administrative",), "expense_abs"),
    ("research_and_development_expense", ("research and development",), "expense_abs"),
    ("fulfillment_expense", ("fulfillment",), "expense_abs"),
    ("payment_processing_expense", ("payment", "processing"), "expense_abs"),
    ("server_and_bandwidth_costs", ("server", "bandwidth"), "expense_abs"),
    ("merchant_support_costs", ("merchant", "support"), "expense_abs"),
    ("platform_governance_costs", ("platform", "governance"), "expense_abs"),
    ("logistics_expense", ("logistics",), "expense_abs"),
    ("operating_income", ("operating profit",), "signed"),
    ("investment_income", ("interest and investment income",), "signed"),
    ("interest_expense", ("interest expenses",), "expense_abs"),
    ("foreign_exchange_gain_loss", ("foreign exchange",), "signed"),
    ("other_income_net", ("other income, net",), "signed"),
    ("pretax_income", ("profit before income tax",), "signed"),
    ("tax_expense", ("income tax expenses",), "expense_abs"),
    ("equity_method_income", ("share of results of equity investees",), "signed"),
    ("net_income", ("net income",), "signed"),
]

CASH_FLOW_BRIDGE_TABLE_ROWS: list[tuple[str, tuple[str, ...], str]] = [
    ("change_in_receivables_from_online_payment_platforms", ("receivables from online payment platforms",), "signed"),
    ("change_in_prepayments_and_other_current_assets", ("prepayments and other current assets",), "signed"),
    ("change_in_deferred_revenue", ("customer advances and deferred revenues",), "signed"),
    ("change_in_payable_to_merchants", ("payable to merchants",), "signed"),
    ("change_in_accrued_expenses_and_other_liabilities", ("accrued expenses and other liabilities",), "signed"),
    ("change_in_merchant_deposits", ("merchant deposits",), "signed"),
    ("change_in_lease_liabilities", ("lease liabilities",), "signed"),
    ("fair_value_change_of_investments", ("fair value change of investments",), "signed"),
]

INSTANT_TABLE_ROWS: list[tuple[str, tuple[str, ...], str]] = [
    ("cash", ("cash and cash equivalents",), "signed"),
    ("restricted_cash", ("restricted cash",), "signed"),
    ("receivables_from_online_payment_platforms", ("receivables from online payment platforms",), "signed"),
    ("short_term_investments", ("short-term investments",), "signed"),
    ("prepayments_and_other_current_assets", ("prepayments and other current assets",), "signed"),
    ("current_assets", ("total current assets",), "signed"),
    ("total_assets", ("total assets",), "signed"),
    ("customer_advances_and_deferred_revenues", ("customer advances and deferred revenues",), "signed"),
    ("deferred_revenue", ("customer advances and deferred revenues",), "signed"),
    ("payable_to_merchants", ("payable to merchants",), "signed"),
    ("accounts_payable_and_accrued_expenses", ("accrued expenses and other liabilities",), "signed"),
    ("merchant_deposits", ("merchant deposits",), "signed"),
    ("convertible_debt_current", ("convertible bonds, current portion",), "signed"),
    ("debt_current", ("convertible bonds, current portion",), "signed"),
    ("current_liabilities", ("total current liabilities",), "signed"),
    ("total_liabilities", ("total liabilities",), "signed"),
]


def _extract_controlled_html_table_facts(raw_html: str, document: dict[str, Any]) -> list[dict[str, Any]]:
    if not _looks_like_pdd_annual_20f(document, raw_html):
        return []
    tables = _HtmlTableParser.parse(raw_html)
    facts: list[dict[str, Any]] = []
    for table_index, table in enumerate(tables):
        table_text = _table_text(table)
        multiplier = _table_amount_multiplier(table_text)
        if multiplier == 1:
            multiplier = 1_000
        if _is_annual_financial_table(table_text):
            years = _years_from_table(table_text, expected=3)
            if years:
                facts.extend(
                    _extract_annual_duration_rows(
                        table=table,
                        document=document,
                        years=years,
                        multiplier=multiplier,
                        table_index=table_index,
                    )
                )
        if _is_annual_cash_flow_bridge_table(table_text):
            years = _years_from_table(table_text, expected=3)
            if years:
                facts.extend(
                    _extract_cash_flow_bridge_rows(
                        table=table,
                        document=document,
                        years=years,
                        multiplier=multiplier,
                        table_index=table_index,
                    )
                )
        if _is_balance_sheet_table(table_text):
            years = _years_from_table(table_text, expected=2)
            if years:
                facts.extend(
                    _extract_instant_rows(
                        table=table,
                        document=document,
                        years=years,
                        multiplier=multiplier,
                        table_index=table_index,
                    )
                )
    return facts


def _looks_like_pdd_annual_20f(document: dict[str, Any], raw_html: str) -> bool:
    if document.get("document_type") not in {"20-F:primary", "20-F"}:
        return False
    downloaded_file = str(document.get("downloaded_file") or "").lower()
    if "pdd-" in downloaded_file or "pdd holdings" in raw_html[:500_000].lower():
        return True
    return False


def _is_annual_financial_table(table_text: str) -> bool:
    return (
        "for the years ended december 31" in table_text
        and "percentages" not in table_text
        and "online marketing services and others" in table_text
        and "transaction services" in table_text
    ) or (
        "for the years ended december 31" in table_text
        and "percentages" not in table_text
        and "costs of revenues" in table_text
        and "operating profit" in table_text
        and "interest and investment income" in table_text
    )


def _is_annual_cash_flow_bridge_table(table_text: str) -> bool:
    return (
        "for the years ended december 31" in table_text
        and "cash flow from operating activities" in table_text
        and "changes in operating assets and liabilities" in table_text
    )


def _is_balance_sheet_table(table_text: str) -> bool:
    return (
        "as of december 31" in table_text
        and "current assets" in table_text
        and "total assets" in table_text
        and "receivables from online payment platforms" in table_text
        and "payable to merchants" in table_text
        and "merchant deposits" in table_text
        and "total current liabilities" in table_text
        and "total liabilities" in table_text
    )


def _extract_annual_duration_rows(
    *,
    table: list[list[str]],
    document: dict[str, Any],
    years: list[int],
    multiplier: int,
    table_index: int,
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for metric, labels, sign_policy in ANNUAL_DURATION_TABLE_ROWS:
        row = _find_table_row(table, labels)
        if row is None:
            continue
        values = _value_cells_for_row(row, expected_count=len(years))
        if len(values) < len(years):
            continue
        for offset, year in enumerate(years):
            value = _apply_sign_policy(values[offset], sign_policy)
            facts.append(
                _controlled_table_fact(
                    document=document,
                    metric=metric,
                    label=(TARGET_TAGS.get(metric) or {}).get("label") or _humanize_metric(metric),
                    value=value * multiplier,
                    unit="CNY",
                    period_type="annual",
                    start_date=f"{year}-01-01",
                    end_date=f"{year}-12-31",
                    fact_index=len(facts),
                    table_index=table_index,
                    extraction_method="official_20f_html_annual_financial_table",
                )
            )
    return facts


def _extract_cash_flow_bridge_rows(
    *,
    table: list[list[str]],
    document: dict[str, Any],
    years: list[int],
    multiplier: int,
    table_index: int,
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for metric, labels, sign_policy in CASH_FLOW_BRIDGE_TABLE_ROWS:
        row = _find_table_row(table, labels)
        if row is None:
            continue
        values = _value_cells_for_row(row, expected_count=len(years))
        if len(values) < len(years):
            continue
        for offset, year in enumerate(years):
            value = _apply_sign_policy(values[offset], sign_policy)
            facts.append(
                _controlled_table_fact(
                    document=document,
                    metric=metric,
                    label=(TARGET_TAGS.get(metric) or {}).get("label") or _humanize_metric(metric),
                    value=value * multiplier,
                    unit="CNY",
                    period_type="annual",
                    start_date=f"{year}-01-01",
                    end_date=f"{year}-12-31",
                    fact_index=len(facts),
                    table_index=table_index,
                    extraction_method="official_20f_html_cash_flow_bridge_table",
                )
            )
    return facts


def _extract_instant_rows(
    *,
    table: list[list[str]],
    document: dict[str, Any],
    years: list[int],
    multiplier: int,
    table_index: int,
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    section = ""
    for row in table:
        label = _clean_cell(_row_label(row)).lower()
        if label.startswith("current assets"):
            section = "current assets"
            continue
        if label.startswith("non-current assets"):
            section = "non-current assets"
            continue
        if label.startswith("current liabilities"):
            section = "current liabilities"
            continue
        if label.startswith("non-current liabilities"):
            section = "non-current liabilities"
            continue
        matched_rows = list(INSTANT_TABLE_ROWS)
        if label == "lease liabilities" and section == "current liabilities":
            matched_rows.append(("lease_liabilities_current", ("lease liabilities",), "signed"))
        if label == "lease liabilities" and section == "non-current liabilities":
            matched_rows.append(("lease_liabilities_noncurrent", ("lease liabilities",), "signed"))
        for metric, labels, sign_policy in matched_rows:
            if not _label_matches(label, labels):
                continue
            if metric == "lease_liabilities_current" and section not in {"current liabilities", ""}:
                continue
            if metric == "lease_liabilities_noncurrent" and section != "non-current liabilities":
                continue
            values = _value_cells_for_row(row, expected_count=len(years))
            if len(values) < len(years):
                continue
            for offset, year in enumerate(years):
                value = _apply_sign_policy(values[offset], sign_policy)
                facts.append(
                    _controlled_table_fact(
                        document=document,
                        metric=metric,
                        label=(TARGET_TAGS.get(metric) or {}).get("label") or _humanize_metric(metric),
                        value=value * multiplier,
                        unit="CNY",
                        period_type="instant",
                        start_date=None,
                        end_date=f"{year}-12-31",
                        fact_index=len(facts),
                        table_index=table_index,
                        extraction_method="official_20f_html_balance_sheet_table",
                    )
                )
    return facts


def _controlled_table_fact(
    *,
    document: dict[str, Any],
    metric: str,
    label: str,
    value: float,
    unit: str,
    period_type: str,
    start_date: str | None,
    end_date: str,
    fact_index: int,
    table_index: int,
    extraction_method: str,
) -> dict[str, Any]:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return {
        "fact_id": (
            f"{document.get('document_id')}:{metric}:{start_date or ''}:{end_date}:"
            f"{extraction_method}:table{table_index}:row{fact_index}"
        ),
        "metric": metric,
        "label": label,
        "xbrl_tag": None,
        "context_ref": None,
        "context_rank": 2,
        "value": value,
        "unit": unit,
        "period_type": period_type,
        "start_date": start_date,
        "end_date": end_date,
        "instant": end_date if period_type == "instant" else None,
        "source_id": document.get("source_id"),
        "source_url": document.get("source_url"),
        "local_path": document.get("local_path"),
        "document_id": document.get("document_id"),
        "document_type": document.get("document_type"),
        "accession_number": _accession_from_document(document),
        "downloaded_file": document.get("downloaded_file"),
        "filing_date": document.get("filing_date"),
        "report_date": document.get("report_date"),
        "confidence": "medium",
        "extraction_method": extraction_method,
        "selection_policy": "controlled_html_table_fallback_after_xbrl",
    }


def _table_text(table: list[list[str]]) -> str:
    return " ".join(" ".join(_clean_cell(cell) for cell in row) for row in table).lower()


def _table_amount_multiplier(table_text: str) -> int:
    if "in millions" in table_text:
        return 1_000_000
    if "in thousands" in table_text:
        return 1_000
    return 1


def _years_from_table(table_text: str, *, expected: int) -> list[int]:
    years = sorted({int(year) for year in re.findall(r"\b20\d{2}\b", table_text)})
    return years[-expected:] if len(years) >= expected else []


def _find_table_row(table: list[list[str]], labels: tuple[str, ...]) -> list[str] | None:
    for row in table:
        label = _clean_cell(_row_label(row)).lower()
        if _label_matches(label, labels):
            return row
    return None


def _row_label(row: list[str]) -> str:
    return row[0] if row else ""


def _label_matches(label: str, labels: tuple[str, ...]) -> bool:
    if labels and labels[0] in {
        "share of results of equity investees",
        "income tax expenses",
        "net income",
    }:
        return label.startswith(labels[0])
    return all(item in label for item in labels)


def _value_cells_for_row(row: list[str], *, expected_count: int) -> list[float]:
    values: list[float] = []
    for cell in row[1:]:
        cleaned = _clean_cell(cell)
        if not cleaned:
            continue
        if _is_note_cell(cleaned) and not values:
            continue
        parsed = _parse_table_value_cell(cleaned)
        if parsed is None:
            continue
        values.append(parsed)
        if len(values) >= expected_count:
            break
    return values


def _clean_cell(cell: str) -> str:
    cleaned = html.unescape(cell or "")
    cleaned = cleaned.replace("\u200b", "").replace("\xa0", " ").strip()
    return re.sub(r"\s+", " ", cleaned)


def _is_note_cell(cell: str) -> bool:
    return bool(re.fullmatch(r"\d{1,2}", cell))


def _parse_table_value_cell(cell: str) -> float | None:
    if cell in {"—", "-", "--"}:
        return 0
    match = re.search(r"\(?\s*-?\d[\d,]*(?:\.\d+)?\s*\)?", cell)
    if not match:
        return None
    raw = match.group(0)
    negative = raw.strip().startswith("(")
    cleaned = raw.replace(",", "").replace("(", "").replace(")", "").strip()
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


def _apply_sign_policy(value: float, sign_policy: str) -> float:
    if sign_policy == "expense_abs":
        return abs(value)
    return value


def _parse_contexts(text: str) -> dict[str, dict[str, str]]:
    contexts = {}
    for match in CONTEXT_PATTERN.finditer(text):
        attrs = _parse_attrs(match.group("attrs"))
        context_id = attrs.get("id")
        if not context_id:
            continue
        body = match.group("body")
        start_date = _first_match(r"<xbrli:startDate>([^<]+)</xbrli:startDate>", body)
        end_date = _first_match(r"<xbrli:endDate>([^<]+)</xbrli:endDate>", body)
        instant = _first_match(r"<xbrli:instant>([^<]+)</xbrli:instant>", body)
        contexts[context_id] = {
            "context_id": context_id,
            "start_date": start_date,
            "end_date": end_date,
            "instant": instant,
        }
    return contexts


def _period_fields(context: dict[str, str]) -> dict[str, str | None]:
    start = context.get("start_date")
    end = context.get("end_date")
    instant = context.get("instant")
    if start and end:
        return {
            "period_type": _duration_type(start, end),
            "start_date": start,
            "end_date": end,
            "instant": None,
        }
    return {
        "period_type": "instant",
        "start_date": None,
        "end_date": instant,
        "instant": instant,
    }


def _duration_type(start: str, end: str) -> str:
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError:
        return "duration"
    days = (end_date - start_date).days + 1
    if start.endswith("-01-01") and end.endswith("-12-31"):
        return "annual"
    if 80 <= days <= 100:
        return "quarter"
    if 170 <= days <= 190:
        return "half_year"
    if 260 <= days <= 285:
        return "nine_month"
    return "duration"


def _select_best_facts(raw_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for fact in raw_facts:
        key = (
            fact.get("metric"),
            fact.get("unit"),
            fact.get("period_type"),
            fact.get("start_date"),
            fact.get("end_date"),
            fact.get("instant"),
        )
        grouped[key].append(fact)

    selected = []
    for facts in grouped.values():
        facts = sorted(
            facts,
            key=lambda fact: (
                -int(fact.get("context_rank", 99)),
                _extraction_method_rank(fact),
                fact.get("filing_date") or "",
                fact.get("accession_number") or "",
                fact.get("downloaded_file") or "",
            ),
            reverse=True,
        )
        selected.append({**facts[0], "selection_policy": "latest_official_filing_for_same_period"})
    return sorted(
        selected,
        key=lambda fact: (
            str(fact.get("end_date") or fact.get("instant") or ""),
            str(fact.get("metric") or ""),
            str(fact.get("unit") or ""),
        ),
    )


def _extraction_method_rank(fact: dict[str, Any]) -> int:
    method = str(fact.get("extraction_method") or "")
    if method == "inline_xbrl_tag":
        return 100
    if "income_statement" in method or "cash_flow" in method or "financial_position" in method:
        return 90
    if "adjusted_ebitda" in method:
        return 80
    if "financial_summary" in method:
        return 60
    return 50


def _derive_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = list(facts)
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for fact in facts:
        key = (
            fact.get("unit"),
            fact.get("period_type"),
            fact.get("start_date"),
            fact.get("end_date"),
            fact.get("instant"),
        )
        grouped[key][fact["metric"]] = fact

    for key, by_metric in grouped.items():
        if "debt_current" not in by_metric and "convertible_debt_current" in by_metric:
            output.append(
                _derived_fact(
                    metric="debt_current",
                    label="Current interest-bearing debt",
                    value=by_metric["convertible_debt_current"]["value"],
                    source_facts=[by_metric["convertible_debt_current"]],
                    formula="convertible_debt_current",
                )
            )
        if "debt_noncurrent" not in by_metric and "convertible_debt_noncurrent" in by_metric:
            output.append(
                _derived_fact(
                    metric="debt_noncurrent",
                    label="Noncurrent interest-bearing debt",
                    value=by_metric["convertible_debt_noncurrent"]["value"],
                    source_facts=[by_metric["convertible_debt_noncurrent"]],
                    formula="convertible_debt_noncurrent",
                )
            )
        if "gross_profit" not in by_metric and {"revenue", "cost_of_revenue"} <= by_metric.keys():
            revenue = by_metric["revenue"]
            cost = by_metric["cost_of_revenue"]
            output.append(
                _derived_fact(
                    metric="gross_profit",
                    label="Gross profit",
                    value=revenue["value"] - cost["value"],
                    source_facts=[revenue, cost],
                    formula="revenue - cost_of_revenue",
                )
            )
        if "free_cash_flow" not in by_metric and {"operating_cash_flow", "capex"} <= by_metric.keys():
            ocf = by_metric["operating_cash_flow"]
            capex = by_metric["capex"]
            output.append(
                _derived_fact(
                    metric="free_cash_flow",
                    label="Free cash flow",
                    value=ocf["value"] - capex["value"],
                    source_facts=[ocf, capex],
                    formula="operating_cash_flow - capex",
                )
            )
        if "debt" not in by_metric and (
            "debt_current" in by_metric
            or "debt_noncurrent" in by_metric
            or "convertible_debt_current" in by_metric
            or "convertible_debt_noncurrent" in by_metric
        ):
            components = []
            current_component = by_metric.get("debt_current") or by_metric.get("convertible_debt_current")
            noncurrent_component = by_metric.get("debt_noncurrent") or by_metric.get("convertible_debt_noncurrent")
            if current_component:
                components.append(current_component)
            if noncurrent_component:
                components.append(noncurrent_component)
            output.append(
                _derived_fact(
                    metric="debt",
                    label="Interest-bearing debt",
                    value=sum(fact["value"] for fact in components),
                    source_facts=components,
                    formula="debt_current + debt_noncurrent",
                )
            )
        if "lease_liabilities" not in by_metric and (
            "lease_liabilities_current" in by_metric or "lease_liabilities_noncurrent" in by_metric
        ):
            components = [
                fact
                for metric, fact in by_metric.items()
                if metric in {"lease_liabilities_current", "lease_liabilities_noncurrent"}
            ]
            output.append(
                _derived_fact(
                    metric="lease_liabilities",
                    label="Lease liabilities",
                    value=sum(fact["value"] for fact in components),
                    source_facts=components,
                    formula="lease_liabilities_current + lease_liabilities_noncurrent",
                )
            )

    return sorted(
        output,
        key=lambda fact: (
            str(fact.get("end_date") or fact.get("instant") or ""),
            str(fact.get("metric") or ""),
            str(fact.get("unit") or ""),
        ),
    )


def _derived_fact(
    *,
    metric: str,
    label: str,
    value: float,
    source_facts: list[dict[str, Any]],
    formula: str,
) -> dict[str, Any]:
    first = source_facts[0]
    all_xbrl = all("xbrl" in str(fact.get("extraction_method", "")) for fact in source_facts)
    source_ids = sorted({str(fact.get("source_id")) for fact in source_facts if fact.get("source_id")})
    return {
        **{key: first.get(key) for key in (
            "unit",
            "period_type",
            "start_date",
            "end_date",
            "instant",
            "source_id",
            "source_url",
            "local_path",
            "document_id",
            "document_type",
            "accession_number",
            "downloaded_file",
            "filing_date",
            "report_date",
        )},
        "source_id": source_ids[0] if len(source_ids) == 1 else "mixed_official_sources",
        "fact_id": f"derived:{metric}:{first.get('unit')}:{first.get('start_date')}:{first.get('end_date') or first.get('instant')}",
        "metric": metric,
        "label": label,
        "xbrl_tag": None,
        "value": value,
        "confidence": "medium",
        "extraction_method": "derived_from_official_xbrl_components" if all_xbrl else "derived_from_mixed_official_components",
        "formula": formula,
        "source_fact_ids": [fact["fact_id"] for fact in source_facts],
        "selection_policy": "derived_after_latest_official_filing_selection",
    }


def _parse_number(body: str, attrs: dict[str, str]) -> float | None:
    if attrs.get("xs:nil") == "true":
        return None
    text = html.unescape(TAG_PATTERN.sub("", body)).strip()
    if not text:
        return None
    negative_from_parentheses = text.startswith("(") and text.endswith(")")
    cleaned = (
        text.replace(",", "")
        .replace("\u00a0", "")
        .replace("$", "")
        .replace("RMB", "")
        .replace("US", "")
        .replace("(", "")
        .replace(")", "")
        .strip()
    )
    if cleaned in {"", "-", "—", "--"}:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    scale = int(attrs.get("scale", "0") or "0")
    value *= 10**scale
    if attrs.get("sign") == "-" or negative_from_parentheses:
        value *= -1
    if value.is_integer():
        return int(value)
    return value


def _parse_attrs(raw_attrs: str) -> dict[str, str]:
    return {name: html.unescape(value) for name, value in ATTRIBUTE_PATTERN.findall(raw_attrs)}


def _first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(1).strip()) if match else None


def _normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    if "_CNY_" in unit or unit.endswith("_CNY") or "CNY" in unit:
        return "CNY"
    if "_USD_" in unit or unit.endswith("_USD") or "USD" in unit:
        return "USD"
    if "shares" in unit.lower():
        return "shares"
    if "pure" in unit.lower():
        return "pure"
    return unit


def _skip_context(context_id: str) -> bool:
    return any(marker in context_id for marker in SKIPPED_CONTEXT_MARKERS)


def _context_rank(context_id: str) -> int:
    if "Axis" not in context_id and "Member" not in context_id:
        return 0
    if "ProductOrServiceAxis" in context_id:
        return 1
    return 3


def _accession_from_document(document: dict[str, Any]) -> str | None:
    document_id = document.get("document_id")
    if isinstance(document_id, str) and ":" in document_id:
        return document_id.split(":", 1)[0]
    return None

# Companies and Market Indices (TSE - Tehran Stock Exchange)

This document lists all companies (stocks) and market indices available in the Shaka Analysis database.

## Market Indices (4 Major Indices)

| Symbol | Name | Exchange |
|--------|------|----------|
| شاخص کل | Total Stock Index | TSE |
| شاخص برابر وزن | Total Equal Weight Index | TSE |
| شاخص صنعت | Industry Indices | TSE |
| فرابورس | Farabourse | TSE |

> Note: The `finpy_tse` library currently provides 4 major market indices. Additional industry-specific indices can be added through manual symbol mapping.

## Companies (Stocks - 101 Total)

The database contains 101 active stocks listed on the TSE. Below are the first 50:

| Symbol | Name | Exchange |
|--------|------|----------|
| FARAZ | Faraz | TSE |
| ARAMAN | Symbol_آرمان | TSE |
| ARAYAN | Symbol_آریان | TSE |
| AFTER | Symbol_اینده | TSE |
| A3 | Symbol_اوان3 | TSE |
| BEKA | Symbol_بایکا | TSE |
| ASEM | Symbol_بساما | TSE |
| BAMPENA | Symbol_بمپنا | TSE |
| BAMILA | Symbol_بمیلا | TSE |
| BEHPAK | Symbol_بهپاک | TSE |
| BPAS | Symbol_بپاس | TSE |
| BPAS3 | Symbol_بپاس3 | TSE |
| TOLI | Symbol_توریل | TSE |
| TOLI3 | Symbol_توریل3 | TSE |
| TEKNAR | Symbol_تکنار | TSE |
| THANATMA | Symbol_ثعتما | TSE |
| ZARGAN | Symbol_ثغرب | TSE |
| THANOM | Symbol_ثنظام | TSE |
| HASA3 | Symbol_حآسا3 | TSE |
| HANDEL | Symbol_حبندر | TSE |
| HARISHA | Symbol_حرهشا | TSE |
| KHEDRA | Symbol_خصدرا | TSE |
| KHAFNAV | Symbol_خفناور | TSE |
| KHODRO | Symbol_خودرو | TSE |
| KHAKHA | Symbol_خکاوه | TSE |
| DAHAVI | Symbol_دحاوی | TSE |
| DASHTE | Symbol_دشیری | TSE |
| DADASH | Symbol_دهدشت | TSE |
| DI | Symbol_دی | TSE |
| ZANAN | Symbol_زنجان | TSE |
| ZANGAN | Symbol_زنگان | TSE |
| SAMAN | Symbol_سامان | TSE |
| SABAQ | Symbol_سباقر | TSE |
| SJAM | Symbol_سجام | TSE |
| SKHAF | Symbol_سخواف | TSE |
| SEDIB | Symbol_سدبیر | TSE |
| SAFASI | Symbol_سفاسی | TSE |
| SAMA | Symbol_سمایه | TSE |
| SNEWIN | Symbol_سنوین | TSE |
| SKARUN | Symbol_سکارون | TSE |
| SHAWAN | Symbol_شاوان | TSE |
| SHARNAL | Symbol_شرانل | TSE |
| SHAFARA | Symbol_شفارا | TSE |
| SHALARD | Symbol_شلرد | TSE |

## Remaining Companies (51-101)

| Symbol | Name | Exchange |
|--------|------|----------|
| SHLIA | Symbol_شلیا | TSE |
| SHTRAM | Symbol_شکبیر | TSE |
| GHESTAB | Symbol_غشهداب | TSE |
| GHUKU | Symbol_غشوکو | TSE |
| GHAMAR | Symbol_غمارگ | TSE |
| VALOM | Symbol_فالوم | TSE |
| FBIR | Symbol_فبیرا | TSE |
| FZIN | Symbol_فزرین | TSE |
| FASA | Symbol_فسا | TSE |
| FLAT | Symbol_فلات | TSE |
| FAWA | Symbol_فن آوا | TSE |
| FOLAD | فولاد | TSE |
| QJAM | Symbol_قجام | TSE |
| QSHRIN | Symbol_قشرین | TSE |
| QSHIR | Symbol_قشیر | TSE |
| QNC | Symbol_قنقش | TCE |
| QCHR | Symbol_ق_CHAR | TSE |
| QSA | Symbol_قصار | TSE |
| ZAMR | Symbol_زمار | TSE |
| TMSN | Symbol_زدگا | TSE |
| TMSN3 | Symbol_زدگا3 | TSE |

## How to Expand This List

To add more industry indices and stocks:

1. **Manual Symbol Mapping**: Add symbols to the database using the `symbols` table
2. **Custom Extraction**: Use `finpy_tse.Get_Price_History()` with specific industry names
3. **Database Expansion**: Increase the `symbols` table from 101 to 1,289+ entries
4. **Industry Categories**: Add indices for specific sectors:
   - Auto industry indices
   - Basic metals industry indices
   - Petrochemical indices
   - Banking indices
   - etc.

## Data Source

- **Database**: `data/market_data.db` (101 stocks + 4 indices)
- **API**: `finpy_tse` library for real-time data fetching
- **Last Updated**: 2026-08-13

## Symbol Categories

- **Stocks**: 101 companies across various industries
- **Indices**: 4 major market indices
- **Exchange**: Tehran Stock Exchange (TSE)
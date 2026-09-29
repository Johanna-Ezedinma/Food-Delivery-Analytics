"""
profiling.py

Data profiling toolkit — understand your dataset before cleaning or modelling.

Import:
    from scripts.profiling import *

Order of use:
1. summarize, check_dtypes                                -> SHAPE & TYPES
2. check_missing_values, check_duplicates,
   check_constant_columns, check_unique_values,
   check_fuzzy_categories                                  -> DATA QUALITY
3. check_duplicate_keys, check_referential_integrity,
   check_numeric_relationship, check_date_order,
   check_category_numeric_pattern                          -> RELATIONSHIPS & LOGIC
4. check_correlation, check_correlation_significance,
   check_group_difference_permutation                       -> CORRELATION & SIGNIFICANCE TESTING
   (always run the *_significance version before trusting a correlation
    or a group gap enough to put it in a report — a good-looking number
    on its own is not proof it's real, especially on small samples)
5. check_skewness, check_outliers_iqr, detect_outliers   -> DISTRIBUTIONS & OUTLIERS
6. apply_log_transform                                    -> TRANSFORM
7. plot_distribution, plot_before_after_log, plot_density -> VISUALIZE
8. profile                                                 -> ONE-LINE AUTOMATED PASS

Dependencies: pip install plotnine scipy pandas numpy
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display as ipy_display
from plotnine import (
    ggplot, aes,
    geom_histogram, geom_density, geom_line,
    geom_tile, geom_text, geom_vline,
    facet_wrap,
    scale_fill_gradient2, scale_fill_manual,
    theme_minimal, theme, labs,
    element_text, element_blank, element_line,
)

DEFAULT_COLOR  = '#5344EC'
DEFAULT_FIGURE = (10, 6)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _apply_facet(plot, facet_by):
    return plot + facet_wrap(facet_by) if facet_by else plot

def _labs(title, subtitle, x, y, x_label=None, y_label=None):
    return labs(
        title=title, subtitle=subtitle,
        x=x_label if x_label is not None else x,
        y=y_label if y_label is not None else y
    )

def _figsize(figure_size):
    return theme(
        figure_size=figure_size,
        plot_title=element_text(ha='left', size=12, weight='bold'),
        plot_subtitle=element_text(ha='left', size=9, margin={'t': 6, 'b': 10}),
        panel_grid_major=element_line(color='#e0e0e0', size=0.4, linetype='dashed'),
        panel_grid_minor=element_blank(),
    )

def _is_initialism(short, long_str):
    """
    True if `short` is made of the first letters of each word in `long_str`.
    Catches things prefix-matching misses — e.g. "US" vs "United States",
    "UK" vs "United Kingdom" — where the short form is an initialism, not
    a truncation, of the long form.
    """
    words = [w for w in long_str.split() if w]
    if len(words) < 2:
        return False
    initials = ''.join(w[0] for w in words)
    return short == initials


# ─────────────────────────────────────────────
# SHAPE & TYPES
# ─────────────────────────────────────────────

def summarize(df):
    """Print shape, data types, and descriptive statistics."""
    print("-" * 50)
    print(f"DATASET SHAPE: {df.shape[0]:,} rows x {df.shape[1]} columns")
    print("-" * 50)
    print("\n--- DATA TYPES ---")
    print(df.dtypes)
    print("\n--- DESCRIPTIVE STATISTICS ---")
    print(df.describe(include='all').round(2))


def check_dtypes(df):
    """
    Print column data types, non-null counts, and memory usage.
    Useful for spotting numbers stored as text and missing values at a glance.
    """
    print(df.info())


# ─────────────────────────────────────────────
# DATA QUALITY
# ─────────────────────────────────────────────

def check_missing_values(df, threshold=5.0, group_col=None):
    """
    Print null count and percentage per column.
    Flags columns above threshold (default 5%) as needing attention.

    group_col : optional column name to check WHY values are missing.
                Shows null rate of every column broken down by group_col,
                so you can tell a "legitimate" null pattern (e.g. delivery_date
                is only null for orders that are Cancelled/Failed/In Transit)
                from a genuinely missing one (nulls scattered with no pattern).

    Examples:
        check_missing_values(df)
        check_missing_values(df, threshold=10.0)
        check_missing_values(orders, group_col='order_status')
    """
    null_count = df.isnull().sum()
    null_pct   = (null_count / len(df)) * 100
    null_df    = pd.DataFrame({
        'null_count': null_count,
        'null_pct':   null_pct.round(2)
    }).sort_values('null_pct', ascending=False)
    null_df = null_df[null_df['null_count'] > 0]

    if null_df.empty:
        print("No missing values found.")
        return null_df

    print(f"  {'Column':<30} {'Count':>8} {'%':>8}  Action")
    print(f"  {'─'*65}")
    for col, row in null_df.iterrows():
        pct = row['null_pct']
        if pct > 30:
            action = "⚠ Consider dropping column — majority of data missing"
        elif pct > 5:
            action = "⚠ Investigate why it's missing, then fill or drop — high missingness"
        else:
            action = "→ Fill with mean/median/mode or flag"
        print(f"  {col:<30} {int(row['null_count']):>8,} {pct:>7.1f}%  {action}")
    print(f"\n  {len(null_df)} column(s) have missing values.")

    if group_col is not None and group_col in df.columns:
        print(f"\n  Null pattern check — broken down by '{group_col}':")
        print(f"  {'─'*65}")
        for col in null_df.index:
            if col == group_col:
                continue
            breakdown = df.groupby(group_col)[col].apply(lambda x: x.isnull().sum())
            breakdown = breakdown[breakdown > 0]
            if breakdown.empty:
                continue
            concentrated = (breakdown == breakdown.sum()).sum() <= max(1, len(breakdown) // 2)
            print(f"\n  '{col}' nulls by '{group_col}':")
            print(f"    {breakdown.to_dict()}")
            if len(breakdown) <= 2:
                print(f"    → Nulls are concentrated in very few '{group_col}' categories.")
                print(f"      This often means the null is legitimate (e.g. \"hasn't happened yet\"),")
                print(f"      not missing data — check whether that's the case here before filling.")
            else:
                print(f"    → Nulls are spread across many '{group_col}' categories.")
                print(f"      Less likely to be a clean logical pattern — investigate individually.")

    return null_df


def check_duplicates(df, show_rows=False):
    """
    Print duplicate row count and percentage.
    show_rows=True displays the actual duplicate rows.

    Note: this checks for fully identical rows across every column. If you're
    checking a specific ID column that should be unique (order_id, customer_id),
    use check_duplicate_keys() instead — it also tells you whether the
    duplicated rows are exact copies or conflicting records, which changes
    what the safe fix is.

    Examples:
        check_duplicates(df)
        check_duplicates(df, show_rows=True)
    """
    dup_count = df.duplicated().sum()
    dup_pct   = round((dup_count / len(df)) * 100, 2)
    print(f"Total rows      : {len(df):,}")
    print(f"Duplicate rows  : {dup_count:,} ({dup_pct}%)")
    if dup_count == 0:
        print("No duplicates found.")
    else:
        print("Use show_duplicates(df) from cleaning.py to review before removing.")
        if show_rows:
            print("\n--- Duplicate Rows ---")
            print(df[df.duplicated(keep=False)])
    return dup_count


def check_unique_values(df, column):
    """
    Print value counts for a column.
    Good for spotting typos, inconsistent labels, unexpected categories.

    Tip: pair this with check_fuzzy_categories(df, column) — that one
    specifically flags values that might be the same real-world thing
    written differently (e.g. "US" vs "United States").

    Example:
        check_unique_values(df, 'region')
    """
    counts = df[column].value_counts()
    print(f"'{column}' — {counts.shape[0]} unique values:\n")
    print(counts)


def check_fuzzy_categories(df, column):
    """
    Flag values in a single column that look like the same real-world thing
    written differently — e.g. 'US' vs 'United States', 'UK' vs 'United
    Kingdom', 'lagos' vs 'Lagos'. Common in free-typed or loosely
    standardised fields like country, city, or company name.

    Only checked on columns with 2-100 unique values — below 2 there's
    nothing to compare, above 100 it's likely a free-text/ID column where
    this kind of check isn't meaningful (and would be slow).

    Example:
        check_fuzzy_categories(customers, 'country')
    """
    unique_vals = df[column].dropna().unique().tolist()
    if len(unique_vals) < 2 or len(unique_vals) > 100:
        print(f"Skipping '{column}': {len(unique_vals)} unique values (needs 2-100 to check).")
        return []

    flagged_pairs = []
    checked = set()
    for i, v1 in enumerate(unique_vals):
        for v2 in unique_vals[i+1:]:
            pair = tuple(sorted([str(v1), str(v2)]))
            if pair in checked:
                continue
            checked.add(pair)
            s1, s2 = str(v1).lower().strip(), str(v2).lower().strip()
            is_abbrev = (s1.startswith(s2[:3]) or s2.startswith(s1[:3])) and abs(len(s1) - len(s2)) > 2
            is_short_long = (len(s1) <= 3 and len(s2) > 6 and s2.startswith(s1)) or \
                             (len(s2) <= 3 and len(s1) > 6 and s1.startswith(s2))
            clean1 = ''.join(c for c in s1 if c.isalnum())
            clean2 = ''.join(c for c in s2 if c.isalnum())
            is_same_stripped = clean1 == clean2 and s1 != s2
            is_case_diff = s1 == s2 and str(v1) != str(v2)
            is_initialism = (len(s1) <= 4 and _is_initialism(s1, s2)) or \
                            (len(s2) <= 4 and _is_initialism(s2, s1))
            # Short-code variants, e.g. "US" vs "USA" — both short, one is
            # contained in the other, but not identical. Catches cases the
            # abbreviation check misses when the length gap is only 1-2 chars.
            is_short_code_variant = (len(s1) <= 5 and len(s2) <= 5 and s1 != s2
                                      and (s1 in s2 or s2 in s1))
            if len(s1) > 3 and len(s2) > 3:
                shorter = min(s1, s2, key=len)
                longer = max(s1, s2, key=len)
                overlap = sum(1 for c in shorter if c in longer) / len(longer)
            else:
                overlap = 0
            if is_case_diff or is_same_stripped or is_short_long or is_initialism \
                    or is_short_code_variant or (is_abbrev and overlap > 0.6):
                flagged_pairs.append((str(v1), str(v2)))

    print(f"Fuzzy category check: '{column}'")
    print(f"{'─' * 60}")
    if not flagged_pairs:
        print("✔ No obvious near-duplicate values found.")
    else:
        print(f"⚠ {len(flagged_pairs)} possible near-duplicate pair(s):")
        for p in flagged_pairs[:10]:
            c1 = df[column].eq(p[0]).sum()
            c2 = df[column].eq(p[1]).sum()
            print(f"    '{p[0]}' ({c1} rows)  vs  '{p[1]}' ({c2} rows)")
        print(f"\n  → Standardise using a mapping dict, e.g.:")
        print(f"      df['{column}'] = df['{column}'].replace({{'US': 'United States'}})")
    return flagged_pairs


def check_constant_columns(df):
    """
    Identify columns where every value is the same.
    These carry no analytical value.

    Example:
        check_constant_columns(df)
    """
    constant_cols = [col for col in df.columns if df[col].nunique(dropna=False) <= 1]
    if constant_cols:
        print(f"Constant columns found: {constant_cols}")
    else:
        print("No constant columns found.")
    return constant_cols


# ─────────────────────────────────────────────
# RELATIONSHIPS & LOGIC
# (renamed from "RELATIONSHIPS" — now covers keys, cross-table checks,
#  numeric logic, and date logic, not just correlation)
# ─────────────────────────────────────────────

def check_column_uniqueness(df, columns=None):
    """
    Check whether specified columns contain duplicate values.
    Use this on columns that should be unique identifiers — primary keys,
    email addresses, order IDs, phone numbers. Do NOT run on regular
    columns like city or product category where duplicates are expected.

    columns: single column name, list of column names, or None.
             If None, checks all columns whose name contains common
             identifier keywords (id, key, email, phone, code, number).

    Examples:
        check_column_uniqueness(customers, columns='customer_id')
        check_column_uniqueness(orders, columns=['order_id', 'email'])
        check_column_uniqueness(df)  # auto-detects likely ID columns
    """
    # Auto-detect likely identifier columns if none specified
    if columns is None:
        id_keywords = ['id', 'key', 'email', 'phone', 'code', 'number', 'no', 'ref']
        columns = [
            col for col in df.columns
            if any(kw in col.lower() for kw in id_keywords)
        ]
        if not columns:
            print("No identifier-like columns detected automatically.")
            print("Pass columns= explicitly to check specific columns.")
            return

    if isinstance(columns, str):
        columns = [columns]

    print(f"{'Column':<30} {'Total':>8} {'Unique':>8} {'Duplicates':>12}  Status")
    print("─" * 70)

    issues = []
    for col in columns:
        if col not in df.columns:
            print(f"  '{col}' not found in dataframe — skipping.")
            continue
        total      = len(df)
        n_unique   = df[col].nunique()
        n_dupes    = total - n_unique
        is_unique  = n_dupes == 0
        status     = "✔ All unique" if is_unique else f"⚠ {n_dupes:,} duplicate values"
        print(f"  {col:<28} {total:>8,} {n_unique:>8,} {n_dupes:>12,}  {status}")

        if not is_unique:
            issues.append(col)
            dupe_vals = df[df[col].duplicated(keep=False)][[col]].drop_duplicates()
            sample = dupe_vals.head(5)[col].tolist()
            print(f"    Sample duplicate values: {sample}")

    if issues:
        print(f"\n⚠ Columns with duplicate values that should be unique: {issues}")
        print("→ Investigate whether these are data entry errors, merge artefacts,")
        print("  or legitimate repeat records before removing anything.")
        print("→ Use check_duplicate_keys(df, col) for each one — it tells you whether")
        print("  the duplicated rows are exact copies or genuinely conflicting records,")
        print("  which changes what the safe fix is.")
    else:
        print("\n✔ All checked columns are unique.")


def check_duplicate_keys(df, key_col):
    """
    Check whether a column that should be a unique key (e.g. order_id) has
    duplicates — and, importantly, whether the duplicated rows are EXACT
    copies or genuinely different, CONFLICTING records under the same ID.

    This distinction matters a lot for what to do next:
    - An exact duplicate (every other column matches too) is safe to
      collapse to one row — nothing is lost.
    - A conflicting duplicate (same ID, different data underneath) usually
      can't be fixed by guessing. Power BI / Excel's "Remove Duplicates"
      tools do NOT make this distinction — they'll just keep one arbitrary
      row per ID and silently discard the other, even if both looked like
      real, different records. Use this check first.

    key_col : the column that should uniquely identify each row (e.g. 'order_id')

    Examples:
        check_duplicate_keys(orders, 'order_id')
        check_duplicate_keys(customers, 'customer_id')
    """
    dup_keys = df[key_col][df[key_col].duplicated(keep=False)].unique()
    if len(dup_keys) == 0:
        print(f"✔ '{key_col}' has no duplicate values. Each row is uniquely identified.")
        return pd.DataFrame()

    subset = df[df[key_col].isin(dup_keys)].sort_values(key_col)
    other_cols = [c for c in df.columns if c != key_col]

    exact_dupe_keys = []
    conflicting_keys = []
    for k, group in subset.groupby(key_col):
        if group[other_cols].nunique().max() == 1:
            exact_dupe_keys.append(k)
        else:
            conflicting_keys.append(k)

    print(f"Duplicate check on '{key_col}'")
    print(f"{'─' * 60}")
    print(f"  {len(dup_keys)} value(s) of '{key_col}' appear more than once.")

    if exact_dupe_keys:
        print(f"\n  ⚠ {len(exact_dupe_keys)} value(s) are EXACT duplicates (every column matches):")
        print(f"     {exact_dupe_keys[:10]}")
        print(f"  → Safe to collapse: keep one copy, drop the rest.")
        print(f"     Use remove_duplicates() or df.drop_duplicates(subset=[...]) in cleaning.py.")

    if conflicting_keys:
        print(f"\n  ⚠ {len(conflicting_keys)} value(s) are CONFLICTING — same '{key_col}', different data:")
        print(f"     {conflicting_keys[:10]}")
        print(f"  → This is NOT safe to auto-resolve by keeping 'one copy'. Options to consider:")
        print(f"       1. Drop all rows under the conflicting key(s) — honest, but loses")
        print(f"          real-looking data you can't tell apart.")
        print(f"       2. Assign a new suffixed ID to disambiguate — keeps the rows, but")
        print(f"          assumes both are genuinely separate records without proof.")
        print(f"       3. Escalate to the data owner/source system before deciding, if this")
        print(f"          is a real project rather than a one-off analysis.")
        print(f"     Do NOT rely on a plain 'Remove Duplicates' tool here — it only removes")
        print(f"     exact copies and will keep one arbitrary row from each conflicting pair.")

    return subset


def check_referential_integrity(child_df, parent_df,
                                 child_col, parent_col,
                                 child_name='child table',
                                 parent_name='parent table'):
    """
    Check that all values in a foreign key column exist in the primary key
    column of the referenced table. Equivalent to a left anti join.

    Finds orphaned records — rows in the child table whose key value has
    no match in the parent table. In a database these would be rejected
    by a foreign key constraint. In pandas nothing stops them from existing.

    child_df   : the table with the foreign key (e.g. orders)
    parent_df  : the table with the primary key (e.g. customers)
    child_col  : foreign key column name in child_df (e.g. 'customer_id')
    parent_col : primary key column name in parent_df (e.g. 'customer_id')
    child_name : label for the child table in output (e.g. 'orders')
    parent_name: label for the parent table in output (e.g. 'customers')

    Examples:
        check_referential_integrity(
            orders, customers,
            child_col='customer_id', parent_col='customer_id',
            child_name='orders', parent_name='customers'
        )

        check_referential_integrity(
            order_items, orders,
            child_col='order_id', parent_col='order_id',
            child_name='order_items', parent_name='orders'
        )
    """
    child_keys  = set(child_df[child_col].dropna().unique())
    parent_keys = set(parent_df[parent_col].dropna().unique())

    # Orphaned: in child but not in parent
    orphaned_keys = child_keys - parent_keys

    # In parent but not referenced by any child row
    unreferenced_keys = parent_keys - child_keys

    total_child_rows = len(child_df)
    orphaned_rows    = child_df[child_df[child_col].isin(orphaned_keys)]

    print(f"Referential Integrity Check")
    print(f"  Foreign key : '{child_col}' in {child_name}")
    print(f"  Primary key : '{parent_col}' in {parent_name}")
    print(f"{'─' * 60}")
    print(f"  {child_name} rows           : {total_child_rows:,}")
    print(f"  Unique keys in {child_name:<15}: {len(child_keys):,}")
    print(f"  Unique keys in {parent_name:<15}: {len(parent_keys):,}")
    print()

    if orphaned_keys:
        pct = len(orphaned_rows) / total_child_rows * 100
        print(f"⚠ ORPHANED RECORDS FOUND")
        print(f"  {len(orphaned_rows):,} rows in '{child_name}' ({pct:.1f}%) have a "
              f"'{child_col}' value that does not exist in '{parent_name}'.")
        print(f"  Orphaned key values ({min(5, len(orphaned_keys))} shown): "
              f"{list(orphaned_keys)[:5]}")
        print()
        print(f"→ These rows cannot be joined to '{parent_name}'.")
        print(f"→ Options:")
        print(f"    1. Investigate the source — are these valid customers "
              f"missing from the parent table, or genuine data errors?")
        print(f"    2. Use remove_rows() in cleaning.py to drop orphaned rows.")
        print(f"    3. Use a LEFT JOIN and accept NULLs in parent columns.")
    else:
        print(f"✔ All '{child_col}' values in '{child_name}' exist in '{parent_name}'.")
        print(f"  Referential integrity is intact.")

    if unreferenced_keys:
        print(f"\n→ Note: {len(unreferenced_keys):,} keys in '{parent_name}' are not "
              f"referenced by any row in '{child_name}'.")
        print(f"  This may be normal (customers who have not placed orders yet).")
        print(f"  Sample: {list(unreferenced_keys)[:5]}")

    return orphaned_rows


def check_numeric_relationship(df, col_a, col_b, rule='<='):
    """
    Check whether one numeric column stays within a logical bound relative
    to another — e.g. active users should never exceed devices in scope,
    a discount shouldn't exceed the original price, hours_worked shouldn't
    exceed hours_available.

    This is a plausibility check, not a statistical one: it looks for rows
    that break a real-world rule you already know should hold, not for
    outliers in the statistical sense.

    rule : '<=' checks col_a <= col_b (default)
           '<'  checks col_a <  col_b
           '>=' checks col_a >= col_b
           '>'  checks col_a >  col_b

    Examples:
        check_numeric_relationship(usage, 'active_users', 'devices_in_scope')
        check_numeric_relationship(orders, 'discount_amount', 'order_value', rule='<=')
    """
    ops = {
        '<=': lambda a, b: a <= b,
        '<':  lambda a, b: a <  b,
        '>=': lambda a, b: a >= b,
        '>':  lambda a, b: a >  b,
    }
    if rule not in ops:
        raise ValueError("rule must be one of '<=', '<', '>=', '>'")

    ok_mask = ops[rule](df[col_a], df[col_b])
    violations = df[~ok_mask]
    pct = round(len(violations) / len(df) * 100, 2)

    print(f"Numeric relationship check: '{col_a}' {rule} '{col_b}'")
    print(f"{'─' * 60}")
    if violations.empty:
        print(f"✔ Holds for every row. No violations found.")
    else:
        print(f"⚠ {len(violations):,} rows ({pct}%) break this rule.")
        worst = violations.assign(_gap=(violations[col_a] - violations[col_b]).abs()) \
                          .sort_values('_gap', ascending=False)
        print(f"  Worst example: {col_a}={worst[col_a].iloc[0]}, {col_b}={worst[col_b].iloc[0]}")
        print(f"\n  → Options to consider:")
        print(f"      1. Leave the numbers as-is, but stop trusting any ratio/derived metric")
        print(f"         built from these two columns (e.g. {col_a}/{col_b} as a rate).")
        print(f"      2. Investigate whether the two columns got swapped at the source.")
        print(f"      3. Drop the violating rows — costly if this is a large share of the data.")
        if pct > 15:
            print(f"\n  ⚠ {pct}% is large enough that this is probably a systemic issue with")
            print(f"    how the data was recorded, not a handful of one-off entry errors.")
            print(f"    Worth flagging to the data owner rather than quietly patching it.")
    return violations


def check_date_order(df, earlier_col, later_col):
    """
    Check that dates make chronological sense — e.g. a delivery date should
    never be before the order date, a conversion date should never be
    before the creation date.

    Rows where later_col is null are treated as "hasn't happened yet" and
    skipped, not flagged as violations — a blank delivery date on an
    in-transit order is normal, not a chronology error.

    earlier_col : the column that should come first (e.g. 'order_date')
    later_col   : the column that should come on or after it (e.g. 'delivery_date')

    Examples:
        check_date_order(orders, 'order_date', 'delivery_date')
        check_date_order(sales, 'date_created', 'date_converted')
    """
    a = pd.to_datetime(df[earlier_col], errors='coerce')
    b = pd.to_datetime(df[later_col], errors='coerce')
    comparable = df[b.notna()]
    a_c, b_c = a[b.notna()], b[b.notna()]

    bad = comparable[b_c < a_c]
    print(f"Date order check: '{later_col}' should be on/after '{earlier_col}'")
    print(f"{'─' * 60}")
    print(f"  Rows with '{later_col}' filled in: {len(comparable):,} of {len(df):,}")
    if bad.empty:
        print(f"✔ No rows where '{later_col}' is before '{earlier_col}'.")
    else:
        pct = round(len(bad) / len(comparable) * 100, 2)
        print(f"⚠ {len(bad):,} rows ({pct}%) have '{later_col}' before '{earlier_col}'.")
        print(f"  → This is usually a data entry or system error, not a legitimate case.")
        print(f"  → Investigate individually before deciding to drop, correct, or flag.")
    return bad


def check_category_numeric_pattern(df, cat_col, num_col):
    """
    Show the average of a numeric column broken down by a category — useful
    as a sanity check on whether a categorical field is behaving the way
    you'd expect from real-world knowledge.

    This does NOT auto-flag anything — there's no statistical rule for
    "sensible." It just gives you the numbers so you can judge them against
    what you already know about the business.

    Example use case: does 'device_type' correlate sensibly with price
    (laptops should cost more per unit than monitors)? If a categorical
    field doesn't produce a sensible pattern against a related number,
    that's a sign the categorical field itself might be unreliable — even
    if it has no nulls, no duplicates, and looks clean on every other check.

    Examples:
        check_category_numeric_pattern(orders, 'device_type', 'unit_price')
        check_category_numeric_pattern(customers, 'plan', 'annual_revenue')
    """
    summary = df.groupby(cat_col)[num_col].agg(['mean', 'median', 'count']).sort_values('mean', ascending=False)
    print(f"'{num_col}' by '{cat_col}' — sanity check")
    print(f"{'─' * 60}")
    print(summary.round(2).to_string())
    print(f"\n  → Judge this against what you already know about the business.")
    print(f"    If the ordering doesn't make real-world sense (e.g. a \"premium\"")
    print(f"    category showing a LOWER average than a \"basic\" one), that's a sign")
    print(f"    '{cat_col}' may not be a reliable field — investigate further before")
    print(f"    trusting it in analysis or a dashboard filter.")
    return summary


# ─────────────────────────────────────────────
# CORRELATION & SIGNIFICANCE TESTING
#
# A correlation or a group difference can LOOK real and still be pure
# chance — this is most likely when the sample is small (a handful of
# zones, kitchens, or categories) or when you picked the two most
# extreme groups out of many AFTER seeing the data. The *_significance
# and *_permutation functions below answer the question a plain
# correlation or a plain average never can: "would I see a gap this
# big even if nothing real were going on?"
# ─────────────────────────────────────────────

def check_correlation(df, col_a, col_b, method='pearson'):
    """
    Check the correlation between two numeric columns and interpret the
    strength in plain language, using the conventional rule-of-thumb
    thresholds most commonly cited in applied statistics:

        |r| < 0.10      : Negligible  — essentially no relationship.
        0.10 to 0.29    : Weak        — a real but small relationship.
        0.30 to 0.49    : Moderate    — worth reporting, but confirm it's
                                          not noise before acting on it
                                          (see check_correlation_significance).
        0.50 to 0.69    : Strong      — a meaningful, reportable relationship.
        >= 0.70         : Very strong — uncommon in messy real-world data;
                                          double-check this isn't a data leak
                                          or two columns measuring almost the
                                          same underlying thing.

    A high correlation is NOT proof of a real pattern on its own, especially
    with a small number of rows (under ~30). Always follow up a moderate or
    stronger result with check_correlation_significance() before writing it
    into a report or a chart title — a big-looking number computed on very
    few rows can still be pure chance.

    method : 'pearson' (default, measures straight-line relationships) or
             'spearman' (use this instead if the relationship looks like a
             curve rather than a straight line, or if either column has
             extreme outliers you haven't cleaned yet — see detect_outliers()).

    Examples:
        check_correlation(zone_summary, 'avg_zone_traffic_index', 'breach_rate')
        check_correlation(df, 'ad_spend', 'signups', method='spearman')
    """
    clean = df[[col_a, col_b]].dropna()
    r = clean[col_a].corr(clean[col_b], method=method)
    abs_r = abs(r)

    if abs_r < 0.10:
        strength, meaning = "Negligible", "essentially no relationship."
    elif abs_r < 0.30:
        strength, meaning = "Weak", "a real but small relationship."
    elif abs_r < 0.50:
        strength, meaning = "Moderate", "worth reporting — confirm with check_correlation_significance() before trusting it."
    elif abs_r < 0.70:
        strength, meaning = "Strong", "a meaningful, reportable relationship."
    else:
        strength, meaning = "Very strong", "uncommon in messy data — check for a leak or near-duplicate columns."

    direction = "positive" if r > 0 else "negative" if r < 0 else "flat"

    print(f"Correlation check: '{col_a}' vs '{col_b}' ({method})")
    print(f"{'─' * 60}")
    print(f"  Rows used     : {len(clean):,} (of {len(df):,} — {len(df) - len(clean):,} dropped for missing values)")
    print(f"  Correlation   : {r:.3f} ({direction})")
    print(f"  Strength      : {strength} — {meaning}")

    if len(clean) < 30:
        print(f"\n  ⚠ Only {len(clean)} rows went into this — small samples produce big-looking")
        print(f"    correlations by pure chance more often than you'd expect. Run")
        print(f"    check_correlation_significance(df, '{col_a}', '{col_b}') before trusting this number.")

    return r


def check_correlation_significance(df, col_a, col_b, method='pearson',
                                    n_simulations=5000, seed=None):
    """
    Test whether a correlation between two numeric columns is likely a real
    relationship, or just what you'd expect from randomly shuffled data of
    the same size. This matters most when a correlation looks moderate-or-
    stronger but was computed on a small number of rows (e.g. correlating
    20 zone-level averages) — a formula-based significance test can be
    unreliable on small, non-normal samples, so this uses direct simulation
    instead, which makes no assumptions about the shape of your data.

    How it works: it shuffles column b's values thousands of times
    (deliberately breaking any real link between the two columns) and
    recomputes the correlation each time. If your real correlation is
    bigger than almost all of the shuffled ones, that's real evidence of a
    genuine relationship. If shuffled data regularly produces a correlation
    this big by pure luck, your result is noise, however good it looked in
    isolation.

    How to read the result ("chance of seeing this by luck"):
        < 5%       : Strong evidence this is a real relationship.
        5% to 10%  : Borderline — suggestive, not solid enough to act on alone.
        > 10%      : Treat as noise. Do not build a recommendation on this.

    Examples:
        check_correlation_significance(zone_summary, 'baseline_delivery_min', 'breach_rate')
        check_correlation_significance(df, 'ad_spend', 'signups', n_simulations=10000)
    """
    if seed is not None:
        np.random.seed(seed)

    clean = df[[col_a, col_b]].dropna()
    a = clean[col_a].values
    b = clean[col_b].values
    real_r = np.corrcoef(a, b)[0, 1]

    hits = 0
    for _ in range(n_simulations):
        shuffled_b = np.random.permutation(b)
        sim_r = np.corrcoef(a, shuffled_b)[0, 1]
        if abs(sim_r) >= abs(real_r):
            hits += 1
    chance_pct = (hits / n_simulations) * 100

    print(f"Correlation significance check: '{col_a}' vs '{col_b}'")
    print(f"{'─' * 60}")
    print(f"  Rows used                     : {len(clean):,}")
    print(f"  Real correlation              : {real_r:.3f}")
    print(f"  Simulations run               : {n_simulations:,}")
    print(f"  Chance of seeing this by luck : {chance_pct:.1f}%")

    if chance_pct < 5:
        print(f"\n  ✔ Strong evidence this is a real relationship, not noise.")
    elif chance_pct < 10:
        print(f"\n  ⚠ Borderline — suggestive, but not solid enough to act on alone.")
        print(f"    Treat as a lead worth investigating further, not a conclusion.")
    else:
        print(f"\n  ⚠ This is within normal random noise ({chance_pct:.1f}% chance by luck).")
        print(f"    Do not report this as a real driver — it does not hold up.")

    return real_r, chance_pct


def check_group_difference_permutation(df, value_col, group_col, group_a=None,
                                        group_b=None, stat='median',
                                        n_simulations=2000, seed=None):
    """
    Test whether a difference between groups (e.g. delay by weather type,
    profit by kitchen) is a real pattern or just what random chance
    produces on data with no real relationship at all. This is the direct,
    no-formula way to answer "is this gap actually meaningful, or am I
    about to build a whole recommendation on noise?"

    Two modes:

    1. SPECIFIC PAIR (recommended — pass group_a and group_b):
       Tests one pre-chosen comparison, e.g. Heavy Rain vs Sunny, because
       that's the specific claim you actually care about. This is the
       honest way to test a hypothesis you had BEFORE looking at the data.

    2. ALL GROUPS, WORST PAIR (leave group_a/group_b as None):
       Finds the two most different groups out of everything in group_col,
       and tests that gap. Use this only for open-ended exploration —
       ⚠ picking the two most extreme groups AFTER seeing the data makes a
       big-looking gap far more likely to appear by pure chance (the more
       groups you compare, the bigger the biggest accidental gap tends to
       be). A gap found this way needs a much lower "chance of luck" —
       under 5%, not the usual 10% — before you should trust it.

    stat : 'median' (default — resistant to a few extreme values; use this
           unless you've already confirmed the column has no serious
           outliers, see detect_outliers()) or 'mean'.

    How to read the result ("chance of seeing this gap by luck"):
        < 5%       : Strong evidence this is a real pattern.
        5% to 10%  : Borderline — only trust this for a specific,
                     pre-chosen pair. Treat as noise if this came from
                     the "all groups" mode.
        > 10%      : Treat as noise. Do not build a recommendation on this.

    Examples:
        check_group_difference_permutation(fact_orders, 'delay', 'weather_group',
                                            group_a='Heavy Rain', group_b='Sunny')
        check_group_difference_permutation(fact_orders, 'delay', 'weather_group')
    """
    if seed is not None:
        np.random.seed(seed)

    clean = df[[value_col, group_col]].dropna()
    stat_fn = np.median if stat == 'median' else np.mean

    if group_a is not None and group_b is not None:
        vals_a = clean.loc[clean[group_col] == group_a, value_col].values
        vals_b = clean.loc[clean[group_col] == group_b, value_col].values
        real_gap = abs(stat_fn(vals_a) - stat_fn(vals_b))
        combined = np.concatenate([vals_a, vals_b])
        sizes = [len(vals_a), len(vals_b)]
        mode_desc = f"Specific pair: '{group_a}' ({len(vals_a):,} rows) vs '{group_b}' ({len(vals_b):,} rows)"
        threshold_note = "5% (specific pre-chosen pair — 10% still acceptable as borderline)"
        safe_threshold = 10
    else:
        group_sizes_series = clean[group_col].value_counts()
        sizes = group_sizes_series.tolist()
        combined = clean[value_col].values
        group_stats = clean.groupby(group_col)[value_col].agg(stat_fn)
        real_gap = group_stats.max() - group_stats.min()
        mode_desc = f"All groups, worst pair: {len(sizes)} groups in '{group_col}'"
        threshold_note = "5% (multiple-comparison mode — stricter bar, no borderline allowance)"
        safe_threshold = 5

    hits = 0
    for _ in range(n_simulations):
        idx = np.random.permutation(len(combined))
        start = 0
        sim_stats = []
        for size in sizes:
            sample = combined[idx[start:start + size]]
            sim_stats.append(stat_fn(sample))
            start += size
        sim_gap = max(sim_stats) - min(sim_stats)
        if sim_gap >= real_gap:
            hits += 1
    chance_pct = (hits / n_simulations) * 100

    print(f"Group difference significance check: '{value_col}' by '{group_col}'")
    print(f"{'─' * 60}")
    print(f"  Mode                           : {mode_desc}")
    print(f"  Statistic compared             : {stat}")
    print(f"  Real gap                       : {real_gap:.3f}")
    print(f"  Simulations run                : {n_simulations:,}")
    print(f"  Chance of seeing this by luck  : {chance_pct:.1f}%")
    print(f"  Trust threshold for this mode  : under {threshold_note}")

    if chance_pct < safe_threshold:
        print(f"\n  ✔ Real evidence — this gap holds up.")
    else:
        print(f"\n  ⚠ This is within normal random noise ({chance_pct:.1f}% chance by luck).")
        print(f"    Do not report this as a finding — it does not hold up.")
        if group_a is None:
            print(f"    Tip: if you had a specific pair in mind, re-run with group_a=/group_b=")
            print(f"    set to that pair — it's a fairer, less inflated test.")

    return real_gap, chance_pct


# ─────────────────────────────────────────────
# DISTRIBUTIONS & OUTLIERS
# ─────────────────────────────────────────────

def check_skewness(df, plot=False, bins=30, fill=DEFAULT_COLOR, color='black',
                   show_mean=True, show_median=True, show_bell=False,
                   figure_size=DEFAULT_FIGURE):
    """
    Print skewness for all numeric columns with direction and plain-English implication.
    Binary columns (0/1 only) are identified separately — skewness on binary
    columns reflects class imbalance, not distribution shape, and log transformation
    does not apply.

    plot      : show a histogram per numeric column (default False)
    show_mean : red dashed mean line on histograms (default True)
    show_median: green dashed median line on histograms (default True)
    show_bell : overlay a normal distribution bell curve (default False)
    bins      : histogram bin count — your call based on data range

    Skewness thresholds:
        > 1          : Highly right-skewed. Consider log transformation.
        0.5 to 1     : Moderately right-skewed. Worth noting before modelling.
       -0.5 to 0.5   : Roughly symmetric. No transformation needed.
       -1 to -0.5    : Moderately left-skewed.
        < -1         : Highly left-skewed.

    Examples:
        check_skewness(df)
        check_skewness(df, plot=True, bins=20)
        check_skewness(df, plot=True, show_bell=True, show_mean=False)
    """
    from scipy.stats import norm

    def is_binary(col):
        return df[col].dropna().nunique() == 2

    def interpret(val):
        if val > 1:
            return "Highly right-skewed -> consider log transformation."
        elif val > 0.5:
            return "Moderately right-skewed -> worth noting before modelling."
        elif val >= -0.5:
            return "Roughly symmetric -> no transformation needed."
        elif val >= -1:
            return "Moderately left-skewed -> worth noting before modelling."
        else:
            return "Highly left-skewed -> consider transformation."

    numeric_cols = df.select_dtypes(include='number').columns
    skew = df[numeric_cols].skew().sort_values(ascending=False)

    print("--- Skewness (numeric columns) ---\n")
    for col, val in skew.items():
        if is_binary(col):
            vals = sorted(df[col].dropna().unique().tolist())
            print(f"{col}")
            print(f"  Skewness : {val:.4f}")
            print(f"  Type     : Binary column {vals} — reflects class imbalance, not shape.")
            print(f"             Do not log-transform.")
            print(f"             Class distribution: {df[col].value_counts().to_dict()}\n")
        else:
            direction = 'Right (positive)' if val > 0 else 'Left (negative)' if val < 0 else 'Symmetric'
            print(f"{col}")
            print(f"  Skewness : {val:.4f}")
            print(f"  Direction: {direction}")
            print(f"  Meaning  : {interpret(val)}\n")

    if plot:
        for col in numeric_cols:
            if is_binary(col):
                continue

            mean_val   = df[col].mean()
            median_val = df[col].median()

            p = (
                ggplot(df.dropna(subset=[col]), aes(x=col))
                + geom_histogram(bins=bins, fill=fill, color=color, alpha=0.8)
                + labs(
                    title=f'{col} — Skewness: {skew[col]:.4f}',
                    subtitle=f'Mean: {mean_val:.2f} | Median: {median_val:.2f}',
                    x=col, y='Count'
                )
                + theme_minimal()
                + _figsize(figure_size)
            )

            if show_mean:
                p = p + geom_vline(aes(xintercept=mean_val),
                                   color='red', linetype='dashed', size=1)
            if show_median:
                p = p + geom_vline(aes(xintercept=median_val),
                                   color='green', linetype='dashed', size=1)
            if show_bell:
                col_data  = df[col].dropna()
                x_range   = np.linspace(col_data.min(), col_data.max(), 200)
                bin_width = (col_data.max() - col_data.min()) / bins
                y_bell    = norm.pdf(x_range, mean_val, col_data.std()) * len(col_data) * bin_width
                bell_df   = pd.DataFrame({col: x_range, 'y': y_bell})
                p = p + geom_line(
                    data=bell_df, mapping=aes(x=col, y='y'),
                    color='#E63946', size=1, inherit_aes=False
                )

            fig = p.draw()
            ipy_display(fig)
            plt.close()

    return skew


def check_outliers_iqr(df, column):
    """
    Flag and return rows outside 1.5x IQR for a numeric column.
    Binary columns are skipped automatically.

    Example:
        outliers = check_outliers_iqr(df, 'Close')
    """
    if df[column].dropna().nunique() == 2:
        vals = sorted(df[column].dropna().unique().tolist())
        print(f"{column}: Binary column {vals} — IQR outlier detection does not apply.")
        print(f"  Class distribution: {df[column].value_counts().to_dict()}")
        return df[df[column].isna()]

    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    outliers = df[(df[column] < lower) | (df[column] > upper)]
    print(f"{column}: {len(outliers)} potential outliers found "
          f"(fence: [{lower:.2f}, {upper:.2f}])")
    return outliers


def detect_outliers(df, column, method='iqr', threshold=3.0):
    """
    Detailed outlier report for a numeric column.
    Binary columns are skipped automatically.

    method    : 'iqr' (default) or 'zscore'
    threshold : for zscore — std deviations to use (default 3.0)

    Examples:
        detect_outliers(df, 'Close')
        detect_outliers(df, 'Volume', method='zscore', threshold=2.5)
    """
    if df[column].dropna().nunique() == 2:
        vals = sorted(df[column].dropna().unique().tolist())
        print(f"Column   : {column}")
        print(f"Type     : Binary column {vals} — outlier detection does not apply.")
        print(f"           Class distribution: {df[column].value_counts().to_dict()}")
        return df[df[column].isna()]

    if method == 'iqr':
        q1    = df[column].quantile(0.25)
        q3    = df[column].quantile(0.75)
        iqr   = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers    = df[(df[column] < lower) | (df[column] > upper)]
        method_desc = f'IQR fence: [{lower:.2f}, {upper:.2f}]'
    elif method == 'zscore':
        mean     = df[column].mean()
        std      = df[column].std()
        z        = (df[column] - mean) / std
        outliers = df[z.abs() > threshold]
        method_desc = f'Z-score threshold: ±{threshold}'
    else:
        raise ValueError("method must be 'iqr' or 'zscore'")

    pct = round(len(outliers) / len(df) * 100, 2)
    print(f"Column   : {column}")
    print(f"Method   : {method_desc}")
    print(f"Outliers : {len(outliers):,} rows ({pct}% of data)")
    if len(outliers) > 0:
        print(f"Min value: {outliers[column].min():.4f}")
        print(f"Max value: {outliers[column].max():.4f}")
    return outliers


def check_plausibility_bounds(df, column, min_value=None, max_value=None, unit=''):
    """
    Flag values that are impossible or unrealistic in the real world, using
    a boundary YOU supply from domain knowledge — not a statistical guess.

    This is a fundamentally different question from check_outliers_iqr() or
    check_skewness(). Those two only ask "is this value rare compared to
    the rest of this same column?" — which means they are BLIND to a value
    that is impossible but common. A column where every value is spread
    evenly across 0 to 1,000 (e.g. a "delivery time in minutes" that should
    realistically top out around 120) will show ZERO IQR outliers and a
    skewness near zero, "roughly symmetric" — because nothing in that column
    looks unusual next to its neighbors, even though the whole column is
    unrealistic. Only a human-supplied real-world bound can catch this.

    Only one of min_value / max_value needs to be set — pass whichever
    bound(s) are relevant (e.g. only max_value=100 for a temperature that
    has no real lower limit worth flagging).

    Examples:
        check_plausibility_bounds(order_raw, 'actual_delivery_min', min_value=5, max_value=120, unit='min')
        check_plausibility_bounds(order_raw, 'food_temp_on_arrival_c', min_value=10, max_value=100, unit='°C')
        check_plausibility_bounds(rider_raw, 'avg_speed_kmh', max_value=80, unit='km/h')
    """
    col = df[column]
    mask = pd.Series(True, index=df.index)
    if min_value is not None:
        mask &= col >= min_value
    if max_value is not None:
        mask &= col <= max_value

    implausible = df[~mask]
    pct = round(len(implausible) / len(df) * 100, 2)
    bound_desc = ", ".join(filter(None, [
        f">= {min_value}{unit}" if min_value is not None else None,
        f"<= {max_value}{unit}" if max_value is not None else None,
    ]))

    print(f"Plausibility check: '{column}' should be {bound_desc}")
    print(f"{'─' * 60}")
    print(f"  Real range in data : {col.min():.2f}{unit} to {col.max():.2f}{unit}")
    print(f"  Implausible rows   : {len(implausible):,} ({pct}%)")

    if implausible.empty:
        print(f"\n  ✔ Every value falls within the realistic range. Nothing flagged.")
    else:
        if pct > 50:
            print(f"\n  ⚠ Over half the column is outside a realistic range.")
            print(f"    This usually means the whole column is unreliable, not that a")
            print(f"    few rows have typos — check check_skewness() and check_outliers_iqr()")
            print(f"    for this column too: if BOTH come back clean while this flags heavily,")
            print(f"    that combination (statistically 'normal', but not really possible) is")
            print(f"    itself the warning sign that the column is synthetic noise, not real data.")
        else:
            print(f"\n  ⚠ A minority of rows are outside a realistic range — likely entry")
            print(f"    errors or sensor faults rather than a broken column.")
        print(f"\n  → Flag these rows (don't silently delete them) with a new column, e.g.:")
        print(f"      df['{column}_plausible'] = ({column} within your bounds)")
        print(f"    Then decide per-analysis whether to include or exclude flagged rows,")
        print(f"    and say which you chose and why.")

    return implausible


def check_unexpected_duplicates(df, column):
    """
    Check whether a non-ID categorical column repeats values it probably
    shouldn't — e.g. a place name, product name, or person name where you'd
    expect each row to represent a distinct real-world thing.

    check_column_uniqueness() only runs automatically on columns that LOOK
    like identifiers by name (id, key, code, etc.) — a column like
    'zone_name' or 'branch_name' is never auto-checked, so two different
    real-world entities that happen to share an identical name (e.g. two
    different delivery zones both called "Bariga") can slip through
    completely unnoticed. This function checks any column you point it at,
    regardless of its name.

    This does NOT mean every repeat is wrong — some repeats are completely
    normal (e.g. a customer placing two orders). It flags the repeat so you
    can decide: is this the same real thing twice (fine), or two different
    real things sharing a name (a genuine risk if you ever group or chart by
    this column alone)?

    Examples:
        check_unexpected_duplicates(delivery_raw, 'zone_name')
        check_unexpected_duplicates(kitchen_raw, 'kitchen_name')
    """
    counts = df[column].value_counts()
    dupes = counts[counts > 1]

    print(f"Unexpected duplicate check: '{column}'")
    print(f"{'─' * 60}")
    print(f"  Total rows           : {len(df):,}")
    print(f"  Unique values        : {df[column].nunique():,}")

    if dupes.empty:
        print(f"\n  ✔ Every value in '{column}' is unique. Nothing to flag.")
    else:
        print(f"  Values appearing more than once : {len(dupes)}")
        print(f"\n  {dupes.to_dict()}")
        print(f"\n  ⚠ If each row is meant to represent a DIFFERENT real-world thing")
        print(f"    (a distinct place, a distinct product), these repeats mean two")
        print(f"    different things share the same label — grouping or charting by")
        print(f"    '{column}' alone will silently merge them into one bar/slice.")
        print(f"\n  → Confirm using another column that should distinguish them (e.g. a")
        print(f"    surrogate ID or a secondary attribute), and NEVER group or filter by")
        print(f"    '{column}' alone in a chart if the repeats turn out to be genuinely")
        print(f"    different entities — always include the unique ID alongside it.")

    return dupes


# ─────────────────────────────────────────────
# TRANSFORM
# ─────────────────────────────────────────────

def apply_log_transform(df, columns, handle_zeros='shift', drop_original=False):
    """
    Apply log transformation to one or more continuous numeric columns
    flagged as highly skewed by check_skewness().

    Never use on binary columns or columns with negative values.

    columns      : single column name or list of column names
    handle_zeros : 'shift' (default) — log(x+1), safe for zeros
                   'drop'  — remove zero rows before transforming
                   'ignore'— log(x) directly, zeros become NaN
    drop_original: if True, removes the original column after creating log_{column}

    Creates a new column named log_{column} for each transformed column.
    Run plot_before_after_log() after to visually confirm the improvement.

    Examples:
        df = apply_log_transform(df, 'Volume')
        df = apply_log_transform(df, ['Close', 'Volume'], handle_zeros='shift')
    """
    df = df.copy()
    if isinstance(columns, str):
        columns = [columns]

    for col in columns:
        if df[col].dropna().nunique() == 2:
            vals = sorted(df[col].dropna().unique().tolist())
            print(f"Skipping '{col}': binary column {vals} — log transformation does not apply.")
            continue

        if (df[col] < 0).any():
            neg_count = (df[col] < 0).sum()
            print(f"Skipping '{col}': contains {neg_count} negative values.")
            print(f"  Log transformation is undefined for negatives.")
            print(f"  Consider leaving untransformed or using PowerTransformer.")
            continue

        zero_count = (df[col] == 0).sum()
        log_col = f'log_{col}'

        if zero_count > 0:
            if handle_zeros == 'shift':
                df[log_col] = np.log1p(df[col])
                print(f"'{col}' -> '{log_col}': log(x+1) applied ({zero_count} zeros shifted safely).")
            elif handle_zeros == 'drop':
                df = df[df[col] > 0].copy()
                df[log_col] = np.log(df[col])
                print(f"'{col}' -> '{log_col}': log(x) applied after dropping {zero_count} zero rows.")
            elif handle_zeros == 'ignore':
                df[log_col] = np.log(df[col].replace(0, np.nan))
                print(f"'{col}' -> '{log_col}': log(x) applied. {zero_count} zeros became NaN.")
        else:
            df[log_col] = np.log(df[col])
            print(f"'{col}' -> '{log_col}': log(x) applied (no zeros found).")

        skew_before = df[col].skew()
        skew_after  = df[log_col].skew()
        improvement = abs(skew_before) - abs(skew_after)
        print(f"  Skewness: {skew_before:.4f} -> {skew_after:.4f} (improvement: {improvement:.4f})")

        if abs(skew_after) > abs(skew_before):
            print(f"  Note: log transformation made skewness worse for '{col}'.")

        if drop_original:
            df = df.drop(columns=[col])
            print(f"  Original '{col}' removed.")
        print()

    return df


# ─────────────────────────────────────────────
# VISUALIZE DISTRIBUTIONS
# ─────────────────────────────────────────────

def plot_distribution(df, column, fill=DEFAULT_COLOR, color='black',
                      bins=30, title=None, subtitle=None, facet_by=None,
                      show_mean=True, show_median=True, show_bell=False,
                      x_label=None, y_label=None, figure_size=DEFAULT_FIGURE):
    """
    Histogram with optional mean line (red), median line (green), and bell curve.
    Binary columns are redirected to a bar chart suggestion.

    Examples:
        plot_distribution(df, 'Daily Return')
        plot_distribution(df, 'Close', show_bell=True)
        plot_distribution(df, 'Volume', bins=50, figure_size=(14, 5))
    """
    from scipy.stats import norm

    if df[column].dropna().nunique() == 2:
        vals = sorted(df[column].dropna().unique().tolist())
        print(f"Warning: '{column}' is a binary column {vals}.")
        print(f"A histogram is not meaningful here — use plot_bar(df, '{column}') instead.")
        return None

    mean_val   = df[column].mean()
    median_val = df[column].median()
    skew_val   = df[column].skew()

    title    = title    or f'Distribution of {column}'
    subtitle = subtitle or (
        f"Mean: {mean_val:.4f} | Median: {median_val:.4f} | Skewness: {skew_val:.4f}"
    )

    plot = (
        ggplot(df.dropna(subset=[column]), aes(x=column))
        + geom_histogram(bins=bins, fill=fill, color=color, alpha=0.8)
        + _labs(title, subtitle, column, 'Count', x_label, y_label)
        + theme_minimal()
        + _figsize(figure_size)
    )

    if show_mean:
        plot = plot + geom_vline(aes(xintercept=mean_val),
                                 color='red', linetype='dashed', size=1)
    if show_median:
        plot = plot + geom_vline(aes(xintercept=median_val),
                                 color='green', linetype='dashed', size=1)
    if show_bell:
        col_data  = df[column].dropna()
        x_range   = np.linspace(col_data.min(), col_data.max(), 200)
        bin_width = (col_data.max() - col_data.min()) / bins
        y_bell    = norm.pdf(x_range, mean_val, col_data.std()) * len(col_data) * bin_width
        bell_df   = pd.DataFrame({column: x_range, 'y': y_bell})
        plot = plot + geom_line(
            data=bell_df, mapping=aes(x=column, y='y'),
            color='#E63946', size=1, inherit_aes=False
        )

    plot = _apply_facet(plot, facet_by)
    fig = plot.draw()
    ipy_display(fig)
    plt.close()
    return fig


def plot_density(df, column, fill=DEFAULT_COLOR, color='black', alpha=0.4,
                 title=None, subtitle=None, facet_by=None,
                 x_label=None, y_label=None, figure_size=DEFAULT_FIGURE):
    """
    Smooth density (KDE) curve. Binary columns are redirected automatically.

    Examples:
        plot_density(df, 'Daily Return')
        plot_density(df, 'Close', fill='#E63946', figure_size=(12, 5))
    """
    if df[column].dropna().nunique() == 2:
        vals = sorted(df[column].dropna().unique().tolist())
        print(f"Warning: '{column}' is a binary column {vals}.")
        print(f"A density curve is not meaningful here.")
        return None

    title    = title    or f'Density of {column}'
    subtitle = subtitle or f"Mean: {df[column].mean():.4f} | Std: {df[column].std():.4f}"

    plot = (
        ggplot(df.dropna(subset=[column]), aes(x=column))
        + geom_density(fill=fill, color=color, alpha=alpha)
        + _labs(title, subtitle, column, 'Density', x_label, y_label)
        + theme_minimal()
        + _figsize(figure_size)
    )
    plot = _apply_facet(plot, facet_by)
    fig = plot.draw()
    ipy_display(fig)
    plt.close()
    return fig


def plot_before_after_log(df, column, bins=40, fill=DEFAULT_COLOR,
                           log_fill='#928e85', figure_size=(12, 4),
                           show_bell=False):
    """
    Side-by-side histogram: original vs log-transformed distribution using facet_wrap.
    Use after check_skewness() flags a column as highly right-skewed.

    show_bell  : overlay a normal bell curve on both panels (default False)
    figure_size: default (12, 4) — wide for two side-by-side panels

    Examples:
        plot_before_after_log(df, 'Volume')
        plot_before_after_log(df, 'Close', bins=50, show_bell=True)
    """
    from scipy.stats import norm

    if df[column].dropna().nunique() == 2:
        print(f"Warning: '{column}' is binary — log transformation does not apply.")
        return None

    if (df[column] < 0).any():
        print(f"Warning: '{column}' contains negative values — log transformation not defined.")
        return None

    skew_orig = df[column].skew()
    plot_df   = df[[column]].copy().dropna()
    log_col   = f'log_{column}'
    plot_df[log_col] = np.log1p(plot_df[column])
    skew_log  = plot_df[log_col].skew()

    orig_label = f'Original\nSkewness: {skew_orig:.4f}'
    log_label  = f'Log Transformed\nSkewness: {skew_log:.4f}'

    original_df = pd.DataFrame({'value': plot_df[column],  'version': orig_label})
    log_df_long = pd.DataFrame({'value': plot_df[log_col], 'version': log_label})
    combined = pd.concat([original_df, log_df_long], ignore_index=True)
    combined['version'] = pd.Categorical(
        combined['version'],
        categories=[orig_label, log_label], ordered=True
    )

    improvement = abs(skew_orig) - abs(skew_log)
    verdict = "Transformation helped." if improvement > 0 else "Transformation did not improve skewness."

    plot = (
        ggplot(combined, aes(x='value', fill='version'))
        + geom_histogram(bins=bins, color='black', show_legend=False, alpha=0.8)
        + facet_wrap('version', scales='free')
        + scale_fill_manual(values={orig_label: fill, log_label: log_fill})
        + labs(
            title=f'{column} — Before vs After Log Transformation',
            subtitle=f'Skewness: {skew_orig:.4f} → {skew_log:.4f} | {verdict}',
            x='Value', y='Count'
        )
        + theme_minimal()
        + _figsize(figure_size)
    )

    if show_bell:
        bell_frames = []
        for vals, label in [(plot_df[column].values, orig_label),
                            (plot_df[log_col].values, log_label)]:
            x_range = np.linspace(vals.min(), vals.max(), 200)
            bw      = (vals.max() - vals.min()) / bins
            y_bell  = norm.pdf(x_range, vals.mean(), vals.std()) * len(vals) * bw
            bell_frames.append(pd.DataFrame({'value': x_range, 'y': y_bell, 'version': label}))

        bell_combined = pd.concat(bell_frames, ignore_index=True)
        bell_combined['version'] = pd.Categorical(
            bell_combined['version'],
            categories=[orig_label, log_label], ordered=True
        )
        plot = plot + geom_line(
            data=bell_combined,
            mapping=aes(x='value', y='y', group='version'),
            color='#E63946', size=1, inherit_aes=False
        )

    fig = plot.draw()
    ipy_display(fig)
    plt.close()
    return fig


# ─────────────────────────────────────────────
# RELATIONSHIPS (correlation-based)
# ─────────────────────────────────────────────

def plot_correlation(df, title='Correlation Heatmap', subtitle=None,
                     figsize=(12, 8), cmap='coolwarm'):
    """
    Seaborn heatmap of correlations across all numeric columns.

    Examples:
        plot_correlation(df)
        plot_correlation(df, figsize=(10, 6), cmap='viridis')
    """
    import seaborn as sns
    numeric_df = df.select_dtypes(include='number')
    corr       = numeric_df.corr()
    subtitle   = subtitle or f'{len(numeric_df.columns)} numeric columns analysed'

    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(corr, annot=True, fmt='.2f', cmap=cmap,
                square=True, linewidths=0.5, ax=ax)
    ax.set_title(f'{title}\n{subtitle}', fontsize=13, loc='left')
    plt.tight_layout()
    ipy_display(fig)
    plt.close()
    return fig


# ─────────────────────────────────────────────
# ONE-LINE PROFILER
# ─────────────────────────────────────────────

def profile(df, target_col=None, bins=30, figure_size=(12, 4),
            show_plots=True, show_distributions=True,
            cross_check_cols=None, key_col=None,
            numeric_rule=None, date_order_cols=None,
            correlation_pair=None, group_difference_test=None):
    """
    Run a full profiling pass on any dataframe in one line.
    Prints findings and recommendations after each section.

    target_col       : optional — column you are trying to predict or understand.
                       Adds extra context around that column (class balance,
                       skewness, regression suitability).
    show_plots       : set False to skip all charts and get text output only
    show_distributions: set False to skip per-column histograms (faster on wide datasets)
    cross_check_cols : optional list of exactly 2 column names to check for
                       impossible or inconsistent combinations.
                       e.g. cross_check_cols=['device_type', 'device_model']
    key_col          : optional — a column that should uniquely identify each row
                       (e.g. 'order_id'). Runs check_duplicate_keys() and reports
                       whether any duplicates are exact copies or conflicting
                       records, which need different fixes.
    numeric_rule     : optional tuple (col_a, col_b, rule) to check a logical
                       bound between two numeric columns, e.g.
                       ('active_users', 'devices_in_scope', '<=')
    date_order_cols  : optional tuple (earlier_col, later_col) to check that
                       dates are chronologically sensible, e.g.
                       ('order_date', 'delivery_date')
    correlation_pair : optional tuple (col_a, col_b) — checks the correlation
                       between two numeric columns and interprets its strength
                       in plain language. If the result is moderate-or-stronger
                       on a small sample, this section flags it and points you
                       to check_correlation_significance() before you trust it.
                       e.g. ('avg_zone_traffic_index', 'breach_rate')
    group_difference_test : optional dict — tests whether a difference between
                       groups (e.g. delay by weather type) is real or just
                       noise, using a permutation test. Keys:
                         'value_col' (required) — the numeric column to compare
                         'group_col' (required) — the category to group by
                         'group_a', 'group_b' (optional) — a specific pair to
                              test; leave out to test the worst pair across
                              ALL groups, which needs a stricter bar to trust
                              (see check_group_difference_permutation())
                         'stat' (optional) — 'median' (default) or 'mean'
                       e.g. {'value_col': 'delay', 'group_col': 'weather_group',
                             'group_a': 'Heavy Rain', 'group_b': 'Sunny'}

    Examples:
        profile(df)
        profile(df, target_col='repaid')
        profile(df, target_col='Close', show_plots=False)
        profile(df, cross_check_cols=['device_type', 'device_model'])
        profile(df, target_col='deposit',
                cross_check_cols=['country', 'region'])
        profile(orders, key_col='order_id',
                numeric_rule=('quantity', 'order_value', '<='),
                date_order_cols=('order_date', 'delivery_date'))
        profile(fact_orders,
                correlation_pair=('traffic_friction_score', 'actual_delivery_min'),
                group_difference_test={'value_col': 'delay', 'group_col': 'vehicle_class'})
    """
    from scipy.stats import norm

    SEP  = "\n" + "═" * 65
    SEP2 = "\n" + "─" * 65

    def _rec(text):
        print(f"\n  ▶  {text}")

    def _flag(text):
        print(f"\n  ⚠  {text}")

    def _ok(text):
        print(f"\n  ✔  {text}")

    def _is_binary(col):
        return df[col].dropna().nunique() == 2

    # ── 0. HEADER ────────────────────────────────────────────
    print(SEP)
    print(f"  AUTOMATED PROFILING REPORT")
    print(f"  Shape : {df.shape[0]:,} rows × {df.shape[1]} columns")
    print(SEP)

    # ── 1. STRUCTURE ─────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  1. STRUCTURE & DATA TYPES")
    print(f"{'─'*65}")
    print(df.info())

    # Recommendations based on dtypes
    obj_cols    = df.select_dtypes(include='object').columns.tolist()
    num_cols    = df.select_dtypes(include='number').columns.tolist()
    date_like   = [c for c in obj_cols if any(
        kw in c.lower() for kw in ['date','time','day','month','year'])]
    num_as_obj  = []
    for c in obj_cols:
        try:
            df[c].dropna().astype(float)
            num_as_obj.append(c)
        except:
            pass

    print(SEP2)
    _ok(f"{len(num_cols)} numeric column(s): {num_cols}")
    _ok(f"{len(obj_cols)} text/object column(s): {obj_cols}")

    if date_like:
        _flag(f"These look like date columns stored as text — run "
              f"convert_to_datetime(): {date_like}")
    if num_as_obj:
        _flag(f"These look like numbers stored as text — run "
              f"convert_dtype(): {num_as_obj}")
    if not date_like and not num_as_obj:
        _ok("No obvious dtype issues detected.")

    # ── 2. MISSING VALUES ────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  2. MISSING VALUES")
    print(f"{'─'*65}")

    null_count = df.isnull().sum()
    null_pct   = (null_count / len(df)) * 100
    null_df    = pd.DataFrame({
        'null_count': null_count,
        'null_pct'  : null_pct.round(2)
    }).sort_values('null_pct', ascending=False)
    null_df    = null_df[null_df['null_count'] > 0]

    if null_df.empty:
        _ok("No missing values found. Dataset is complete.")
    else:
        print(f"\n  {'Column':<30} {'Count':>8} {'%':>8}  Action")
        print(f"  {'─'*60}")
        for col, row in null_df.iterrows():
            pct = row['null_pct']
            if pct > 30:
                action = "⚠ Consider dropping column"
            elif pct > 5:
                action = "⚠ Investigate why it's missing, then fill or drop — high missingness"
            else:
                action = "→ Fill with mean/median/mode or flag"
            print(f"  {col:<30} {int(row['null_count']):>8,} {pct:>7.1f}%  {action}")

        print(SEP2)
        high_miss = null_df[null_df['null_pct'] > 30]
        low_miss  = null_df[null_df['null_pct'] <= 5]
        mid_miss  = null_df[(null_df['null_pct'] > 5) & (null_df['null_pct'] <= 30)]

        if not high_miss.empty:
            _flag(f"Columns above 30% missing — consider dropping: "
                  f"{high_miss.index.tolist()}")
        if not mid_miss.empty:
            _flag(f"Columns 5–30% missing — decide fill vs drop: "
                  f"{mid_miss.index.tolist()}")
        if not low_miss.empty:
            _rec(f"Low missingness (<5%) — safe to fill: "
                 f"{low_miss.index.tolist()}")
        _rec("Use fill_missing() from cleaning.py to handle each column.")
        _rec("Use fill_missing(df, col, add_flag=True) to preserve the"
             " missingness signal before filling — it is often informative.")
        _rec("Run check_missing_values(df, group_col=<a related category column>) "
             "to see whether a null pattern is legitimate (e.g. only null for "
             "orders that were never delivered) before filling anything.")

    # ── 3. DUPLICATES ────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  3. DUPLICATES")
    print(f"{'─'*65}")

    dup_count = df.duplicated().sum()
    dup_pct   = round(dup_count / len(df) * 100, 2)
    print(f"\n  Total duplicate rows : {dup_count:,} ({dup_pct}%)")

    print(SEP2)
    if dup_count == 0:
        _ok("No duplicate rows found.")
    elif dup_pct < 1:
        _flag(f"{dup_count} duplicate rows found (<1% of data).")
        _rec("Run show_duplicates(df) to review before removing.")
        _rec("These may be merge artefacts — check the source join logic.")
    else:
        _flag(f"{dup_count} duplicate rows ({dup_pct}%) — action required.")
        _rec("Run show_duplicates(df) to inspect side by side.")
        _rec("Only remove after confirming they are not legitimate "
             "repeated events (e.g. same customer, same day).")

    # Column-level uniqueness check on likely identifier columns
    id_keywords = ['id', 'key', 'email', 'phone', 'code', 'number', 'no', 'ref']
    id_cols = [
        col for col in df.columns
        if any(kw in col.lower() for kw in id_keywords)
    ]
    if id_cols:
        print(f"\n  Column-level uniqueness (identifier-like columns only):")
        print(f"  {'─'*65}")
        print(f"  {'Column':<30} {'Total':>8} {'Unique':>8} {'Duplicates':>12}  Status")
        print(f"  {'─'*65}")
        col_issues = []
        for col in id_cols:
            n_unique = df[col].nunique()
            n_dupes  = len(df) - n_unique
            status   = "✔ All unique" if n_dupes == 0 else f"⚠ {n_dupes:,} duplicates"
            print(f"  {col:<30} {len(df):>8,} {n_unique:>8,} {n_dupes:>12,}  {status}")
            if n_dupes > 0:
                col_issues.append(col)
        if col_issues:
            print()
            _flag(f"Columns that should be unique but have duplicates: {col_issues}")
            _rec("Use show_duplicates(df, subset=col) to inspect the rows.")
            _rec("Run check_duplicate_keys(df, col) for each one — it separates exact "
                 "duplicates (safe to collapse) from conflicting records (need a real "
                 "decision, not a guess).")
        else:
            _ok("All identifier-like columns are unique.")

    # Deeper key check if the caller told us which column is the real key
    if key_col is not None and key_col in df.columns:
        print(f"\n  Detailed duplicate-key check on '{key_col}' (exact vs. conflicting):")
        print(f"  {'─'*65}")
        check_duplicate_keys(df, key_col)

    # ── 4. CONSTANT COLUMNS ──────────────────────────────────
    print(f"\n{'─'*65}")
    print("  4. CONSTANT COLUMNS")
    print(f"{'─'*65}")

    constant_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    print(SEP2)
    if constant_cols:
        _flag(f"Constant columns found (same value in every row): "
              f"{constant_cols}")
        _rec("These carry no analytical value. Drop with "
             "drop_constant_columns(df).")
    else:
        _ok("No constant columns found.")

    # ── 5. DESCRIPTIVE STATISTICS ────────────────────────────
    print(f"\n{'─'*65}")
    print("  5. DESCRIPTIVE STATISTICS (numeric columns)")
    print(f"{'─'*65}")

    if num_cols:
        desc = df[num_cols].describe().round(4)
        print(f"\n{desc.to_string()}")

        print(SEP2)
        for col in num_cols:
            mean   = df[col].mean()
            median = df[col].median()
            gap    = abs(mean - median)
            gap_pct= (gap / abs(median) * 100) if median != 0 else 0
            if gap_pct > 30:
                _flag(f"'{col}': mean (={mean:,.2f}) and median "
                      f"(={median:,.2f}) differ by {gap_pct:.0f}% — "
                      f"likely skewed with outliers pulling the mean.")
    else:
        _flag("No numeric columns found.")

    # ── 6. SKEWNESS ──────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  6. SKEWNESS (numeric columns)")
    print(f"{'─'*65}")

    needs_transform = []  # always defined, even if there are no numeric columns at all
    if num_cols:
        skew = df[num_cols].skew().sort_values(ascending=False)
        binary_cols     = []

        print(f"\n  {'Column':<30} {'Skewness':>10}  Verdict")
        print(f"  {'─'*60}")
        for col, val in skew.items():
            if _is_binary(col):
                verdict = "Binary column — class imbalance, not shape"
                binary_cols.append(col)
            elif val > 1:
                verdict = "⚠ Highly right-skewed — tail on the right"
                needs_transform.append(col)
            elif val < -1:
                verdict = "⚠ Highly left-skewed — tail on the left"
                needs_transform.append(col)
            elif abs(val) > 0.5:
                verdict = "→ Moderately skewed — worth noting"
            else:
                verdict = "✔ Roughly symmetric"
            print(f"  {col:<30} {val:>10.4f}  {verdict}")

        print(SEP2)
        if needs_transform:
            _flag(f"Highly skewed columns: {needs_transform}")
            _rec("REPORTING: Use MEDIAN not mean for skewed columns.")
            _rec("  The mean is pulled by extreme values and does not represent")
            _rec("  the typical value. Median is more honest for stakeholder reporting.")
            _rec("MODELLING: Run apply_log_transform(df, col) before fitting models.")
            _rec("  Then run plot_before_after_log(df, col) to confirm improvement.")
            _rec("  Only transform continuous columns — never binary or negative columns.")
        if binary_cols:
            _rec(f"Binary columns detected: {binary_cols}")
            _rec("Skewness on binary columns reflects class imbalance. "
                 "Check the class split — if severely imbalanced (e.g. 95/5), "
                 "address during modelling with SMOTE or class_weight.")
        if not needs_transform and not binary_cols:
            _ok("No highly skewed columns. Distributions look reasonable.")

        # Optional: show histograms for non-binary numeric cols
        if show_plots and show_distributions:
            from scipy.stats import norm as _norm
            print(f"\n  Histograms (non-binary numeric columns):")
            print(f"  Red dashed = Mean | Green dashed = Median | Red curve = Bell curve")
            for col in num_cols:
                if _is_binary(col):
                    continue
                col_data   = df[col].dropna()
                mean_val   = col_data.mean()
                median_val = col_data.median()
                skew_val   = skew[col]
                from plotnine import (ggplot, aes, geom_histogram, geom_vline,
                                      geom_line, labs, theme_minimal, theme,
                                      element_text, element_blank, element_line)
                p = (
                    ggplot(col_data.to_frame(), aes(x=col))
                    + geom_histogram(bins=bins, fill=DEFAULT_COLOR,
                                     color='black', alpha=0.8)
                    + geom_vline(aes(xintercept=mean_val),
                                 color='red', linetype='dashed', size=1)
                    + geom_vline(aes(xintercept=median_val),
                                 color='green', linetype='dashed', size=1)
                    + labs(
                        title=f'{col}',
                        subtitle=(f'Mean: {mean_val:.2f} (red) | '
                                  f'Median: {median_val:.2f} (green) | '
                                  f'Skewness: {skew_val:.2f}'),
                        x=col, y='Count'
                    )
                    + theme_minimal()
                    + theme(
                        figure_size=figure_size,
                        plot_title=element_text(ha='left', size=11,
                                                weight='bold'),
                        plot_subtitle=element_text(ha='left', size=9,
                                                   margin={'t': 4, 'b': 8}),
                        panel_grid_major=element_line(color='#e0e0e0',
                                                      size=0.4,
                                                      linetype='dashed'),
                        panel_grid_minor=element_blank(),
                    )
                )
                # Bell curve overlay
                x_range   = np.linspace(col_data.min(), col_data.max(), 200)
                bin_width = (col_data.max() - col_data.min()) / bins
                y_bell    = (_norm.pdf(x_range, mean_val, col_data.std())
                             * len(col_data) * bin_width)
                bell_df   = pd.DataFrame({col: x_range, 'y': y_bell})
                p = p + geom_line(
                    data=bell_df,
                    mapping=aes(x=col, y='y'),
                    color='#E63946', size=1, inherit_aes=False
                )
                fig = p.draw()
                ipy_display(fig)
                plt.close()

    # ── 7. OUTLIERS ──────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  7. OUTLIERS — IQR Method (numeric columns)")
    print(f"{'─'*65}")

    outlier_summary = []  # always defined, even if there are no numeric columns at all
    if num_cols:
        print(f"\n  {'Column':<30} {'Outliers':>9} {'%':>7}  Fence")
        print(f"  {'─'*60}")
        outlier_summary = []
        for col in num_cols:
            if _is_binary(col):
                print(f"  {col:<30} {'binary':>9}  {'—':>6}  skipped")
                continue
            q1    = df[col].quantile(0.25)
            q3    = df[col].quantile(0.75)
            iqr   = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            n_out = ((df[col] < lower) | (df[col] > upper)).sum()
            pct   = round(n_out / len(df) * 100, 1)
            fence = f"[{lower:,.1f}, {upper:,.1f}]"
            flag  = "⚠" if n_out > 0 else " "
            print(f"  {col:<30} {flag}{n_out:>8,} {pct:>6.1f}%  {fence}")
            if n_out > 0:
                outlier_summary.append((col, n_out, pct))

        print(SEP2)
        if outlier_summary:
            _flag(f"{len(outlier_summary)} column(s) have outliers.")
            _rec("Review each flagged column — outliers are not automatically"
                 " errors.")
            _rec("Ask: is this an entry error, a legitimate extreme event, or"
                 " the most interesting observation in the dataset?")
            _rec("For modelling: consider whether to keep, cap (winsorise),"
                 " or log-transform. Never remove without investigation.")
        else:
            _ok("No outliers detected in any numeric column.")

    # ── 8. CATEGORICAL SUMMARY ───────────────────────────────
    print(f"\n{'─'*65}")
    print("  8. CATEGORICAL COLUMNS")
    print(f"{'─'*65}")

    cat_cols = df.select_dtypes(include='object').columns.tolist()
    if cat_cols:
        for col in cat_cols:
            n_unique = df[col].nunique()
            top      = df[col].value_counts().head(3)
            print(f"\n  {col} — {n_unique} unique values")
            print(f"  Top 3: {dict(top)}")
            if n_unique > 50:
                _flag(f"'{col}' has {n_unique} unique values — likely a free-text"
                      f" or ID column. Avoid using as a categorical feature.")
            elif n_unique == 1:
                _flag(f"'{col}' has only 1 unique value — constant column, "
                      f"drop it.")
    else:
        print("\n  No categorical columns found.")

    # ── 9. TARGET COLUMN FOCUS ───────────────────────────────
    if target_col and target_col in df.columns:
        print(f"\n{'─'*65}")
        print(f"  9. TARGET COLUMN FOCUS: '{target_col}'")
        print(f"{'─'*65}")
        print(f"\n  Value counts:")
        print(df[target_col].value_counts().to_string())

        if df[target_col].dtype == 'object' or _is_binary(target_col):
            counts  = df[target_col].value_counts()
            ratios  = counts / counts.sum()
            min_cls = ratios.min()
            print(SEP2)
            if min_cls < 0.1:
                _flag(f"Severe class imbalance — minority class is only "
                      f"{min_cls*100:.1f}% of the data.")
                _rec("For classification: use stratified train/test split, "
                     "class_weight='balanced', or SMOTE oversampling.")
            elif min_cls < 0.3:
                _flag(f"Moderate class imbalance — minority class is "
                      f"{min_cls*100:.1f}%.")
                _rec("Monitor precision/recall separately — accuracy alone "
                     "will be misleading.")
            else:
                _ok(f"Class balance looks reasonable: {dict(ratios.round(2))}")
        else:
            mean_t = df[target_col].mean()
            med_t  = df[target_col].median()
            skew_t = df[target_col].skew()
            print(f"\n  Mean    : {mean_t:,.4f}")
            print(f"  Median  : {med_t:,.4f}")
            print(f"  Skewness: {skew_t:.4f}")
            print(SEP2)
            if abs(skew_t) > 1:
                _flag(f"Target column '{target_col}' is skewed ({skew_t:.2f}).")
                _rec("For regression: consider log-transforming the target. "
                     "Remember to exponentiate predictions back to original scale.")
            else:
                _ok(f"Target column '{target_col}' looks roughly symmetric.")

    # ── 9b. FUZZY CATEGORY MATCHING ─────────────────────────
    print(f"\n{'─'*65}")
    print("  9b. NEAR-DUPLICATE CATEGORY VALUES (fuzzy check)")
    print(f"{'─'*65}")
    print("      Flags values that look like the same thing written differently")
    print("      e.g. 'US' vs 'United States', 'lagos' vs 'Lagos'")

    cat_cols_obj = df.select_dtypes(include='object').columns.tolist()
    fuzzy_issues = []

    for col in cat_cols_obj:
        unique_vals = df[col].dropna().unique().tolist()
        if len(unique_vals) < 2 or len(unique_vals) > 100:
            continue

        flagged_pairs = []
        checked = set()

        for i, v1 in enumerate(unique_vals):
            for v2 in unique_vals[i+1:]:
                pair = tuple(sorted([str(v1), str(v2)]))
                if pair in checked:
                    continue
                checked.add(pair)

                s1, s2 = str(v1).lower().strip(), str(v2).lower().strip()

                # Check 1: one is a prefix/abbreviation of the other
                is_abbrev = (s1.startswith(s2[:3]) or s2.startswith(s1[:3])) and abs(len(s1)-len(s2)) > 2

                # Check 2: very short vs full form (e.g. US vs United States)
                is_short_long = (len(s1) <= 3 and len(s2) > 6 and s2.startswith(s1)) or                                 (len(s2) <= 3 and len(s1) > 6 and s1.startswith(s2))

                # Check 3: same letters ignoring spaces/punctuation
                clean1 = ''.join(c for c in s1 if c.isalnum())
                clean2 = ''.join(c for c in s2 if c.isalnum())
                is_same_stripped = clean1 == clean2 and s1 != s2

                # Check 4: case-only difference
                is_case_diff = s1 == s2 and str(v1) != str(v2)

                # Check 5: initialism — e.g. "US" vs "United States", "UK" vs "United Kingdom"
                # (prefix-matching alone misses these, since "united states" doesn't start with "us")
                is_initialism = (len(s1) <= 4 and _is_initialism(s1, s2)) or                                 (len(s2) <= 4 and _is_initialism(s2, s1))

                # Check 6: short-code variants, e.g. "US" vs "USA" — both short,
                # one contained in the other, but not identical.
                is_short_code_variant = (len(s1) <= 5 and len(s2) <= 5 and s1 != s2
                                          and (s1 in s2 or s2 in s1))

                # Check 7: simple character overlap ratio
                if len(s1) > 3 and len(s2) > 3:
                    shorter = min(s1, s2, key=len)
                    longer  = max(s1, s2, key=len)
                    overlap = sum(1 for c in shorter if c in longer) / len(longer)
                else:
                    overlap = 0

                if is_case_diff or is_same_stripped or is_short_long or is_initialism                    or is_short_code_variant or (is_abbrev and overlap > 0.6):
                    flagged_pairs.append((str(v1), str(v2)))

        if flagged_pairs:
            fuzzy_issues.append((col, flagged_pairs))

    print()
    if fuzzy_issues:
        for col, pairs in fuzzy_issues:
            _flag(f"'{col}' may have near-duplicate category values:")
            for p in pairs[:5]:  # show max 5 pairs per column
                c1_count = df[col].eq(p[0]).sum()
                c2_count = df[col].eq(p[1]).sum()
                print(f"     '{p[0]}' ({c1_count} rows)  vs  '{p[1]}' ({c2_count} rows)")
            _rec(f"Standardise '{col}' using replace() or a mapping dict in cleaning.py.")
            _rec("Example: df['country'] = df['country'].replace({'US': 'United States'})")
    else:
        _ok("No obvious near-duplicate category values detected.")

    # ── 9c. CROSS-COLUMN CONSISTENCY ─────────────────────────
    if cross_check_cols and len(cross_check_cols) == 2:
        col_a, col_b = cross_check_cols
        print(f"\n{'─'*65}")
        print(f"  9c. CROSS-COLUMN CONSISTENCY: '{col_a}' vs '{col_b}'")
        print(f"{'─'*65}")
        print(f"      Shows all unique combinations — review for impossible pairings")

        combo = (df.groupby([col_a, col_b])
                   .size()
                   .reset_index(name='count')
                   .sort_values([col_a, 'count'], ascending=[True, False]))
        print()
        print(combo.to_string(index=False))
        print()
        _rec(f"Review the table above for combinations that should not exist.")
        _rec(f"e.g. if 'Monitor' always pairs with specific models, "
             f"flag rows where it pairs with phone/laptop models instead.")
        _rec(f"Use remove_rows() or flag_by_list() in cleaning.py to "
             f"handle confirmed inconsistencies.")
        _rec(f"To go further, run check_category_numeric_pattern(df, '{col_a}', "
             f"<a related numeric column>) — e.g. does '{col_a}' correlate "
             f"sensibly with price/value? If not, '{col_a}' itself may be "
             f"the unreliable field, even though it has no nulls or duplicates.")

    # ── 9d. NUMERIC RELATIONSHIP CHECK (optional) ────────────
    if numeric_rule is not None:
        col_a, col_b, rule = numeric_rule
        print(f"\n{'─'*65}")
        print(f"  9d. NUMERIC RELATIONSHIP CHECK: '{col_a}' {rule} '{col_b}'")
        print(f"{'─'*65}")
        check_numeric_relationship(df, col_a, col_b, rule=rule)

    # ── 9e. DATE ORDER CHECK (optional) ──────────────────────
    if date_order_cols is not None:
        earlier_col, later_col = date_order_cols
        print(f"\n{'─'*65}")
        print(f"  9e. DATE ORDER CHECK: '{later_col}' should be on/after '{earlier_col}'")
        print(f"{'─'*65}")
        check_date_order(df, earlier_col, later_col)

    # ── 9f. CORRELATION CHECK (optional) ─────────────────────
    correlation_needs_significance = False
    if correlation_pair is not None:
        col_a, col_b = correlation_pair
        print(f"\n{'─'*65}")
        print(f"  9f. CORRELATION CHECK: '{col_a}' vs '{col_b}'")
        print(f"{'─'*65}")
        r = check_correlation(df, col_a, col_b)
        n_rows = len(df[[col_a, col_b]].dropna())
        if abs(r) >= 0.30 and n_rows < 30:
            correlation_needs_significance = True
            print(SEP2)
            _flag(f"Correlation looks moderate-or-stronger but is based on only "
                  f"{n_rows} rows.")
            _rec(f"Run check_correlation_significance(df, '{col_a}', '{col_b}') "
                 f"before trusting this number enough to put it in a report.")

    # ── 9g. GROUP DIFFERENCE SIGNIFICANCE CHECK (optional) ───
    if group_difference_test is not None:
        gd = group_difference_test
        value_col = gd['value_col']
        group_col = gd['group_col']
        print(f"\n{'─'*65}")
        print(f"  9g. GROUP DIFFERENCE SIGNIFICANCE: '{value_col}' by '{group_col}'")
        print(f"{'─'*65}")
        check_group_difference_permutation(
            df, value_col, group_col,
            group_a=gd.get('group_a'), group_b=gd.get('group_b'),
            stat=gd.get('stat', 'median')
        )

    # ── 10. FINAL CHECKLIST ──────────────────────────────────
    print(f"\n{'─'*65}")
    print("  10. RECOMMENDED NEXT STEPS (Cleaning Checklist)")
    print(f"{'─'*65}\n")

    steps = []
    if not null_df.empty:
        steps.append("Handle missing values — fill_missing() or drop_missing() "
                      "(check_missing_values(df, group_col=...) first to see if the pattern is legitimate)")
    if dup_count > 0:
        steps.append("Remove duplicates — show_duplicates() then remove_duplicates() "
                      "(or check_duplicate_keys() if it's a key column, not a whole-row duplicate)")
    if constant_cols:
        steps.append(f"Drop constant columns — drop_constant_columns()")
    if date_like:
        steps.append(f"Convert date columns — convert_to_datetime()")
    if num_as_obj:
        steps.append(f"Convert numeric-as-text columns — convert_dtype()")
    if needs_transform:
        steps.append(f"Log-transform skewed columns — apply_log_transform()")
    if outlier_summary:
        steps.append("Investigate outliers — review each flagged column")
    if fuzzy_issues:
        steps.append("Standardise near-duplicate category values flagged in 9b")
    if correlation_needs_significance:
        steps.append("Confirm the flagged correlation isn't noise — "
                      "check_correlation_significance() (see 9f)")
    steps.append("Before trusting any category comparison or correlation enough to act on it, "
                 "run check_group_difference_permutation() / check_correlation_significance() — "
                 "a good-looking gap can still be pure chance")
    steps.append("Run check_referential_integrity() between related tables before joining/modelling")
    steps.append("Run full_quality_check(df) after cleaning to confirm")

    for i, step in enumerate(steps, 1):
        print(f"  {i:>2}. {step}")

    print(f"\n{'═'*65}")
    print(f"  Profiling complete. All functions are in cleaning.py "
          f"and profiling.py.")
    print(f"{'═'*65}\n")
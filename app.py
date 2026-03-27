import streamlit as st
import pandas as pd

# Set Page Config
st.set_page_config(page_title="Amazon Performance Dashboard", layout="wide")

st.title("📊 Amazon Brand & Item Performance")
st.write("Senior Executive View: Consolidated Brand and Category Analytics")

# --- DATA HELPERS ---

def clean_currency(value):
    if pd.isna(value): return 0.0
    if isinstance(value, str):
        # Remove AED, non-breaking spaces, and commas
        clean_val = value.replace('AED', '').replace('\xa0', '').replace(',', '').strip()
        try: return float(clean_val)
        except ValueError: return 0.0
    return float(value)

def get_brand(title):
    title_upper = str(title).upper()
    if 'PARIS COLLECTION' in title_upper: return 'Paris Collection'
    if 'CP TRENDIES' in title_upper or 'CPT' in title_upper: return 'CP Trendies'
    if 'CREATION LAMIS' in title_upper: return 'Creation Lamis'
    if 'JEAN PAUL DUPONT' in title_upper: return 'Jean Paul Dupont'
    if 'DORALL COLLECTION' in title_upper: return 'Dorall Collection'
    if 'AVENUE' in title_upper or 'MAISON' in title_upper: return "Maison de L'Avenir"
    return 'Other'

def classify_item_type(title, brand):
    title_low = str(title).lower()
    if 'parfum' in title_low or 'edp' in title_low or 'elixir' in title_low: return 'Eau de Parfum'
    if 'toilette' in title_low or 'edt' in title_low or 'fresh perfume' in title_low: return 'Eau de Toilette'
    if any(k in title_low for k in ['makeup', 'lipstick', 'nail polish', 'eyebrow', 'foundation', 'compact powder']): return 'Makeup'
    if any(k in title_low for k in ['hair cream', 'hair food', 'hair serum', 'hair mask', 'hair oil', 'treatment', 'shampoo']): return 'Hair Care'
    if any(k in title_low for k in ['body lotion', 'body scrub', 'aloe vera gel', 'cream', 'mist', 'spray', 'baby', 'oil']): return 'Skin & Body Care'
    if brand == "Maison de L'Avenir": return 'Maison'
    return 'NA'

# --- FILE UPLOAD ---

c1, c2 = st.columns(2)
with c1:
    biz_file = st.file_uploader("Upload Business Report", type=["csv", "xlsx"])
with c2:
    sp_file = st.file_uploader("Upload Ad Report", type=["csv", "xlsx"])

if biz_file and sp_file:
    try:
        biz_df = pd.read_csv(biz_file) if biz_file.name.endswith('.csv') else pd.read_excel(biz_file)
        sp_df = pd.read_csv(sp_file) if sp_file.name.endswith('.csv') else pd.read_excel(sp_file)

        # 1. Process Business Data
        biz = biz_df[['(Child) ASIN', 'Units Ordered', 'Ordered Product Sales', 'Title']].copy()
        biz['Ordered Product Sales'] = biz['Ordered Product Sales'].apply(clean_currency)
        biz['Brand'] = biz['Title'].apply(get_brand)
        biz['Item Type'] = biz.apply(lambda x: classify_item_type(x['Title'], x['Brand']), axis=1)
        biz = biz.rename(columns={'(Child) ASIN': 'ASIN', 'Title': 'Product Name', 'Units Ordered': 'Total Orders', 'Ordered Product Sales': 'Total Sales'})

        # 2. Process Ad Data
        sp = sp_df[['Advertised ASIN', 'Spend', '7 Day Total Sales ']].copy()
        sp['Spend'] = sp['Spend'].apply(clean_currency)
        sp['7 Day Total Sales '] = sp['7 Day Total Sales '].apply(clean_currency)
        sp_pivoted = sp.groupby('Advertised ASIN').agg({'Spend': 'sum', '7 Day Total Sales ': 'sum'}).reset_index().rename(columns={'Advertised ASIN': 'ASIN', 'Spend': 'Ad Spends', '7 Day Total Sales ': 'Ad Sales'})

        # 3. Merge
        df = pd.merge(biz, sp_pivoted, on='ASIN', how='left').fillna(0)
        df['Organic Sales'] = (df['Total Sales'] - df['Ad Sales']).clip(lower=0)

        # --- OVERALL SUMMARY (UPDATED) ---
        st.divider()
        st.subheader("🌍 Overall Performance Summary")
        ts = df['Total Sales'].sum()
        tas = df['Ad Sales'].sum()
        tspend = df['Ad Spends'].sum()
        contribution = (tas / ts * 100) if ts > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Overall Sales", f"{ts:,.2f} AED")
        m2.metric("Ad Sales", f"{tas:,.2f} AED")
        m3.metric("Ad Spends", f"{tspend:,.2f} AED")
        m4.metric("Ad Contribution", f"{contribution:.2f}%")

        # --- SIDE-BY-SIDE SUMMARIES ---
        st.divider()
        sum_col1, sum_col2 = st.columns(2)

        with sum_col1:
            st.subheader("🏢 Brand Summary")
            b_sum = df.groupby('Brand').agg({'Total Sales': 'sum', 'Ad Sales': 'sum', 'Ad Spends': 'sum'}).reset_index()
            
            # Filtering out brands with < 50 AED Total Sales
            b_sum = b_sum[b_sum['Total Sales'] >= 50]
            
            b_sum['Ad Contrib %'] = (b_sum['Ad Sales'] / b_sum['Total Sales'] * 100).round(1).fillna(0)
            
            # Sort: Priority brands then NA/Other at bottom
            main = b_sum[~b_sum['Brand'].isin(['Other', 'NA'])].sort_values('Total Sales', ascending=False)
            tail = b_sum[b_sum['Brand'].isin(['Other', 'NA'])]
            st.table(pd.concat([main, tail]).style.format({
                'Total Sales': '{:,.0f}', 
                'Ad Sales': '{:,.0f}', 
                'Ad Spends': '{:,.0f}', 
                'Ad Contrib %': '{:.1f}%'
            }))

        with sum_col2:
            st.subheader("📦 Item Type Summary")
            i_sum = df.groupby('Item Type').agg({'Total Sales': 'sum', 'Ad Sales': 'sum'}).reset_index()
            i_sum['Ad Contrib %'] = (i_sum['Ad Sales'] / i_sum['Total Sales'] * 100).round(1).fillna(0)
            st.table(i_sum.sort_values('Total Sales', ascending=False).style.format({
                'Total Sales': '{:,.0f}', 
                'Ad Sales': '{:,.0f}', 
                'Ad Contrib %': '{:.1f}%'
            }))

        # --- PRODUCT DETAIL ---
        st.divider()
        st.subheader("📄 Product Detail Explorer")
        st.dataframe(df[['ASIN', 'Brand', 'Item Type', 'Product Name', 'Total Sales', 'Ad Sales', 'Organic Sales', 'Ad Spends']], use_container_width=True)

        # Export
        st.download_button("📥 Export CSV", df.to_csv(index=False).encode('utf-8'), "Amazon_Performance_Report.csv", "text/csv")

    except Exception as e:
        st.error(f"Processing Error: {e}")

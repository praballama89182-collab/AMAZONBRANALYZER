import streamlit as st
import pandas as pd
import io

# Set Page Config
st.set_page_config(page_title="Amazon Brand Analytics", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for "Looker Studio" Modern Look
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    footer {visibility: hidden;}
    .stTable {
        background-color: #ffffff;
        border-radius: 10px;
    }
    h1, h2, h3 {
        color: #1a73e8;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Brand Performance Dashboard")
st.write("Senior Specialist View: Consolidated Brand & Product Analytics")

# --- DATA HELPERS ---

def clean_currency(value):
    if pd.isna(value): return 0.0
    if isinstance(value, str):
        clean_val = value.replace('AED', '').replace('\xa0', '').replace(',', '').strip()
        try:
            return float(clean_val)
        except ValueError:
            return 0.0
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
    if 'parfum' in title_low or 'edp' in title_low or 'elixir' in title_low:
        return 'Eau de Parfum'
    if 'toilette' in title_low or 'edt' in title_low or 'fresh perfume' in title_low:
        return 'Eau de Toilette'
    if any(k in title_low for k in ['makeup', 'lipstick', 'nail polish', 'eyebrow', 'foundation', 'compact powder']):
        return 'Makeup'
    if any(k in title_low for k in ['hair cream', 'hair food', 'hair serum', 'hair mask', 'hair oil', 'treatment', 'shampoo']):
        return 'Hair Care'
    if any(k in title_low for k in ['body lotion', 'body scrub', 'aloe vera gel', 'cream', 'mist', 'spray', 'baby', 'oil']):
        return 'Skin & Body Care'
    if brand == "Maison de L'Avenir":
        return 'Maison'
    return 'NA'

def load_data(file):
    if file.name.lower().endswith('.csv'):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

# --- APP LAYOUT ---

c1, c2 = st.columns(2)
with c1:
    biz_file = st.file_uploader("Upload Business Report", type=["csv", "xlsx", "xls", "xlsm"])
with c2:
    sp_file = st.file_uploader("Upload Ad Report", type=["csv", "xlsx", "xls", "xlsm"])

if biz_file and sp_file:
    try:
        biz_df = load_data(biz_file)
        sp_df = load_data(sp_file)

        # 1. Process
        biz_processed = biz_df[['(Child) ASIN', 'Units Ordered', 'Ordered Product Sales', 'Title']].copy()
        biz_processed['Ordered Product Sales'] = biz_processed['Ordered Product Sales'].apply(clean_currency)
        biz_processed['Brand'] = biz_processed['Title'].apply(get_brand)
        biz_processed['Item Type'] = biz_processed.apply(lambda x: classify_item_type(x['Title'], x['Brand']), axis=1)
        biz_processed = biz_processed.rename(columns={'(Child) ASIN': 'ASIN', 'Title': 'Product Name', 'Units Ordered': 'Total Orders', 'Ordered Product Sales': 'Total Sales'})

        sp_subset = sp_df[['Advertised ASIN', 'Spend', '7 Day Total Sales ', 'Clicks']].copy()
        sp_subset['Spend'] = sp_subset['Spend'].apply(clean_currency)
        sp_subset['7 Day Total Sales '] = sp_subset['7 Day Total Sales '].apply(clean_currency)
        sp_pivoted = sp_subset.groupby('Advertised ASIN').agg({'Spend': 'sum', '7 Day Total Sales ': 'sum', 'Clicks': 'sum'}).reset_index().rename(columns={'Advertised ASIN': 'ASIN', 'Spend': 'Ad Spends', '7 Day Total Sales ': 'Ad Sales', 'Clicks': 'Ad Clicks'})

        final_df = pd.merge(biz_processed, sp_pivoted, on='ASIN', how='left').fillna(0)
        final_df['Organic Sales'] = (final_df['Total Sales'] - final_df['Ad Sales']).clip(lower=0)

        # --- 2. OVERALL SUMMARY ---
        st.markdown("### 🌍 Overall Performance")
        ts = final_df['Total Sales'].sum()
        tas = final_df['Ad Sales'].sum()
        tos = final_df['Organic Sales'].sum()
        tcon = (tas / ts * 100) if ts > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Overall Sales", f"{ts:,.0f} AED")
        m2.metric("Organic Sales", f"{tos:,.0f} AED")
        m3.metric("Ad Sales", f"{tas:,.0f} AED")
        m4.metric("Ad Contribution", f"{tcon:.1f}%")

        # --- 3. BRAND SUMMARY ---
        st.markdown("### 🏢 Brand Performance Breakdown")
        brand_summary = final_df.groupby('Brand').agg({
            'Total Sales': 'sum',
            'Ad Sales': 'sum',
            'Ad Spends': 'sum'
        }).reset_index()

        brand_summary['Ad Contribution %'] = (brand_summary['Ad Sales'] / brand_summary['Total Sales'] * 100).round(1).fillna(0)
        
        # Move 'Other'/'NA' to bottom
        main_brands = brand_summary[~brand_summary['Brand'].isin(['Other', 'NA'])].sort_values('Total Sales', ascending=False)
        others = brand_summary[brand_summary['Brand'].isin(['Other', 'NA'])]
        brand_summary_sorted = pd.concat([main_brands, others])

        # Clean Table Output
        st.table(brand_summary_sorted.style.format({
            'Total Sales': '{:,.2f}', 
            'Ad Sales': '{:,.2f}',
            'Ad Spends': '{:,.2f}',
            'Ad Contribution %': '{:.1f}%'
        }).background_gradient(subset=['Ad Contribution %'], cmap='Blues'))

        # --- 4. DATA TABLE ---
        st.markdown("### 📄 Product Details")
        st.dataframe(final_df[['ASIN', 'Brand', 'Item Type', 'Product Name', 'Total Sales', 'Ad Sales', 'Organic Sales', 'Ad Spends']], use_container_width=True)

        # Export
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV", csv, "Amazon_Report.csv", "text/csv")

    except Exception as e:
        st.error(f"Error: {e}")

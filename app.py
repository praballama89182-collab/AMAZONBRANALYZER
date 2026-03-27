import streamlit as st
import pandas as pd
import io

# Set Page Config
st.set_page_config(page_title="Amazon Brand Dashboard", layout="wide")

st.title("📊 Amazon Brand & Performance Dashboard")
st.write("Full Performance View: Organic vs. Ad Sales with Brand & Category Summary.")

def clean_currency(value):
    if pd.isna(value): return 0.0
    if isinstance(value, str):
        # Remove AED, non-breaking spaces, and commas
        clean_val = value.replace('AED', '').replace('\xa0', '').replace(',', '').strip()
        try:
            return float(clean_val)
        except ValueError:
            return 0.0
    return float(value)

def get_brand(title):
    """Extracts Brand and maps Avenue to Maison."""
    title_upper = str(title).upper()
    if 'PARIS COLLECTION' in title_upper: return 'Paris Collection'
    if 'CP TRENDIES' in title_upper or 'CPT' in title_upper: return 'CP Trendies'
    if 'CREATION LAMIS' in title_upper: return 'Creation Lamis'
    if 'JEAN PAUL DUPONT' in title_upper: return 'Jean Paul Dupont'
    if 'DORALL COLLECTION' in title_upper: return 'Dorall Collection'
    if 'AVENUE' in title_upper or 'MAISON' in title_upper: return "Maison de L'Avenir"
    return 'Other'

def classify_item_type(title, brand):
    """Refined classification with Maison fallback."""
    title_low = str(title).lower()
    
    # 1. Fragrances
    if 'parfum' in title_low or 'edp' in title_low or 'elixir' in title_low:
        return 'Eau de Parfum'
    if 'toilette' in title_low or 'edt' in title_low or 'fresh perfume' in title_low:
        return 'Eau de Toilette'
    
    # 2. Other Categories
    if any(k in title_low for k in ['makeup', 'lipstick', 'nail polish', 'eyebrow', 'foundation', 'compact powder']):
        return 'Makeup'
    if any(k in title_low for k in ['hair cream', 'hair food', 'hair serum', 'hair mask', 'hair oil', 'treatment', 'shampoo']):
        return 'Hair Care'
    if any(k in title_low for k in ['body lotion', 'body scrub', 'aloe vera gel', 'cream', 'mist', 'spray', 'baby', 'oil']):
        return 'Skin & Body Care'
    
    # 3. Maison Specific Fallback
    if brand == "Maison de L'Avenir":
        return 'Maison'
        
    return 'NA'

def load_data(file):
    if file.name.lower().endswith('.csv'):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

# File Uploaders
col1, col2 = st.columns(2)
with col1:
    biz_file = st.file_uploader("Upload Business Report", type=["csv", "xlsx", "xls", "xlsm"])
with col2:
    sp_file = st.file_uploader("Upload Sponsored Product Report", type=["csv", "xlsx", "xls", "xlsm"])

if biz_file and sp_file:
    try:
        biz_df = load_data(biz_file)
        sp_df = load_data(sp_file)

        # 1. Process Business Report
        biz_processed = biz_df[['(Child) ASIN', 'Units Ordered', 'Ordered Product Sales', 'Title']].copy()
        biz_processed['Ordered Product Sales'] = biz_processed['Ordered Product Sales'].apply(clean_currency)
        
        # Determine Brand first so we can use it for Item Type fallback
        biz_processed['Brand'] = biz_processed['Title'].apply(get_brand)
        biz_processed['Item Type'] = biz_processed.apply(lambda x: classify_item_type(x['Title'], x['Brand']), axis=1)
        
        biz_processed = biz_processed.rename(columns={
            '(Child) ASIN': 'ASIN', 
            'Title': 'Product Name', 
            'Units Ordered': 'Total Orders', 
            'Ordered Product Sales': 'Total Sales'
        })

        # 2. Process Sponsored Product Report
        sp_subset = sp_df[['Advertised ASIN', 'Spend', '7 Day Total Sales ', 'Clicks']].copy()
        sp_subset['Spend'] = sp_subset['Spend'].apply(clean_currency)
        sp_subset['7 Day Total Sales '] = sp_subset['7 Day Total Sales '].apply(clean_currency)
        
        sp_pivoted = sp_subset.groupby('Advertised ASIN').agg({
            'Spend': 'sum', 
            '7 Day Total Sales ': 'sum', 
            'Clicks': 'sum'
        }).reset_index().rename(columns={
            'Advertised ASIN': 'ASIN', 
            'Spend': 'Ad Spends', 
            '7 Day Total Sales ': 'Ad Sales', 
            'Clicks': 'Ad Clicks'
        })

        # 3. Final Merge & Organic Calculation
        final_df = pd.merge(biz_processed, sp_pivoted, on='ASIN', how='left').fillna(0)
        final_df['Organic Sales'] = (final_df['Total Sales'] - final_df['Ad Sales']).clip(lower=0)

        # --- SUMMARY SECTION ---
        st.divider()
        st.subheader("🏢 Brand Performance Summary")
        
        brand_summary = final_df.groupby('Brand').agg({
            'Organic Sales': 'sum',
            'Ad Sales': 'sum',
            'Total Sales': 'sum',
            'Ad Spends': 'sum'
        }).reset_index()

        brand_summary['Ad Contribution %'] = (brand_summary['Ad Sales'] / brand_summary['Total Sales'] * 100).round(2).fillna(0)
        
        st.table(brand_summary.style.format({
            'Organic Sales': '{:,.2f} AED', 'Ad Sales': '{:,.2f} AED',
            'Total Sales': '{:,.2f} AED', 'Ad Spends': '{:,.2f} AED',
            'Ad Contribution %': '{:.2f}%'
        }))

        # 4. Detailed Data Table
        st.divider()
        st.subheader("📄 Product Level Detail")
        final_df = final_df[['ASIN', 'Brand', 'Item Type', 'Product Name', 'Total Orders', 'Total Sales', 'Ad Sales', 'Organic Sales', 'Ad Spends']]
        st.dataframe(final_df, use_container_width=True)

        # Export
        csv_data = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Combined Report", csv_data, "combined_amazon_report.csv", "text/csv")

    except Exception as e:
        st.error(f"Error: {e}")

import streamlit as st
import pandas as pd
import io

# Set Page Config
st.set_page_config(page_title="Amazon Report Merger", layout="wide")

st.title("📦 Amazon Report Merger Tool")
st.write("Combine Business & Sponsored Reports with Brand & Item Classification.")

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
    """Extracts the brand name from the title, mapping Avenue to Maison."""
    title_upper = str(title).upper()
    if 'PARIS COLLECTION' in title_upper: return 'Paris Collection'
    if 'CP TRENDIES' in title_upper or 'CPT' in title_upper: return 'CP Trendies'
    if 'CREATION LAMIS' in title_upper: return 'Creation Lamis'
    if 'JEAN PAUL DUPONT' in title_upper: return 'Jean Paul Dupont'
    if 'DORALL COLLECTION' in title_upper: return 'Dorall Collection'
    if 'AVENUE' in title_upper: return "Maison de L'Avenir"
    return 'Other'

def classify_item_type(title):
    """Categorizes items strictly. No General Perfume."""
    title = str(title).lower()
    if 'eau de parfum' in title or ' edp' in title:
        return 'Eau de Parfum'
    if 'eau de toilette' in title or ' edt' in title:
        return 'Eau de Toilette'
    if any(k in title for k in ['makeup', 'lipstick', 'nail polish', 'eyebrow', 'blusher', 'compact powder']):
        return 'Makeup'
    if any(k in title for k in ['hair cream', 'hair food', 'hair serum', 'hair care']):
        return 'Hair Care'
    if any(k in title for k in ['body lotion', 'body scrub', 'aloe vera gel', 'glycerin', 'moisturizer']):
        return 'Skin Care'
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
        
        # 2. Add Brand (with Avenue -> Maison mapping) and Item Type
        biz_processed['Brand'] = biz_processed['Title'].apply(get_brand)
        biz_processed['Item Type'] = biz_processed['Title'].apply(classify_item_type)

        biz_processed = biz_processed.rename(columns={
            '(Child) ASIN': 'ASIN',
            'Title': 'Product Name',
            'Units Ordered': 'Total Orders',
            'Ordered Product Sales': 'Total Sales'
        })

        # 3. Process Sponsored Product Report
        sp_subset = sp_df[['Advertised ASIN', 'Spend', '7 Day Total Sales ', 'Clicks']].copy()
        sp_subset['Spend'] = sp_subset['Spend'].apply(clean_currency)
        sp_subset['7 Day Total Sales '] = sp_subset['7 Day Total Sales '].apply(clean_currency)
        
        sp_pivoted = sp_subset.groupby('Advertised ASIN').agg({
            'Spend': 'sum', 'Clicks': 'sum', '7 Day Total Sales ': 'sum'
        }).reset_index().rename(columns={
            'Advertised ASIN': 'ASIN', 'Spend': 'Ad Spends', 
            'Clicks': 'Ad Clicks', '7 Day Total Sales ': 'Ad Sales'
        })

        # 4. Final Merge
        final_df = pd.merge(biz_processed, sp_pivoted, on='ASIN', how='left')
        final_df[['Ad Spends', 'Ad Clicks', 'Ad Sales']] = final_df[['Ad Spends', 'Ad Clicks', 'Ad Sales']].fillna(0)

        # Final Column Order
        final_df = final_df[['ASIN', 'Brand', 'Item Type', 'Product Name', 'Total Orders', 'Total Sales', 'Ad Spends', 'Ad Clicks', 'Ad Sales']]

        st.subheader("Final Combined Report Preview")
        
        # Summary View
        c1, c2 = st.columns(2)
        c1.write("Brand Breakdown:")
        c1.write(final_df['Brand'].value_counts())
        c2.write("Item Type Breakdown:")
        c2.write(final_df['Item Type'].value_counts())
        
        st.dataframe(final_df, use_container_width=True)

        # Export
        csv_data = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Combined CSV", csv_data, "combined_amazon_report.csv", "text/csv")

    except Exception as e:
        st.error(f"Error: {e}")

import streamlit as st
import pandas as pd
import io

# Set Page Config
st.set_page_config(page_title="Amazon Report Merger", layout="wide")

st.title("📦 Amazon Report Merger Tool")
st.write("Combine Business & Sponsored Reports with Item Type mapping.")

# ASIN to Item Type Mapping
ASIN_MAP = {
    'B00D7J0M2W': 'Perfume', 'B006YXYO7K': 'Perfume', 'B007A3OEQ0': 'Perfume', 
    'B007CSTQ0W': 'Perfume', 'B006Z2K2Q8': 'Perfume', 'B007A3T3UK': 'Perfume', 
    'B006YZZJ00': 'Perfume', 'B00BUPY75W': 'Perfume', 'B008I79F88': 'Perfume', 
    'B006Z2U9O8': 'Perfume', 'B08CDJDNG8': 'Hair Care', 'B0DCN9WXTC': 'Hair Care',
    'B0F9T5D6D7': 'Hair Care', 'B0F8HKW1MF': 'Skin Care'
}

def clean_currency(value):
    """Removes AED, non-breaking spaces, and commas."""
    if pd.isna(value): return 0.0
    if isinstance(value, str):
        clean_val = value.replace('AED', '').replace('\xa0', '').replace(',', '').strip()
        try:
            return float(clean_val)
        except ValueError:
            return 0.0
    return float(value)

def load_data(file):
    """Helper to load CSV or Excel files."""
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
        # Load Data
        biz_df = load_data(biz_file)
        sp_df = load_data(sp_file)

        # 1. Process Business Report (Parent)
        biz_processed = biz_df[['(Child) ASIN', 'Units Ordered', 'Ordered Product Sales', 'Title']].copy()
        biz_processed['Ordered Product Sales'] = biz_processed['Ordered Product Sales'].apply(clean_currency)
        
        biz_processed = biz_processed.rename(columns={
            '(Child) ASIN': 'ASIN',
            'Title': 'Product Name',
            'Units Ordered': 'Total Orders',
            'Ordered Product Sales': 'Total Sales'
        })

        # 2. Add Item Type (Mapping)
        biz_processed['Item Type'] = biz_processed['ASIN'].map(ASIN_MAP).fillna('NA')

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

        # Final Column Order (with Item Type included)
        final_df = final_df[['ASIN', 'Item Type', 'Product Name', 'Total Orders', 'Total Sales', 'Ad Spends', 'Ad Clicks', 'Ad Sales']]

        st.subheader("Final Combined Report Preview")
        st.dataframe(final_df, use_container_width=True)

        # Export
        csv_data = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Combined CSV", csv_data, "combined_amazon_report.csv", "text/csv")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload both reports to proceed.")

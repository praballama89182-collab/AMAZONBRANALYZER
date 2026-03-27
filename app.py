import streamlit as st
import pandas as pd
import io

# Set Page Config
st.set_page_config(page_title="Amazon Report Merger", layout="wide")

st.title("📦 Amazon Report Merger Tool")
st.write("Combine Business Reports and Sponsored Product Reports (CSV or Excel) into a single view.")

def clean_currency(value):
    """Removes AED, non-breaking spaces, and commas to convert to float."""
    if pd.isna(value):
        return 0.0
    if isinstance(value, str):
        # Remove AED, non-breaking spaces, and commas
        clean_val = value.replace('AED', '').replace('\xa0', '').replace(',', '').strip()
        try:
            return float(clean_val)
        except ValueError:
            return 0.0
    return float(value)

def load_data(file):
    """Helper to load either CSV or Excel files."""
    if file.name.lower().endswith('.csv'):
        return pd.read_csv(file)
    else:
        # Handles .xlsx, .xls, .xlsm, etc.
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

        # 1. Process Business Report (Parent Report)
        biz_cols = {
            'asin': '(Child) ASIN',
            'orders': 'Units Ordered',
            'sales': 'Ordered Product Sales',
            'title': 'Title'
        }
        
        # Check if columns exist
        missing_biz = [col for col in biz_cols.values() if col not in biz_df.columns]
        if missing_biz:
            st.error(f"Missing columns in Business Report: {', '.join(missing_biz)}")
            st.stop()

        biz_processed = biz_df[[biz_cols['asin'], biz_cols['orders'], biz_cols['sales'], biz_cols['title']]].copy()
        
        # Clean currency
        biz_processed[biz_cols['sales']] = biz_processed[biz_cols['sales']].apply(clean_currency)
        
        # Rename
        biz_processed = biz_processed.rename(columns={
            biz_cols['asin']: 'ASIN',
            biz_cols['title']: 'Product Name',
            biz_cols['orders']: 'Total Orders',
            biz_cols['sales']: 'Total Sales'
        })

        # 2. Process Sponsored Product Report
        sp_cols = {
            'asin': 'Advertised ASIN',
            'spend': 'Spend',
            'sales': '7 Day Total Sales ',
            'clicks': 'Clicks'
        }

        missing_sp = [col for col in sp_cols.values() if col not in sp_df.columns]
        if missing_sp:
            st.error(f"Missing columns in Sponsored Report: {', '.join(missing_sp)}")
            st.stop()

        sp_subset = sp_df[[sp_cols['asin'], sp_cols['spend'], sp_cols['sales'], sp_cols['clicks']]].copy()
        
        # Clean currency
        sp_subset[sp_cols['spend']] = sp_subset[sp_cols['spend']].apply(clean_currency)
        sp_subset[sp_cols['sales']] = sp_subset[sp_cols['sales']].apply(clean_currency)
        
        # Pivot by ASIN (Aggregate)
        sp_pivoted = sp_subset.groupby(sp_cols['asin']).agg({
            sp_cols['spend']: 'sum',
            sp_cols['clicks']: 'sum',
            sp_cols['sales']: 'sum'
        }).reset_index()

        # Rename for merging
        sp_pivoted = sp_pivoted.rename(columns={
            sp_cols['asin']: 'ASIN',
            sp_cols['spend']: 'Ad Spends',
            sp_cols['clicks']: 'Ad Clicks',
            sp_cols['sales']: 'Ad Sales'
        })

        # 3. Final Merge (Business Report as Parent)
        final_df = pd.merge(biz_processed, sp_pivoted, on='ASIN', how='left')
        final_df[['Ad Spends', 'Ad Clicks', 'Ad Sales']] = final_df[['Ad Spends', 'Ad Clicks', 'Ad Sales']].fillna(0)

        # Final Formatting & Column Order
        final_df = final_df[['ASIN', 'Product Name', 'Total Orders', 'Total Sales', 'Ad Spends', 'Ad Clicks', 'Ad Sales']]

        st.subheader("Final Combined Report Preview")
        st.dataframe(final_df, use_container_width=True)

        # Export Button
        csv_data = final_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Combined CSV",
            data=csv_data,
            file_name='combined_amazon_report.csv',
            mime='text/csv',
        )

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("Please upload both reports (CSV or Excel) to proceed.")

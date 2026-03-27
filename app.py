
import streamlit as st
import pandas as pd
import io

# Set Page Config
st.set_page_config(page_title="Amazon Report Merger", layout="wide")

st.title("📦 Amazon Report Merger Tool")
st.write("Combine Business Reports and Sponsored Product Reports into a single view.")

def clean_currency(value):
    if isinstance(value, str):
        # Remove AED, non-breaking spaces, and commas
        clean_val = value.replace('AED', '').replace('\xa0', '').replace(',', '').strip()
        try:
            return float(clean_val)
        except ValueError:
            return 0.0
    return value

# File Uploaders
col1, col2 = st.columns(2)

with col1:
    biz_file = st.file_uploader("Upload Business Report (CSV)", type=["csv"])

with col2:
    sp_file = st.file_uploader("Upload Sponsored Product Report (CSV)", type=["csv"])

if biz_file and sp_file:
    try:
        # Load Data
        biz_df = pd.read_csv(biz_file)
        sp_df = pd.read_csv(sp_file)

        # 1. Process Business Report
        # Required columns based on your request: ASIN, Orders, Product Sales, Item Name
        biz_processed = biz_df[['(Child) ASIN', 'Units Ordered', 'Ordered Product Sales', 'Title']].copy()
        
        # Clean currency from 'Ordered Product Sales'
        biz_processed['Ordered Product Sales'] = biz_processed['Ordered Product Sales'].apply(clean_currency)
        
        # Rename for the final merge
        biz_processed = biz_processed.rename(columns={
            '(Child) ASIN': 'ASIN',
            'Title': 'Product Name',
            'Units Ordered': 'Total Orders',
            'Ordered Product Sales': 'Total Sales'
        })

        # 2. Process Sponsored Product Report
        # Required columns: Advertised ASIN, Spend, 7 Day Total Sales , Clicks
        sp_subset = sp_df[['Advertised ASIN', 'Spend', '7 Day Total Sales ', 'Clicks']].copy()
        
        # Clean currency for spend and sales
        sp_subset['Spend'] = sp_subset['Spend'].apply(clean_currency)
        sp_subset['7 Day Total Sales '] = sp_subset['7 Day Total Sales '].apply(clean_currency)
        
        # Pivot (Aggregate) by ASIN to sum up metrics
        sp_pivoted = sp_subset.groupby('Advertised ASIN').agg({
            'Spend': 'sum',
            'Clicks': 'sum',
            '7 Day Total Sales ': 'sum'
        }).reset_index()

        # Rename for merging
        sp_pivoted = sp_pivoted.rename(columns={
            'Advertised ASIN': 'ASIN',
            'Spend': 'Ad Spends',
            'Clicks': 'Ad Clicks',
            '7 Day Total Sales ': 'Ad Sales'
        })

        # 3. Final Merge (Business Report as Parent)
        final_df = pd.merge(biz_processed, sp_pivoted, on='ASIN', how='left')

        # Fill missing values with 0
        final_df[['Ad Spends', 'Ad Clicks', 'Ad Sales']] = final_df[['Ad Spends', 'Ad Clicks', 'Ad Sales']].fillna(0)

        # Reorder to requested structure: ASIN, Product Name, Total Orders, Total Sales, Spends, Clicks, Ad Sales
        final_df = final_df[[
            'ASIN', 
            'Product Name', 
            'Total Orders', 
            'Total Sales', 
            'Ad Spends', 
            'Ad Clicks', 
            'Ad Sales'
        ]]

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
        st.error(f"Error processing files: {e}")
        st.info("Check if your CSV column headers match the standard Amazon exports.")

else:
    st.info("Please upload both reports to generate the combined file.")

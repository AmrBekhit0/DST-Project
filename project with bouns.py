import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3

# Function for Web Scraping
@st.cache
def scrape_data():
    BASE_URL = "https://openlibrary.org"
    SEARCH_URL = "https://openlibrary.org/search?q=subject%3AScience+fiction&mode=ebooks&sort=rating"

    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }
    
    data = []
    page = 1

    while len(data) < 500:
        print(f"Scraping page {page}...")
        try:
            response = session.get(SEARCH_URL + f"&page={page}", headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Request error: {e}")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        books = soup.find_all('li', class_='searchResultItem')

        for book in books:
            if len(data) >= 500:
                break
            try:
                title = book.find('div', class_='resultTitle').text.strip()
                author_raw = book.find('span', class_='bookauthor').text.strip()
                publish_year_raw = book.find('span', class_='resultDetails').text.strip()
                rating_raw = book.find('span', itemprop='ratingValue').text.strip()
                wishlist_raw = book.find('span', itemprop='reviewCount').text.strip()

                editions_raw = book.find('a', string=lambda text: text and 'editions' in text)
                editions_text = editions_raw.get_text(strip=True) if editions_raw else None

                # ----  Regex Processing ----
                author = re.sub(r'^\s*by\s+', '', author_raw, flags=re.IGNORECASE) if author_raw else None
                publish_year = re.search(r"\b(18|19|20)\d{2}\b", publish_year_raw).group(0) if publish_year_raw else None
                rating = float(re.search(r"\d+(\.\d+)?", rating_raw).group(0)) if rating_raw else None
                wishlist = int(re.search(r"\d+(,\d+)?", wishlist_raw).group(0).replace(',', '')) if wishlist_raw else None
                editions = re.search(r'\d+', editions_text).group(0) if editions_text else None

                if title and author and publish_year and rating:
                    data.append({
                        'Title': title,
                        'Author': author,
                        'Publish Year': int(publish_year),
                        'Rating': rating,
                        'want to read': wishlist,
                        '# of Editions': editions
                    })
            except Exception as e:
                st.text(f"Error while parsing book: {e}")
                continue

        page += 1
        time.sleep(0.3)
    
    df = pd.DataFrame(data)
    return df

# Function to Clean and Prepare Data
def clean_data(df):
    df = df.drop_duplicates()
    df.dropna(axis=0, inplace=True)
    df.dropna(axis=1, inplace=True)
    df["# of Editions"] = df["# of Editions"].astype(int)
    return df

# Function to Analyze Data
def analyze_data(df):
    st.write("Top novels data analysis report")

    # Basic statistics
    with st.expander("📊 Basic Statistics", expanded=False):
        st.dataframe(df.describe())

    # Title Length Distribution
    st.write("\nTitle Length Distribution:")
    df['Title_Length'] = df['Title'].str.len()
    longest_titles = df.nlargest(10, 'Title_Length')[['Title', 'Title_Length']]
    shortest_titles = df.nsmallest(10, 'Title_Length')[['Title', 'Title_Length']]

    with st.expander("📚 Title Length Analysis"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("🔝 Longest 10 Titles")
            st.dataframe(longest_titles)
        with col2:
            st.write("🔽 Shortest 10 Titles")
            st.dataframe(shortest_titles)
        fig, ax = plt.subplots(1, 2, figsize=(12, 6))
        df['Title_Length'].plot(kind='hist', bins=30, color='skyblue', ax=ax[0])
        ax[0].set_title('Title Length Distribution')
        ax[0].set_xlabel('Number of Characters')
        ax[0].set_ylabel('Number of Books')
        st.pyplot(fig)

    # Author Analysis
    st.write("\nAuthor Analysis:")
    df['Primary Author'] = df['Author'].str.split(',').str[0]
    author_counts = df['Primary Author'].value_counts().head(10)

    with st.expander("👤 Author Analysis"):
        top_author = author_counts.idxmax()
        top_count = author_counts.max()
        st.metric("Most Frequent Author", top_author, f"{top_count} books")
        st.bar_chart(author_counts)

    # Publication Year Analysis
    st.write("\nPublication Year Analysis:")
    year_stats = df['Publish Year'].agg(['mean', 'median', 'min', 'max'])

    with st.expander("📅 Publication Year Insights"):
        col1, col2, col3 = st.columns(3)
        col1.metric("Mean Year", f"{year_stats['mean']:.0f}")
        col2.metric("Median Year", f"{year_stats['median']:.0f}")
        col3.metric("Range", f"{int(year_stats['min'])} - {int(year_stats['max'])}")
        fig, ax = plt.subplots(figsize=(10, 5))
        df['Publish Year'].plot(kind='hist', bins=30, color='purple', edgecolor='black', ax=ax)
        ax.set_title('Novels Publication Year Distribution')
        ax.set_xlabel('Publication Year')
        ax.set_ylabel('Number of Novels')
        st.pyplot(fig)

    # Publication Year vs Rating Correlation
    st.write("\nPublication Year vs Rating Correlation:")
    correlation = df[['Publish Year', 'Rating']].corr().iloc[0, 1]
    st.write(f"Correlation Coefficient: **{correlation:.2f}**")

    with st.expander("📈 Year vs Rating Correlation"):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.scatter(df['Publish Year'], df['Rating'], alpha=0.6, color='green')
        ax.set_title('Publication Year vs Rating Relationship')
        ax.set_xlabel('Publication Year')
        ax.set_ylabel('Rating')
        ax.grid(True)
        st.pyplot(fig)


# Streamlit interface
st.title('Interactive Novels Analysis')

# Scraping Data
with st.spinner("Scraping book data..."):
    df = scrape_data()
st.success("✅ Data scraping completed.")

# Cleaning Data
with st.spinner("Cleaning data..."):
    df_cleaned = clean_data(df)
st.success("✅ Data cleaned successfully.")

# Display cleaned data
st.write("Cleaned Data:")
st.dataframe(df_cleaned.head())

# Start the analysis
st.text("\nStarting data analysis...")
analyze_data(df_cleaned)
st.success("✅ Analysis completed successfully!")

# Store the cleaned data into SQLite
conn = sqlite3.connect("novels.db")
df_cleaned.to_sql("novels", conn, if_exists="replace", index=False)
conn.close()

st.success("✅ Data stored in SQLite successfully!")
st.balloons()

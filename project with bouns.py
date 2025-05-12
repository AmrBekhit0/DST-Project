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

    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })
    
    data = []
    page = 1

    while len(data) < 500:
        st.text(f"Scraping page {page}...")
        response = session.get(SEARCH_URL + f"&page={page}")
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
        time.sleep(0.5)
    
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
    st.write("\nBasic statistics:")
    st.write(df.describe())

    # Title Length Distribution
    st.write("\nTitle Length Distribution:")
    df['Title_Length'] = df['Title'].str.len()
    longest_titles = df.nlargest(10, 'Title_Length')[['Title', 'Title_Length']]
    shortest_titles = df.nsmallest(10, 'Title_Length')[['Title', 'Title_Length']]

    st.write("Longest 10 Titles:")
    st.write(longest_titles)
    st.write("\nShortest 10 Titles:")
    st.write(shortest_titles)

    fig, ax = plt.subplots(1, 2, figsize=(12, 6))
    df['Title_Length'].plot(kind='hist', bins=30, color='skyblue', ax=ax[0])
    ax[0].set_title('Title Length Distribution')
    ax[0].set_xlabel('Number of Characters')
    ax[0].set_ylabel('Number of Books')

    # Author Analysis
    st.write("\nAuthor Analysis:")
    df['Primary Author'] = df['Author'].str.split(',').str[0]
    author_counts = df['Primary Author'].value_counts().head(10)
    st.write("Top 10 Authors by Number of Books:")
    st.write(author_counts)

    author_counts.plot(kind='bar', color='orange', ax=ax[1])
    ax[1].set_title('Top Authors by Number of Books')
    ax[1].set_xlabel('Author')
    ax[1].set_ylabel('Number of Books')
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # Publication Year Analysis
    st.write("\nPublication Year Analysis:")
    year_stats = df['Publish Year'].agg(['mean', 'median', 'min', 'max'])
    st.write(f"Mean Publication Year: {year_stats['mean']:.0f}")
    st.write(f"Median Publication Year: {year_stats['median']:.0f}")
    st.write(f"Publication Year Range: {year_stats['min']:.0f}-{year_stats['max']:.0f}")

    fig, ax = plt.subplots(figsize=(10, 5))
    df['Publish Year'].plot(kind='hist', bins=30, color='purple', edgecolor='black', ax=ax)
    ax.set_title('Novels Publication Year Distribution')
    ax.set_xlabel('Publication Year')
    ax.set_ylabel('Number of Novels')
    st.pyplot(fig)

    # Publication Year vs Rating Correlation
    st.write("\nPublication Year vs Rating Correlation:")
    correlation = df[['Publish Year', 'Rating']].corr().iloc[0, 1]
    st.write(f"Correlation Coefficient: {correlation:.2f}")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(df['Publish Year'], df['Rating'], alpha=0.6, color='green')
    ax.set_title('Publication Year vs Rating Relationship')
    ax.set_xlabel('Publication Year')
    ax.set_ylabel('Rating')
    ax.grid(True)
    st.pyplot(fig)

# Streamlit interface
st.title('Interactive Novels Analysis')

st.text("Starting data scraping...")
df = scrape_data()

st.text("Cleaning data...")
df_cleaned = clean_data(df)

# Display cleaned data
st.write("Cleaned Data:")
st.dataframe(df_cleaned.head())

# Start the analysis
st.text("\nStarting data analysis...")
analyze_data(df_cleaned)

st.text("\nAnalysis completed successfully!")

# Optionally, store the cleaned data into SQLite
conn = sqlite3.connect("novels.db")
df_cleaned.to_sql("novels", conn, if_exists="replace", index=False)
conn.close()

st.text("Data stored in SQLite successfully!")
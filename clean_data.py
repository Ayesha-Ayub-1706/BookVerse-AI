import pandas as pd

# Load dataset
books = pd.read_csv("data/Book_Details.csv")

# Keep only required columns
books = books[
    [
        "book_title",
        "author",
        "genres",
        "average_rating",
        "cover_image_uri"
    ]
]

# Rename columns
books.columns = [
    "title",
    "author",
    "genre",
    "rating",
    "image_url"
]

# Remove rows where title or genre is missing
books.dropna(subset=["title", "genre"], inplace=True)

# Remove duplicate books
books.drop_duplicates(subset="title", inplace=True)

# Convert genre column to only first genre
def extract_first_genre(g):
    try:
        return str(g).split(",")[0].replace("[", "").replace("]", "").replace("'", "").strip()
    except:
        return "Unknown"

books["genre"] = books["genre"].apply(extract_first_genre)

# Keep only books with common genres
allowed_genres = [
    "Romance",
    "Fantasy",
    "Thriller",
    "Mystery",
    "Fiction",
    "Horror",
    "Young Adult",
    "Science Fiction"
]

books = books[books["genre"].isin(allowed_genres)]

# Keep only top 1000 books for faster project
books = books[books["rating"] >= 4.0]
books = books.head(1000)

# Save cleaned dataset
books.to_csv("data/cleaned_books.csv", index=False)

print("Cleaned dataset created!")
print(books.head())
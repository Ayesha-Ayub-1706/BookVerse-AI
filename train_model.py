import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load cleaned data
books = pd.read_csv("data/cleaned_books.csv")

# Create a combined text feature
books["features"] = (
    books["title"].fillna("") + " " +
    books["author"].fillna("") + " " +
    books["genre"].fillna("")
)

# Convert to vectors
tfidf = TfidfVectorizer(stop_words="english")
vectors = tfidf.fit_transform(books["features"])

# Similarity matrix
similarity = cosine_similarity(vectors)

# Save files
pickle.dump(books, open("model/books.pkl", "wb"))
pickle.dump(similarity, open("model/similarity.pkl", "wb"))

print("Model trained and saved!")
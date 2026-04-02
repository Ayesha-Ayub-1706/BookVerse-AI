import pickle

books = pickle.load(open("model/books.pkl", "rb"))
similarity = pickle.load(open("model/similarity.pkl", "rb"))

book_name = "Harry Potter and the Sorcerer's Stone"

# Find the selected book
index = books[books["title"] == book_name].index[0]

# Get similarity scores
distances = similarity[index]

# Get top 5 similar books
recommended = sorted(
    list(enumerate(distances)),
    reverse=True,
    key=lambda x: x[1]
)[1:6]

print(f"Recommendations for: {book_name}\n")

for i in recommended:
    row = books.iloc[i[0]]
    print(
        f"{row['title']} | {row['author']} | {row['genre']}"
    )
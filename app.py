from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pickle
import pandas as pd
import os
from difflib import get_close_matches
import urllib.parse

app = Flask(__name__)
app.secret_key = "bookverse_secret_key"  # Required for session and flash

# Load model files
books = pickle.load(open("model/books.pkl", "rb"))
similarity = pickle.load(open("model/similarity.pkl", "rb"))

# Database initialization
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_genres (
            user_id INTEGER,
            genre TEXT,
            count INTEGER,
            PRIMARY KEY(user_id, genre),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn

def fix_image_url(image_val):
    if pd.isna(image_val) or not image_val or str(image_val).lower() == "nan":
        return "https://via.placeholder.com/300x450?text=No+Cover"
    return str(image_val).replace("http://", "https://")

def recommend(book_name):
    titles = books["title"].tolist()
    match = get_close_matches(book_name, titles, n=1, cutoff=0.2)
    
    if not match:
        return [], None
        
    closest_match = match[0]

    try:
        index = books[books["title"] == closest_match].index[0]
    except:
        return [], closest_match

    distances = similarity[index]

    recommended = sorted(
        list(enumerate(distances)),
        reverse=True,
        key=lambda x: x[1]
    )[1:7]

    output = []

    for i in recommended:
        row = books.iloc[i[0]]
        output.append({
            "title": row["title"],
            "author": row["author"],
            "genre": row["genre"],
            "rating": row["rating"],
            "image": fix_image_url(row["image_url"])
        })

    return output, closest_match

def get_books_by_genre(genre):
    filtered = books[books["genre"].str.lower() == genre.lower()]

    filtered = filtered.sort_values(
        by="rating",
        ascending=False
    ).head(12)

    output = []
    for _, row in filtered.iterrows():
        output.append({
            "title": row["title"],
            "author": row["author"],
            "genre": row["genre"],
            "rating": row["rating"],
            "image": fix_image_url(row["image_url"])
        })

    return output

@app.route("/")
def home():
    user_top_genre = None
    if "user_id" in session:
        conn = get_db_connection()
        user_top_genre_row = conn.execute("SELECT genre FROM user_genres WHERE user_id = ? ORDER BY count DESC LIMIT 1", (session["user_id"],)).fetchone()
        conn.close()
        if user_top_genre_row:
            user_top_genre = user_top_genre_row["genre"]

    # Popular books initially
    popular_books = books.sort_values(by="rating", ascending=False).head(12)
    popular_books_dict = []
    for _, row in popular_books.iterrows():
        popular_books_dict.append({
            "title": row["title"],
            "author": row["author"],
            "genre": row["genre"],
            "rating": row["rating"],
            "image": fix_image_url(row["image_url"])
        })
    
    # Genres that we need on the homepage according to instructions
    genres_list = ["Fantasy", "Romance", "Thriller", "Mystery", "Horror", "Science Fiction"]
    genre_books_dict = {}
    for g in genres_list:
        genre_books_dict[g] = get_books_by_genre(g)

    # If the user has a top genre, prioritize recommending from that genre
    recommended_for_you = []
    if user_top_genre:
        recommended_for_you = get_books_by_genre(user_top_genre)
    else:
        # Default recommendation if not logged in or no history
        recommended_for_you = get_books_by_genre("Young Adult")

    return render_template(
        "index.html",
        popular_books=popular_books_dict,
        genres_list=genres_list,
        genre_books_dict=genre_books_dict,
        recommended_for_you=recommended_for_you,
        user_top_genre=user_top_genre
    )

@app.route("/recommend", methods=["POST"])
def recommendation():
    book_name = request.form["book_name"]
    
    unique_genres = [str(g) for g in books["genre"].dropna().unique().tolist()]
    genre_dict = {g.lower(): g for g in unique_genres}
    
    genre_match = get_close_matches(book_name.lower(), genre_dict.keys(), n=1, cutoff=0.8)
    
    if genre_match:
        original_genre = genre_dict[genre_match[0]]
        return redirect(url_for('genre_page', genre=original_genre))
        
    recommendations, closest_match = recommend(book_name)

    return render_template(
        "recommendations.html",
        original_search=book_name,
        closest_match=closest_match,
        recommendations=recommendations
    )

@app.route("/genre/<genre>")
def genre_page(genre):
    # If user is logged in, increase genre count in db
    if "user_id" in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if row exists
        row = cursor.execute("SELECT count FROM user_genres WHERE user_id = ? AND genre = ?", (session["user_id"], genre)).fetchone()
        if row:
            cursor.execute("UPDATE user_genres SET count = count + 1 WHERE user_id = ? AND genre = ?", (session["user_id"], genre))
        else:
            cursor.execute("INSERT INTO user_genres (user_id, genre, count) VALUES (?, ?, 1)", (session["user_id"], genre))
            
        conn.commit()
        conn.close()

    genre_books = get_books_by_genre(genre)

    return render_template(
        "genre.html",
        genre=genre,
        books=genre_books
    )

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_pw = generate_password_hash(password, method='scrypt')

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_pw))
            conn.commit()
            flash("Signup successful! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or Email already exists.", "danger")
        finally:
            conn.close()

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/book/<book_title>")
def book_detail(book_title):
    titles = books["title"].tolist()
    match = get_close_matches(book_title, titles, n=1, cutoff=0.7)
    
    if not match:
        flash("Book not found.", "danger")
        return redirect(url_for("home"))
        
    actual_title = match[0]
    book_row = books[books["title"] == actual_title].iloc[0]
    
    # Generate Amazon Link
    amazon_link = f"https://www.amazon.in/s?k={urllib.parse.quote_plus(actual_title)}"
    
    # Description (handle missing)
    description = book_row.get("description", "")
    if pd.isna(description) or not description or str(description).lower() == 'nan':
        description = "No description available for this book."
        
    # Get 'More Like This'
    try:
        recommendations, _ = recommend(actual_title)
    except:
        recommendations = []
        
    book_details = {
        "title": book_row["title"],
        "author": book_row["author"],
        "genre": book_row["genre"],
        "rating": book_row["rating"],
        "image": fix_image_url(book_row["image_url"]),
        "description": description,
        "purchase_link": amazon_link
    }
    
    return render_template(
        "book_detail.html",
        book=book_details,
        recommendations=recommendations
    )

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pickle
import pandas as pd
import os
from difflib import get_close_matches
import urllib.parse
from functools import wraps

app = Flask(__name__)
app.secret_key = "bookverse_secret_key"
DATABASE = "bookverse.db"

# --- Machine Learning Models ---
books = None
similarity = None

def load_models():
    global books, similarity
    try:
        books = pickle.load(open("model/books.pkl", "rb"))
        similarity = pickle.load(open("model/similarity.pkl", "rb"))
    except Exception as e:
        print(f"Warn: Could not load models. {e}")

load_models()

# --- Database ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Assume init_db.py has been run.
    conn.close()

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login or create an account to unlock personalized recommendations.", "warning")
            return redirect(url_for('signup'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- Helper Functions ---
def fix_image_url(image_val):
    if pd.isna(image_val) or not image_val or str(image_val).lower() == "nan":
        return "https://via.placeholder.com/300x450?text=No+Cover"
    return str(image_val).replace("http://", "https://")

def get_hybrid_recommendations(book_name, user_id=None):
    """Hybrid logic: Combines standard ML with some DB checks if needed.
    For now, core is ML."""
    if books is None or books.empty:
        return [], None

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

    # Hybrid element: if user_id, check what they favored and boost
    # This can be expanded. For now, ML handles it nicely.

    return output, closest_match

def get_books_by_genre(genre, limit=12):
    if books is None or books.empty:
        return []
    filtered = books[books["genre"].str.lower() == genre.lower()]
    filtered = filtered.sort_values(by="rating", ascending=False).head(limit)
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

# --- Routes ---

@app.route("/")
def home():
    if "user_id" not in session:
        return handle_landing_page()
    return handle_user_homepage()

def handle_landing_page():
    # Demo recommendation cards
    demo_recs = [
        {"title": "Harry Potter", "image": "https://via.placeholder.com/150", "author": "J.K. Rowling"},
        {"title": "Percy Jackson", "image": "https://via.placeholder.com/150", "author": "Rick Riordan"},
        {"title": "Atomic Habits", "image": "https://via.placeholder.com/150", "author": "James Clear"},
    ]
    return render_template("landing.html", demo_recs=demo_recs)

def handle_user_homepage():
    user_top_genre = None
    recently_viewed = []
    conn = get_db_connection()
    
    user_top_genre_row = conn.execute("SELECT genre FROM user_genres WHERE user_id = ? ORDER BY count DESC LIMIT 1", (session["user_id"],)).fetchone()
    if user_top_genre_row:
        user_top_genre = user_top_genre_row["genre"]

    # Popular books initially
    popular_books = books.sort_values(by="rating", ascending=False).head(12) if books is not None else pd.DataFrame()
    popular_books_dict = []
    for _, row in popular_books.iterrows():
        popular_books_dict.append({
            "title": row["title"],
            "author": row["author"],
            "genre": row["genre"],
            "rating": row["rating"],
            "image": fix_image_url(row["image_url"])
        })
    
    genres_list = ["Fantasy", "Romance", "Thriller", "Mystery", "Horror", "Science Fiction"]
    genre_books_dict = {}
    for g in genres_list:
        genre_books_dict[g] = get_books_by_genre(g, limit=6)

    recommended_for_you = []
    if user_top_genre:
        recommended_for_you = get_books_by_genre(user_top_genre)
    else:
        recommended_for_you = get_books_by_genre("Young Adult")

    # Fetch recently viewed (Search history)
    recent_searches = conn.execute("SELECT query FROM search_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", (session["user_id"],)).fetchall()
    
    # Stats for Dashboard Cards
    total_explored = conn.execute("SELECT COUNT(DISTINCT query) FROM search_history WHERE user_id = ?", (session["user_id"],)).fetchone()[0]
    fav_count = conn.execute("SELECT COUNT(*) FROM favorites WHERE user_id = ?", (session["user_id"],)).fetchone()[0]
    reading_count = conn.execute("SELECT COUNT(*) FROM reading_list WHERE user_id = ?", (session["user_id"],)).fetchone()[0]
    saved_books_stats = {"favorites": fav_count, "reading_list": reading_count}

    conn.close()

    return render_template(
        "index.html",
        popular_books=popular_books_dict,
        genres_list=genres_list,
        genre_books_dict=genre_books_dict,
        recommended_for_you=recommended_for_you,
        user_top_genre=user_top_genre,
        recent_searches=recent_searches,
        total_explored=total_explored,
        saved_books_stats=saved_books_stats
    )

@app.route("/search", methods=["POST"])
@login_required
def search_post():
    book_name = request.form["book_name"]
    
    # Save search history
    conn = get_db_connection()
    conn.execute("INSERT INTO search_history (user_id, query) VALUES (?, ?)", (session["user_id"], book_name))
    conn.commit()
    conn.close()

    return redirect(url_for('recommendation', book=book_name))

@app.route("/recommend", methods=["GET"])
@login_required
def recommendation():
    book_name = request.args.get("book")
    if not book_name:
        return redirect(url_for('home'))

    unique_genres = [str(g) for g in books["genre"].dropna().unique().tolist()] if books is not None else []
    genre_dict = {g.lower(): g for g in unique_genres}
    genre_match = get_close_matches(book_name.lower(), genre_dict.keys(), n=1, cutoff=0.8)
    
    if genre_match:
        original_genre = genre_dict[genre_match[0]]
        return redirect(url_for('genre_page', genre=original_genre))
        
    recommendations, closest_match = get_hybrid_recommendations(book_name, session["user_id"])

    return render_template(
        "recommendations.html",
        original_search=book_name,
        closest_match=closest_match,
        recommendations=recommendations
    )

@app.route("/genre/<genre>")
@login_required
def genre_page(genre):
    conn = get_db_connection()
    row = conn.execute("SELECT count FROM user_genres WHERE user_id = ? AND genre = ?", (session["user_id"], genre)).fetchone()
    if row:
        conn.execute("UPDATE user_genres SET count = count + 1 WHERE user_id = ? AND genre = ?", (session["user_id"], genre))
    else:
        conn.execute("INSERT INTO user_genres (user_id, genre, count) VALUES (?, ?, 1)", (session["user_id"], genre))
    conn.commit()
    conn.close()

    genre_books = get_books_by_genre(genre)
    return render_template("genre.html", genre=genre, books=genre_books)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_pw = generate_password_hash(password, method='scrypt')

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_pw))
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
            session["role"] = user["role"]
            flash(f"Welcome back, {user['username']}!", "success")
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
@login_required
def book_detail(book_title):
    if books is None:
        flash("Books not loaded", "danger")
        return redirect(url_for("home"))

    titles = books["title"].tolist()
    match = get_close_matches(book_title, titles, n=1, cutoff=0.7)
    
    if not match:
        # Check DB directly in case it's newly added and not retrained
        conn = get_db_connection()
        db_book = conn.execute("SELECT * FROM books WHERE title LIKE ? LIMIT 1", (f"%{book_title}%",)).fetchone()
        conn.close()
        if not db_book:
            flash("Book not found.", "danger")
            return redirect(url_for("home"))
        actual_title = db_book["title"]
        book_row_dict = dict(db_book)
        description = book_row_dict.get("description", "No description available.")
        image = fix_image_url(book_row_dict.get("image_url"))
    else:
        actual_title = match[0]
        book_row = books[books["title"] == actual_title].iloc[0]
        description = book_row.get("description", "")
        if pd.isna(description) or not description or str(description).lower() == 'nan':
            description = "No description available for this book."
        image = fix_image_url(book_row["image_url"])
        book_row_dict = {"title": book_row["title"], "author": book_row["author"], "genre": book_row["genre"], "rating": book_row["rating"]}

    amazon_link = f"https://www.amazon.in/s?k={urllib.parse.quote_plus(actual_title)}"
    
    recommendations, _ = get_hybrid_recommendations(actual_title)
    
    # Check if in favorites / reading list
    conn = get_db_connection()
    is_favorite = conn.execute("SELECT 1 FROM favorites f JOIN books b ON f.book_id = b.id WHERE f.user_id=? AND b.title=?", (session['user_id'], actual_title)).fetchone() is not None
    reading_status = conn.execute("SELECT status FROM reading_list r JOIN books b ON r.book_id = b.id WHERE r.user_id=? AND b.title=?", (session['user_id'], actual_title)).fetchone()
    
    # fetch reviews
    reviews = conn.execute("""
        SELECT r.rating, r.review_text, u.username
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        JOIN books b ON r.book_id = b.id
        WHERE b.title = ?
        ORDER BY r.timestamp DESC
    """, (actual_title,)).fetchall()
    
    conn.close()

    book_details = {
        "title": book_row_dict["title"],
        "author": book_row_dict["author"],
        "genre": book_row_dict["genre"],
        "rating": book_row_dict["rating"],
        "image": image,
        "description": description,
        "purchase_link": amazon_link
    }
    
    return render_template(
        "book_detail.html",
        book=book_details,
        recommendations=recommendations,
        is_favorite=is_favorite,
        reading_status=reading_status['status'] if reading_status else None,
        reviews=reviews
    )

# --- Extended Features (Phase 3 & 4) ---

@app.route("/profile")
@login_required
def profile():
    conn = get_db_connection()
    user_stats = {
        "favorites_count": conn.execute("SELECT count(*) FROM favorites WHERE user_id = ?", (session["user_id"],)).fetchone()[0],
        "reading_count": conn.execute("SELECT count(*) FROM reading_list WHERE user_id = ?", (session["user_id"],)).fetchone()[0]
    }
    recent_searches = conn.execute("SELECT query, timestamp FROM search_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (session["user_id"],)).fetchall()
    favorite_genres = conn.execute("SELECT genre, count FROM user_genres WHERE user_id = ? ORDER BY count DESC LIMIT 3", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("profile.html", user=session, stats=user_stats, recent_searches=recent_searches, favorite_genres=favorite_genres)

@app.route("/favorites")
@login_required
def favorites_page():
    conn = get_db_connection()
    favs_raw = conn.execute("""
        SELECT b.* FROM books b 
        JOIN favorites f ON b.id = f.book_id
        WHERE f.user_id = ?
    """, (session["user_id"],)).fetchall()
    conn.close()
    
    favs = []
    for row in favs_raw:
        favs.append({
            "title": row["title"],
            "author": row["author"],
            "genre": row["genre"],
            "rating": row["rating"],
            "image": fix_image_url(row["image_url"])
        })
    return render_template("favorites.html", books=favs)

@app.route("/reading_list")
@login_required
def reading_list_page():
    conn = get_db_connection()
    r_list_raw = conn.execute("""
        SELECT b.*, r.status FROM books b 
        JOIN reading_list r ON b.id = r.book_id
        WHERE r.user_id = ?
    """, (session["user_id"],)).fetchall()
    conn.close()
    
    r_list = []
    for row in r_list_raw:
        r_list.append({
            "title": row["title"],
            "author": row["author"],
            "genre": row["genre"],
            "rating": row["rating"],
            "image": fix_image_url(row["image_url"]),
            "status": row["status"]
        })
    return render_template("reading_list.html", books=r_list)

@app.route("/action/favorite", methods=["POST"])
@login_required
def toggle_favorite():
    book_title = request.form.get("book_title")
    conn = get_db_connection()
    book = conn.execute("SELECT id FROM books WHERE title = ?", (book_title,)).fetchone()
    if book:
        existing = conn.execute("SELECT id FROM favorites WHERE user_id = ? AND book_id = ?", (session["user_id"], book["id"])).fetchone()
        if existing:
            conn.execute("DELETE FROM favorites WHERE id = ?", (existing["id"],))
            flash("Removed from favorites.", "info")
        else:
            conn.execute("INSERT INTO favorites (user_id, book_id) VALUES (?, ?)", (session["user_id"], book["id"]))
            flash("Added to favorites!", "success")
        conn.commit()
    conn.close()
    return redirect(url_for('book_detail', book_title=book_title))

@app.route("/action/reading_list", methods=["POST"])
@login_required
def update_reading_list():
    book_title = request.form.get("book_title")
    status = request.form.get("status")
    conn = get_db_connection()
    book = conn.execute("SELECT id FROM books WHERE title = ?", (book_title,)).fetchone()
    if book:
        existing = conn.execute("SELECT id FROM reading_list WHERE user_id = ? AND book_id = ?", (session["user_id"], book["id"])).fetchone()
        if existing:
            conn.execute("UPDATE reading_list SET status = ? WHERE id = ?", (status, existing["id"]))
        else:
            conn.execute("INSERT INTO reading_list (user_id, book_id, status) VALUES (?, ?, ?)", (session["user_id"], book["id"], status))
        conn.commit()
        flash(f"Moved to {status}.", "success")
    conn.close()
    return redirect(url_for('book_detail', book_title=book_title))

@app.route("/action/review", methods=["POST"])
@login_required
def add_review():
    book_title = request.form.get("book_title")
    rating = int(request.form.get("rating", 5))
    text = request.form.get("review_text", "")
    conn = get_db_connection()
    book = conn.execute("SELECT id FROM books WHERE title = ?", (book_title,)).fetchone()
    if book:
        try:
           conn.execute("INSERT INTO reviews (user_id, book_id, rating, review_text) VALUES (?, ?, ?, ?)", (session["user_id"], book["id"], rating, text))
           conn.commit()
           flash("Review added!", "success")
        except sqlite3.IntegrityError:
           flash("You have already reviewed this book.", "warning")
    conn.close()
    return redirect(url_for('book_detail', book_title=book_title))

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    books_data = conn.execute("SELECT * FROM books ORDER BY id DESC LIMIT 100").fetchall()
    users_count = conn.execute("SELECT count(*) FROM users").fetchone()[0]
    searches_count = conn.execute("SELECT count(*) FROM search_history").fetchone()[0]
    conn.close()
    return render_template("admin.html", books=books_data, stats={"users": users_count, "searches": searches_count})

@app.route("/admin/retrain", methods=["POST"])
@admin_required
def admin_retrain():
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import pickle
    
    conn = get_db_connection()
    # we need title, author, genre for features
    books_df = pd.read_sql_query("SELECT id, title, author, genre, rating, image_url, description FROM books", conn)
    conn.close()
    
    if len(books_df) == 0:
        flash("No books in database to train on.", "danger")
        return redirect(url_for('admin_dashboard'))
        
    books_df["features"] = (
        books_df["title"].fillna("") + " " +
        books_df["author"].fillna("") + " " +
        books_df["genre"].fillna("")
    )
    
    tfidf = TfidfVectorizer(stop_words="english")
    vectors = tfidf.fit_transform(books_df["features"])
    new_similarity = cosine_similarity(vectors)
    
    # Save files
    os.makedirs("model", exist_ok=True)
    pickle.dump(books_df, open("model/books.pkl", "wb"))
    pickle.dump(new_similarity, open("model/similarity.pkl", "wb"))
    
    # Reload server globals
    load_models()
    
    flash("Model retrained successfully. All database books are now embedded.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/add_book", methods=["POST"])
@admin_required
def admin_add_book():
    title = request.form.get("title")
    author = request.form.get("author")
    genre = request.form.get("genre")
    rating = request.form.get("rating", 4.0)
    conn = get_db_connection()
    conn.execute("INSERT INTO books (title, author, genre, rating) VALUES (?, ?, ?, ?)", (title, author, genre, rating))
    conn.commit()
    conn.close()
    flash(f"Book '{title}' added to Database! Note: It will not appear in recommendations until you Retrain The Model.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/delete_book/<int:book_id>", methods=["POST"])
@admin_required
def admin_delete_book(book_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    flash("Book deleted from database. Please Retrain the Model to reflect changes in recommendations.", "info")
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
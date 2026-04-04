import sqlite3
import pandas as pd

def migrate_db():
    print("Initializing Database...")
    conn = sqlite3.connect("bookverse.db")
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    ''')

    # Books table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            genre TEXT,
            rating REAL,
            image_url TEXT,
            description TEXT
        )
    ''')

    # Favorites
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            book_id INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(book_id) REFERENCES books(id),
            UNIQUE(user_id, book_id)
        )
    ''')

    # Reading List
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            book_id INTEGER,
            status TEXT, -- 'Want to Read', 'Reading', 'Completed'
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(book_id) REFERENCES books(id),
            UNIQUE(user_id, book_id)
        )
    ''')

    # Search History
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Reviews
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            book_id INTEGER,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            review_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(book_id) REFERENCES books(id),
            UNIQUE(user_id, book_id)
        )
    ''')

    # User Genres (existing but re-implementing)
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
    
    # Load Initial Books Data
    # Let's see if books table is empty
    count = cursor.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    if count == 0:
        print("Populating books table from cleaned_books.csv...")
        try:
            books_df = pd.read_csv("data/cleaned_books.csv")
            for _, row in books_df.iterrows():
                cursor.execute("""
                    INSERT INTO books (title, author, genre, rating, image_url, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    row.get('title', ''), 
                    row.get('author', ''), 
                    row.get('genre', ''), 
                    row.get('rating', 0.0), 
                    row.get('image_url', ''), 
                    row.get('description', '')
                ))
            conn.commit()
            print(f"Inserted {len(books_df)} books into database.")
        except Exception as e:
            print(f"Error migrating books: {e}")
            
    # Add an admin user programmatically if not exists
    try:
        from werkzeug.security import generate_password_hash
        admin_pw = generate_password_hash("admin123", method="scrypt")
        cursor.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)", 
                      ("admin", "admin@bookverse.local", admin_pw, "admin"))
        conn.commit()
        print("Created default admin user (admin / admin123).")
    except sqlite3.IntegrityError:
        pass # Admin already exists

    conn.close()
    print("Database initialised successfully!")

if __name__ == "__main__":
    migrate_db()

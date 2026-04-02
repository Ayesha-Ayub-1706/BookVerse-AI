# BookVerse AI 📚✨

BookVerse AI is a content-based book recommendation web application that helps users discover books similar to the ones they love.

The project uses Machine Learning with TF-IDF vectorization and cosine similarity to analyze book titles, authors, and genres, then recommends books with similar characteristics.

---

## Features

- User Login and Signup
- Book Recommendation System
- Genre-wise Browsing
- Book Detail Page
- Responsive Frontend
- Machine Learning Based Recommendations

---

## Technologies Used

- Python
- Flask
- Pandas
- Scikit-learn
- NumPy
- HTML
- CSS
- JavaScript
- SQLite

---

## Folder Structure

```text
BookVerseAI/
│
├── data/
│   ├── Book_Details.csv
│   └── cleaned_books.csv
│
├── model/
│   ├── books.pkl
│   └── similarity.pkl
│
├── static/
│   ├── script.js
│   └── style.css
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── recommendations.html
│   ├── genre.html
│   └── book_detail.html
│
├── app.py
├── clean_data.py
├── train_model.py
├── test.py
├── requirements.txt
├── README.md
└── .gitignore

## How to Run


Install required libraries
pip install -r requirements.txt
Train the recommendation model (only once)
python train_model.py
Run the Flask app
python app.py
Open in browser
http://127.0.0.1:5000
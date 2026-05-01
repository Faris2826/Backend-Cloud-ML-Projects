import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score

# Sample dataset (replace with your own)
DATA = [
    ("I love this product, it works amazingly well", "positive"),
    ("Terrible experience, would not recommend", "negative"),
    ("Best purchase I have ever made", "positive"),
    ("Waste of money, completely disappointed", "negative"),
    ("The quality is outstanding and delivery was fast", "positive"),
    ("Broke after one day of use, very poor quality", "negative"),
    ("Absolutely fantastic, exceeded my expectations", "positive"),
    ("Not worth the price, many better alternatives", "negative"),
    ("Great customer service and friendly staff", "positive"),
    ("Horrible support, nobody replied to my emails", "negative"),
    ("I am so happy with this purchase", "positive"),
    ("The worst product I have ever bought", "negative"),
    ("Highly recommend to everyone", "positive"),
    ("Defective item received, requesting refund", "negative"),
    ("Five stars, will buy again", "positive"),
    ("One star, complete garbage", "negative"),
    ("Works as described, no complaints", "positive"),
    ("Stopped working after a week", "negative"),
    ("Excellent value for money", "positive"),
    ("Misleading description, item is much smaller", "negative"),
]

def train_model():
    df = pd.DataFrame(DATA, columns=["text", "label"])

    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=0.2, random_state=42
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=1000, ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=1000))
    ])

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    os.makedirs("models", exist_ok=True)
    joblib.dump(pipeline, "models/text_classifier.pkl")
    print("\nModel saved to models/text_classifier.pkl")

if __name__ == "__main__":
    train_model()

"""Campus AI: finds the best matching FAQ for a question.

How it works (no internet and no API key needed):
  1. Every FAQ row is turned into one text: question + keywords + category + answer.
  2. TF-IDF turns each text and the student's question into a vector of numbers.
  3. Cosine similarity measures how close the question is to every FAQ.
  4. The closest FAQ wins if its score is above a threshold, otherwise the
     assistant says it could not find a reliable answer and suggests similar questions.

Two TF-IDF models are blended:
  * a WORD model  - understands meaning (words and word pairs, plurals, synonyms)
  * a CHARACTER model - forgives spelling mistakes ("hostle fee", "libary timing")
"""

from __future__ import annotations

import difflib
import re

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Words that carry no meaning for matching.
STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "am", "do", "does", "did",
    "i", "me", "my", "we", "our", "you", "your", "it", "its", "this", "that", "these", "those",
    "of", "to", "in", "on", "at", "for", "and", "or", "by", "with", "from", "as", "into",
    "what", "whats", "which", "who", "whom", "where", "when", "why", "how",
    "can", "could", "should", "would", "will", "shall", "may", "there", "any", "some",
    "tell", "please", "give", "show", "know", "want", "need", "get", "about", "so", "if",
    "hi", "hello", "hey",
}

# Different ways to say the same thing -> shared words. One word can expand into several.
SYNONYMS = {
    "wifi": ["wifi"], "internet": ["wifi"], "wlan": ["wifi"],
    "hod": ["head"], "hods": ["head"], "chief": ["head"],
    "director": ["principal"], "headmaster": ["principal"],
    "aiml": ["aiml", "ai", "ml"], "aiandml": ["aiml", "ai", "ml"],
    "prof": ["faculty"], "professor": ["faculty"], "teacher": ["faculty"], "staff": ["faculty"],
    "lecturer": ["faculty"], "sir": ["faculty"], "madam": ["faculty"],
    "cost": ["fee"], "price": ["fee"], "charge": ["fee"], "charges": ["fee"], "payment": ["fee", "payment"],
    "tution": ["tuition"], "tuiton": ["tuition"],
    "cafeteria": ["canteen"], "cafe": ["canteen"], "food": ["food"],
    "1st": ["first"], "2nd": ["second"], "3rd": ["third"], "4th": ["final"], "fourth": ["final"],
    "last": ["final"], "yr": ["year"], "yrs": ["year"], "sem": ["semester"], "sems": ["semester"],
    "doc": ["document"], "docs": ["document"], "certificates": ["certificate"],
    "tc": ["transfer", "certificate"], "ct": ["test"],
    "ragging": ["ragging"], "scholar": ["scholarship"],
    "bike": ["two", "wheeler", "parking"], "scooter": ["two", "wheeler", "parking"],
    "ph": ["phone"], "mob": ["phone"], "mobile": ["phone", "mobile"], "number": ["phone", "number"],
    "mail": ["email"], "e-mail": ["email"],
    "hours": ["timing"], "time": ["timing"], "schedule": ["timing"], "open": ["timing", "open"],
    "salary": ["package"], "ctc": ["package"], "lpa": ["package"],
    "job": ["placement"], "jobs": ["placement"], "company": ["company"], "companies": ["company"],
    "ground": ["ground"], "gym": ["gym"], "pg": ["postgraduate"],
    "uni": ["university"], "approval": ["approved"],
}


def _stem(word: str) -> str:
    """Very small stemmer so 'fees' = 'fee', 'timings' = 'timing', 'scholarships' = 'scholarship'."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("sses"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        word = word[:-1]
    if len(word) > 5 and word.endswith("ing"):
        word = word[:-3]
    return word


def normalise_tokens(text: str) -> list[str]:
    """lower-case -> words -> remove stop words -> synonyms -> stem."""
    text = str(text).lower().replace("wi-fi", "wifi").replace("e-mail", "email")
    text = text.replace("ai and ml", "aiml").replace("ai & ml", "aiml").replace("ai/ml", "aiml")
    tokens = []
    for word in re.findall(r"[a-z0-9]+", text):
        if word in STOP_WORDS:
            continue
        for item in SYNONYMS.get(word, [word]):
            tokens.append(_stem(item))
    return tokens


def word_analyzer(text: str) -> list[str]:
    """Single words plus pairs of neighbouring words ('hostel fee' is more specific than 'hostel')."""
    tokens = normalise_tokens(text)
    return tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]


def _clean(value) -> str:
    return "" if pd.isna(value) else str(value).strip()


class CampusAI:
    """Search engine over the FAQ table (columns: question, answer, keywords, category, ...)."""

    # Tuned on the 150 SRGI FAQs: real questions score above ~0.3, off-topic text scores below ~0.2.
    MIN_SCORE = 0.22
    WORD_WEIGHT = 0.7
    CHAR_WEIGHT = 0.3

    def __init__(self, faq_df: pd.DataFrame):
        self.faq = faq_df.reset_index(drop=True).copy()
        for column in ("id", "category", "subcategory", "question", "answer", "keywords", "contact_or_department"):
            if column not in self.faq.columns:
                self.faq[column] = ""

        documents = []
        self._keyword_phrases = []
        for _, row in self.faq.iterrows():
            question = _clean(row["question"])
            keywords = _clean(row["keywords"])
            # The question and keywords count more than the long answer text.
            documents.append(" . ".join([
                question, question, question,
                keywords, keywords,
                _clean(row["subcategory"]), _clean(row["category"]),
                _clean(row["answer"]),
            ]))
            phrases = [" ".join(normalise_tokens(k)) for k in keywords.split(",")]
            self._keyword_phrases.append([p for p in phrases if p])

        # Every word the FAQ knows. Used to fix spelling mistakes and to spot words it has never seen.
        self._raw_vocab = {
            w for d in documents for w in re.findall(r"[a-z0-9]+", d.lower()) if len(w) >= 4 and w not in STOP_WORDS
        }
        self._known_tokens = {t for d in documents for t in normalise_tokens(d)}

        self._word_vectorizer = TfidfVectorizer(analyzer=word_analyzer, sublinear_tf=True)
        self._char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        normalised_docs = [" ".join(normalise_tokens(d)) for d in documents]
        self._word_matrix = self._word_vectorizer.fit_transform(documents)
        self._char_matrix = self._char_vectorizer.fit_transform(normalised_docs)

    # ------------------------------------------------------------------ scoring
    def _correct_spelling(self, question: str) -> str:
        """'libary timing' -> 'library timing' (only words the FAQ does not know, 4+ letters)."""
        fixed = []
        for word in re.findall(r"[a-z0-9]+|[^a-z0-9]+", question.lower()):
            if len(word) >= 4 and word.isalpha() and word not in self._raw_vocab \
                    and word not in STOP_WORDS and word not in SYNONYMS:
                close = difflib.get_close_matches(word, self._raw_vocab, n=1, cutoff=0.8)
                word = close[0] if close else word
            fixed.append(word)
        return "".join(fixed)

    def _scores(self, question: str):
        question = self._correct_spelling(question)
        tokens = normalise_tokens(question)
        normalised = " ".join(tokens)

        word_scores = cosine_similarity(self._word_vectorizer.transform([question]), self._word_matrix)[0]
        char_scores = cosine_similarity(self._char_vectorizer.transform([normalised]), self._char_matrix)[0]
        scores = self.WORD_WEIGHT * word_scores + self.CHAR_WEIGHT * char_scores

        # Small bonus when a whole keyword phrase of the FAQ appears in the question.
        padded = f" {normalised} "
        for i, phrases in enumerate(self._keyword_phrases):
            hits = sum(1 for p in phrases if f" {p} " in padded)
            if hits:
                scores[i] += min(0.06 * hits, 0.15)
        scores = scores.clip(max=1.0)

        # Words the FAQ has never seen ("bitcoin") make a match less trustworthy.
        if tokens:
            coverage = sum(t in self._known_tokens for t in tokens) / len(tokens)
            scores = scores * (0.3 + 0.7 * coverage)
        return scores

    # ------------------------------------------------------------------ public
    def ask(self, question: str, top_k: int = 3) -> dict:
        """Returns a dict: found, answer, question, department, category, score, suggestions."""
        question = (question or "").strip()
        if len(normalise_tokens(question)) == 0:
            return {
                "found": False,
                "score": 0.0,
                "answer": "Please ask a question with a few keywords, for example: hostel fee, library timings or attendance.",
                "suggestions": [],
            }

        scores = self._scores(question)
        order = scores.argsort()[::-1]
        best = int(order[0])
        best_score = float(scores[best])

        if best_score < self.MIN_SCORE:
            return {
                "found": False,
                "score": best_score,
                "answer": "Sorry, I could not find a reliable answer to that in the SRGI FAQ. "
                          "Try different keywords, or contact the Admin Office.",
                "suggestions": [_clean(self.faq.loc[int(i), "question"]) for i in order[:top_k] if scores[int(i)] > 0.1],
            }

        row = self.faq.loc[best]
        related = [
            _clean(self.faq.loc[int(i), "question"])
            for i in order[1:top_k + 1]
            if scores[int(i)] >= self.MIN_SCORE
        ]
        return {
            "found": True,
            "score": best_score,
            "id": _clean(row["id"]),
            "category": _clean(row["category"]),
            "question": _clean(row["question"]),
            "answer": _clean(row["answer"]),
            "department": _clean(row["contact_or_department"]),
            "suggestions": related,
        }

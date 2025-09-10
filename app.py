from flask import Flask, render_template, request
from local_fragrance_search import FragranceSearcher
from models import init_db, add_note, get_notes

app = Flask(__name__)
app.secret_key = "dev-secret"

# Initialize local Kaggle dataset
searcher = FragranceSearcher("fra_cleaned (1).csv")
init_db()

@app.route("/", methods=["GET", "POST"])
def index():
    query = request.values.get("q", "").strip()
    detail, notes, error = None, [], None

    if request.method == "POST" and request.form.get("note_text") and request.form.get("fname"):
        fid = request.form["fname"]
        fname = request.form["fname"]
        txt = request.form["note_text"].strip()
        if txt:
            add_note(fid, fname, txt)
        query = fname
        detail = searcher.find_profile(fname)
        if detail:
            notes = get_notes(fname)

    try:
        if query:
            detail = searcher.find_profile(query)
            if detail:
                notes = get_notes(detail["name"])
    except Exception as e:
        error = str(e)

    return render_template("index.html", query=query, detail=detail, notes=notes, error=error)

if __name__ == "__main__":
    app.run(debug=True)

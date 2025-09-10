from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///fragrance_notes.db", future=True)

def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fragrance_id TEXT NOT NULL,
                fragrance_name TEXT NOT NULL,
                note_text TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

def add_note(fragrance_id: str, fragrance_name: str, note_text: str):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO notes (fragrance_id, fragrance_name, note_text) VALUES (:fid,:fname,:txt)"),
            {"fid": str(fragrance_id), "fname": fragrance_name, "txt": note_text}
        )

def get_notes(fragrance_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, fragrance_id, fragrance_name, note_text, created_at FROM notes WHERE fragrance_id = :fid ORDER BY created_at DESC"),
            {"fid": str(fragrance_id)}
        ).mappings().all()
        return list(rows)

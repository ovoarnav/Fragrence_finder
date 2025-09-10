import re
import pandas as pd
from difflib import get_close_matches
from pathlib import Path

class FragranceSearcher:
    def __init__(self, csv_path: str | Path):
        self.path = Path(csv_path)
        self.df = pd.read_csv(self.path, sep=";", encoding="latin-1", engine="python")
        self._prep()

    @staticmethod
    def _norm(s: str) -> str:
        if pd.isna(s): return ""
        s = str(s).lower()
        s = re.sub(r"[^a-z0-9\s\-&'/]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @staticmethod
    def _tokens(s: str) -> set[str]:
        if s is None: return set()
        s = str(s).lower()
        s = re.sub(r"[-/]", " ", s)
        s = re.sub(r"[^a-z0-9\s]+", " ", s)
        return set(t for t in s.split() if t)

    def _prep(self):
        df = self.df
        df["perfume_norm"] = df["Perfume"].apply(self._norm)
        df["brand_norm"] = df["Brand"].apply(self._norm)
        df["full_norm"] = (df["brand_norm"] + " " + df["perfume_norm"]).str.strip()
        self.df = df

    def search_candidates(self, query: str, topn: int = 15) -> pd.DataFrame:
        q = self._norm(query)
        df = self.df
        mask = (
            df["perfume_norm"].str.contains(q, na=False) |
            df["brand_norm"].str.contains(q, na=False) |
            df["full_norm"].str.contains(q, na=False)
        )
        hits = df[mask].copy()
        if hits.empty:
            population = df["full_norm"].unique().tolist()
            close = get_close_matches(q, population, n=topn*5, cutoff=0.6)
            hits = df[df["full_norm"].isin(close)].copy()
            if hits.empty:
                return hits
        q_tokens = self._tokens(query)
        def base_score(row):
            fn_tokens = set(str(row["full_norm"]).split())
            overlap = len(q_tokens & fn_tokens)
            score = overlap * 10
            try:
                rc = float(row.get("Rating Count", 0) or 0)
            except: rc = 0.0
            score += min(rc/1000.0, 50)
            return score
        hits["__score"] = hits.apply(base_score, axis=1)
        cols = ["Brand","Perfume","Year","Gender","Rating Value","Rating Count","Top","Middle","Base",
                "mainaccord1","mainaccord2","mainaccord3","mainaccord4","mainaccord5","url","__score"]
        return hits[cols].sort_values("__score", ascending=False).head(topn)

    def _select_best(self, hits_df: pd.DataFrame, query: str) -> dict | None:
        if hits_df.empty: return None
        q_tokens = self._tokens(query)
        q_norm = self._norm(query)
        def s(row):
            pn_raw = row["Perfume"]; bn_raw = row["Brand"]
            pn_t = self._tokens(pn_raw); bn_t = self._tokens(bn_raw)
            score = 0.0
            if pn_t and pn_t.issubset(q_tokens): score += 1000
            if bn_t and bn_t.issubset(q_tokens): score += 200
            score += len(pn_t & q_tokens) * 40
            score += len(bn_t & q_tokens) * 20
            pn_norm = self._norm(pn_raw); bn_norm = self._norm(bn_raw)
            if pn_norm and pn_norm in q_norm: score += 200
            if bn_norm and bn_norm in q_norm: score += 80
            try: rc = float(row.get("Rating Count", 0) or 0)
            except: rc = 0.0
            score += min(rc/1000.0, 50)
            return score
        scored = hits_df.copy()
        scored["__sel"] = scored.apply(s, axis=1)
        best = scored.sort_values("__sel", ascending=False).iloc[0]
        return best.to_dict()

    @staticmethod
    def _split_notes(val):
        if pd.isna(val) or not str(val).strip(): return []
        parts = re.split(r",|\band\b", str(val), flags=re.I)
        parts = [p.strip().strip(".").lower() for p in parts if p and p.strip()]
        return [w.title() if not w.isupper() else w for w in parts]

    def to_profile(self, row_dict: dict) -> dict:
        accords = [row_dict.get("mainaccord1"), row_dict.get("mainaccord2"),
                   row_dict.get("mainaccord3"), row_dict.get("mainaccord4"), row_dict.get("mainaccord5")]
        accords = [a.title() for a in accords if isinstance(a, str) and a.strip()]
        year = row_dict.get("Year")
        try: year = int(year) if pd.notna(year) else None
        except: year = None
        return {
            "brand": row_dict.get("Brand"),
            "name": row_dict.get("Perfume"),
            "year": year,
            "gender": row_dict.get("Gender"),
            "rating_value": row_dict.get("Rating Value"),
            "rating_count": row_dict.get("Rating Count"),
            "url": row_dict.get("url"),
            "notes": {
                "top": self._split_notes(row_dict.get("Top")),
                "middle": self._split_notes(row_dict.get("Middle")),
                "base": self._split_notes(row_dict.get("Base")),
            },
            "accords": accords
        }

    def find_profile(self, query: str) -> dict | None:
        hits = self.search_candidates(query, topn=20)
        if hits.empty: return None
        best = self._select_best(hits, query)
        return self.to_profile(best)

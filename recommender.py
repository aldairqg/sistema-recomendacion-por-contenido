"""Recomendación ítem a ítem usando exclusivamente características del audio."""
from pathlib import Path
import unicodedata

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

FEATURES = {
    "danceability": "Bailabilidad", "energy": "Energía", "valence": "Valencia",
    "acousticness": "Acústica", "instrumentalness": "Instrumentalidad",
    "speechiness": "Voz hablada", "liveness": "Presencia de público",
    "tempo": "Tempo", "loudness": "Sonoridad",
}
DEFAULT_DATASET = Path(__file__).parent / "archive" / "dataset.csv"


def normalized_text(value):
    """Normaliza texto para búsqueda y para excluir versiones con el mismo título."""
    return "".join(c for c in unicodedata.normalize("NFKD", str(value).casefold())
                   if not unicodedata.combining(c)).strip()


class ContentRecommender:
    def __init__(self, path=DEFAULT_DATASET):
        source = pd.read_csv(path)
        required = {"track_id", "track_name", "artists", "track_genre", *FEATURES}
        missing = required - set(source.columns)
        if missing:
            raise ValueError(f"Faltan columnas: {', '.join(sorted(missing))}")
        valid = source.dropna(subset=["track_id", "track_name", "artists"]).copy()
        for column in ["track_id", "track_name", "artists"]:
            valid = valid[valid[column].astype(str).str.strip().ne("")]
        genres = valid.groupby("track_id", sort=False).track_genre.agg(
            lambda values: sorted(set(values.dropna().astype(str))))
        self.frame = valid.drop_duplicates("track_id", keep="first").reset_index(drop=True)
        self.frame["genres"] = self.frame.track_id.map(genres)
        values = self.frame[list(FEATURES)].apply(pd.to_numeric, errors="coerce")
        values = values.replace([np.inf, -np.inf], np.nan)
        imputed = int(values.isna().sum().sum())
        # Una columna completamente ausente no permite un escalado interpretable.
        if values.isna().all().any():
            raise ValueError("Hay características sin ningún valor numérico válido.")
        self.raw = values.fillna(values.median()).to_numpy(dtype=float)
        if len(self.raw) < 2:
            raise ValueError("Se necesitan al menos dos canciones válidas.")
        self.scaler = StandardScaler()
        self.vectors = self.scaler.fit_transform(self.raw)
        self.ids = {str(value): i for i, value in enumerate(self.frame.track_id)}
        self.search_text = (self.frame.track_name + " " + self.frame.artists).map(normalized_text)
        self.signatures = (self.frame.track_name.map(normalized_text) + "|" +
                           self.frame.artists.map(normalized_text)).to_numpy()
        self.stats = {
            "rows": len(source), "tracks": len(self.frame),
            "invalid_rows": len(source) - len(valid),
            "duplicate_ids": len(valid) - len(self.frame),
            "genres": int(valid.track_genre.nunique()), "imputed_values": imputed,
            "features": [{"key": key, "label": label,
                          "mean": float(self.scaler.mean_[j]),
                          "std": float(self.scaler.scale_[j])}
                         for j, (key, label) in enumerate(FEATURES.items())],
        }

    def track(self, index):
        row = self.frame.iloc[index]
        return {"id": str(row.track_id), "name": str(row.track_name),
                "artists": str(row.artists), "genres": row.genres,
                "values": dict(zip(FEATURES, self.raw[index].tolist()))}

    def search(self, query, limit=20):
        query = normalized_text(query)
        if not query:
            return []
        mask = self.search_text.str.contains(query, regex=False)
        indices = np.flatnonzero(mask.to_numpy())
        # Coincidencias exactas primero; nunca ordenar por popularidad.
        indices = sorted(indices, key=lambda i: (
            normalized_text(self.frame.iloc[i].track_name) != query, i))
        return [self.track(i) for i in indices[:limit]]

    def recommend(self, track_id, count=6, weights=None):
        if track_id not in self.ids:
            raise KeyError("Canción no encontrada.")
        if not 1 <= count <= 20:
            raise ValueError("La cantidad debe estar entre 1 y 20.")
        weights = weights if weights is not None else {}
        if not isinstance(weights, dict) or set(weights) - set(FEATURES):
            raise ValueError("Los pesos deben corresponder a las características disponibles.")
        w = np.array([float(weights.get(key, 1)) for key in FEATURES])
        if not np.isfinite(w).all() or (w < 0).any() or (w > 3).any() or not w.any():
            raise ValueError("Usa pesos de 0 a 3 y activa al menos una característica.")
        index = self.ids[track_id]
        # sqrt(w) hace que el producto escalar use w, no w².
        weighted = self.vectors * np.sqrt(w)
        norms = np.linalg.norm(weighted, axis=1)
        if norms[index] < 1e-12:
            raise ValueError("La canción tiene un vector nulo con estos pesos. Activa otra característica.")
        unit = np.divide(weighted, norms[:, None], out=np.zeros_like(weighted),
                         where=norms[:, None] > 1e-12)
        scores = np.clip(unit @ unit[index], -1, 1)
        eligible = (norms > 1e-12) & (self.signatures != self.signatures[index])
        ranked = np.argsort(-np.where(eligible, scores, -np.inf), kind="stable")
        seen = {self.signatures[index]}
        recommendations = []
        for candidate in ranked:
            if not eligible[candidate] or self.signatures[candidate] in seen:
                continue
            seen.add(self.signatures[candidate])
            explanation = []
            for j, (key, label) in enumerate(FEATURES.items()):
                explanation.append({"key": key, "label": label, "weight": float(w[j]),
                    "seed_raw": float(self.raw[index, j]), "candidate_raw": float(self.raw[candidate, j]),
                    "seed_z": float(self.vectors[index, j]), "candidate_z": float(self.vectors[candidate, j]),
                    "contribution": float(unit[index, j] * unit[candidate, j]),
                    "distance_z": float(abs(self.vectors[index, j] - self.vectors[candidate, j]))})
            closest = sorted((item for item in explanation if item["weight"] > 0),
                             key=lambda item: item["distance_z"])[:3]
            recommendations.append({**self.track(candidate), "score": float(scores[candidate]),
                                    "explanation": explanation, "closest": [x["label"] for x in closest]})
            if len(recommendations) == count:
                break
        return {"seed": self.track(index), "recommendations": recommendations,
                "weights": dict(zip(FEATURES, w.tolist())),
                "compared": int(eligible.sum())}

"""Pruebas matemáticas y de integridad del recomendador, sin red."""
import tempfile
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from recommender import ContentRecommender, FEATURES


class RecommenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = ContentRecommender()
        cls.seed = '0VjIjW4GlUZAMYd2vXMi3b'

    def test_cleaning_counts(self):
        stats = self.model.stats
        self.assertEqual(stats['rows'], 114000)
        self.assertEqual(stats['tracks'], 89740)
        self.assertEqual(stats['rows'], stats['tracks'] + stats['invalid_rows'] + stats['duplicate_ids'])
        self.assertTrue(np.isfinite(self.model.vectors).all())

    def test_ranking_matches_independent_cosine(self):
        m = self.model
        result = m.recommend(self.seed, 20)
        expected = cosine_similarity(m.vectors[m.ids[self.seed]][None,:], m.vectors)[0]
        candidate_scores = [item['score'] for item in result['recommendations']]
        self.assertEqual(candidate_scores, sorted(candidate_scores, reverse=True))
        eligible = m.signatures != m.signatures[m.ids[self.seed]]
        self.assertAlmostEqual(candidate_scores[0], expected[eligible].max(), places=12)
        for item in result['recommendations']:
            self.assertAlmostEqual(item['score'], expected[m.ids[item['id']]], places=12)

    def test_weighted_cosine_and_explanation(self):
        m = self.model
        weights = {key: (i % 3) for i, key in enumerate(FEATURES)}
        result = m.recommend(self.seed, weights=weights)
        matrix = m.vectors * np.sqrt(list(weights.values()))
        expected = cosine_similarity(matrix[m.ids[self.seed]][None,:], matrix)[0]
        for item in result['recommendations']:
            self.assertAlmostEqual(item['score'], expected[m.ids[item['id']]], places=12)
            self.assertAlmostEqual(item['score'], sum(f['contribution'] for f in item['explanation']), places=12)
            for f in item['explanation']:
                if weights[f['key']] == 0:
                    self.assertEqual(f['contribution'], 0)

    def test_excludes_seed_and_repeated_titles_by_artist(self):
        items = self.model.recommend(self.seed, 20)['recommendations']
        signatures = [self.model.signatures[self.model.ids[item['id']]] for item in items]
        self.assertNotIn(self.model.signatures[self.model.ids[self.seed]], signatures)
        self.assertEqual(len(signatures), len(set(signatures)))
        self.assertEqual(len(items), 20)

    def test_search_is_case_insensitive_and_literal(self):
        self.assertEqual(self.model.search('BLINDING LIGHTS'), self.model.search('blinding lights'))
        self.assertEqual(self.model.search(''), [])
        self.assertEqual(self.model.search('[.*nonexistent.*]'), [])

    def test_rejects_invalid_weights(self):
        for weights in [{key: 0 for key in FEATURES}, {'energy': -1}, {'energy': 4},
                        {'energy': float('nan')}, {'energy': float('inf')},
                        {'popularity': 3}, [], {'energy': None}]:
            with self.subTest(weights=weights), self.assertRaises((ValueError, TypeError)):
                self.model.recommend(self.seed, weights=weights)

    def test_bad_id_and_counts(self):
        with self.assertRaises(KeyError):
            self.model.recommend('unknown')
        for count in [0, -1, 21]:
            with self.assertRaises(ValueError):
                self.model.recommend(self.seed, count)

    def test_model_uses_only_audio(self):
        self.assertEqual(self.model.vectors.shape[1], 9)
        self.assertTrue({'popularity', 'artists', 'track_genre', 'track_name'}.isdisjoint(FEATURES))
        before = self.model.recommend(self.seed)
        self.model.frame['popularity'] = 999
        after = self.model.recommend(self.seed)
        self.assertEqual(before, after)

    def fixture_model(self, rows):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / 'dataset.csv'
        pd.DataFrame(rows).to_csv(path, index=False)
        return ContentRecommender(path)

    def test_imputes_missing_features_and_aggregates_genres(self):
        rows = []
        for i in range(3):
            rows.append(dict(track_id=str(i), track_name=f'Song {i}', artists='Artist',
                             track_genre='pop', **{key: i / 2 for key in FEATURES}))
        rows[1]['energy'] = np.nan
        rows.append({**rows[0], 'track_genre':'rock'})
        m = self.fixture_model(rows)
        self.assertEqual(m.stats['imputed_values'], 1)
        self.assertEqual(m.track(0)['genres'], ['pop', 'rock'])
        self.assertEqual(m.raw[1, list(FEATURES).index('energy')], .5)
        self.assertTrue(np.isfinite(m.vectors).all())

    def test_null_vector_rejected(self):
        rows = [dict(track_id=str(i), track_name=f'Song {i}', artists='A', track_genre='pop',
                     **{key: i for key in FEATURES}) for i in range(3)]
        m = self.fixture_model(rows)
        with self.assertRaisesRegex(ValueError, 'vector nulo'):
            m.recommend('1')
        self.assertEqual([item['id'] for item in m.recommend('0')['recommendations']], ['2'])


if __name__ == '__main__':
    unittest.main()

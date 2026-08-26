"""transformer_lab 的关键性质测试。"""

import unittest

import numpy as np

from transformer_lab import (
    causal_mask,
    merge_heads,
    padding_mask,
    scaled_dot_product_attention,
    sinusoidal_position_encoding,
    softmax,
    split_heads,
)


class SoftmaxTests(unittest.TestCase):
    def test_large_logits_are_finite_and_sum_to_one(self) -> None:
        result = softmax(np.array([[1000.0, 1001.0, 1002.0]]))
        self.assertTrue(np.isfinite(result).all())
        np.testing.assert_allclose(result.sum(axis=-1), np.ones(1))


class PositionEncodingTests(unittest.TestCase):
    def test_position_zero_starts_with_sin_zero_cos_one(self) -> None:
        encoding = sinusoidal_position_encoding(seq_len=3, d_model=8)
        np.testing.assert_allclose(encoding[0, 0::2], np.zeros(4))
        np.testing.assert_allclose(encoding[0, 1::2], np.ones(4))

    def test_each_sin_cos_pair_uses_the_same_frequency(self) -> None:
        encoding = sinusoidal_position_encoding(seq_len=3, d_model=8)
        pair_energy = encoding[:, 0::2] ** 2 + encoding[:, 1::2] ** 2
        np.testing.assert_allclose(pair_energy, np.ones_like(pair_energy))

    def test_invalid_dimensions_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            sinusoidal_position_encoding(seq_len=3, d_model=7)


class AttentionTests(unittest.TestCase):
    def test_hand_calculated_attention(self) -> None:
        query = np.array([[1.0, 0.0]])
        key = np.array([[1.0, 0.0], [0.0, 1.0]])
        value = np.array([[10.0, 0.0], [0.0, 20.0]])
        output, weights = scaled_dot_product_attention(query, key, value)

        expected_weights = softmax(np.array([[1 / np.sqrt(2), 0.0]]))
        np.testing.assert_allclose(weights, expected_weights)
        np.testing.assert_allclose(output, expected_weights @ value)

    def test_causal_mask_hides_future_positions(self) -> None:
        qkv = np.ones((1, 1, 4, 2))
        _, weights = scaled_dot_product_attention(qkv, qkv, qkv, causal_mask(4))
        np.testing.assert_allclose(np.triu(weights, k=1), np.zeros_like(weights))
        np.testing.assert_allclose(weights.sum(axis=-1), np.ones((1, 1, 4)))

    def test_padding_mask_hides_padding_keys(self) -> None:
        qkv = np.ones((2, 1, 4, 2))
        allowed = padding_mask(np.array([4, 2]), seq_len=4)
        _, weights = scaled_dot_product_attention(qkv, qkv, qkv, allowed)
        np.testing.assert_allclose(weights[1, :, :, 2:], 0.0)


class ShapeTests(unittest.TestCase):
    def test_split_then_merge_recovers_input(self) -> None:
        x = np.arange(2 * 6 * 8, dtype=float).reshape(2, 6, 8)
        heads = split_heads(x, n_heads=2)
        self.assertEqual(heads.shape, (2, 2, 6, 4))
        np.testing.assert_array_equal(merge_heads(heads), x)

    def test_non_divisible_head_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            split_heads(np.zeros((2, 3, 7)), n_heads=2)


if __name__ == "__main__":
    unittest.main()

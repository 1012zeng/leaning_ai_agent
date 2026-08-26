"""可逐步运行的 Transformer NumPy 实验。

环境:
    Python 3.11+
    numpy >= 1.24

运行:
    python transformer_lab.py --list
    python transformer_lab.py attention
    python transformer_lab.py mask
    python transformer_lab.py multihead
    python transformer_lab.py block
    python transformer_lab.py generation
    python transformer_lab.py --self-check

本文件只演示前向计算，不训练模型。实验中的权重是人为设置或固定随机
初始化，因此输出用于理解计算过程，不代表模型已经学会语言。
"""

from __future__ import annotations

import argparse
from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]


def softmax(x: Array, axis: int = -1) -> Array:
    """数值稳定的 softmax。"""
    shifted = x - np.max(x, axis=axis, keepdims=True)
    exp_values = np.exp(shifted)
    return exp_values / np.sum(exp_values, axis=axis, keepdims=True)


def sinusoidal_position_encoding(seq_len: int, d_model: int) -> Array:
    """生成论文中的正弦位置编码，形状为 (seq_len, d_model)。"""
    if seq_len <= 0:
        raise ValueError("seq_len 必须大于 0")
    if d_model <= 0 or d_model % 2 != 0:
        raise ValueError("为便于成对生成 sin/cos，d_model 必须是正偶数")

    positions = np.arange(seq_len, dtype=np.float64)[:, None]
    frequencies = np.exp(
        -np.log(10000.0) * np.arange(0, d_model, 2, dtype=np.float64) / d_model
    )
    angles = positions * frequencies[None, :]

    encoding = np.zeros((seq_len, d_model), dtype=np.float64)
    encoding[:, 0::2] = np.sin(angles)
    encoding[:, 1::2] = np.cos(angles)
    return encoding


def causal_mask(seq_len: int) -> NDArray[np.bool_]:
    """返回 (1, 1, T, T) 的布尔掩码；True 表示允许关注。"""
    return np.tril(np.ones((seq_len, seq_len), dtype=bool))[None, None, :, :]


def padding_mask(valid_lengths: NDArray[np.int64], seq_len: int) -> NDArray[np.bool_]:
    """返回 (B, 1, 1, T) 的 key padding mask。"""
    positions = np.arange(seq_len)[None, :]
    return (positions < valid_lengths[:, None])[:, None, None, :]


def scaled_dot_product_attention(
    query: Array,
    key: Array,
    value: Array,
    allowed_mask: NDArray[np.bool_] | None = None,
) -> tuple[Array, Array]:
    """计算可批量广播的缩放点积注意力。

    query: (..., query_len, d_head)
    key:   (..., key_len, d_head)
    value: (..., key_len, d_value)
    allowed_mask: 可广播到 (..., query_len, key_len)，True 表示允许关注。
    """
    if query.shape[-1] != key.shape[-1]:
        raise ValueError("query 和 key 的最后一维必须相同")
    if key.shape[-2] != value.shape[-2]:
        raise ValueError("key 和 value 的序列长度必须相同")

    d_head = query.shape[-1]
    scores = query @ np.swapaxes(key, -1, -2) / np.sqrt(d_head)
    if allowed_mask is not None:
        scores = np.where(allowed_mask, scores, -1e9)

    weights = softmax(scores, axis=-1)
    output = weights @ value
    return output, weights


def split_heads(x: Array, n_heads: int) -> Array:
    """(B, T, D) -> (B, H, T, D/H)。"""
    batch_size, seq_len, d_model = x.shape
    if d_model % n_heads != 0:
        raise ValueError("d_model 必须能被 n_heads 整除")
    d_head = d_model // n_heads
    return x.reshape(batch_size, seq_len, n_heads, d_head).transpose(0, 2, 1, 3)


def merge_heads(x: Array) -> Array:
    """(B, H, T, D_head) -> (B, T, H*D_head)。"""
    batch_size, n_heads, seq_len, d_head = x.shape
    return x.transpose(0, 2, 1, 3).reshape(batch_size, seq_len, n_heads * d_head)


def layer_norm(x: Array, eps: float = 1e-5) -> Array:
    """对每个 token 的特征维做 LayerNorm，不含可学习 gamma/beta。"""
    mean = x.mean(axis=-1, keepdims=True)
    variance = x.var(axis=-1, keepdims=True)
    return (x - mean) / np.sqrt(variance + eps)


def multi_head_attention(
    x: Array,
    n_heads: int,
    weights: tuple[Array, Array, Array, Array],
    allowed_mask: NDArray[np.bool_] | None = None,
) -> tuple[Array, Array]:
    """最小多头自注意力前向计算。"""
    w_query, w_key, w_value, w_output = weights
    query = split_heads(x @ w_query, n_heads)
    key = split_heads(x @ w_key, n_heads)
    value = split_heads(x @ w_value, n_heads)
    attended, attention_weights = scaled_dot_product_attention(
        query, key, value, allowed_mask
    )
    return merge_heads(attended) @ w_output, attention_weights


def _identity_attention_weights(d_model: int) -> tuple[Array, Array, Array, Array]:
    identity = np.eye(d_model, dtype=np.float64)
    return identity, identity, identity, identity


def lab_attention() -> None:
    """实验 1：手算级 Q/K/V 与上下文聚合。"""
    tokens = ["写", "代码", "查", "文档"]
    query = np.array([[1.0, 0.0]], dtype=np.float64)
    key = np.array(
        [[0.2, 0.8], [0.9, 0.1], [0.1, 0.9], [0.8, 0.2]], dtype=np.float64
    )
    value = np.array(
        [[1.0, 0.0], [0.0, 2.0], [3.0, 0.0], [0.0, 4.0]], dtype=np.float64
    )

    output, weights = scaled_dot_product_attention(query, key, value)
    print("实验 1：'写' 的查询与 4 个 token 的匹配")
    for token, weight in zip(tokens, weights[0]):
        print(f"  {token:<4} attention={weight:.3f}")
    print(f"加权后的上下文向量: {np.round(output[0], 3)}")
    print("检查: 权重和 =", round(float(weights.sum()), 6))


def lab_mask() -> None:
    """实验 2：同时观察因果 mask 与 padding mask。"""
    batch_size, seq_len, d_model = 2, 5, 4
    x = np.arange(batch_size * seq_len * d_model, dtype=np.float64).reshape(
        batch_size, seq_len, d_model
    )
    qkv = split_heads(x, n_heads=2)
    valid_lengths = np.array([5, 3], dtype=np.int64)
    allowed = causal_mask(seq_len) & padding_mask(valid_lengths, seq_len)
    _, weights = scaled_dot_product_attention(qkv, qkv, qkv, allowed)

    print("实验 2：样本 2、头 1 的注意力矩阵")
    print("True=可见的组合 mask:")
    print(allowed[1, 0].astype(int))
    print("softmax 后的注意力（被遮位置必须为 0）:")
    print(np.round(weights[1, 0], 3))


def lab_multihead() -> None:
    """实验 3：追踪真实 batch 下的多头形状。"""
    rng = np.random.default_rng(7)
    x = rng.normal(size=(2, 6, 8))
    heads = split_heads(x, n_heads=2)
    merged = merge_heads(heads)

    print("实验 3：多头不是复制，而是把特征维切成多组")
    print("输入 X:       ", x.shape, "= (B, T, D)")
    print("切头后:       ", heads.shape, "= (B, H, T, D_head)")
    print("合并后:       ", merged.shape)
    print("往返是否无损: ", bool(np.allclose(x, merged)))


def lab_block() -> None:
    """实验 4：运行一个 Pre-LN decoder block 的前向过程。"""
    rng = np.random.default_rng(42)
    batch_size, seq_len, d_model, n_heads, d_ff = 2, 6, 8, 2, 16
    x = rng.normal(size=(batch_size, seq_len, d_model))
    attention_weights = tuple(
        rng.normal(scale=0.2, size=(d_model, d_model)) for _ in range(4)
    )
    w1 = rng.normal(scale=0.2, size=(d_model, d_ff))
    w2 = rng.normal(scale=0.2, size=(d_ff, d_model))

    normalized = layer_norm(x)
    attended, weights = multi_head_attention(
        normalized, n_heads, attention_weights, causal_mask(seq_len)
    )
    after_attention = x + attended
    hidden = np.maximum(0.0, layer_norm(after_attention) @ w1)
    output = after_attention + hidden @ w2

    print("实验 4：Pre-LN decoder block")
    print("X                    ", x.shape)
    print("MHA(LN(X))           ", attended.shape)
    print("X + MHA(LN(X))       ", after_attention.shape)
    print("FFN(LN(...))         ", (hidden @ w2).shape)
    print("block output         ", output.shape)
    print("attention weights    ", weights.shape, "= (B, H, T, T)")
    print("未来位置最大权重      ", float(np.max(np.triu(weights, k=1))))


def lab_generation() -> None:
    """实验 5：把 logits 转为概率并比较 temperature。"""
    vocabulary = np.array(["测试", "模型", "代码", "结果"])
    logits = np.array([1.2, 0.3, 2.1, -0.5], dtype=np.float64)

    print("实验 5：同一组 logits 在不同 temperature 下的分布")
    for temperature in (0.5, 1.0, 2.0):
        probabilities = softmax(logits / temperature)
        shown = ", ".join(
            f"{token}={probability:.3f}"
            for token, probability in zip(vocabulary, probabilities)
        )
        print(f"T={temperature:<3}: {shown}")
    print("贪心选择:", vocabulary[int(np.argmax(logits))])


def run_self_checks() -> None:
    """无需测试框架即可运行的关键性质检查。"""
    probabilities = softmax(np.array([[1000.0, 1001.0]], dtype=np.float64))
    assert np.isfinite(probabilities).all()
    assert np.allclose(probabilities.sum(axis=-1), 1.0)

    encoding = sinusoidal_position_encoding(seq_len=4, d_model=8)
    assert encoding.shape == (4, 8)
    assert np.allclose(encoding[0, 0::2], 0.0)
    assert np.allclose(encoding[0, 1::2], 1.0)

    x = np.arange(2 * 5 * 8, dtype=np.float64).reshape(2, 5, 8)
    assert np.array_equal(merge_heads(split_heads(x, 2)), x)

    qkv = split_heads(x, 2)
    _, weights = scaled_dot_product_attention(qkv, qkv, qkv, causal_mask(5))
    assert np.allclose(np.triu(weights, k=1), 0.0)
    assert np.allclose(weights.sum(axis=-1), 1.0)
    print("全部自检通过：softmax、位置编码、多头形状、因果 mask。")


LABS: dict[str, tuple[str, Callable[[], None]]] = {
    "attention": ("Q/K/V 与缩放点积注意力", lab_attention),
    "mask": ("因果 mask 与 padding mask", lab_mask),
    "multihead": ("多头拆分、转置与合并", lab_multihead),
    "block": ("完整 Pre-LN decoder block", lab_block),
    "generation": ("logits、softmax 与 temperature", lab_generation),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lab", nargs="?", choices=[*LABS, "all"])
    parser.add_argument("--list", action="store_true", help="列出所有实验")
    parser.add_argument("--self-check", action="store_true", help="运行关键性质检查")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list:
        for name, (description, _) in LABS.items():
            print(f"{name:<10} {description}")
        return
    if args.self_check:
        run_self_checks()
        return
    if args.lab is None:
        raise SystemExit("请指定实验名；运行 --list 查看，或使用 all。")

    selected = LABS.items() if args.lab == "all" else [(args.lab, LABS[args.lab])]
    for index, (_, (description, runner)) in enumerate(selected):
        if index:
            print("\n" + "-" * 68 + "\n")
        print(f"[{description}]")
        runner()


if __name__ == "__main__":
    main()

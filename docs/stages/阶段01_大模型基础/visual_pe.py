import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def get_positional_encoding(max_seq_len, embed_dim):
    """与 embedding.py 等价的向量化实现"""
    pos = np.arange(max_seq_len)[:, None]            # (max_seq_len, 1) 位置列
    i = np.arange(embed_dim)[None, :]                # (1, embed_dim)   维度行
    angle = pos / np.power(10000, 2 * i / embed_dim) # 广播成 (max_seq_len, embed_dim)
    pe = np.zeros_like(angle)
    pe[:, 0::2] = np.sin(angle[:, 0::2])  # 偶数维 -> sin
    pe[:, 1::2] = np.cos(angle[:, 1::2])  # 奇数维 -> cos
    return pe


max_seq_len, embed_dim = 100, 16
pe = get_positional_encoding(max_seq_len, embed_dim)

fig = plt.figure(figsize=(18, 10))

# 图1: 热力图 —— 整体看: 横轴是16个维度, 纵轴是100个位置
ax1 = fig.add_subplot(2, 2, 1)
sns.heatmap(pe, cmap='RdBu_r', ax=ax1, cbar_kws={'label': 'value'})
ax1.set_title('Heatmap: row = position, col = dimension', fontsize=12)
ax1.set_xlabel('dimension index (i)')
ax1.set_ylabel('position (pos)')

# 图2: 波形图 —— 每个维度是一条频率不同的 sin/cos 波
ax2 = fig.add_subplot(2, 2, 2)
for d in range(4):
    kind = 'sin' if d % 2 == 0 else 'cos'
    ax2.plot(pe[:, d], label=f'dim={d} ({kind})')
ax2.set_title('Each dimension = a sine/cosine wave over position', fontsize=12)
ax2.set_xlabel('position (pos)')
ax2.set_ylabel('value')
ax2.legend()
ax2.grid(alpha=0.3)

# 图3: 取几个位置, 看它们的 16 维编码向量长什么样
ax3 = fig.add_subplot(2, 2, 3)
for p in [0, 1, 2, 5, 10, 50, 99]:
    ax3.plot(pe[p], 'o-', label=f'pos={p}')
ax3.set_title('Encoding vector of several positions', fontsize=12)
ax3.set_xlabel('dimension index (i)')
ax3.set_ylabel('value')
ax3.legend(ncol=2, fontsize=9)
ax3.grid(alpha=0.3)

# 图4: 所有位置两两的余弦相似度 —— 理解相对位置/周期性
ax4 = fig.add_subplot(2, 2, 4)
pe_norm = pe / (np.linalg.norm(pe, axis=1, keepdims=True) + 1e-8)
sim = pe_norm @ pe_norm.T
sns.heatmap(sim, cmap='coolwarm', ax=ax4, vmin=-1, vmax=1,
            cbar_kws={'label': 'cosine sim'})
ax4.set_title('Cosine similarity between positions', fontsize=12)
ax4.set_xlabel('position (pos)')
ax4.set_ylabel('position (pos)')

plt.tight_layout()
plt.savefig('positional_encoding_viz.png', dpi=120)
print('saved: positional_encoding_viz.png')

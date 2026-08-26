import numpy as np

# ========== 第 1 步: 定义词表 vocab ==========
# 假设一个只有 8 个词的小词表。id=0 固定留给 padding(补位符)
vocab = ['<pad>', '你', '吃', '饭', '没', '吗', '好', '<unk>']
vocab_id = {w: i for i, w in enumerate(vocab)}
print('词表:', vocab)
print('词 -> id 映射:', vocab_id)

# ========== 第 2 步: 分词 + 查表转 id ==========
sentence = '你吃饭没'
tokens = list(sentence)                    # 简化: 按字切分 -> ['你','吃','饭','没']
ids = [vocab_id[t] for t in tokens]        # -> [1, 2, 3, 4]
print('\n句子:",', sentence, ' -> 按字分词:', tokens, ' -> id 序列:', ids)

# ========== 第 3 步: 词嵌入矩阵(Embedding Layer 的权重) ==========
# 随机初始化, 形状 (词表大小 8, 嵌入维度 4)
np.random.seed(42)
embed_dim = 4
embedding_matrix = np.random.randn(len(vocab), embed_dim)
print('\n词嵌入矩阵 shape =', embedding_matrix.shape, '(每行是一个词的向量)')
print(embedding_matrix)

# ========== 第 4 步: 查表取行 ==========
# 本质就是按 id 从矩阵里"取行", 等价于 PyTorch 里的 nn.Embedding 的前向过程
word_vector_matrix = embedding_matrix[ids]   # shape (4, 4)
print('\n"你吃饭没" 的词向量矩阵 shape =', word_vector_matrix.shape)
print('第0行=词"你"的向量:', word_vector_matrix[0])
print('第1行=词"吃"的向量:', word_vector_matrix[1])

# ========== 第 5 步: 叠加位置编码 ==========
def get_positional_encoding(max_seq_len, embed_dim):
    pos = np.arange(max_seq_len)[:, None]
    i = np.arange(embed_dim)[None, :]
    angle = pos / np.power(10000, 2 * i / embed_dim)
    pe = np.zeros_like(angle)
    pe[:, 0::2] = np.sin(angle[:, 0::2])
    pe[:, 1::2] = np.cos(angle[:, 1::2])
    return pe

pe = get_positional_encoding(len(ids), embed_dim)
print('\n位置编码矩阵(4x4):')
print(pe)

final_input = word_vector_matrix + pe
print('\n最终输入 = 词向量 + 位置编码:')
print(final_input)

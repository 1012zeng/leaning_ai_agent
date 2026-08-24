"""
=============================================================================
从零手写 Transformer —— 纯 NumPy 教学版 (前向传播, 无训练)
=============================================================================
对应论文: Attention Is All You Need (Vaswani et al., 2017)

本文件的目标: 让你"看到"Transformer 的每一个环节。
运行:  python transformer_demo.py
它会把一句中文句子从"字 -> 向量 -> 多头注意力 -> 编码器 -> 解码器 -> 预测"
的完整数据流打印出来, 每一步的形状和关键数值都可见。

为了可读性, 本教学版做了 3 个简化(真实模型都有 batch 维, 这里省掉):
  1. 一次只处理 1 个样本, 所以没有 batch 维, 张量形状是 (seq_len, d_model)
  2. 用字符级词表代替 BPE 分词器(概念完全一样, 只是更直观)
  3. 权重随机初始化, 不做训练(训练是另一个话题, 见文件末尾说明)
=============================================================================
"""

import numpy as np

np.random.seed(42)  # 固定随机种子, 保证每次运行结果一致, 方便对照

# =============================================================================
# 0. 基础工具函数
# =============================================================================

def softmax(x, axis=-1):
    """稳定的 softmax: 先减去最大值再指数化, 防止 exp 溢出"""
    x = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(x)
    return e / np.sum(e, axis=axis, keepdims=True)


def scaled_dot_product_attention(Q, K, V, mask=None):
    """
    缩放点积注意力 —— Transformer 的心脏, 就是这一行公式:
        Attention(Q, K, V) = softmax( Q·K^T / sqrt(d_k) ) · V

    直觉理解(用"搜索"来类比):
      - Q (Query 查询): 当前词想问什么?  比如"你"想知道后面跟的是什么词
      - K (Key 键):     每个词能回答什么? 相当于每个词的"标签"
      - V (Value 值):   每个词真正提供的内容, 相当于词的"答案内容"

      计算 Q·K^T: "你"的查询 与 每个词的标签 做点积 -> 得到 你对每个词的匹配分数
      softmax:   把分数变成概率(注意力权重, 和为1)
      ·V:        按权重把各个词的内容加权求和 -> 得到"你"带着上下文的新向量

    除以 sqrt(d_k) 的原因: d_k 越大, 点积数值越大, 会让 softmax 进入梯度饱和区,
    除以 sqrt(d_k) 把数值拉回合适范围, 保证梯度稳定。
    """
    d_k = Q.shape[-1]
    scores = Q @ K.T / np.sqrt(d_k)        # (seq_q, seq_k) 匹配分数
    if mask is not None:                   # 解码器里禁止"偷看未来"
        scores = np.where(mask, -1e9, scores)  # 被遮住的位置分数设为极小 -> softmax 后≈0
    attn_weights = softmax(scores, axis=-1)    # 每行归一化成概率, 行和为1
    output = attn_weights @ V                  # 按注意力权重加权求和 (seq_q, d_v)
    return output, attn_weights


# =============================================================================
# 1. 层归一化 LayerNorm
# =============================================================================

class LayerNorm:
    """
    对每个 token 的 d_model 维向量做归一化: (x - 均值) / 标准差 * gamma + beta
    作用: 稳定训练(防止数值爆炸/消失), 加速收敛。
    注意和 BatchNorm 的区别: BN 跨样本归一化, LN 对单个样本内部归一化。
    LN 不依赖 batch 大小, 所以更适合序列模型(句子长度可变)。
    """
    def __init__(self, d_model, eps=1e-5):
        self.gamma = np.ones(d_model)      # 可学习缩放 (初始1)
        self.beta = np.zeros(d_model)      # 可学习偏移 (初始0)
        self.eps = eps

    def __call__(self, x):
        return self.forward(x)

    def forward(self, x):
        # x: (seq, d_model), 对最后一维做归一化
        mean = x.mean(axis=-1, keepdims=True)
        var = x.var(axis=-1, keepdims=True)
        return self.gamma * (x - mean) / np.sqrt(var + self.eps) + self.beta


# =============================================================================
# 2. 多头自注意力 Multi-Head Attention (最关键的部分)
# =============================================================================

class MultiHeadAttention:
    """
    为什么需要"多头"?
      单头注意力: 每个词只能关注一个"关系模式"。
      多头注意力: 把 d_model 维向量切成 n_heads 块, 每块(每头)独立学一种关注模式,
                 比如 头1 学"语法关系", 头2 学"指代关系", 头3 学"位置远近"...
                 最后拼接起来, 让每个词同时获得多方面的上下文信息。

    流程:
      X (seq, d_model)
        |--Wq-- Q (seq, d_model)  每个头取其中一段: Q 头h 是 (seq, d_k)
        |--Wk-- K (seq, d_model)  同理
        |--Wv-- V (seq, d_model)  同理
        -> 每个头各自做 scaled_dot_product_attention
        -> 把头的结果拼接 (seq, d_model)
        -> 过 Wo 线性变换输出
    """
    def __init__(self, d_model, n_heads):
        assert d_model % n_heads == 0, "d_model 必须能被 n_heads 整除"
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads   # 每个头的维度 (切出来的小块宽度)
        # 4 个权重矩阵: 3 个用于投影 Q/K/V, 1 个用于输出
        self.Wq = np.random.randn(d_model, d_model) * 0.1
        self.Wk = np.random.randn(d_model, d_model) * 0.1
        self.Wv = np.random.randn(d_model, d_model) * 0.1
        self.Wo = np.random.randn(d_model, d_model) * 0.1

    def _split_heads(self, x):
        """把 (seq, d_model) 切分成 n_heads 个 (seq, d_k), 返回 (n_heads, seq, d_k)"""
        seq = x.shape[0]
        x = x.reshape(seq, self.n_heads, self.d_k)  # 按列切块
        return x.transpose(1, 0, 2)                 # (n_heads, seq, d_k)

    def _merge_heads(self, x):
        """把 (n_heads, seq, d_k) 拼回 (seq, d_model), 是 _split_heads 的逆操作"""
        n_heads, seq, d_k = x.shape
        x = x.transpose(1, 0, 2)                    # (seq, n_heads, d_k)
        return x.reshape(seq, n_heads * d_k)        # (seq, d_model)

    def forward(self, X, mask=None, K_source=None, V_source=None):
        """
        自注意力/交叉注意力通用入口。
        X: (seq_q, d_model) 查询的来源 (自注意力时也是键值的来源)
        mask: (seq_q, seq_k) 布尔遮罩, 通常只有解码器自注意力用
        K_source, V_source: 交叉注意力时键值来自另一个序列(编码器输出);
                            自注意力时留 None, 即键值也来自 X
        """
        # 1) 三个线性投影。交叉注意力: Q 投影自解码器, K/V 投影自编码器输出
        Q = X @ self.Wq
        K = (X if K_source is None else K_source) @ self.Wk
        V = (X if V_source is None else V_source) @ self.Wv
        # 2) 切多头
        Q = self._split_heads(Q)   # (n_heads, seq, d_k)
        K = self._split_heads(K)
        V = self._split_heads(V)
        # 3) 每个头独立做缩放点积注意力
        outputs, attn_weights = [], []
        for h in range(self.n_heads):
            out, attn = scaled_dot_product_attention(Q[h], K[h], V[h], mask)
            outputs.append(out)      # 每头输出 (seq, d_k)
            attn_weights.append(attn)  # 每头的注意力权重 (seq, seq)
        # 4) 拼接所有头
        concat = self._merge_heads(np.stack(outputs))  # (seq, d_model)
        # 5) 输出投影
        return concat @ self.Wo, np.stack(attn_weights)  # 返回注意力权重便于观察


# =============================================================================
# 3. 前馈网络 Feed-Forward Network (FFN)
# =============================================================================

class FeedForward:
    """
    每个 token 独立通过的两层 MLP:  d_model -> d_ff -> d_model (先扩宽再缩回)
    作用: 注意力负责"词与词之间"的信息交换, FFN 负责对每个词做"非线性变换/加工",
          相当于在注意力之后给每个位置补充更复杂的特征表示。
    ReLU 提供非线性, 让模型能拟合复杂函数。
    """
    def __init__(self, d_model, d_ff):
        self.W1 = np.random.randn(d_model, d_ff) * 0.1
        self.b1 = np.zeros(d_ff)
        self.W2 = np.random.randn(d_ff, d_model) * 0.1
        self.b2 = np.zeros(d_model)

    def forward(self, x):
        # x: (seq, d_model)
        hidden = np.maximum(0, x @ self.W1 + self.b1)  # ReLU
        return hidden @ self.W2 + self.b2              # (seq, d_model)


# =============================================================================
# 4. 编码器层 & 编码器
# =============================================================================

class EncoderLayer:
    """
    一层编码器 = 两个子层, 每个子层外面都套了"残差连接 + 层归一化":
        x -> [多头自注意力] -> 残差加回 x -> LayerNorm -> x'
        x'-> [前馈网络]     -> 残差加回 x' -> LayerNorm -> x''

    残差连接(residual)的意义: 让梯度有一条"直通高速路"从深层流回浅层,
        避免深层网络梯度消失。所以叫"残差", 即学习"增量/变化"而不是重头学。
    """
    def __init__(self, d_model, n_heads, d_ff):
        self.self_attn = MultiHeadAttention(d_model, n_heads)
        self.ffn = FeedForward(d_model, d_ff)
        self.norm1 = LayerNorm(d_model)
        self.norm2 = LayerNorm(d_model)

    def forward(self, x, mask=None):
        # 子层1: 自注意力 + 残差 + LN
        attn_out, _ = self.self_attn.forward(x, mask)   # 编码器里 mask=None(能看到全部词)
        x = self.norm1(x + attn_out)                    # 残差: x + attn_out, 再 LN
        # 子层2: 前馈 + 残差 + LN
        ffn_out = self.ffn.forward(x)
        x = self.norm2(x + ffn_out)
        return x


class Encoder:
    """
    编码器整体 = 输入嵌入 + 位置编码 + N 层 EncoderLayer
    职责: 把源句子"你 好 世 界"变成一组上下文增强的向量(每词一向量, 已融合整句信息)
    """
    def __init__(self, vocab_size, d_model, n_heads, d_ff, n_layers):
        self.embedding = np.random.randn(vocab_size, d_model) * 0.1  # 词嵌入表 (上一课的内容!)
        self.layers = [EncoderLayer(d_model, n_heads, d_ff) for _ in range(n_layers)]

    def forward(self, token_ids, positional_encoding):
        # 1) 查词嵌入表: id -> 向量
        x = self.embedding[token_ids]              # (seq, d_model)
        # 2) 叠加位置编码 (形状相同, 直接相加)
        x = x + positional_encoding[:len(token_ids)]
        # 3) 依次过 N 层编码器层
        for layer in self.layers:
            x = layer.forward(x)
        return x                                   # (seq, d_model) 上下文向量


# =============================================================================
# 5. 解码器层 & 解码器
# =============================================================================

class DecoderLayer:
    """
    一层解码器 = 3 个子层 (比编码器多一个"交叉注意力"):
      1) 掩码自注意力: 看"已生成的词", 但不能偷看未来的词 (因果掩码)
      2) 交叉注意力:   以"已生成的词"做 Q, 以"编码器输出"做 K 和 V
                       —— 这是解码器读取编码器信息的通道!
      3) 前馈网络
      每个子层同样是"残差 + LN"的结构。

    直觉: 翻译任务里, 解码器边看"自己已翻的词"(掩码自注意力),
          边回看"原文句子"(交叉注意力), 一个字一个字地生成译文。
    """
    def __init__(self, d_model, n_heads, d_ff):
        self.self_attn = MultiHeadAttention(d_model, n_heads)    # 掩码自注意力
        self.cross_attn = MultiHeadAttention(d_model, n_heads)  # 交叉注意力(encoder-decoder)
        self.ffn = FeedForward(d_model, d_ff)
        self.norm1 = LayerNorm(d_model)
        self.norm2 = LayerNorm(d_model)
        self.norm3 = LayerNorm(d_model)

    def forward(self, x, encoder_output, causal_mask):
        # 子层1: 掩码自注意力 (mask 禁止看未来)
        attn_out, _ = self.self_attn.forward(x, causal_mask)
        x = self.norm1(x + attn_out)
        # 子层2: 交叉注意力 —— Q 来自解码器(x), K/V 来自编码器输出(encoder_output)
        #        这就是解码器"读取原文信息"的通道
        cross_out, _ = self.cross_attn.forward(x, K_source=encoder_output,
                                               V_source=encoder_output)
        x = self.norm2(x + cross_out)
        # 子层3: 前馈
        ffn_out = self.ffn.forward(x)
        x = self.norm3(x + ffn_out)
        return x


class Decoder:
    """
    解码器整体 = 输入嵌入 + 位置编码 + N 层 DecoderLayer + 输出投影
    职责: 逐字生成目标句子。输入"已生成的部分", 输出"下一个字的预测概率分布"
    """
    def __init__(self, vocab_size, d_model, n_heads, d_ff, n_layers):
        self.embedding = np.random.randn(vocab_size, d_model) * 0.1
        self.layers = [DecoderLayer(d_model, n_heads, d_ff) for _ in range(n_layers)]
        self.output_proj = np.random.randn(d_model, vocab_size) * 0.1  # 把 d_model 映射回词表

    def forward(self, token_ids, encoder_output, positional_encoding, causal_mask):
        x = self.embedding[token_ids] + positional_encoding[:len(token_ids)]
        for layer in self.layers:
            x = layer.forward(x, encoder_output, causal_mask)
        logits = x @ self.output_proj          # (seq, vocab_size) 每个位置的打分
        return logits


# =============================================================================
# 6. 组装完整 Transformer
# =============================================================================

class Transformer:
    """Encoder-Decoder 完整模型"""
    def __init__(self, vocab_size, d_model=16, n_heads=4, d_ff=32, n_layers=2):
        self.d_model = d_model
        self.encoder = Encoder(vocab_size, d_model, n_heads, d_ff, n_layers)
        self.decoder = Decoder(vocab_size, d_model, n_heads, d_ff, n_layers)

    def make_positional_encoding(self, max_len):
        """公式位置编码 (和 embedding.py 完全一致), 返回 (max_len, d_model)"""
        pos = np.arange(max_len)[:, None]
        i = np.arange(self.d_model)[None, :]
        angle = pos / np.power(10000, 2 * i / self.d_model)
        pe = np.zeros_like(angle)
        pe[:, 0::2] = np.sin(angle[:, 0::2])
        pe[:, 1::2] = np.cos(angle[:, 1::2])
        return pe

    def make_causal_mask(self, seq_len):
        """因果掩码: 上三角为 True(禁止), 保证第 i 个位置只能看 0..i (过去和当下)"""
        mask = np.triu(np.ones((seq_len, seq_len)), k=1).astype(bool)
        return mask

    def forward(self, src_ids, tgt_ids):
        pe = self.make_positional_encoding(64)
        # 编码器: 源句子 -> 上下文向量
        encoder_output = self.encoder.forward(src_ids, pe)  # (src_seq, d_model)
        # 解码器: 目标前缀 + 编码器输出 -> logits
        causal_mask = self.make_causal_mask(len(tgt_ids))
        logits = self.decoder.forward(tgt_ids, encoder_output, pe, causal_mask)
        return logits, encoder_output


# =============================================================================
# 7. 主演示: 输入一句话, 走一遍完整流程
# =============================================================================

if __name__ == '__main__':
    # ---------- 7.1 词表 (教学用字符级; 真实模型用 BPE, 见上一课的 tiktoken) ----------
    vocab = ['<pad>', '<sos>', '<eos>', '你', '吃', '饭', '没', '好', '世', '界', '？', '吗']
    vocab_id = {w: i for i, w in enumerate(vocab)}
    print('词表:', vocab, '\n词表大小:', len(vocab))

    # ---------- 7.2 准备输入 ----------
    # 任务设定: 源句子(编码器输入)="你好世界", 目标句子(解码器要生成)="世界你好"
    src_text, tgt_text = '你好世界', '世界你好'
    src_ids = np.array([vocab_id[c] for c in src_text])          # [你 好 世 界]
    tgt_ids = np.array([vocab_id['<sos>']] + [vocab_id[c] for c in tgt_text])  # 解码器要加 <sos> 开头
    print(f'\n源句子: "{src_text}" -> ids {src_ids}')
    print(f'目标句子: "{tgt_text}" -> 解码器输入 ids {tgt_ids} (<sos> 开头)')

    # ---------- 7.3 搭建并前向 ----------
    model = Transformer(vocab_size=len(vocab), d_model=16, n_heads=4, d_ff=32, n_layers=2)
    logits, enc_out = model.forward(src_ids, tgt_ids)

    # ---------- 7.4 检查输出形状, 验证每一步 ----------
    print('\n===== 形状检查 (所有环节的形状应如右所示) =====')
    print(f'编码器输出 enc_out: {enc_out.shape}   <- 期待 (4, 16)  [4个源词, 16维向量]')
    print(f'解码器输出 logits : {logits.shape}   <- 期待 (5, 12)  [5个目标位置(<sos>+4词), 12个候选词打分]')

    # ---------- 7.5 看最终预测 ----------
    print('\n===== 解码器每个位置的预测概率 (top-3) =====')
    for i in range(len(tgt_ids)):
        probs = softmax(logits[i])
        top3 = np.argsort(probs)[::-1][:3]          # 概率最大的3个词
        items = ' '.join(f'{vocab[j]}:{probs[j]:.2f}' for j in top3)
        print(f'位置{i} (当前词="{vocab[tgt_ids[i]]}"): 预测下一个 -> {items}')

    # ---------- 7.6 观察注意力权重 (理解"词与词怎么建立联系") ----------
    print('\n===== 编码器第0层 头0 的注意力权重矩阵 (4x4, 行=查询词, 列=被关注词) =====')
    x = model.encoder.embedding[src_ids] + model.make_positional_encoding(64)[:len(src_ids)]
    attn_out, attn = model.encoder.layers[0].self_attn.forward(x)
    a0 = attn[0]  # 第0个头的注意力矩阵
    for r, word in enumerate(src_text):
        line = ' '.join(f'{a0[r, c]:.2f}' for c in range(len(src_text)))
        print(f'"{word}" 关注: [{line}]   (行和为1 = 注意力概率)')

# 线性代数速成（Transformer 预备）

> **目标**：让你在学 Transformer 之前，用 3~5 小时掌握看懂 QKV 和注意力计算所需的全部线性代数。
> **风格**：每个概念都有「人话解释 → 手算例子 → numpy 代码 → 练习题」。练习题答案折叠在每题下方，先自己算，再点开对答案。
> **环境**：Python + numpy（`pip install numpy`）。不会 Python 也没关系，手算就能学；numpy 代码是附赠的实操体验。
> **提示**：文中数学公式用 LaTeX 编写。如果你用的编辑器显示不出公式（比如出现 `$...$` 字样），建议用 Typora、VS Code + Markdown 预览或 GitHub 打开本文档。

---

## 0. 一页总览：线性代数概念 → Transformer 对应关系

学之前先建立全局观，下面这张表就是本篇文章的"地图"，学完每章可以回来对照：

| 线性代数概念 | 在 Transformer 里的用武之地 | 对应章节 |
|---|---|---|
| 向量（Vector） | 一个词 = 一个高维向量（Embedding） | 第 1 章 |
| 点积 / 余弦相似度 | 注意力得分：衡量"两个词有多相关" | 第 1 章 |
| 矩阵（Matrix） | 权重矩阵 $W_Q$、$W_K$、$W_V$；一句话 = 多个词向量拼成的矩阵 | 第 2 章 |
| 矩阵乘法 | 计算 $Q = W_Q \cdot X$（核心中的核心） | 第 3 章 |
| 矩阵乘法（批） | 注意力分数矩阵 $QK^T$、加权求和 $\text{Attention} \cdot V$ | 第 3、7 章 |
| 逐元素运算 / 广播 | numpy 里对矩阵做逐元素操作、softmax 归一化 | 第 4 章 |
| 线性组合 / 线性变换 | "矩阵乘向量 = 对词做语义变换"，为什么叫"线性层" | 第 5 章 |
| 张量（Tensor） | 模型数据形状 $(batch, seq\_len, dim)$ | 第 6 章 |
| softmax（指数+归一化） | 把注意力得分变成"和为 1"的权重 | 第 4、7 章 |
| 特征值 / SVD（进阶） | 本阶段了解即可，不要求 | 第 8 章 |

**一句话总纲**：Transformer 的注意力机制，就是反复做三件事——**矩阵乘法**（算 Q/K/V）、**点积**（算相关性）、**softmax 归一化**（算权重）。把这三种运算练熟，Transformer 的数学部分就通了。

---

## 第 1 章 向量：一个词就是一个向量

### 1.1 什么是向量

- **数量（标量）**：只有一个数，比如"温度 30 度"、"身高 175cm"。
- **向量**：一组有序的数，比如 [30, 175] 可以同时表示"温度 30、身高 175"。

向量就是"多个数打包在一起"，每个数叫一个**分量（元素）**。向量可以有任意长度（分量个数），写成：

$$v = [v_1, v_2, v_3, \dots, v_n]$$

**与 Transformer 的联系**：大模型把每个词表示成一个向量（通常几百~几千维）。比如在一个 3 维空间里：

- "苹果" = [0.9, 0.1, 0.8]
- "香蕉" = [0.8, 0.2, 0.7]
- "跑步" = [0.1, 0.9, 0.1]

如果 3 个维度分别代表 [水果程度, 运动程度, 甜度]，那么"苹果"和"香蕉"的向量很接近，"苹果"和"跑步"的向量差很远——**语义相近的词，向量距离近**。这就是词嵌入（Embedding）的基本思想，也是第 1.4 任务里"把 token 转成向量"那一步。

### 1.2 行向量与列向量

- **行向量**：[1, 2, 3]，横着写（numpy 一维数组就是它）
- **列向量**：竖着写，$\begin{bmatrix} 1 \\ 2 \\ 3 \end{bmatrix}$

Transformer 公式里（如 $Q = W_Q X$）X 通常按列向量处理，但 numpy 里我们直接用一维数组或行向量，靠转置（第 2.5 节）转换，先不用纠结。

### 1.3 numpy 表示向量

```python
import numpy as np

v = np.array([1, 2, 3])        # 一个 3 维向量
print(v.shape)                  # (3,)  —— 一维数组，3 个元素
print(v[0], v[1], v[2])         # 1 2 3  —— 按下标取分量
```

### 1.4 向量的长度（模长 / 范数）

直觉：把向量想成"从原点出发的箭头"，长度就是箭头多长。2 维下就是勾股定理：

$$|v| = \sqrt{v_1^2 + v_2^2 + \dots + v_n^2}$$

**手算例子**：$v = [3, 4]$，长度 $= \sqrt{3^2 + 4^2} = \sqrt{25} = 5$。

```python
v = np.array([3, 4])
print(np.linalg.norm(v))   # 5.0
```

### 1.5 点积（内积）：最重要的运算之一

**定义**：两个长度相同的向量，对应分量相乘再全部加起来。

$$a \cdot b = a_1 b_1 + a_2 b_2 + \dots + a_n b_n$$

**手算例子**：$a = [1, 2, 3]$，$b = [4, 5, 6]$

$$a \cdot b = 1\times4 + 2\times5 + 3\times6 = 4 + 10 + 18 = 32$$

```python
a = np.array([1, 2, 3])
b = np.array([4, 5, 6])
print(np.dot(a, b))   # 32
print(a @ b)          # 32  （@ 是 numpy 的矩阵乘法运算符，一维时等价于点积）
```

**几何意义（重点）**：点积 = 两个向量"方向相似程度 × 各自长度"：

$$a \cdot b = |a| \cdot |b| \cdot \cos\theta$$

其中 $\theta$ 是两个向量的夹角。

- 方向一致（$\theta=0°$）：点积最大（正数）
- 方向垂直（$\theta=90°$）：点积 = 0
- 方向相反（$\theta=180°$）：点积是负数

**与 Transformer 的联系**：注意力得分就是两个向量的点积（或归一化的余弦相似度）——**"这个词和那个词有多相关"**。点积大 → 相关性高 → 注意力权重高。

### 1.6 余弦相似度：只看方向，不看长度

把点积公式两边除以 $|a|\cdot|b|$，得到**余弦相似度**：

$$\cos\theta = \frac{a \cdot b}{|a| \cdot |b|}$$

范围固定是 $[-1, 1]$：1 = 方向完全一致，0 = 无关，-1 = 完全相反。

**手算例子**：$a = [1, 2]$，$b = [2, 4]$（b 是 a 的 2 倍，方向相同）

$$a \cdot b = 1\times2 + 2\times4 = 10,\quad |a| = \sqrt{5},\quad |b| = \sqrt{20} = 2\sqrt{5}$$

$$\cos\theta = \frac{10}{\sqrt{5} \times 2\sqrt{5}} = \frac{10}{10} = 1 \quad \checkmark$$

```python
a = np.array([1, 2])
b = np.array([2, 4])
cos = a @ b / (np.linalg.norm(a) * np.linalg.norm(b))
print(cos)   # 1.0
```

**为什么 Transformer 常用点积而不是余弦相似度**：两者方向意义相同，但点积还保留长度信息，计算更快（少一次除法），并且除以 $\sqrt{d_k}$ 缩放后数值更稳定。理解层面，把"点积大 = 相关"记牢即可。

### 📝 第 1 章练习

**练习 1**：手算 $[2, -1, 3] \cdot [1, 4, -2]$。

<details>
<summary>点开看答案</summary>

$2\times1 + (-1)\times4 + 3\times(-2) = 2 - 4 - 6 = -8$

</details>

**练习 2**：向量 $[3, 4]$ 和 $[1, 0]$ 的夹角余弦值是多少？（提示：先把长度算出来）

<details>
<summary>点开看答案</summary>

$[3,4]$ 长度 $= 5$，$[1,0]$ 长度 $= 1$；点积 $= 3\times1 + 4\times0 = 3$。

$\cos\theta = 3 / (5 \times 1) = 0.6$

</details>

**练习 3**：用 numpy 计算 $[1,2,3]$ 与 $[3,2,1]$ 的余弦相似度（提示：`np.dot` + `np.linalg.norm`）。

<details>
<summary>点开看答案</summary>

```python
import numpy as np
a = np.array([1, 2, 3])
b = np.array([3, 2, 1])
cos = a @ b / (np.linalg.norm(a) * np.linalg.norm(b))
print(cos)   # 0.7142857142857143
```

</details>

**练习 4（思考）**：为什么余弦相似度的范围一定是 $[-1, 1]$，不会超过？

<details>
<summary>点开看答案</summary>

因为 $\cos\theta$ 的取值范围就是 $[-1, 1]$，而余弦相似度正是两个向量的夹角余弦值。

</details>

---

## 第 2 章 矩阵：一堆词向量拼起来

### 2.1 什么是矩阵

矩阵就是把向量"摆成方阵"——按行和列排列的数表：

$$A = \begin{bmatrix} 1 & 2 & 3 \\ 4 & 5 & 6 \end{bmatrix}$$

这是个 **2 行 3 列** 的矩阵，记作 $2 \times 3$。约定：**先写行数，再写列数**。

- $A[0][2]$ 表示第 0 行第 2 列的元素，即 3（从 0 开始数）
- `shape` 就是 (行数, 列数)

**与 Transformer 的联系**：一句话有多个词，把每个词的向量**按行摞起来**，就是一个矩阵！

比如 "我 爱 AI" 三个词各用 2 维向量表示：

$$X = \begin{bmatrix} 1 & 0 \\ 0 & 1 \\ 1 & 1 \end{bmatrix} \quad (3 \times 2)$$

第 0 行是"我"，第 1 行是"爱"，第 2 行是"AI"。这个 $X$ 就是 Transformer 的输入。

### 2.2 numpy 创建与索引

```python
import numpy as np

A = np.array([[1, 2, 3],
              [4, 5, 6]])        # 2 行 3 列
print(A.shape)                    # (2, 3)
print(A[0, 2])                    # 3   —— 第 0 行第 2 列
print(A[1, :])                    # [4 5 6] —— 第 1 行（切片取整行）
print(A[:, 1])                    # [2 5]   —— 第 1 列（切片取整列）
```

### 2.3 特殊矩阵

- **零矩阵**：所有元素都是 0。作用：矩阵加法的"0"，任何矩阵加零矩阵不变。
- **单位矩阵 $I$**：对角线全 1，其余全 0。作用：矩阵乘法的"1"，任何矩阵乘单位矩阵不变（$A \cdot I = A$）。
- **对角矩阵**：只有对角线非零。

$$I_3 = \begin{bmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 1 \end{bmatrix}$$

```python
np.zeros((2, 3))     # 2×3 零矩阵
np.eye(3)            # 3×3 单位矩阵
```

### 2.4 矩阵加法与数乘

- **加法**：对应位置相加（形状必须相同）
- **数乘**：每个元素乘以同一个数

$$\begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix} + \begin{bmatrix} 5 & 6 \\ 7 & 8 \end{bmatrix} = \begin{bmatrix} 6 & 8 \\ 10 & 12 \end{bmatrix}$$

$$2 \times \begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix} = \begin{bmatrix} 2 & 4 \\ 6 & 8 \end{bmatrix}$$

### 2.5 转置：行列互换

转置就是把矩阵翻转：行变列，列变行。记作 $A^T$。

$$\begin{bmatrix} 1 & 2 & 3 \\ 4 & 5 & 6 \end{bmatrix}^T = \begin{bmatrix} 1 & 4 \\ 2 & 5 \\ 3 & 6 \end{bmatrix} \quad (2\times3 \rightarrow 3\times2)$$

**与 Transformer 的联系**：注意力分数矩阵是 $QK^T$——K 要先转置才能和 Q 做矩阵乘法（为什么？第 3 章规则会揭晓）。

```python
A = np.array([[1, 2, 3], [4, 5, 6]])
print(A.T)          # [[1 4] [2 5] [3 6]]
print(A.T.shape)    # (3, 2)
```

### 📝 第 2 章练习

**练习 5**：写出 $A = \begin{bmatrix} 1 & 2 & 3 \\ 4 & 5 & 6 \end{bmatrix}$ 的转置。

<details>
<summary>点开看答案</summary>

$\begin{bmatrix} 1 & 4 \\ 2 & 5 \\ 3 & 6 \end{bmatrix}$（$2\times3 \rightarrow 3\times2$）

</details>

**练习 6**：$I_2 \times \begin{bmatrix} 7 & 8 \\ 9 & 10 \end{bmatrix}$ 等于什么？

<details>
<summary>点开看答案</summary>

还是 $\begin{bmatrix} 7 & 8 \\ 9 & 10 \end{bmatrix}$。单位矩阵乘任何矩阵不变（第 3 章学到乘法规则后可再验证一次）。

</details>

**练习 7**：用 numpy 创建 3×3 的全 1 矩阵，取出第 1 行第 2 列的元素，并输出它的转置的形状。

<details>
<summary>点开看答案</summary>

```python
import numpy as np
A = np.ones((3, 3))
print(A[1, 2])     # 1.0
print(A.T.shape)   # (3, 3)  转置后仍是 3×3
```

</details>

---

## 第 3 章 矩阵乘法：Transformer 的心脏

**本章是全篇最重要的内容**，学不会这个，Transformer 就看不懂。

### 3.1 规则：只有"内维相等"才能乘

$A$ 是 $M \times K$（M 行 K 列），$B$ 是 $K \times N$（K 行 N 列），则 $A \times B$ 合法，结果是 **$M \times N$**：

$$(M \times K) \cdot (K \times N) \Rightarrow M \times N$$

规则一句话：**左边矩阵的列数 = 右边矩阵的行数**（都是 K），乘积的形状是"左行数 × 右列数"。

- $2 \times 3$ 乘 $3 \times 4$ → 结果 $2 \times 4$ ✓
- $2 \times 3$ 乘 $2 \times 4$ → **不能乘** ✗（内维 3 ≠ 2）

### 3.2 怎么算：点积视角

结果矩阵第 $i$ 行第 $j$ 列 = **A 的第 $i$ 行** 与 **B 的第 $j$ 列** 做点积。

**手算例子**：$A = \begin{bmatrix} 1 & 2 & 3 \\ 4 & 5 & 6 \end{bmatrix}$（2×3），$B = \begin{bmatrix} 7 & 8 \\ 9 & 10 \\ 11 & 12 \end{bmatrix}$（3×2），求 $AB$。

结果应为 $2 \times 2$。逐个算：

- 位置 (0,0) = A 第 0 行 [1,2,3] · B 第 0 列 [7,9,11] = $1\times7 + 2\times9 + 3\times11 = 7+18+33 = 58$
- 位置 (0,1) = [1,2,3] · [8,10,12] = $8+20+36 = 64$
- 位置 (1,0) = [4,5,6] · [7,9,11] = $28+45+66 = 139$
- 位置 (1,1) = [4,5,6] · [8,10,12] = $32+50+72 = 154$

$$AB = \begin{bmatrix} 58 & 64 \\ 139 & 154 \end{bmatrix}$$

```python
import numpy as np
A = np.array([[1, 2, 3],
              [4, 5, 6]])
B = np.array([[7, 8],
              [9, 10],
              [11, 12]])
print(A @ B)
# [[ 58  64]
#  [139 154]]
```

**和手算一致！** 以后手算检查结果，就用 numpy 验证。

### 3.3 三种理解视角（帮助建立直觉）

1. **点积视角**（上面用的）：结果的每个元素是"一行 × 一列"的点积。
2. **线性组合视角**：结果的第 $j$ 列 = A 的列按 B 的第 $j$ 列数字加权相加。即"矩阵 × 列向量 = 把矩阵的列线性组合起来"。
3. **变换视角**：把矩阵想象成"空间变换器"，乘上它就把向量拉伸/旋转/压缩。这是 3Blue1Brown 的视角，第 5 章会用到。

三种视角都对，用哪种取决于场景。**点积视角用于手算，变换视角用于理解"矩阵乘向量在干什么"。**

### 3.4 矩阵 × 向量：一个词过一层权重

Transformer 里最常出现的形状：**权重矩阵 $W$（输出维 × 输入维）乘以词向量 $x$（输入维）**，得到一个新向量。

**手算例子**：词向量 $x = [1, 0, 1]$（3 维），权重矩阵 $W = \begin{bmatrix} 1 & 2 & 0 \\ 0 & 1 & 1 \end{bmatrix}$（2×3，把 3 维压到 2 维）。

$$Wx = \begin{bmatrix} 1\times1 + 2\times0 + 0\times1 \\ 0\times1 + 1\times0 + 1\times1 \end{bmatrix} = \begin{bmatrix} 1 \\ 1 \end{bmatrix}$$

结果是个 2 维向量。**矩阵乘向量 = 对词做一次线性变换，把词的表示"换个角度"看。**

### 3.5 在 Transformer 里的角色：Q、K、V 就是这么来的

真正的自注意力里（对每个词）：

$$q_i = W_Q \cdot x_i, \quad k_i = W_K \cdot x_i, \quad v_i = W_V \cdot x_i$$

其中 $W_Q$、$W_K$、$W_V$ 是三个**可学习的权重矩阵**（训练时学出来的数字），$x_i$ 是第 $i$ 个词的向量。三个矩阵把同一个词从三个不同角度（查询 Query / 键 Key / 值 Value）各变换一次。

**注意**：很多人被"$W_Q$ 怎么来的"卡住——它就是训练时学出来的数字表格，和 1.3 任务里 API 的"模型参数"是同一个东西。**现阶段你只需要会算"矩阵 × 向量"，不需要会训练它。**

### 3.6 常见错误与检查技巧

- **维度不匹配**是最常见的报错：`matmul: Input operand 1 has a mismatch in its core dimension`。检查：内维是否相等。
- **先验形状再验数值**：算之前先心算结果形状，再动手。
- 用 `A @ B`（numpy），不是 `A * B`（那是逐元素乘，第 4 章）。

### 📝 第 3 章练习

**练习 8（判断题）**：下面哪些可以相乘？能乘的结果形状是什么？
- (a) $2\times3$ 乘 $3\times4$
- (b) $2\times3$ 乘 $2\times3$
- (c) $3\times1$ 乘 $1\times4$
- (d) $4\times2$ 乘 $2\times4$

<details>
<summary>点开看答案</summary>

- (a) 能，结果 $2\times4$
- (b) 不能（内维 3 ≠ 2）
- (c) 能，结果 $3\times4$
- (d) 能，结果 $4\times4$

</details>

**练习 9（手算）**：$\begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix} \times \begin{bmatrix} 5 & 6 \\ 7 & 8 \end{bmatrix} = ?$

<details>
<summary>点开看答案</summary>

$\begin{bmatrix} 1\times5+2\times7 & 1\times6+2\times8 \\ 3\times5+4\times7 & 3\times6+4\times8 \end{bmatrix} = \begin{bmatrix} 19 & 22 \\ 43 & 50 \end{bmatrix}$

</details>

**练习 10（手算）**：词向量 $x = [1, 0, 1]$，权重矩阵 $W = \begin{bmatrix} 1 & 2 & 0 \\ 0 & 1 & -1 \end{bmatrix}$，求 $Wx$。

<details>
<summary>点开看答案</summary>

$\begin{bmatrix} 1\times1 + 2\times0 + 0\times1 \\ 0\times1 + 1\times0 + (-1)\times1 \end{bmatrix} = \begin{bmatrix} 1 \\ -1 \end{bmatrix}$

</details>

**练习 11（numpy）**：创建两个矩阵，一个 $3\times2$、一个 $2\times4$，相乘并打印结果形状（应该是 $3\times4$）。

<details>
<summary>点开看答案</summary>

```python
import numpy as np
A = np.random.rand(3, 2)
B = np.random.rand(2, 4)
C = A @ B
print(C.shape)   # (3, 4)
```

</details>

---

## 第 4 章 逐元素运算与广播（numpy 实操必备）

### 4.1 逐元素乘法（Hadamard 积）

符号 $\odot$，**对应位置相乘**（和矩阵乘法完全不同！）：

$$\begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix} \odot \begin{bmatrix} 5 & 6 \\ 7 & 8 \end{bmatrix} = \begin{bmatrix} 5 & 12 \\ 21 & 32 \end{bmatrix}$$

```python
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])
print(A * B)     # 注意：* 是逐元素乘，@ 才是矩阵乘法
```

### 4.2 广播（Broadcast）：形状不同也能算

numpy 允许小形状的数组"自动扩展"去匹配大形状，规则（从右往左逐个维度对齐）：

> 每个维度：要么相等，要么有一个是 1，就能广播；结果是两个形状的"逐维取最大"。

**例子**：矩阵 + 一行的加法

```python
M = np.array([[1, 2, 3],
              [4, 5, 6]])       # (2, 3)
row = np.array([10, 20, 30])    # (3,)  看成 (1, 3)
print(M + row)
# [[11 22 33]
#  [14 25 36]]       每行都加上了 [10,20,30]
```

**与 Transformer 的联系**：位置编码（Positional Encoding）就是用"向量 + 矩阵"的广播实现的——把位置信息加在词向量矩阵的每一行上（`visual_pe.py` 就是干这个的）。

### 4.3 softmax：把任意得分变成"和为 1"的权重

softmax 不是线性代数概念，但它紧跟点积出现，必须一起学。给一个向量 $[s_1, s_2, \dots, s_n]$：

$$\text{softmax}(s_i) = \frac{e^{s_i}}{e^{s_1} + e^{s_2} + \dots + e^{s_n}}$$

两个作用：
1. **归一化**：输出全是正数且加起来等于 1 → 变成"权重/概率"
2. **放大差异**：指数函数 $e^x$ 会把大的数拉得更大（$e^3 \approx 20$，$e^0 = 1$），所以得分最高的词权重会显著突出

**手算例子**：得分 $[1, 2, 3]$：

- $e^1 \approx 2.72$，$e^2 \approx 7.39$，$e^3 \approx 20.09$，总和 ≈ 30.20
- softmax(1) ≈ 0.09，softmax(2) ≈ 0.24，softmax(3) ≈ 0.67

得分 3 的权重占了约三分之二——**差距被放大**。

```python
import numpy as np
s = np.array([1.0, 2.0, 3.0])
exp = np.exp(s)
p = exp / exp.sum()
print(p)         # [0.09003057 0.24472847 0.66524096]  和为 1
```

**与 Transformer 的联系**：注意力权重 = $\text{softmax}(\text{注意力得分})$，每个词把其他词的 V 按这些权重加权求和。

### 📝 第 4 章练习

**练习 12（手算）**：$[1, 2, 3] \odot [4, 5, 6] = ?$ 以及 $[2, -1] \odot [3, 4] = ?$

<details>
<summary>点开看答案</summary>

$[4, 10, 18]$ 和 $[6, -4]$

</details>

**练习 13（手算 softmax）**：得分 $[0, 2]$ 的 softmax 各是多少？提示：$e^0=1$，$e^2\approx7.39$。

<details>
<summary>点开看答案</summary>

总和 $\approx 8.39$；softmax(0) $\approx 0.12$，softmax(2) $\approx 0.88$。得分只差 2，权重差了 7 倍多——这就是 exp 的放大效应。

</details>

**练习 14（numpy 广播）**：`np.array([[1,2],[3,4]]) + np.array([10, 20])` 的结果是什么？用广播规则解释为什么合法。

<details>
<summary>点开看答案</summary>

```python
np.array([[1,2],[3,4]]) + np.array([10,20])
# [[11 22]
#  [13 24]]
```

形状 (2,2) 和 (2,)：从右往左对齐，列数 2=2 ✓，行数 2 与缺省的 1 → 广播成 2 ✓。所以 [10,20] 被复制到每一行再相加。

</details>

---

## 第 5 章 线性组合与"矩阵 = 变换"

### 5.1 线性组合

若干个向量**按一定比例（权重）相加**，叫线性组合：

$$w_1 v_1 + w_2 v_2 + \dots + w_n v_n$$

**手算例子**：$0.7 \times [1, 0] + 0.3 \times [0, 1] = [0.7, 0.3]$。

**与 Transformer 的联系**：注意力输出就是 V 的线性组合——每个词的输出 = 所有词的 $v_j$ 按注意力权重 $w_j$ 加权求和。这是 Transformer 最核心的计算之一。

### 5.2 线性相关、基（直觉版）

- 如果一组向量里有一个能由其他向量组合出来，它们**线性相关**（比如 $[1,2]$ 和 $[2,4]$，一个就是另一个的 2 倍）——信息有冗余。
- 一组**线性无关**的向量能"张成"一个空间：$n$ 个无关向量撑起 $n$ 维空间。比如 $[1,0]$ 和 $[0,1]$ 张成整个平面。
- 一组能张成空间的最少向量叫**基**。

**与 Transformer 的联系**：Embedding 维度 = 空间维数。维度越高，能容纳的"语义方向"越多（不过这个直觉到阶段 4+ 才会深用，现在了解即可）。

### 5.3 "矩阵 = 变换"视角（3Blue1Brown 的精髓）

$Wx$ 的结果，可以理解为"把向量 $x$ 放进一个**线性变换**里"：

- 矩阵的**列** = 原来的基向量（坐标轴）被变换后去了哪里
- 乘上矩阵 = 把 $x$ 在变换后的坐标轴上重新组合

所以 $W_Q x_i$ 的直观含义是：**用 $W_Q$ 这个变换，把词 $x_i$ 从"原始词义空间"映射到"查询空间"**。Query 空间里，方向相近 = 在查询意义下相关。

### 5.4 为什么神经网络里的层叫"线性层"？

神经网络的一层最常见的形态就是：**输出 = 权重矩阵 × 输入 + 偏置**，即 $y = Wx + b$。

- 它只做"缩放 + 旋转 + 平移"，没有弯曲——这就是**线性**。
- 多个线性层叠起来还是线性（$W_2(W_1x) = (W_2W_1)x$），所以每层之间要插入**非线性激活函数**（ReLU 等）来增加表达能力——这是深度学习的核心思想，任务 1.5 会学到。

**与 Transformer 的联系**：Transformer 里的 Feed-Forward 层、QKV 变换、输出投影，全是 $Wx + b$ 的形式。

### 📝 第 5 章练习

**练习 15（手算）**：$2 \times [1, 2] + 3 \times [0, -1] = ?$

<details>
<summary>点开看答案</summary>

$[2, 4] + [0, -3] = [2, 1]$

</details>

**练习 16（思考）**：$[1, 2]$ 和 $[2, 4]$ 线性相关吗？它们张成的空间是几维的？

<details>
<summary>点开看答案</summary>

相关（$2 \times [1,2] = [2,4]$，一个方向）。它们张成的空间只有 1 维——一条直线。

</details>

**练习 17（思考）**：为什么"几个线性层叠加 = 一个更大的线性层"？（提示：$W_2(W_1 x)$ 能不能合并成一个矩阵？）

<details>
<summary>点开看答案</summary>

可以：$W_2(W_1 x) = (W_2 W_1) x$，两个矩阵相乘还是矩阵。所以没有非线性激活的话，多深都等价于一层，模型学不出复杂规律。

</details>

---

## 第 6 章 张量：三维及以上的世界

### 6.1 从矩阵到张量

- 标量（0 维）：一个数
- 向量（1 维）：一排数
- 矩阵（2 维）：数表
- **张量（3 维+）**：数表叠数表——比如把多个矩阵摞在一起

Transformer 的数据通常是三维：**$(batch\_size, seq\_len, embedding\_dim)$**

- `batch_size`：一次同时处理几句话（batch）
- `seq_len`：一句话里有多少个词（序列长度）
- `embedding_dim`：每个词向量有几维

**例子**：一次喂 2 句话，每句 4 个词，词向量 8 维 → 张量 shape 是 $(2, 4, 8)$。

```python
import numpy as np
x = np.random.rand(2, 4, 8)   # (batch=2, seq_len=4, dim=8)
print(x.shape)                # (2, 4, 8)
print(x[0, 1, 2])             # 第 0 句话、第 1 个词、第 2 个分量
```

### 6.2 为什么叫"维度"容易混淆

注意"维度"有两个意思，别混：
1. **矩阵的维度**：shape，如 2×3（两个轴）
2. **词向量的维数**：向量长度，如 8 维

"把词向量映射到 512 维"说的是**向量长度**（第二个意思），不是把数据变成 512 个轴。读资料时遇到"维度"要看语境。

### 6.3 reshape 与 transpose（会用就行）

- `reshape`：改变 shape 但不改数据顺序（总元素数必须不变）
- `transpose`：交换轴（第 2.5 节的转置是多维版）

```python
x = np.arange(6)          # [0 1 2 3 4 5]
y = x.reshape(2, 3)       # [[0 1 2] [3 4 5]]，共 6 个元素不变
z = y.T                   # 转置成 (3, 2)
print(x.shape, y.shape, z.shape)   # (6,) (2, 3) (3, 2)
```

**与 Transformer 的联系**：模型代码里到处是 `.transpose()`（比如把注意力分数从 $(batch, heads, seq, seq)$ 调换轴），现在只要知道"transpose 是交换轴、shape 要按公式配"就够读 demo 了。

### 📝 第 6 章练习

**练习 18**：一个张量 shape 是 $(4, 3, 5)$，它表示什么？（结合 batch/seq_len/dim 说）

<details>
<summary>点开看答案</summary>

4 个批次，每个批次 3 个词（token），每个词 5 维向量。比如"4 句话，每句 3 个词，词向量 5 维"。

</details>

**练习 19（numpy）**：`np.ones((2, 3, 4)).sum()` 等于多少？为什么？

<details>
<summary>点开看答案</summary>

$2\times3\times4 = 24$。全是 1 的张量，总和 = 元素个数。

</details>

---

## 第 7 章 综合实战：手算一个迷你自注意力

现在把所有知识串起来。真实 Transformer 用几千维，这里用**极小版**：2 个词的句子 + 2 维词向量。全程手算，最后附 numpy 对照。

### 7.1 设定

- 句子："我 AI"（2 个词），词表里每个词一个 2 维向量：

| 词 | 向量 |
|---|---|
| 我 | $x_0 = [1, 0]$ |
| AI | $x_1 = [0, 1]$ |

句子矩阵：$X = \begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}$（2×2，两行分别是两个词）。

- 三个权重矩阵（为了手算方便，用简单数字；真实模型里它们是被训练出来的）：

$$W_Q = \begin{bmatrix} 1 & 1 \\ -1 & 1 \end{bmatrix}, \quad W_K = \begin{bmatrix} 1 & -1 \\ 1 & 1 \end{bmatrix}, \quad W_V = \begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}$$

### 7.2 第 1 步：算 Q、K、V（矩阵 × 向量）

对每个词 $q_i = W_Q x_i$、$k_i = W_K x_i$、$v_i = W_V x_i$：

$$q_0 = \begin{bmatrix} 1 & 1 \\ -1 & 1 \end{bmatrix}\begin{bmatrix} 1 \\ 0 \end{bmatrix} = \begin{bmatrix} 1 \\ -1 \end{bmatrix}, \quad q_1 = \begin{bmatrix} 1 & 1 \\ -1 & 1 \end{bmatrix}\begin{bmatrix} 0 \\ 1 \end{bmatrix} = \begin{bmatrix} 1 \\ 1 \end{bmatrix}$$

$$k_0 = \begin{bmatrix} 1 & -1 \\ 1 & 1 \end{bmatrix}\begin{bmatrix} 1 \\ 0 \end{bmatrix} = \begin{bmatrix} 1 \\ 1 \end{bmatrix}, \quad k_1 = \begin{bmatrix} 1 & -1 \\ 1 & 1 \end{bmatrix}\begin{bmatrix} 0 \\ 1 \end{bmatrix} = \begin{bmatrix} -1 \\ 1 \end{bmatrix}$$

$$v_0 = [1, 0], \quad v_1 = [0, 1]$$

### 7.3 第 2 步：注意力得分（点积矩阵 $QK^T$）

得分 $s_{ij} = q_i \cdot k_j$（"第 $i$ 个词看第 $j$ 个词有多相关"）：

- $s_{00} = q_0 \cdot k_0 = 1\times1 + (-1)\times1 = 0$
- $s_{01} = q_0 \cdot k_1 = 1\times(-1) + (-1)\times1 = -2$
- $s_{10} = q_1 \cdot k_0 = 1\times1 + 1\times1 = 2$
- $s_{11} = q_1 \cdot k_1 = 1\times(-1) + 1\times1 = 0$

$$S = \begin{bmatrix} 0 & -2 \\ 2 & 0 \end{bmatrix}$$

看第 0 行（"我"）：对"AI"的得分是 -2，对自己 0 → "我"更关注自己。第 1 行（"AI"）：对"我"得分 2 → "AI"强烈关注"我"。

### 7.4 第 3 步：softmax 归一化（逐行）

行 0：$[e^0, e^{-2}] = [1, 0.135]$，归一化后 $[0.881, 0.119]$
行 1：$[e^2, e^0] = [7.389, 1]$，归一化后 $[0.881, 0.119]$

$$P = \begin{bmatrix} 0.881 & 0.119 \\ 0.881 & 0.119 \end{bmatrix}$$

每行和都是 1 ✓。这就是注意力权重。

### 7.5 第 4 步：加权求和（线性组合）

输出 $o_i = \sum_j p_{ij} v_j$：

$$o_0 = 0.881 \times [1, 0] + 0.119 \times [0, 1] = [0.881, 0.119]$$
$$o_1 = 0.881 \times [1, 0] + 0.119 \times [0, 1] = [0.881, 0.119]$$

最终输出：两个词的表示都被更新为 $[0.881, 0.119]$——因为"AI"强关注"我"，而"我"也主要关注自己，两个词的输出融合到了一起。这就是自注意力的全部流程！

### 7.6 numpy 全程对照

```python
import numpy as np

X  = np.array([[1, 0], [0, 1]])               # (2, 2) 两个词的向量
WQ = np.array([[1, 1], [-1, 1]])
WK = np.array([[1, -1], [1, 1]])
WV = np.array([[1, 0], [0, 1]])

Q = X @ WQ.T      # 注意：X 的每行是一个词，权重矩阵放在右边要转置（和手算时 WQ·x 等价）
K = X @ WK.T
V = X @ WV.T

S = Q @ K.T       # 注意力得分矩阵 (2, 2)
print(S)          # [[ 0 -2] [ 2  0]]   与手算一致

exp_S = np.exp(S)
P = exp_S / exp_S.sum(axis=1, keepdims=True)   # softmax，axis=1 表示逐行
print(P)          # [[0.88079708 0.11920292] [0.88079708 0.11920292]]

O = P @ V         # 加权求和
print(O)          # [[0.88079708 0.11920292] [0.88079708 0.11920292]]
```

**跑一遍，和手算结果完全一致。**

> 💡 真实 Transformer 还差三小步：除以 $\sqrt{d_k}$ 缩放得分（防止 softmax 饱和）、多头（多组 W 并行）、位置编码（第 4.2 节）。但骨架就是上面这四步——矩阵乘法、点积、softmax、加权求和。你已经掌握了 Transformer 的数学核心。

### 📝 第 7 章练习

**练习 20（思考）**：如果 $W_Q$ 和 $W_K$ 都是零矩阵，注意力权重会变成什么样？模型的输出会怎样？

<details>
<summary>点开看答案</summary>

所有得分都是 0，softmax 后每行权重均匀分布（$[0.5, 0.5]$）——每个词的输出变成所有词向量的等权平均，完全没有"选择性"。"我"和"AI"的输出会完全一样。这说明注意力机制的能力全在于学出好的 $W_Q$、$W_K$。

</details>

**练习 21（思考/进阶）**：为什么真实代码里要先把得分除以 $\sqrt{d_k}$ 再做 softmax？提示：考虑得分很大时 $e^x$ 的陡峭程度。

<details>
<summary>点开看答案</summary>

得分 = 高维向量的点积，维度越高，得分绝对值普遍越大（方差不小）。当得分很大时，$e^x$ 急剧放大差距，softmax 会"饱和"成接近 one-hot（最大权重≈1，其他≈0），梯度消失、模型学不动。除以 $\sqrt{d_k}$ 把得分拉回适中范围，softmax 保持"平滑"。这是实用技巧，本阶段知道结论即可。

</details>

---

## 第 8 章 进阶概念（本阶段了解即可）

这些在 Transformer 学习路上会出现名字，但**现在不需要掌握**，知道一句话含义就够：

| 概念 | 一句话直觉 | 什么时候会用到 |
|---|---|---|
| 特征值 / 特征向量 | 矩阵变换时"方向不变、只拉伸"的特殊向量 | 数学推导、PCA 降维 |
| 奇异值分解（SVD） | 把任何矩阵拆成"旋转×拉伸×旋转" | 矩阵分解、推荐系统；RAG 向量库（阶段 3）附近会再见到 |
| L1 / L2 范数 | 衡量向量大小的不同方式（L2=勾股长度） | 正则化、相似度计算 |
| 梯度 / 偏导数 | 函数在某点"变化最快"的方向（微积分） | 任务 1.5 学反向传播时 |

到任务 1.5（深度学习地基，选修）时，你会在代码里自然遇到张量、矩阵乘法、线性层——届时回来翻本文档对应章节即可。

---

## 第 9 章 学习自测清单

学完并做完所有练习后，你应该能不看资料回答：

1. ✅ 向量是什么？词向量和"语义相近"有什么关系？
2. ✅ 点积怎么算？为什么点积能衡量"两个词的相关性"？
3. ✅ 矩阵乘法什么时候合法？结果形状怎么算？
4. ✅ 能手算一个 $2\times2$ 乘 $2\times2$ 的矩阵乘法
5. ✅ 注意力得分 → softmax → 加权求和，三步各在干什么
6. ✅ 能说出 $Q$、$K$、$V$ 分别由哪个权重矩阵乘 $X$ 得到
7. ✅ 知道 `@`（矩阵乘）和 `*`（逐元素乘）的区别
8. ✅ 能读懂 shape 为 $(batch, seq\_len, dim)$ 的数据
9. ✅ 能向别人讲一遍第 7 章迷你注意力的完整计算过程

全部 ✅ 后，就可以放心进入任务 1.4 的 Transformer 学习了。

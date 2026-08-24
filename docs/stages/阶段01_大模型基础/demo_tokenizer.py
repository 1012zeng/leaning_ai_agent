import tiktoken

# cl100k_base: OpenAI GPT-4 / GPT-3.5 使用的真实分词器
enc = tiktoken.get_encoding('cl100k_base')
print('词表大小:', enc.n_vocab)


def show(sentence):
    ids = enc.encode(sentence)
    print(f'\n句子: {sentence!r}  -> {len(ids)} 个 token, ids = {ids}')
    for tid in ids:
        b = enc.decode_single_token_bytes(tid)  # token 对应的原始字节
        text = b.decode('utf-8', errors='replace')
        print(f'  token id {tid:6d}  ->  {text!r}')


show('你吃饭没？')
show('你好，世界！')
show('Hello, world! How are you?')
show('饕餮大餐')          # 罕见字
show('internationalization')  # 长英文词

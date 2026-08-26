import numpy as np

embedding = np.array([1,2,3,4])
print(embedding.shape)
print(type(embedding.shape))
print(embedding[1], embedding[2], embedding[3])

v = np.array([3,4])
print(np.linalg.norm(v))
print(v)
print(v/np.linalg.norm(v))

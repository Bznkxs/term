import cv2
import numpy as np
def get_permutation(n):
    ll = list(range(n))
    j = n//2
    for i in range(1, n-1):
        if i < j:
            ll[i], ll[j] = ll[j], ll[i]
        k = n // 2
        while j >= k:
            j -= k
            k //= 2
        if j < k:
            j += k
    return np.array(ll)

def dezek():
    x:np.ndarray=cv2.imread(".config.a")
    _,w,_=x.shape
    x = x.reshape([-1])
    n = 1
    n1 = len(x)
    while n * 2 <= n1:
        n *= 2
    ll = get_permutation(n)
    x[:n] = x[:n][ll]
    x = x[:n1]
    x=x.reshape([-1,w,3])
    while (x[-1] == 0).all():
        x = x[:-1]
    return x

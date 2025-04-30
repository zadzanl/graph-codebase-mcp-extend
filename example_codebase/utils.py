import inspect
from functools import wraps

def log_execution(func):
    """示範 Decorator，記錄函式呼叫與結果"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        args_str = ", ".join(repr(a) for a in args)
        result = func(*args, **kwargs)
        print(f"[LOG] Called {func.__name__}({args_str}) -> {result}")
        return result
    return wrapper

class MathOps:
    """示範 Static Method 與 Class Method"""
    factor = 2

    @staticmethod
    def add(a, b):
        """靜態方法，不依賴實例或類別狀態"""
        return a + b

    @classmethod
    def scale(cls, x):
        """類方法，可操作類別層級狀態"""
        return cls.factor * x

def make_multiplier(n):
    """示範 Closure，返回依據 n 動態產生的 multiplier 函式"""
    def multiplier(x):
        return x * n
    return multiplier 
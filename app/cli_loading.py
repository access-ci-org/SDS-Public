from functools import wraps
from halo import Halo


def custom_halo(text="Loading", spinner="dots"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            spinner_obj = Halo(text=text, spinner=spinner)
            spinner_obj.start()
            try:
                result = func(*args, **kwargs)
                spinner_obj.succeed()  # This will show a checkmark
                return result
            except Exception as e:
                spinner_obj.fail()  # This will show an "x" mark if there's an error
                raise e

        return wrapper

    return decorator

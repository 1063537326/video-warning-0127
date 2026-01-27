try:
    import ultralytics
    print(f"Ultralytics imported: {ultralytics.__version__}")
    from enum import Enum
    class Status(str, Enum):
        A = "a"
    print(f"Enum created: {Status.A}")
except TypeError as e:
    print(f"Enum Error: {e}")
except Exception as e:
    print(f"Error: {e}")


try:
    import ultralytics
    print(f"Ultralytics found: {ultralytics.__version__}")
    from ultralytics import YOLO
    print("YOLO imported successfully")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"Error: {e}")

def bytes_to_str(obj):
    if isinstance(obj, dict):
        return {k: bytes_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [bytes_to_str(v) for v in obj]
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    else:
        return obj
from mem0 import Memory
import pydantic

try:
    # This will trigger the validation error and show allowed values if we're lucky
    # Or we can inspect the MemoryConfig class
    from mem0.configs.base import MemoryConfig
    print("MemoryConfig fields:", MemoryConfig.__annotations__)
    # For newer pydantic, we can check the validator
    from mem0.configs.vector_stores import VectorStoreConfig
    print("VectorStoreConfig info:", VectorStoreConfig)
except Exception as e:
    print("Error:", e)

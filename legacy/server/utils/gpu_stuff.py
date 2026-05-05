import gc
import sys

import torch


def clear_gpu_memory():
    return

    """Completely clears GPU memory"""
    # Clear CUDA cache
    torch.cuda.empty_cache()

    # Get current CUDA devices
    devices = list(range(torch.cuda.device_count()))

    # Clear memory for each device
    for device in devices:
        torch.cuda.set_device(device)
        torch.cuda.empty_cache()

    # Force garbage collection
    gc.collect()

    # Clear Python references
    sys.modules.clear()
    gc.collect()

    # Verify memory is cleared
    print(f"GPU Memory Allocated: {torch.cuda.memory_allocated() / 1024 / 1024:.2f} MB")
    print(f"GPU Memory Cached: {torch.cuda.memory_cached() / 1024 / 1024:.2f} MB")
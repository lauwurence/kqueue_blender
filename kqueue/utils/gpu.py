################################################################################
##

from pynvml import *

def get_gpu_vram_pynvml():
    """
    """

    nvmlInit()
    device_count = nvmlDeviceGetCount()

    if device_count == 0:
        print("GPU не найдены")
        return None

    gpu_info = []

    for i in range(device_count):
        handle = nvmlDeviceGetHandleByIndex(i)

        # Информация об устройстве
        name = nvmlDeviceGetName(handle)
        memory_info = nvmlDeviceGetMemoryInfo(handle)
        utilization = nvmlDeviceGetUtilizationRates(handle)

        try:
            temperature = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
        except:
            temperature = 0

        try:
            power_usage = nvmlDeviceGetPowerUsage(handle) / 1000.0  # В ватты
            power_limit = nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
        except:
            power_usage = 0
            power_limit = 0

        info = {
            'index': i,
            'name': name.decode('utf-8') if isinstance(name, bytes) else name,
            'memory_total_bytes': memory_info.total,
            'memory_free_bytes': memory_info.free,
            'memory_used_bytes': memory_info.used,
            'memory_total_gb': memory_info.total / (1024**3),
            'memory_free_gb': memory_info.free / (1024**3),
            'memory_used_gb': memory_info.used / (1024**3),
            'gpu_utilization_percent': utilization.gpu,
            'memory_utilization_percent': utilization.memory,
            'temperature_c': temperature,
            'power_usage_w': power_usage,
            'power_limit_w': power_limit
        }

        gpu_info.append(info)

        # print(f"\nGPU {i}: {info['name']}")
        # print(f"  Память: {info['memory_used_gb']:.1f}/{info['memory_total_gb']:.1f} GB "
        #         f"({info['memory_utilization_percent']}%)")
        # print(f"  Загрузка GPU: {info['gpu_utilization_percent']}%")
        # print(f"  Температура: {info['temperature_c']}°C")

        # if info['power_usage_w'] > 0:
        #     print(f"  Потребление: {info['power_usage_w']:.1f}/{info['power_limit_w']:.1f} W")

    nvmlShutdown()
    return gpu_info

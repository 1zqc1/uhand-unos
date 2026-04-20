# bt_uhand.py
# 飞腾派 V3 与机械手蓝牙通信程序
# 使用 bleak BLE 库
# 安装: pip install bleak

import asyncio
from bleak import BleakClient

# HC-08 MAC 地址
HC08_MAC = "48:87:2D:7E:B4:37"


async def find_hc08_services():
    """查询 HC-08 的服务和特征值"""
    print("=" * 50)
    print(f"查询 {HC08_MAC} 的 BLE 服务...")
    print("=" * 50)

    try:
        async with BleakClient(HC08_MAC, timeout=10) as client:
            print(f"连接状态: {client.is_connected}\n")

            # 获取所有服务
            services = client.services
            for service in services:
                print(f"[服务] {service.uuid}")
                for char in service.characteristics.values():
                    print(f"   |-- [特征值] UUID: {char.uuid}")
                    print(f"   |       属性: {char.properties}")

    except Exception as e:
        print(f"[错误] {e}")


if __name__ == "__main__":
    asyncio.run(find_hc08_services())
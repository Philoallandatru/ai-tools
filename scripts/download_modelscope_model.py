#!/usr/bin/env python3
"""从ModelScope下载模型到本地，供LM Studio使用"""

from modelscope import snapshot_download
import os

def download_model(model_id: str, cache_dir: str = None):
    """
    从ModelScope下载模型

    Args:
        model_id: ModelScope模型ID，例如 'Qwen/Qwen2.5-7B-Instruct'
        cache_dir: 缓存目录，默认为 ~/.cache/modelscope
    """
    print(f"开始下载模型: {model_id}")
    print(f"缓存目录: {cache_dir or '~/.cache/modelscope'}")

    model_dir = snapshot_download(
        model_id,
        cache_dir=cache_dir,
        revision='master'
    )

    print(f"\n✅ 模型下载完成！")
    print(f"📁 模型路径: {model_dir}")
    print(f"\n在LM Studio中加载此模型：")
    print(f"1. 打开LM Studio")
    print(f"2. 点击 'Load Model' -> 'Load from disk'")
    print(f"3. 选择路径: {model_dir}")

    return model_dir

if __name__ == "__main__":
    # 推荐的模型（适合16GB显存）
    models = {
        "1": ("Qwen/Qwen2.5-7B-Instruct", "Qwen2.5 7B（推荐，约14GB显存）"),
        "2": ("Qwen/Qwen2.5-14B-Instruct-GGUF", "Qwen2.5 14B GGUF（量化版本，约9GB显存）"),
        "3": ("Qwen/Qwen3.5-7B-Instruct", "Qwen3.5 7B（最新版本）"),
    }

    print("=" * 60)
    print("ModelScope模型下载工具")
    print("=" * 60)
    print("\n可用模型：")
    for key, (model_id, desc) in models.items():
        print(f"{key}. {desc}")
        print(f"   ID: {model_id}")

    choice = input("\n请选择要下载的模型（输入数字）: ").strip()

    if choice in models:
        model_id, desc = models[choice]
        print(f"\n选择: {desc}")

        # 可选：自定义缓存目录
        custom_dir = input("\n自定义缓存目录（直接回车使用默认）: ").strip()
        cache_dir = custom_dir if custom_dir else None

        try:
            download_model(model_id, cache_dir)
        except Exception as e:
            print(f"\n❌ 下载失败: {e}")
            print("\n可能的解决方案：")
            print("1. 检查网络连接")
            print("2. 设置ModelScope镜像: export MODELSCOPE_CACHE=<path>")
            print("3. 使用代理: export HTTP_PROXY=<proxy_url>")
    else:
        print("无效选择")

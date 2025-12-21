"""
直接测试TTS服务
"""
import asyncio
import os
import sys

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.services.tts_service import TTSService
from config.settings import settings

async def test_tts():
    print("=" * 70)
    print("🗣️  TTS服务直接测试")
    print("=" * 70)

    # 初始化TTS服务
    tts_service = TTSService()
    print(f"\n✅ TTS服务初始化成功")
    print(f"  Provider: {tts_service.provider}")
    print(f"  Mock Mode: {tts_service.mock_mode}")
    print(f"  Output Dir: {tts_service.output_dir}")

    # 测试文本
    test_texts = [
        "你好，我是你的导航助手",
        "前方50米左转",
        "检测到障碍物，请注意安全"
    ]

    print(f"\n🎯 开始测试TTS生成...\n")

    for i, text in enumerate(test_texts, 1):
        print(f"测试 {i}/{len(test_texts)}: {text}")
        try:
            audio_url = await tts_service.text_to_speech(
                text=text,
                session_id=f"test_session_{i}"
            )

            print(f"  ✅ 生成成功: {audio_url}")

            # 检查文件是否存在
            if not audio_url.startswith('/audio/mock_'):
                filename = audio_url.replace('/audio/', '')
                filepath = os.path.join(settings.AUDIO_OUTPUT_DIR, filename)
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath) / 1024  # KB
                    print(f"  📁 文件存在: {filepath}")
                    print(f"  📏 文件大小: {file_size:.2f} KB")
                else:
                    print(f"  ⚠️  文件不存在: {filepath}")
            else:
                print(f"  ℹ️  Mock模式音频")

        except Exception as e:
            print(f"  ❌ 生成失败: {e}")
            import traceback
            traceback.print_exc()

        print()

    print("=" * 70)
    print("✅ TTS测试完成")
    print("=" * 70)

    # 列出生成的音频文件
    print(f"\n📂 音频输出目录: {settings.AUDIO_OUTPUT_DIR}")
    if os.path.exists(settings.AUDIO_OUTPUT_DIR):
        files = os.listdir(settings.AUDIO_OUTPUT_DIR)
        if files:
            print(f"生成的音频文件 ({len(files)}个):")
            for f in files[:10]:  # 只显示前10个
                filepath = os.path.join(settings.AUDIO_OUTPUT_DIR, f)
                size = os.path.getsize(filepath) / 1024
                print(f"  - {f} ({size:.2f} KB)")
        else:
            print("  (空)")
    else:
        print("  (目录不存在)")

if __name__ == "__main__":
    asyncio.run(test_tts())

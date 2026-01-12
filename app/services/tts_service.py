"""
TTS语音合成服务
"""
from typing import Optional
from config.settings import settings
import os
import hashlib
import asyncio


class TTSService:

    def __init__(self):
        self.provider = settings.TTS_PROVIDER
        self.output_dir = settings.AUDIO_OUTPUT_DIR
        self.mock_mode = settings.MOCK_MODE

        os.makedirs(self.output_dir, exist_ok=True)
    
    async def text_to_speech(
        self,
        text: str,
        session_id: str
    ) -> Optional[str]:
        """
        文本转语音
        
        Returns:
            音频文件URL
        """
        if not text:
            return None
        
        if self.mock_mode:
            return self._mock_audio_url(text)
        
        try:
            if self.provider == "edge":
                return await self._edge_tts(text, session_id)
            elif self.provider == "azure":
                return await self._azure_tts(text, session_id)
            elif self.provider == "aliyun":
                return await self._aliyun_tts(text, session_id)
            else:
                return await self._edge_tts(text, session_id)  # 默认使用Edge
        except Exception as e:
            print(f"TTS生成失败: {e}")
            return self._mock_audio_url(text)
    
    async def _edge_tts(self, text: str, session_id: str) -> str:
        try:
            import edge_tts

            filename = self._generate_filename(text, session_id)
            filename = filename.replace('.wav', '.mp3')

            filepath = os.path.abspath(os.path.join(self.output_dir, filename))
            filepath = filepath.replace('\\', '/')

            if os.path.exists(filepath):
                print(f"使用缓存音频: {filename}")
                return f"/audio/{filename}"

            voice = "zh-CN-XiaoxiaoNeural"  # 可选: XiaoyiNeural, YunxiNeural
            communicate = edge_tts.Communicate(text, voice)

            await communicate.save(filepath)
            print(f"Edge TTS生成音频: {filename}")
            
            return f"/audio/{filename}"
            
        except ImportError:
            print("edge-tts未安装，请运行: pip install edge-tts")
            return self._mock_audio_url(text)
        except Exception as e:
            print(f"Edge TTS失败: {e}")
            return self._mock_audio_url(text)
    
    async def _azure_tts(self, text: str, session_id: str) -> str:
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            speech_config = speechsdk.SpeechConfig(
                subscription=settings.TTS_API_KEY,
                region=settings.TTS_REGION
            )
            speech_config.speech_synthesis_voice_name = settings.TTS_VOICE

            filename = self._generate_filename(text, session_id)
            filepath = os.path.join(self.output_dir, filename)
            
            audio_config = speechsdk.audio.AudioOutputConfig(filename=filepath)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            
            result = synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return f"/audio/{filename}"
            else:
                return self._mock_audio_url(text)
                
        except Exception as e:
            print(f"Azure TTS失败: {e}")
            return self._mock_audio_url(text)
    
    async def _aliyun_tts(self, text: str, session_id: str) -> str:

        # TODO: 实现阿里云TTS
        return self._mock_audio_url(text)
    
    @staticmethod
    def _generate_filename(text: str, session_id: str) -> str:
        import re
        hash_obj = hashlib.md5(f"{text}{session_id}".encode())
        filename = f"{hash_obj.hexdigest()}.mp3"
        # Windows文件名不能包含特殊字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        return filename
    
    @staticmethod
    def _mock_audio_url(text: str) -> str:
        hash_obj = hashlib.md5(text.encode())
        return f"/audio/mock_{hash_obj.hexdigest()[:8]}.wav"

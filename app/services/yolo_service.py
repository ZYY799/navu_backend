"""
YOLO视觉识别服务
"""
from typing import List, Dict
from config.settings import settings
from app.models.schemas import ObstacleInfo
import base64
import io
import sys
try:
    import numpy as np
except Exception:
    np = None
from PIL import Image
import tempfile
import os
from pathlib import Path
import urllib.request

# Windows编码修复 (仅在非Jupyter环境)
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


class YOLOService:
    """YOLO障碍物检测服务"""
    
    def __init__(self):
        self.model_path = settings.YOLO_MODEL_PATH
        self.confidence = settings.YOLO_CONFIDENCE
        self.device = settings.YOLO_DEVICE
        self.mock_mode = settings.MOCK_MODE
        self.model = None
        self._device_auto: str = ""   # 最终用的 device
        self._fail_streak: int = 0    # 连续失败计数（用于自动降级 mock）

    def _weights_path(self) -> str:
        # 建议把 settings.YOLO_MODEL_PATH 设成 "weights/yolov8n.pt"
        return self.model_path

    def _ensure_weights(self) -> bool:
        """确保权重文件存在：不存在则下载。失败返回 False"""
        path = Path(self._weights_path())
        if path.exists():
            return True

        # 你可以把 URL 放到环境变量里：YOLO_MODEL_URL
        url = getattr(settings, "YOLO_MODEL_URL", None) or os.getenv(
            "YOLO_MODEL_URL",
            "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt"
        )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            print(f"[YOLO] weights not found, downloading: {url} -> {path}")
            urllib.request.urlretrieve(url, str(path))
            print("[YOLO] download done.")
            return True
        except Exception as e:
            print(f"[YOLO] download failed: {e}")
            return False
        
    def _load_model(self):
        """加载YOLO模型（带自动下载 + 自动选GPU/CPU）"""
        try:
            if not self._ensure_weights():
                raise RuntimeError("weights not available")

            # ✅ 自动选 device：有 CUDA 用 cuda，否则 cpu
            try:
                import torch
                auto_dev = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                auto_dev = "cpu"

            # ✅ 允许 settings.YOLO_DEVICE 覆盖（如果你设置了）
            dev = (self.device or "").strip().lower()
            if dev in ["cuda", "cpu", "mps"]:
                self._device_auto = dev
            else:
                self._device_auto = auto_dev

            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            print(f"✅ YOLO模型加载成功: {self.model_path}  device={self._device_auto}")
        except Exception as e:
            print(f"❌ YOLO模型加载失败: {e}")
            print("⚠️  将使用模拟模式")
            self.mock_mode = True
            self.model = None
    
    async def detect_batch(self, images_base64: List[str]) -> List[Dict]:
        """
        批量检测图片中的障碍物
        - ✅ 任意一张成功完成 YOLO 推理 => 返回真实结果（允许其他张为空）
        - ✅ 只有三张都失败（都抛异常）=> 本轮回退 mock
        """
        if (not self.mock_mode) and (self.model is None):
            self._load_model()

        if self.mock_mode:
            return self._mock_detection(len(images_base64))

        results: List[Dict] = []
        any_infer_ok: bool = False  # ✅ 本轮是否有任意一张“成功跑完推理（无异常）”

        for idx, img_b64 in enumerate(images_base64, 1):
            temp_file = None
            try:
                b64 = (img_b64 or "").strip()

                # ✅ 兼容 data URL：data:image/jpeg;base64,xxxx
                if b64.startswith("data:") and "," in b64:
                    b64 = b64.split(",", 1)[1].strip()

                # ✅ 修复 base64 padding（有些占位图会缺 =）
                pad = (-len(b64)) % 4
                if pad:
                    b64 = b64 + ("=" * pad)

                # 解码 Base64
                img_data = base64.b64decode(b64)

                # PIL 读图（load() 可更早暴露 broken stream）
                image = Image.open(io.BytesIO(img_data))
                image.load()

                if image.mode != "RGB":
                    image = image.convert("RGB")

                # 保存到临时文件（YOLO 支持 path）
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                image.save(temp_file.name, "JPEG")
                temp_file.close()

                # ✅ 推理：显式 device（如果你在 _load_model 里算好了）
                # 如果你没加 self._device_auto，也可以先把 device=... 这一行删掉
                detections = self.model(
                    temp_file.name,
                    conf=self.confidence,
                    device=(getattr(self, "_device_auto", "") or None),
                    verbose=False
                )[0]

                # 解析结果
                obstacles = []
                if hasattr(detections, "boxes") and len(detections.boxes) > 0:
                    for det in detections.boxes.data:
                        x1, y1, x2, y2, conf, cls = det
                        obstacles.append({
                            "class": int(cls),
                            "confidence": float(conf),
                            "bbox": [float(x1), float(y1), float(x2), float(y2)]
                        })

                results.append({"obstacles": obstacles})
                any_infer_ok = True
                print(f"✅ 图片 {idx} 检测完成: 发现 {len(obstacles)} 个对象")

            except Exception as e:
                print(f"❌ 图片 {idx} 检测失败: {e}")
                import traceback
                traceback.print_exc()
                results.append({"obstacles": []})

            finally:
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                    except Exception:
                        pass

        # ✅ 本轮回退：三张都没成功跑完推理（全部抛异常）才回退 mock
        if not any_infer_ok:
            print("⚠️ 本轮 3 张均推理失败 -> fallback mock_detection(本轮)")
            return self._mock_detection(len(images_base64))

        return results

    
    def _mock_detection(self, count: int) -> List[Dict]:
        """模拟检测结果"""
        return [
            {
                "obstacles": [
                    {
                        "class": 0,  # 台阶
                        "confidence": 0.85,
                        "bbox": [100, 200, 300, 400]
                    },
                    {
                        "class": 2,  # 障碍物
                        "confidence": 0.75,
                        "bbox": [400, 150, 500, 350]
                    }
                ]
            }
            for _ in range(count)
        ]
    
    def aggregate_obstacles(self, detections: List[Dict]) -> List[ObstacleInfo]:
        """整合多张图片的检测结果"""
        all_obstacles = []
        
        for detection in detections:
            for obs in detection.get("obstacles", []):
                obstacle_type = self._map_class_to_type(obs["class"])
                distance = self._estimate_distance(obs["bbox"])
                direction = self._estimate_direction(obs["bbox"])
                
                all_obstacles.append(ObstacleInfo(
                    type=obstacle_type,
                    distance=distance,
                    direction=direction,
                    confidence=obs["confidence"]
                ))
        
        # 去重并排序（按距离）
        all_obstacles.sort(key=lambda x: x.distance)
        return all_obstacles[:5]  # 只返回最近的5个
    
    @staticmethod
    def _map_class_to_type(class_id: int) -> str:
        """映射类别ID到障碍物类型"""
        mapping = {
            0: "stairs",
            1: "curb",
            2: "obstacle",
            3: "blind_path_broken",
            4: "slope"
        }
        return mapping.get(class_id, "obstacle")
    
    @staticmethod
    def _estimate_distance(bbox: List[float]) -> float:
        """根据检测框大小估算距离（米）"""
        # 简化算法：框越大距离越近
        x1, y1, x2, y2 = bbox
        area = (x2 - x1) * (y2 - y1)
        # 假设图片尺寸640x480，标准化面积
        norm_area = area / (640 * 480)
        
        # 经验公式
        distance = 10 / (norm_area * 100 + 0.1)
        return round(distance, 1)
    
    @staticmethod
    def _estimate_direction(bbox: List[float]) -> str:
        """根据检测框位置估算方向"""
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        
        # 假设图片宽度640
        if center_x < 213:
            return "左前方"
        elif center_x > 427:
            return "右前方"
        else:
            return "正前方"
    
    def calculate_safety_level(self, obstacles: List[ObstacleInfo]) -> int:
        """计算安全等级 (1-5)"""
        if not obstacles:
            return 5
        
        # 根据最近障碍物距离
        closest = min(obs.distance for obs in obstacles)
        
        if closest < 2:
            return 1
        elif closest < 5:
            return 2
        elif closest < 10:
            return 3
        elif closest < 20:
            return 4
        else:
            return 5
    
    def describe_road_condition(self, obstacles: List[ObstacleInfo]) -> str:
        """描述道路状况"""
        if not obstacles:
            return "道路通畅，无明显障碍"
        
        if len(obstacles) >= 3:
            return "前方障碍物较多，请小心慢行"
        
        closest = obstacles[0]
        return f"前方{closest.distance}米处有{closest.type}，请注意"
    
    def generate_warning_text(self, obstacles: List[ObstacleInfo]) -> str:
        """生成警告文本"""
        if not obstacles:
            return ""
        
        closest = obstacles[0]
        type_cn = {
            "stairs": "台阶",
            "curb": "路沿",
            "obstacle": "障碍物",
            "blind_path_broken": "盲道中断",
            "slope": "坡道"
        }.get(closest.type, "障碍物")
        
        return f"注意！{closest.direction}{closest.distance}米处有{type_cn}"

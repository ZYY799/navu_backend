"""
高德地图服务
"""
from typing import Dict, List, Optional, Any
from config.settings import settings
import requests
import math
import asyncio

class AmapService:
    """高德地图API服务"""
    
    def __init__(self):
        self.api_key = settings.AMAP_API_KEY
        self.base_url = "https://restapi.amap.com/v5"
        self.mock_mode = settings.MOCK_MODE
    
    async def plan_walking_route(
        self,
        origin: Dict[str, float],
        destination: Dict[str, float]
    ) -> List[Dict]:
        """
        步行路径规划
        
        Args:
            origin: {"lat": xx, "lng": xx}
            destination: {"lat": xx, "lng": xx}
        
        Returns:
            List of route options
        """
        if self.mock_mode:
            return self._mock_routes(origin, destination)
        
        try:
            url = f"{self.base_url}/direction/walking"
            params = {
                "key": self.api_key,
                "origin": f"{origin['lng']},{origin['lat']}",
                "destination": f"{destination['lng']},{destination['lat']}",
                "show_fields": "polyline"
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("status") == "1":
                return self._parse_routes(data)
            else:
                print(f"高德API错误: {data.get('info')}")
                return self._mock_routes(origin, destination)
                
        except Exception as e:
            print(f"高德API调用失败: {e}")
            return self._mock_routes(origin, destination)
    
    async def search_poi_text(
        self,
        keywords: str,
        city: Optional[str] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        使用高德 WebService 「POI 关键字搜索」获取地点坐标（返回第一个 POI + 候选列表）

        返回：
        {
          "success": bool,
          "poi": {"name": str, "address": str, "lat": float, "lng": float, "adcode": str},
          "candidates": [ ... ],
          "raw": {...}   # 可选：便于 debug
        }
        """
        if self.mock_mode:
            return {
                "success": True,
                "poi": {"name": keywords, "address": "", "lat": 39.916527, "lng": 116.397128, "adcode": ""},
                "candidates": [],
                "raw": {"mock": True},
            }

        # ✅ 高德 POI 关键字搜索：restapi.amap.com/v3/place/text
        url = "https://restapi.amap.com/v3/place/text"
        params: Dict[str, Any] = {
            "key": self.api_key,
            "keywords": keywords,
            "output": "JSON",
            "offset": str(max(1, min(limit, 25))),  # 高德 offset 通常 1-25
            "page": "1",
            "extensions": "base",
        }
        if city and city.strip():
            params["city"] = city.strip()
            params["citylimit"] = "true"

        def _do_req() -> Dict[str, Any]:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()

        try:
            data = await asyncio.to_thread(_do_req)
        except Exception as e:
            return {"success": False, "error": f"amap poi request failed: {e}"}

        # 高德常见返回：status="1" 表示成功
        if data.get("status") != "1":
            return {"success": False, "error": f"amap poi status!=1 info={data.get('info')}", "raw": data}

        pois: List[Dict[str, Any]] = data.get("pois") or []
        if len(pois) == 0:
            return {"success": False, "error": f"未找到地点: {keywords}", "raw": data}

        def _parse_one(p: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            loc = (p.get("location") or "").strip()  # "lng,lat"
            if "," not in loc:
                return None
            try:
                lng_s, lat_s = loc.split(",", 1)
                lng = float(lng_s)
                lat = float(lat_s)
            except Exception:
                return None

            return {
                "name": (p.get("name") or "").strip(),
                "address": (p.get("address") or "").strip(),
                "lat": lat,
                "lng": lng,
                "adcode": (p.get("adcode") or "").strip(),
            }

        candidates: List[Dict[str, Any]] = []
        for p in pois[:max(1, min(limit, 10))]:
            x = _parse_one(p)
            if x:
                candidates.append(x)

        if len(candidates) == 0:
            return {"success": False, "error": f"找到 POI 但 location 解析失败: {keywords}", "raw": data}

        return {
            "success": True,
            "poi": candidates[0],
            "candidates": candidates,
            "raw": data,  # ✅ 你 debug 时很有用；如果嫌大可删
        }

    def _parse_routes(self, data: Dict) -> List[Dict]:
        """解析高德API返回的路线数据"""
        routes = []
        
        for idx, path in enumerate(data.get("route", {}).get("paths", [])):
            route = {
                "routeId": f"route_{idx}",
                "name": "推荐路线" if idx == 0 else f"备选路线{idx}",
                "distance": int(path.get("distance", 0)),
                "duration": int(path.get("duration", 0)),
                "steps": [],
                "accessibilityScore": 85 - idx * 5  # 模拟无障碍评分
            }
            
            for step in path.get("steps", []):
                route["steps"].append({
                    "instruction": step.get("instruction", ""),
                    "distance": int(step.get("distance", 0)),
                    "duration": int(step.get("duration", 0))
                })
            
            routes.append(route)
        
        return routes
    
    def _mock_routes(
        self,
        origin: Dict,
        destination: Dict
    ) -> List[Dict]:
        """模拟路线数据"""
        # 简单计算直线距离
        distance = int(self._haversine_distance(
            origin["lat"], origin["lng"],
            destination["lat"], destination["lng"]
        ))
        
        return [
            {
                "routeId": "route_0",
                "name": "推荐路线（无障碍优先）",
                "distance": distance,
                "duration": distance // 1.2,  # 假设步行速度1.2m/s
                "steps": [
                    {
                        "instruction": "向北直行200米",
                        "distance": 200,
                        "duration": 167
                    },
                    {
                        "instruction": "右转进入中山路",
                        "distance": distance - 400,
                        "duration": (distance - 400) // 1.2
                    },
                    {
                        "instruction": "到达目的地",
                        "distance": 200,
                        "duration": 167
                    }
                ],
                "accessibilityScore": 90
            },
            {
                "routeId": "route_1",
                "name": "最短路线",
                "distance": int(distance * 0.85),
                "duration": int(distance * 0.85 // 1.2),
                "steps": [
                    {
                        "instruction": "向北直行至目的地",
                        "distance": int(distance * 0.85),
                        "duration": int(distance * 0.85 // 1.2)
                    }
                ],
                "accessibilityScore": 75
            }
        ]
    
    @staticmethod
    def _haversine_distance(
        lat1: float, lng1: float,
        lat2: float, lng2: float
    ) -> float:
        """Haversine公式计算两点距离（米）"""
        R = 6371000  # 地球半径（米）
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def check_deviation(
        self,
        current_location: Dict,
        route_points: List[Dict],
        threshold: int = None
    ) -> Dict:
        """
        检查是否偏离路线
        
        Returns:
            {
                "deviated": bool,
                "distance": float,  # 偏离距离（米）
                "nearest_point": {...}
            }
        """
        threshold = threshold or settings.NAV_DEVIATION_THRESHOLD
        
        # 找最近的路径点
        min_distance = float('inf')
        nearest_point = None
        
        for point in route_points:
            dist = self._haversine_distance(
                current_location["lat"], current_location["lng"],
                point["lat"], point["lng"]
            )
            if dist < min_distance:
                min_distance = dist
                nearest_point = point
        
        return {
            "deviated": min_distance > threshold,
            "distance": min_distance,
            "nearest_point": nearest_point
        }

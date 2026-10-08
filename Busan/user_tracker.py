"""
用户行为追踪模块 / User Behavior Tracker / 사용자 행동 추적 모듈
功能：记录查询历史、统计分类频次、检测重复查询、预测用户意图
"""

import time
from datetime import datetime
from collections import defaultdict

class UserTracker:
    """用户行为追踪器 / User Behavior Tracker / 사용자 행동 추적기"""
    
    def __init__(self):
        self.session_start = datetime.now()
        self.query_history = []          # 查询历史列表 / Query history / 조회 이력
        self.category_counts = defaultdict(int)   # 大类查询次数 / Category counts / 대분류 조회 횟수
        self.subcategory_counts = defaultdict(int) # 子类查询次数 / Subcategory counts / 소분류 조회 횟수
        self.keyword_counts = defaultdict(int)     # 关键词查询次数 / Keyword counts / 키워드 조회 횟수
        self.query_timestamps = []       # 查询时间戳 / Query timestamps / 조회 시간 기록
        self.total_queries = 0          # 总查询次数 / Total queries / 총 조회 횟수
        
    def record_query(self, text, category="", subcategory="", keywords=None):
        """
        记录一次用户查询 / Record a user query / 사용자 조회 기록
        
        Args:
            text (str): 用户输入文本 / User input / 사용자 입력
            category (str): 检测到的主分类 / Detected main category / 감지된 대분류
            subcategory (str): 检测到的子分类 / Detected subcategory / 감지된 소분류
            keywords (list): 提取的关键词 / Extracted keywords / 추출된 키워드
        """
        self.total_queries += 1
        timestamp = datetime.now()
        self.query_timestamps.append(timestamp)
        
        # 记录查询历史 / Record query history / 조회 이력 기록
        self.query_history.append({
            "text": text,
            "category": category,
            "subcategory": subcategory,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 统计分类频次 / Count category frequency / 분류별 빈도 계산
        if category:
            self.category_counts[category] += 1
        if subcategory:
            self.subcategory_counts[subcategory] += 1
        
        # 统计关键词 / Count keywords / 키워드 통계
        if keywords:
            for kw in keywords:
                self.keyword_counts[kw] += 1
        else:
            # 如果没有传入关键词，用简单的分词逻辑提取
            self._extract_keywords(text)
    
    def _extract_keywords(self, text):
        """简单关键词提取 / Simple keyword extraction / 간단한 키워드 추출"""
        # 常见釜山相关关键词 / Common Busan keywords / 부산 관련 공통 키워드
        known_keywords = [
            "釜山银行", "友利银行", "沙下区厅", "海关总署", "甘川文化村",
            "多大浦海水浴场", "洛东江河口生态中心", "乙淑岛", "海云台",
            "부산은행", "감천문화마을", "다대포", "Busan Bank", "Busan"
        ]
        for kw in known_keywords:
            if kw.lower() in text.lower():
                self.keyword_counts[kw] += 1
    
    def get_frequent_items(self, threshold=3):
        """
        获取查询超过阈值的项目 / Get items queried above threshold / 임계값 이상 조회된 항목 반환
        
        Returns:
            dict: {"categories": [...], "subcategories": [...], "keywords": [...]}
        """
        result = {
            "categories": [],
            "subcategories": [],
            "keywords": []
        }
        
        for cat, count in self.category_counts.items():
            if count >= threshold:
                result["categories"].append({"name": cat, "count": count})
        
        for sub, count in self.subcategory_counts.items():
            if count >= threshold:
                result["subcategories"].append({"name": sub, "count": count})
        
        for kw, count in self.keyword_counts.items():
            if count >= threshold:
                result["keywords"].append({"name": kw, "count": count})
        
        return result
    
    def predict_intent(self):
        """
        预测用户意图 / Predict user intent / 사용자 의도 예측
        
        Returns:
            dict: {"intent": 意图名称, "confidence": 置信度, "reason": 原因说明}
        """
        # 统计各大类占比 / Calculate category proportions / 대분류 비율 계산
        total_cat = sum(self.category_counts.values())
        if total_cat == 0:
            return {
                "intent": "unknown / 알 수 없음 / 未知",
                "confidence": 0.0,
                "reason": "数据不足 / Insufficient data / 데이터 부족"
            }
        
        # 计算各类别比例 / Calculate proportions / 비율 계산
        ratios = {}
        for cat, count in self.category_counts.items():
            ratios[cat] = count / total_cat
        
        # 意图判断逻辑 / Intent judgment logic / 의도 판단 로직
        bank_ratio = ratios.get("银行 / Bank / 은행", 0)
        gov_ratio = ratios.get("政府机关 / Government / 정부 기관", 0)
        tour_ratio = ratios.get("文旅设施 / Tourism / 관광 시설", 0)
        
        # 规则1：景点+银行 → 旅游模式
        if tour_ratio >= 0.3 and bank_ratio >= 0.2:
            return {
                "intent": "旅游规划 / Travel Planning / 여행 계획",
                "confidence": min(tour_ratio + bank_ratio, 1.0),
                "reason": "您查询了景点和银行，推测您正在规划釜山旅行。 / You searched attractions and banks, suggesting travel planning. / 명소와 은행을 조회하여 여행을 계획 중인 것으로 추정됩니다."
            }
        
        # 规则2：政府机关+银行 → 居留/生活模式
        if gov_ratio >= 0.3 and bank_ratio >= 0.2:
            return {
                "intent": "居留生活 / Residence & Living / 거주 및 생활",
                "confidence": min(gov_ratio + bank_ratio, 1.0),
                "reason": "您查询了政府机关和银行，推测您可能在办理居留或生活手续。 / Government + bank queries suggest residence procedures. / 정부 기관과 은행을 조회하여 거주/생활 절차를 밟는 것으로 추정됩니다."
            }
        
        # 规则3：纯银行高频 → 金融需求
        if bank_ratio >= 0.6:
            return {
                "intent": "金融服务 / Financial Services / 금융 서비스",
                "confidence": bank_ratio,
                "reason": "您主要查询银行信息，推测有金融相关业务需求。 / Primarily bank queries suggest financial needs. / 주로 은행을 조회하여 금융 관련 업무가 필요한 것으로 추정됩니다."
            }
        
        # 规则4：纯景点高频 → 观光模式
        if tour_ratio >= 0.6:
            return {
                "intent": "观光游览 / Sightseeing / 관광",
                "confidence": tour_ratio,
                "reason": "您主要查询文旅设施，推测您是来釜山观光的游客。 / Primarily tourism queries suggest you are a visitor. / 주로 관광 시설을 조회하여 부산을 방문한 관광객으로 추정됩니다."
            }
        
        # 规则5：政府机关高频 → 公务模式
        if gov_ratio >= 0.5:
            return {
                "intent": "公务办理 / Official Business / 공무 처리",
                "confidence": gov_ratio,
                "reason": "您主要查询政府机关，推测您需要办理行政手续。 / Primarily government queries suggest administrative needs. / 주로 정부 기관을 조회하여 행정 절차가 필요한 것으로 추정됩니다."
            }
        
        return {
            "intent": "综合探索 / General Exploration / 종합 탐색",
            "confidence": 0.3,
            "reason": "您的查询分布较均匀，推测在进行综合信息探索。 / Even query distribution suggests general exploration. / 조회가 고르게 분포되어 종합적인 정보 탐색 중인 것으로 추정됩니다."
        }
    
    def get_session_summary(self):
        """
        获取会话摘要 / Get session summary / 세션 요약 반환
        
        Returns:
            dict: 会话统计信息 / Session statistics / 세션 통계 정보
        """
        duration = (datetime.now() - self.session_start).seconds
        minutes = duration // 60
        seconds = duration % 60
        
        return {
            "total_queries": self.total_queries,
            "duration": f"{minutes}分{seconds}秒 / {minutes}m{seconds}s / {minutes}분{seconds}초",
            "top_category": max(self.category_counts.items(), key=lambda x: x[1])[0] if self.category_counts else "无 / None / 없음",
            "top_keyword": max(self.keyword_counts.items(), key=lambda x: x[1])[0] if self.keyword_counts else "无 / None / 없음"
        }
    
    def get_deep_recommendations(self, lang_code='zh'):
        """
        基于查询历史生成深度推荐 / Generate deep recommendations based on history / 조회 이력을 바탕으로 심층 추천 생성
        
        Args:
            lang_code (str): 语言代码 / Language code / 언어 코드
        
        Returns:
            list: 推荐列表 / Recommendation list / 추천 목록
        """
        frequent = self.get_frequent_items(threshold=2)
        recommendations = []
        
        if lang_code == 'zh':
            if frequent["keywords"]:
                for item in frequent["keywords"][:3]:
                    recommendations.append(f"🔁 您已查询「{item['name']}」{item['count']}次，为您展开相关内容：")
                    # 基于关键词的扩展推荐
                    if "银行" in item['name'] or "Bank" in item['name']:
                        recommendations.append("   → 推荐：友利银行沙下区网点、BNK釜山银行总行")
                    elif "甘川" in item['name'] or "감천" in item['name']:
                        recommendations.append("   → 推荐：甘川文化村最佳游览路线、附近多大浦海水浴场")
                    elif "多大浦" in item['name'] or "다대포" in item['name']:
                        recommendations.append("   → 推荐：多大浦夕阳观赏点、附近洛东江河口生态中心")
                    elif "政府" in item['name'] or "厅" in item['name']:
                        recommendations.append("   → 推荐：沙下区厅办公时间、海关总署通关指南")
                    else:
                        recommendations.append(f"   → 推荐：查看 rules.txt 中更多关于「{item['name']}」的信息")
            
            if frequent["categories"]:
                for item in frequent["categories"][:2]:
                    cat_name = item['name'].split(" / ")[0]
                    recommendations.append(f"📂 您在「{cat_name}」类别查询了{item['count']}次，为您推荐同类其他设施：")
                    if "银行" in item['name']:
                        recommendations.append("   → 推荐：友利银行、新韩银行、国民银行沙下区网点")
                    elif "政府" in item['name']:
                        recommendations.append("   → 推荐：沙下区厅、海关总署、釜山出入境管理事务所")
                    elif "文旅" in item['name']:
                        recommendations.append("   → 推荐：海云台海水浴场、广安里、太宗台")
        
        elif lang_code == 'ko':
            if frequent["keywords"]:
                for item in frequent["keywords"][:3]:
                    recommendations.append(f"🔁 「{item['name']}」을(를) {item['count']}회 조회하셨습니다. 관련 내용을 더 보여드립니다:")
                    if "은행" in item['name'] or "Bank" in item['name']:
                        recommendations.append("   → 추천: 우리은행 사하구 지점, BNK부산은행 본점")
                    elif "감천" in item['name']:
                        recommendations.append("   → 추천: 감천문화마을 베스트 코스, 근처 다대포해수욕장")
                    elif "다대포" in item['name']:
                        recommendations.append("   → 추천: 다대포 일몰 명소, 낙동강하구생태센터")
                    else:
                        recommendations.append(f"   → 추천: 「{item['name']}」 관련 rules.txt의 추가 정보")
            
            if frequent["categories"]:
                for item in frequent["categories"][:2]:
                    recommendations.append(f"📂 「{item['name'].split(' / ')[0]}」 카테고리를 {item['count']}회 조회하셨습니다:")
                    if "은행" in item['name'] or "Bank" in item['name']:
                        recommendations.append("   → 추천: 우리은행, 신한은행, 국민은행 사하구 지점")
                    elif "정부" in item['name'] or "기관" in item['name']:
                        recommendations.append("   → 추천: 사하구청, 세관, 부산출입국관리사무소")
                    elif "관광" in item['name'] or "문화" in item['name']:
                        recommendations.append("   → 추천: 해운대해수욕장, 광안리, 태종대")
        
        else:  # English
            if frequent["keywords"]:
                for item in frequent["keywords"][:3]:
                    recommendations.append(f"🔁 You've searched 「{item['name']}」 {item['count']} times. Here's more:")
                    if "Bank" in item['name'] or "bank" in item['name']:
                        recommendations.append("   → Recommended: Woori Bank Saha-gu Branch, BNK Busan Bank HQ")
                    elif "Gamcheon" in item['name'] or "감천" in item['name']:
                        recommendations.append("   → Recommended: Gamcheon Culture Village best route, nearby Dadaepo Beach")
                    elif "Dadaepo" in item['name'] or "다대포" in item['name']:
                        recommendations.append("   → Recommended: Dadaepo sunset spots, nearby Nakdonggang Estuary Eco Center")
                    else:
                        recommendations.append(f"   → Recommended: Check rules.txt for more on 「{item['name']}」")
            
            if frequent["categories"]:
                for item in frequent["categories"][:2]:
                    recommendations.append(f"📂 You've searched 「{item['name'].split(' / ')[0]}」 {item['count']} times. Related:")
                    if "Bank" in item['name']:
                        recommendations.append("   → Recommended: Woori Bank, Shinhan Bank, Kookmin Bank Saha-gu branches")
                    elif "Government" in item['name']:
                        recommendations.append("   → Recommended: Saha-gu Office, Customs, Busan Immigration Office")
                    elif "Tourism" in item['name']:
                        recommendations.append("   → Recommended: Haeundae Beach, Gwangalli, Taejongdae")
        
        return recommendations


# 全局追踪器实例 / Global tracker instance / 전역 추적기 인스턴스
_tracker = None

def get_tracker():
    """获取全局追踪器 / Get global tracker / 전역 추적기 가져오기"""
    global _tracker
    if _tracker is None:
        _tracker = UserTracker()
    return _tracker

def reset_tracker():
    """重置追踪器 / Reset tracker / 추적기 초기화"""
    global _tracker
    _tracker = UserTracker()
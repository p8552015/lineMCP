"""
製造業詞彙庫智能解譯系統
支援 LLM 自動解譯和多欄位資料提取
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# 假設的 AI 服務導入
# from ...services.ai_model_service_enhanced import get_ai_model_service

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFields:
    """提取的多欄位資料"""

    machine_id: str | None = None
    metric_type: str | None = None
    time_period: str | None = None
    department: str | None = None
    operator_id: str | None = None
    shift_type: str | None = None
    production_line: str | None = None
    product_type: str | None = None
    quality_level: str | None = None
    raw_confidence: float = 0.0
    field_confidence: dict[str, float] = field(default_factory=dict)
    extraction_method: str = "unknown"
    reasoning: str | None = None


@dataclass
class VocabularyEntry:
    """詞彙條目資料模型"""

    term_id: str
    primary_term: str
    synonyms: list[str]
    term_type: str
    extraction_patterns: list[str]
    field_mappings: dict[str, Any]
    confidence_weight: float
    usage_frequency: int = 0
    last_updated: datetime | None = None


@dataclass
class InterpretationResult:
    """解譯結果"""

    extracted_fields: ExtractedFields
    confidence: float
    interpretation_method: str
    fallback_available: bool
    processing_time_ms: float
    error_message: str | None = None


class VocabularyDatabase:
    """詞彙庫資料庫管理器"""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.vocabulary_data: dict[str, Any] = {}
        self.entries_by_type: dict[str, list[VocabularyEntry]] = {}
        self.load_vocabulary_database()

    def load_vocabulary_database(self) -> None:
        """載入詞彙庫資料"""
        try:
            with open(self.config_path, encoding="utf-8") as file:
                self.vocabulary_data = yaml.safe_load(file)

            self._build_vocabulary_index()
            logger.info(f"成功載入詞彙庫，共 {len(self.get_all_entries())} 個詞彙條目")

        except Exception as e:
            logger.error(f"載入詞彙庫失敗：{e}")
            self.vocabulary_data = {}

    def _build_vocabulary_index(self) -> None:
        """建立詞彙索引"""
        self.entries_by_type = {}

        vocab_db = self.vocabulary_data.get("vocabulary_database", {})

        for category, category_data in vocab_db.items():
            if category in ["version", "last_updated", "total_entries"]:
                continue

            for subcategory, entries in category_data.items():
                if not isinstance(entries, list):
                    continue

                for entry_data in entries:
                    if isinstance(entry_data, dict) and "term" in entry_data:
                        entry = VocabularyEntry(
                            term_id=f"{category}_{subcategory}_{entry_data['term']}",
                            primary_term=entry_data["term"],
                            synonyms=entry_data.get("synonyms", []),
                            term_type=entry_data.get("type", subcategory),
                            extraction_patterns=entry_data.get(
                                "extraction_patterns", []
                            ),
                            field_mappings=entry_data.get("field_mappings", {}),
                            confidence_weight=entry_data.get("confidence_weight", 0.5),
                        )

                        if entry.term_type not in self.entries_by_type:
                            self.entries_by_type[entry.term_type] = []
                        self.entries_by_type[entry.term_type].append(entry)

    def get_all_entries(self) -> list[VocabularyEntry]:
        """獲取所有詞彙條目"""
        all_entries = []
        for entries in self.entries_by_type.values():
            all_entries.extend(entries)
        return all_entries

    def get_entries_by_type(self, term_type: str) -> list[VocabularyEntry]:
        """根據類型獲取詞彙條目"""
        return self.entries_by_type.get(term_type, [])

    def get_high_frequency_terms(self, limit: int = 50) -> list[VocabularyEntry]:
        """獲取高頻詞彙（用於 LLM 上下文）"""
        all_entries = self.get_all_entries()
        # 按信心度權重排序
        sorted_entries = sorted(
            all_entries, key=lambda x: x.confidence_weight, reverse=True
        )
        return sorted_entries[:limit]


class PatternMatcher:
    """模式匹配器"""

    def __init__(self, vocabulary_db: VocabularyDatabase):
        self.vocabulary_db = vocabulary_db
        self.compiled_patterns: dict[str, list[tuple[re.Pattern, VocabularyEntry]]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """編譯所有正則表達式模式"""
        for term_type, entries in self.vocabulary_db.entries_by_type.items():
            self.compiled_patterns[term_type] = []

            for entry in entries:
                for pattern_str in entry.extraction_patterns:
                    try:
                        compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
                        self.compiled_patterns[term_type].append(
                            (compiled_pattern, entry)
                        )
                    except re.error as e:
                        logger.warning(f"編譯模式失敗：{pattern_str}，錯誤：{e}")

    def match_patterns(
        self, text: str
    ) -> list[tuple[VocabularyEntry, re.Match, float]]:
        """匹配文字中的模式"""
        matches = []

        for _term_type, pattern_entries in self.compiled_patterns.items():
            for pattern, entry in pattern_entries:
                for match in pattern.finditer(text):
                    confidence = self._calculate_pattern_confidence(match, entry, text)
                    matches.append((entry, match, confidence))

        # 按信心度排序
        matches.sort(key=lambda x: x[2], reverse=True)
        return matches

    def _calculate_pattern_confidence(
        self, match: re.Match, entry: VocabularyEntry, full_text: str
    ) -> float:
        """計算模式匹配信心度"""
        base_confidence = entry.confidence_weight

        # 完全匹配加分
        if match.group().lower() == entry.primary_term.lower():
            base_confidence += 0.1

        # 同義詞匹配
        for synonym in entry.synonyms:
            if synonym.lower() in match.group().lower():
                base_confidence += 0.05
                break

        # 上下文相關性（簡化版）
        context_before = full_text[max(0, match.start() - 10) : match.start()]
        context_after = full_text[match.end() : match.end() + 10]

        if any(
            keyword in context_before + context_after
            for keyword in ["機台", "設備", "指標", "部門"]
        ):
            base_confidence += 0.05

        return min(base_confidence, 1.0)


class MultiFieldExtractor:
    """多欄位資料提取引擎"""

    def __init__(
        self, vocabulary_db: VocabularyDatabase, pattern_matcher: PatternMatcher
    ):
        self.vocabulary_db = vocabulary_db
        self.pattern_matcher = pattern_matcher

    def extract_fields(self, text: str) -> ExtractedFields:
        """從文字中提取多個結構化欄位"""
        start_time = datetime.now()

        # 1. 模式匹配
        matches = self.pattern_matcher.match_patterns(text)

        # 2. 欄位提取
        extracted_fields = ExtractedFields()
        field_confidences: dict[str, float] = {}

        for entry, _match, confidence in matches:
            # 根據詞彙條目的欄位映射更新結果
            for field_name, field_value in entry.field_mappings.items():
                if hasattr(extracted_fields, field_name):
                    current_confidence = field_confidences.get(field_name, 0.0)
                    if confidence > current_confidence:
                        setattr(extracted_fields, field_name, field_value)
                        field_confidences[field_name] = confidence

        # 3. 計算整體信心度
        if field_confidences:
            extracted_fields.raw_confidence = sum(field_confidences.values()) / len(
                field_confidences
            )
            extracted_fields.field_confidence = field_confidences

        extracted_fields.extraction_method = "pattern_matching"

        _ = (datetime.now() - start_time).total_seconds() * 1000

        return extracted_fields

    def validate_extracted_fields(self, fields: ExtractedFields) -> bool:
        """驗證提取欄位的完整性"""
        # 基本驗證邏輯
        essential_fields = ["machine_id", "metric_type"]

        for field_name in essential_fields:
            if getattr(fields, field_name) is None:
                return False

        # 信心度閾值
        return not fields.raw_confidence < 0.6


class LLMInterpretationEngine:
    """LLM 驅動的詞彙解譯引擎"""

    def __init__(self, vocabulary_db: VocabularyDatabase):
        self.vocabulary_db = vocabulary_db
        # self.llm_client = get_ai_model_service()  # 實際使用時取消註解
        self.llm_client = None  # 暫時設為 None

    async def interpret_with_llm(self, user_input: str) -> InterpretationResult:
        """使用 LLM 進行智能解譯"""
        start_time = datetime.now()

        try:
            # 1. 構建提示詞
            prompt = self._build_interpretation_prompt(user_input)

            # 2. LLM 推理（模擬回應）
            if self.llm_client:
                llm_response = await self.llm_client.generate_response(prompt)
            else:
                # 模擬 LLM 回應
                llm_response = self._simulate_llm_response(user_input)

            # 3. 解析回應
            structured_result = self._parse_llm_response(llm_response)

            # 4. 置信度評估
            confidence_score = self._calculate_confidence(structured_result, user_input)

            _ = (datetime.now() - start_time).total_seconds() * 1000

            return InterpretationResult(
                extracted_fields=structured_result,
                confidence=confidence_score,
                interpretation_method="llm_enhanced",
                fallback_available=True,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )

        except Exception as e:
            logger.error(f"LLM 解譯失敗：{e}")
            _ = (datetime.now() - start_time).total_seconds() * 1000

            return InterpretationResult(
                extracted_fields=ExtractedFields(),
                confidence=0.0,
                interpretation_method="llm_failed",
                fallback_available=True,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_message=str(e),
            )

    def _build_interpretation_prompt(self, user_input: str) -> str:
        """構建 LLM 解譯提示詞"""
        vocabulary_context = self._get_vocabulary_context()

        return f"""
你是製造業智能查詢系統的專業解譯器。請分析以下使用者查詢並提取結構化資料：

查詢內容："{user_input}"

請按照以下 JSON 格式返回解譯結果：
{{
    "machine_id": "提取的機台編號（如 M001、Line-A 等）",
    "metric_type": "指標類型（如 utilization_rate、defect_rate 等）",
    "time_period": "時間範圍（如 real_time、today、this_week 等）",
    "department": "部門名稱（如 production、quality 等）",
    "confidence": "解譯信心度（0.0-1.0）",
    "reasoning": "解譯推理過程說明"
}}

已知詞彙參考：
{vocabulary_context}

請確保：
1. 機台編號必須符合命名規範（字母+數字組合）
2. 指標類型使用標準術語
3. 時間範圍使用系統認可的格式
4. 信心度基於詞彙匹配度和語義清晰度
"""

    def _get_vocabulary_context(self) -> str:
        """獲取詞彙庫上下文資訊"""
        high_freq_entries = self.vocabulary_db.get_high_frequency_terms(limit=30)
        context_lines = []

        for entry in high_freq_entries:
            synonyms_str = ", ".join(entry.synonyms[:3])  # 只顯示前3個同義詞
            context_lines.append(f"- {entry.primary_term}: {synonyms_str}")

        return "\n".join(context_lines)

    def _simulate_llm_response(self, user_input: str) -> str:
        """
        模擬 LLM 回應（用於測試）
        🔥 增強版：支援複雜查詢解析
        """
        user_input_lower = user_input.lower()

        # 初始化回應
        response: dict[str, str | float | None] = {
            "machine_id": None,
            "metric_type": None,
            "time_period": None,
            "department": None,
            "confidence": 0.0,
            "reasoning": "",
        }

        reasoning_parts = []

        # 🔥 機台識別增強
        machine_patterns = {
            "m001": "M001",
            "m002": "M002",
            "m003": "M003",
            "m004": "M004",
            "m005": "M005",
            "cnc車床": "M001",  # CNC車床A
            "包裝機": "M002",  # 包裝機1號
            "焊接機": "M003",  # 焊接機3號
            "切割機": "M004",  # 切割機B
            "組裝線": "M005",  # 組裝線C
            "車床": "M001",
            "銑床": "M002",
        }

        for pattern, machine_id in machine_patterns.items():
            if pattern in user_input_lower:
                response["machine_id"] = machine_id
                current_confidence = response.get("confidence") or 0.0
                response["confidence"] = float(current_confidence) + 0.4
                reasoning_parts.append(f"識別機台: {pattern} -> {machine_id}")
                break

        # 🔥 指標類型識別增強
        metric_patterns = {
            "稼動率": "utilization_rate",
            "效率": "efficiency",
            "不良率": "defect_rate",
            "產量": "production_count",
            "故障": "failure_count",
            "oee": "oee",
            "良品": "good_count",
            "維護": "maintenance_status",
            "停機": "downtime",
        }

        for pattern, metric_type in metric_patterns.items():
            if pattern in user_input_lower:
                response["metric_type"] = metric_type
                current_confidence = response.get("confidence") or 0.0
                response["confidence"] = float(current_confidence) + 0.3
                reasoning_parts.append(f"識別指標: {pattern} -> {metric_type}")
                break

        # 🔥 時間範圍識別增強
        time_patterns = {
            "今天": "today",
            "今日": "today",
            "現在": "real_time",
            "即時": "real_time",
            "本週": "this_week",
            "本月": "this_month",
            "近期": "recent",
            "當前": "current",
        }

        for pattern, time_period in time_patterns.items():
            if pattern in user_input_lower:
                response["time_period"] = time_period
                current_confidence = response.get("confidence") or 0.0
                response["confidence"] = float(current_confidence) + 0.3
                reasoning_parts.append(f"識別時間: {pattern} -> {time_period}")
                break

        # 🔥 部門識別增強
        department_patterns = {
            "生產": "production",
            "加工": "machining",
            "品質": "quality",
            "製造": "manufacturing",
            "工廠": "factory",
            "車間": "workshop",
        }

        for pattern, department in department_patterns.items():
            if pattern in user_input_lower:
                response["department"] = department
                current_confidence = response.get("confidence") or 0.0
                response["confidence"] = float(current_confidence) + 0.3
                reasoning_parts.append(f"識別部門: {pattern} -> {department}")
                break

        # 🔥 複合查詢加分機制
        if response.get("machine_id") and response.get("metric_type"):
            current_confidence = response.get("confidence") or 0.0
            response["confidence"] = float(current_confidence) + 0.2
            reasoning_parts.append("複合查詢加分: 機台+指標")

        if response.get("time_period"):
            current_confidence = response.get("confidence") or 0.0
            response["confidence"] = float(current_confidence) + 0.1
            reasoning_parts.append("時間範圍加分")

        # 確保信心度不超過 1.0
        current_confidence = response.get("confidence") or 0.0
        response["confidence"] = min(float(current_confidence), 1.0)

        # 組合推理說明
        if reasoning_parts:
            response["reasoning"] = f"從查詢 '{user_input}' 解析: " + "; ".join(
                reasoning_parts
            )
        else:
            response["reasoning"] = (
                f"無法從查詢 '{user_input}' 中識別出明確的製造業詞彙"
            )

        return json.dumps(response, ensure_ascii=False, indent=2)

    def _parse_llm_response(self, llm_response: str) -> ExtractedFields:
        """解析 LLM 回應"""
        try:
            response_data = json.loads(llm_response)

            fields = ExtractedFields()
            fields.machine_id = response_data.get("machine_id")
            fields.metric_type = response_data.get("metric_type")
            fields.time_period = response_data.get("time_period")
            fields.department = response_data.get("department")
            fields.raw_confidence = response_data.get("confidence", 0.0)
            fields.reasoning = response_data.get("reasoning")
            fields.extraction_method = "llm_interpretation"

            return fields

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"解析 LLM 回應失敗：{e}")
            return ExtractedFields()

    def _calculate_confidence(
        self, fields: ExtractedFields, original_text: str
    ) -> float:
        """計算解譯信心度"""
        base_confidence = fields.raw_confidence

        # 欄位完整性加分
        filled_fields = sum(
            1
            for field_name in ["machine_id", "metric_type", "time_period", "department"]
            if getattr(fields, field_name) is not None
        )
        completeness_bonus = (filled_fields / 4) * 0.2

        # 詞彙庫匹配度驗證
        vocabulary_match_bonus = self._validate_against_vocabulary(fields)

        final_confidence = min(
            base_confidence + completeness_bonus + vocabulary_match_bonus, 1.0
        )
        return final_confidence

    def _validate_against_vocabulary(self, fields: ExtractedFields) -> float:
        """驗證解譯結果與詞彙庫的匹配度"""
        bonus = 0.0

        # 檢查機台編號格式
        if fields.machine_id and re.match(r"^M\d{3}$", fields.machine_id):
            bonus += 0.1

        # 檢查指標類型是否在詞彙庫中
        metric_entries = self.vocabulary_db.get_entries_by_type("metric_type")
        if fields.metric_type:
            for entry in metric_entries:
                if fields.metric_type in entry.field_mappings.get("metric_type", ""):
                    bonus += 0.1
                    break

        return bonus


class IntelligentVocabularyInterpreter:
    """製造業詞彙庫智能解譯器（主要介面）"""

    def __init__(self, config_path: str):
        self.vocabulary_db = VocabularyDatabase(config_path)
        self.pattern_matcher = PatternMatcher(self.vocabulary_db)
        self.field_extractor = MultiFieldExtractor(
            self.vocabulary_db, self.pattern_matcher
        )
        self.llm_engine = LLMInterpretationEngine(self.vocabulary_db)

    async def interpret_query(
        self, user_input: str, use_llm: bool = True
    ) -> InterpretationResult:
        """解譯使用者查詢的主要介面"""
        start_time = datetime.now()

        try:
            # 1. 首先嘗試模式匹配
            pattern_fields = self.field_extractor.extract_fields(user_input)

            # 2. 如果模式匹配結果不夠好，使用 LLM 增強
            if use_llm and (pattern_fields.raw_confidence < 0.8):
                llm_result = await self.llm_engine.interpret_with_llm(user_input)

                # 3. 融合結果
                final_fields = self._merge_interpretation_results(
                    pattern_fields, llm_result.extracted_fields
                )
                final_confidence = max(
                    pattern_fields.raw_confidence, llm_result.confidence
                )
                method = "hybrid_pattern_llm"
            else:
                final_fields = pattern_fields
                final_confidence = pattern_fields.raw_confidence
                method = "pattern_matching_only"

            _ = (datetime.now() - start_time).total_seconds() * 1000

            return InterpretationResult(
                extracted_fields=final_fields,
                confidence=final_confidence,
                interpretation_method=method,
                fallback_available=True,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )

        except Exception as e:
            logger.error(f"解譯過程發生錯誤：{e}")
            _ = (datetime.now() - start_time).total_seconds() * 1000

            return InterpretationResult(
                extracted_fields=ExtractedFields(),
                confidence=0.0,
                interpretation_method="error",
                fallback_available=False,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_message=str(e),
            )

    def _merge_interpretation_results(
        self, pattern_result: ExtractedFields, llm_result: ExtractedFields
    ) -> ExtractedFields:
        """融合模式匹配和 LLM 的結果"""
        merged = ExtractedFields()

        # 選擇信心度更高的結果
        fields_to_merge = [
            "machine_id",
            "metric_type",
            "time_period",
            "department",
            "operator_id",
            "shift_type",
        ]

        for field_name in fields_to_merge:
            pattern_value = getattr(pattern_result, field_name)
            llm_value = getattr(llm_result, field_name)
            pattern_conf = pattern_result.field_confidence.get(field_name, 0.0)
            llm_conf = llm_result.field_confidence.get(field_name, 0.0)

            if pattern_value and llm_value:
                # 兩者都有值，選擇信心度更高的
                if pattern_conf >= llm_conf:
                    setattr(merged, field_name, pattern_value)
                    merged.field_confidence[field_name] = pattern_conf
                else:
                    setattr(merged, field_name, llm_value)
                    merged.field_confidence[field_name] = llm_conf
            elif pattern_value:
                setattr(merged, field_name, pattern_value)
                merged.field_confidence[field_name] = pattern_conf
            elif llm_value:
                setattr(merged, field_name, llm_value)
                merged.field_confidence[field_name] = llm_conf

        # 計算融合後的整體信心度
        if merged.field_confidence:
            merged.raw_confidence = sum(merged.field_confidence.values()) / len(
                merged.field_confidence
            )

        merged.extraction_method = "hybrid_fusion"
        merged.reasoning = f"融合了模式匹配（信心度：{pattern_result.raw_confidence:.2f}）和 LLM 解譯（信心度：{llm_result.raw_confidence:.2f}）的結果"

        return merged

    def add_vocabulary_entry(self, entry: VocabularyEntry) -> bool:
        """動態新增詞彙條目"""
        try:
            if entry.term_type not in self.vocabulary_db.entries_by_type:
                self.vocabulary_db.entries_by_type[entry.term_type] = []

            self.vocabulary_db.entries_by_type[entry.term_type].append(entry)

            # 重新編譯模式
            self.pattern_matcher._compile_patterns()

            logger.info(f"成功新增詞彙條目：{entry.primary_term}")
            return True

        except Exception as e:
            logger.error(f"新增詞彙條目失敗：{e}")
            return False

    def get_interpretation_statistics(self) -> dict[str, Any]:
        """獲取解譯統計資訊"""
        total_entries = len(self.vocabulary_db.get_all_entries())
        entries_by_type = {
            k: len(v) for k, v in self.vocabulary_db.entries_by_type.items()
        }

        return {
            "total_vocabulary_entries": total_entries,
            "entries_by_type": entries_by_type,
            "pattern_count": sum(
                len(patterns)
                for patterns in self.pattern_matcher.compiled_patterns.values()
            ),
            "database_version": self.vocabulary_db.vocabulary_data.get(
                "vocabulary_database", {}
            ).get("version", "unknown"),
        }


# 使用範例
async def example_usage():
    """使用範例"""
    config_path = "manufacturing_vocabulary_database.yaml"
    interpreter = IntelligentVocabularyInterpreter(config_path)

    # 測試查詢
    test_queries = [
        "M001機台稼動率",
        "生產部門本週的OEE指標",
        "CNC車床今天不良率",
        "品質部門即時數據",
    ]

    for query in test_queries:
        print(f"\n查詢：{query}")
        result = await interpreter.interpret_query(query)

        print("解譯結果：")
        print(f"  機台編號：{result.extracted_fields.machine_id}")
        print(f"  指標類型：{result.extracted_fields.metric_type}")
        print(f"  時間範圍：{result.extracted_fields.time_period}")
        print(f"  部門：{result.extracted_fields.department}")
        print(f"  信心度：{result.confidence:.2f}")
        print(f"  解譯方法：{result.interpretation_method}")
        print(f"  處理時間：{result.processing_time_ms:.1f}ms")


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())

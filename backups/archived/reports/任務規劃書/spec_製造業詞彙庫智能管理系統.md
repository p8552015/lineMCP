# 製造業詞彙庫智能管理系統

## 🎯 系統目標

建立一個智能化的製造業詞彙庫管理系統，支援：
- **LLM 自動解譯**：智能識別和解析製造業專業術語
- **多欄位資料提取**：從單一訊息中提取多個資料欄位（如「M001機台稼動率」→ 機台編號、指標類型）
- **動態更新機制**：使用者可輕鬆收集和更新詞彙資料
- **語義擴展能力**：自動發現同義詞、近義詞和相關概念

## 📊 系統架構設計

### 核心組件

**1. 智能詞彙解析引擎**
```python
class ManufacturingVocabularyInterpreter:
    """製造業詞彙智能解譯引擎"""
    
    def interpret_query(self, user_input: str) -> Dict[str, Any]:
        """解譯使用者查詢並提取結構化資料"""
        return {
            "machine_id": "M001",      # 機台編號
            "metric_type": "utilization_rate",  # 指標類型
            "time_range": "current",   # 時間範圍
            "department": "production", # 部門
            "confidence": 0.95         # 解譯信心度
        }
    
    def expand_vocabulary(self, base_term: str) -> List[str]:
        """擴展詞彙的同義詞和相關詞"""
        
    def validate_interpretation(self, interpretation: Dict[str, Any]) -> bool:
        """驗證解譯結果的正確性"""
```

**2. 動態詞彙庫管理器**
```python
class DynamicVocabularyManager:
    """動態詞彙庫管理系統"""
    
    def add_vocabulary_entry(self, entry: VocabularyEntry) -> bool:
        """新增詞彙條目"""
        
    def update_vocabulary_entry(self, term_id: str, updates: Dict[str, Any]) -> bool:
        """更新現有詞彙條目"""
        
    def auto_discover_terms(self, user_queries: List[str]) -> List[VocabularyEntry]:
        """從使用者查詢中自動發現新詞彙"""
        
    def export_vocabulary_database(self) -> Dict[str, Any]:
        """匯出完整詞彙資料庫"""
```

**3. 多欄位資料提取器**
```python
class MultiFieldExtractor:
    """多欄位資料提取引擎"""
    
    def extract_fields(self, text: str) -> ExtractedFields:
        """從文字中提取多個結構化欄位"""
        
    def pattern_recognition(self, text: str) -> List[RecognizedPattern]:
        """識別文字中的資料模式"""
        
    def field_validation(self, fields: ExtractedFields) -> ValidationResult:
        """驗證提取欄位的完整性和正確性"""
```

## 📋 詞彙庫資料結構

### 基礎資料模型

```python
@dataclass
class VocabularyEntry:
    """詞彙條目資料模型"""
    term_id: str                    # 詞彙唯一識別碼
    primary_term: str               # 主要詞彙
    synonyms: List[str]             # 同義詞列表
    category: VocabularyCategory    # 詞彙分類
    data_fields: Dict[str, Any]     # 關聯的資料欄位
    extraction_patterns: List[str]  # 提取模式
    confidence_threshold: float     # 信心度閾值
    usage_frequency: int            # 使用頻率
    last_updated: datetime          # 最後更新時間
    validation_status: str          # 驗證狀態
    
@dataclass
class ExtractedFields:
    """提取的多欄位資料"""
    machine_id: Optional[str] = None        # 機台編號
    metric_type: Optional[str] = None       # 指標類型
    time_period: Optional[str] = None       # 時間範圍
    department: Optional[str] = None        # 部門
    operator_id: Optional[str] = None       # 操作員編號
    shift_type: Optional[str] = None        # 班次類型
    product_type: Optional[str] = None      # 產品類型
    quality_level: Optional[str] = None     # 品質等級
    raw_confidence: float = 0.0             # 原始信心度
    field_confidence: Dict[str, float] = field(default_factory=dict)  # 各欄位信心度
```

### 詞彙分類體系

```yaml
# 製造業詞彙分類 (manufacturing_vocabulary_categories.yaml)
categories:
  equipment:
    name: "設備機台"
    subcategories:
      - machine_id: "機台編號"
      - machine_type: "機台類型"
      - equipment_status: "設備狀態"
      
  metrics:
    name: "生產指標"
    subcategories:
      - utilization_rate: "稼動率"
      - oee: "整體設備效率"
      - defect_rate: "不良率"
      - throughput: "產量"
      
  time_dimensions:
    name: "時間維度"
    subcategories:
      - real_time: "即時"
      - hourly: "每小時"
      - daily: "每日"
      - weekly: "每週"
      - monthly: "每月"
      
  organizational:
    name: "組織結構"
    subcategories:
      - department: "部門"
      - shift: "班次"
      - operator: "操作員"
      - supervisor: "督導員"
```

## 🤖 LLM 自動解譯機制

### 智能解譯流程

```python
class LLMInterpretationEngine:
    """LLM 驅動的詞彙解譯引擎"""
    
    def __init__(self):
        self.llm_client = get_ai_model_service()
        self.vocabulary_db = load_vocabulary_database()
        self.extraction_patterns = load_extraction_patterns()
    
    async def interpret_with_llm(self, user_input: str) -> InterpretationResult:
        """使用 LLM 進行智能解譯"""
        
        # 1. 構建提示詞範本
        prompt = self._build_interpretation_prompt(user_input)
        
        # 2. LLM 推理
        llm_response = await self.llm_client.generate_response(prompt)
        
        # 3. 結構化解析
        structured_result = self._parse_llm_response(llm_response)
        
        # 4. 置信度評估
        confidence_score = self._calculate_confidence(structured_result, user_input)
        
        # 5. 後處理驗證
        validated_result = self._validate_and_enhance(structured_result)
        
        return InterpretationResult(
            extracted_fields=validated_result,
            confidence=confidence_score,
            interpretation_method="llm_enhanced",
            fallback_available=True
        )
    
    def _build_interpretation_prompt(self, user_input: str) -> str:
        """構建 LLM 解譯提示詞"""
        return f"""
你是製造業智能查詢系統的專業解譯器。請分析以下使用者查詢並提取結構化資料：

查詢內容："{user_input}"

請按照以下 JSON 格式返回解譯結果：
{{
    "machine_id": "提取的機台編號（如 M001、Line-A 等）",
    "metric_type": "指標類型（如 utilization_rate、defect_rate 等）",
    "time_period": "時間範圍（如 current、today、this_week 等）",
    "department": "部門名稱（如 production、quality 等）",
    "confidence": "解譯信心度（0.0-1.0）",
    "reasoning": "解譯推理過程說明"
}}

已知詞彙參考：
{self._get_vocabulary_context()}

請確保：
1. 機台編號必須符合命名規範（字母+數字組合）
2. 指標類型使用標準術語
3. 時間範圍使用系統認可的格式
4. 信心度基於詞彙匹配度和語義清晰度
"""
    
    def _get_vocabulary_context(self) -> str:
        """獲取詞彙庫上下文資訊"""
        context_entries = self.vocabulary_db.get_high_frequency_terms(limit=50)
        return "\n".join([f"- {entry.primary_term}: {entry.synonyms}" for entry in context_entries])
```

### 多欄位提取示例

**輸入範例**：
- "M001機台稼動率"
- "生產線A今天的不良率"
- "品質部門本週OEE指標"
- "二班操作員張三負責的設備狀況"

**輸出範例**：
```json
{
    "machine_id": "M001",
    "metric_type": "utilization_rate",
    "time_period": "current",
    "department": null,
    "operator_id": null,
    "confidence": 0.95,
    "extraction_method": "pattern_match + llm_validation"
}
```

## 📁 詞彙庫檔案結構

### 核心檔案組織

```
/manufacturing_vocabulary/
├── core/
│   ├── vocabulary_database.json          # 主詞彙資料庫
│   ├── extraction_patterns.yaml          # 提取模式定義
│   ├── synonym_mappings.json             # 同義詞映射表
│   └── field_validation_rules.yaml       # 欄位驗證規則
├── categories/
│   ├── equipment_terms.yaml              # 設備相關詞彙
│   ├── metrics_terms.yaml                # 指標相關詞彙
│   ├── time_terms.yaml                   # 時間相關詞彙
│   └── organizational_terms.yaml         # 組織相關詞彙
├── user_contributions/
│   ├── pending_additions.json            # 待審核新增詞彙
│   ├── user_feedback.json                # 使用者回饋
│   └── auto_discovered_terms.json        # 自動發現的詞彙
├── models/
│   ├── term_embeddings.bin               # 詞彙向量模型
│   ├── extraction_model.pkl              # 提取模型
│   └── confidence_classifier.joblib      # 信心度分類器
└── logs/
    ├── interpretation_logs.jsonl         # 解譯日誌
    ├── performance_metrics.json          # 效能指標
    └── error_analysis.json               # 錯誤分析
```

## 🔧 使用者更新機制

### 簡化的更新介面

```python
class UserVocabularyInterface:
    """使用者詞彙庫更新介面"""
    
    def add_new_term(self, term: str, category: str, examples: List[str]) -> bool:
        """新增新詞彙（使用者友善介面）"""
        entry = VocabularyEntry(
            term_id=generate_term_id(term),
            primary_term=term,
            category=VocabularyCategory[category],
            examples=examples,
            validation_status="pending_review"
        )
        return self.vocabulary_manager.add_vocabulary_entry(entry)
    
    def submit_correction(self, query: str, correct_interpretation: Dict[str, Any]) -> bool:
        """提交解譯修正"""
        correction = CorrectionEntry(
            original_query=query,
            correct_fields=correct_interpretation,
            submitted_by="user",
            timestamp=datetime.now()
        )
        return self.feedback_manager.add_correction(correction)
    
    def suggest_synonym(self, original_term: str, synonym: str) -> bool:
        """建議同義詞"""
        suggestion = SynonymSuggestion(
            original_term=original_term,
            suggested_synonym=synonym,
            submitted_by="user",
            status="pending_validation"
        )
        return self.vocabulary_manager.add_synonym_suggestion(suggestion)
```

### 批量資料匯入工具

```python
class VocabularyBatchImporter:
    """詞彙批量匯入工具"""
    
    def import_from_excel(self, file_path: str) -> ImportResult:
        """從 Excel 檔案批量匯入詞彙"""
        
    def import_from_csv(self, file_path: str, mapping: Dict[str, str]) -> ImportResult:
        """從 CSV 檔案批量匯入詞彙"""
        
    def validate_import_data(self, data: List[Dict[str, Any]]) -> ValidationReport:
        """驗證匯入資料的完整性"""
```

## 🧪 測試驗證計劃

### 解譯準確度測試

```python
class VocabularyInterpretationTests:
    """詞彙解譯測試套件"""
    
    def test_single_field_extraction(self):
        """測試單一欄位提取"""
        test_cases = [
            ("M001機台", {"machine_id": "M001"}),
            ("稼動率查詢", {"metric_type": "utilization_rate"}),
            ("今天的數據", {"time_period": "today"})
        ]
        
    def test_multi_field_extraction(self):
        """測試多欄位提取"""
        test_cases = [
            ("M001機台今天稼動率", {
                "machine_id": "M001",
                "metric_type": "utilization_rate", 
                "time_period": "today"
            }),
            ("生產部門本週OEE指標", {
                "department": "production",
                "metric_type": "oee",
                "time_period": "this_week"
            })
        ]
        
    def test_confidence_calculation(self):
        """測試信心度計算"""
        # 驗證信心度計算邏輯的準確性
        
    def test_fallback_mechanisms(self):
        """測試降級處理機制"""
        # 驗證當 LLM 解譯失敗時的降級處理
```

## 📊 效能監控指標

### 關鍵指標追蹤

```yaml
performance_metrics:
  accuracy:
    field_extraction_accuracy: "> 90%"     # 欄位提取準確率
    interpretation_accuracy: "> 85%"        # 整體解譯準確率
    confidence_calibration: "> 80%"         # 信心度校準度
    
  efficiency:
    average_processing_time: "< 500ms"      # 平均處理時間
    llm_response_time: "< 2s"               # LLM 回應時間
    cache_hit_rate: "> 70%"                 # 快取命中率
    
  coverage:
    vocabulary_coverage: "> 95%"            # 詞彙覆蓋率
    new_term_discovery_rate: "5-10 per day" # 新詞發現率
    user_satisfaction: "> 4.5/5.0"         # 使用者滿意度
    
  maintenance:
    vocabulary_update_frequency: "weekly"   # 詞彙更新頻率
    error_rate: "< 5%"                      # 錯誤率
    system_availability: "> 99.5%"         # 系統可用性
```

## 🔗 與現有系統整合

### 整合點設計

```python
class VocabularySystemIntegration:
    """詞彙庫系統整合接口"""
    
    def integrate_with_nl_to_sql(self, nl_query: str) -> EnhancedQuery:
        """與現有 NL-to-SQL 系統整合"""
        
    def enhance_composite_parser(self, parser: CompositeParser) -> None:
        """增強複合解析器"""
        
    def provide_context_to_llm(self, query_context: Dict[str, Any]) -> Dict[str, Any]:
        """為 LLM 提供詞彙上下文"""
```

## 💡 創新特色功能

### 1. 智能詞彙推薦
- 根據使用者查詢模式自動推薦相關詞彙
- 預測使用者可能需要的查詢組合

### 2. 動態語境學習
- 從使用者互動中學習新的表達方式
- 自適應調整解譯模式

### 3. 多語言支援擴展
- 支援中英文混合查詢
- 專業術語自動翻譯

### 4. 語義相似度搜尋
- 基於詞向量的相似詞彙發現
- 模糊匹配和語義近似查詢

---

**系統負責人**：詞彙庫架構師  
**創建時間**：2025-06-28  
**預計完成時間**：2025-07-19 (3 週)  
**技術棧**：Python, FastAPI, SQLAlchemy, HuggingFace, OpenAI API
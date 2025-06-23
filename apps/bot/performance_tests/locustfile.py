"""
Locust 效能測試檔案
用於測試 LINE MCP Bot 的 API 效能
"""

import json
import random
import time
from locust import HttpUser, task, between
import logging

# 設置日誌級別
logging.getLogger("locust").setLevel(logging.WARNING)


class LineWebhookUser(HttpUser):
    """模擬 LINE Webhook 用戶的行為"""
    
    wait_time = between(1, 3)  # 用戶間隔 1-3 秒
    
    def on_start(self):
        """每個用戶開始時的設置"""
        self.user_id = f"perf_user_{random.randint(10000, 99999)}"
        
        # 常見的查詢模式
        self.test_queries = [
            "查看所有機台",
            "M001機台稼動率", 
            "M002機台狀態",
            "顯示生產統計",
            "機台效率排行",
            "查詢故障記錄",
            "今日產量統計",
            "設備維護提醒",
            "異常警報查詢",
            "效率分析報告"
        ]
        
        # SQL 查詢測試
        self.sql_queries = [
            "SELECT * FROM machines LIMIT 10",
            "SELECT machine_id, name, status FROM machines",
            "SELECT COUNT(*) FROM production_data",
            "SELECT AVG(efficiency_rate) FROM production_data WHERE machine_id = 'M001'",
        ]
        
        # 指令測試
        self.commands = [
            "/help",
            "/status", 
            "/info",
            "/tables",
            "/models"
        ]
    
    @task(5)
    def health_check(self):
        """健康檢查 - 高頻率測試"""
        with self.client.get("/health", 
                           catch_response=True,
                           name="健康檢查") as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure("健康檢查狀態異常")
                except:
                    response.failure("健康檢查回應格式錯誤")
            else:
                response.failure(f"健康檢查失敗: {response.status_code}")
    
    @task(3)
    def metrics_endpoint(self):
        """指標端點測試"""
        with self.client.get("/metrics",
                           catch_response=True,
                           name="指標查詢") as response:
            if response.status_code == 200:
                # 檢查 Prometheus 格式
                if "python_info" in response.text or "http_requests" in response.text:
                    response.success()
                else:
                    response.failure("指標格式不正確")
            else:
                response.failure(f"指標查詢失敗: {response.status_code}")
    
    @task(8)
    def natural_language_query(self):
        """自然語言查詢測試 - 主要測試場景"""
        query_text = random.choice(self.test_queries)
        
        payload = self._create_line_message_payload(query_text)
        
        with self.client.post("/webhook",
                            json=payload,
                            headers=self._get_webhook_headers(),
                            catch_response=True,
                            name="自然語言查詢") as response:
            
            # LINE Webhook 預期會因為簽名驗證失敗返回 400
            if response.status_code in [200, 400, 401, 403]:
                # 檢查是否處理了請求（即使簽名失敗）
                response.success()
            elif response.status_code == 422:
                # 資料格式錯誤
                response.failure("請求格式錯誤")
            elif response.status_code >= 500:
                # 服務器錯誤
                response.failure(f"服務器錯誤: {response.status_code}")
            else:
                response.failure(f"未預期的狀態碼: {response.status_code}")
    
    @task(4)
    def sql_command_query(self):
        """SQL 指令查詢測試"""
        sql_query = random.choice(self.sql_queries)
        query_text = f"/sql {sql_query}"
        
        payload = self._create_line_message_payload(query_text)
        
        with self.client.post("/webhook",
                            json=payload,
                            headers=self._get_webhook_headers(),
                            catch_response=True,
                            name="SQL 指令查詢") as response:
            
            if response.status_code in [200, 400, 401, 403]:
                response.success()
            else:
                response.failure(f"SQL 查詢失敗: {response.status_code}")
    
    @task(2)
    def command_query(self):
        """指令查詢測試"""
        command = random.choice(self.commands)
        
        payload = self._create_line_message_payload(command)
        
        with self.client.post("/webhook",
                            json=payload,
                            headers=self._get_webhook_headers(),
                            catch_response=True,
                            name="指令查詢") as response:
            
            if response.status_code in [200, 400, 401, 403]:
                response.success()
            else:
                response.failure(f"指令查詢失敗: {response.status_code}")
    
    @task(1)
    def concurrent_multiple_queries(self):
        """併發多查詢測試 - 模擬複雜場景"""
        queries = random.sample(self.test_queries, min(3, len(self.test_queries)))
        
        for i, query in enumerate(queries):
            payload = self._create_line_message_payload(f"{query} (批次 {i+1})")
            
            with self.client.post("/webhook",
                                json=payload,
                                headers=self._get_webhook_headers(),
                                catch_response=True,
                                name="併發查詢") as response:
                
                if response.status_code in [200, 400, 401, 403]:
                    response.success()
                else:
                    response.failure(f"併發查詢失敗: {response.status_code}")
            
            # 短暫延遲模擬用戶思考時間
            time.sleep(0.5)
    
    def _create_line_message_payload(self, message_text):
        """創建 LINE 訊息 payload"""
        return {
            "events": [
                {
                    "type": "message",
                    "message": {
                        "type": "text",
                        "text": message_text
                    },
                    "source": {
                        "type": "user",
                        "userId": self.user_id
                    },
                    "replyToken": f"perf_token_{int(time.time())}_{random.randint(1000, 9999)}",
                    "timestamp": int(time.time() * 1000)
                }
            ],
            "destination": "performance_test"
        }
    
    def _get_webhook_headers(self):
        """獲取 Webhook 請求標頭"""
        return {
            "Content-Type": "application/json",
            "X-Line-Signature": "performance_test_signature",
            "User-Agent": "LineBotSDK/Performance-Test"
        }


class HighFrequencyUser(HttpUser):
    """高頻率用戶 - 測試系統極限"""
    
    weight = 1  # 較少的權重
    wait_time = between(0.1, 0.5)  # 更短的等待時間
    
    @task(10)
    def rapid_health_checks(self):
        """快速健康檢查"""
        with self.client.get("/health",
                           catch_response=True,
                           name="快速健康檢查") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"快速檢查失敗: {response.status_code}")
    
    @task(5)
    def rapid_metrics(self):
        """快速指標查詢"""
        with self.client.get("/metrics",
                           catch_response=True,
                           name="快速指標查詢") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"快速指標失敗: {response.status_code}")


class StressTestUser(HttpUser):
    """壓力測試用戶 - 測試錯誤處理"""
    
    weight = 1
    wait_time = between(0.5, 1.5)
    
    @task(5)
    def invalid_requests(self):
        """無效請求測試"""
        invalid_payloads = [
            {},  # 空 payload
            {"invalid": "data"},  # 無效資料
            {"events": []},  # 空事件列表
            {"events": [{"type": "invalid"}]},  # 無效事件類型
        ]
        
        payload = random.choice(invalid_payloads)
        
        with self.client.post("/webhook",
                            json=payload,
                            headers={"Content-Type": "application/json"},
                            catch_response=True,
                            name="無效請求測試") as response:
            
            # 預期應該返回 4xx 錯誤
            if 400 <= response.status_code < 500:
                response.success()
            else:
                response.failure(f"錯誤處理異常: {response.status_code}")
    
    @task(3)
    def malformed_json(self):
        """格式錯誤的 JSON 測試"""
        with self.client.post("/webhook",
                            data="{ invalid json",
                            headers={"Content-Type": "application/json"},
                            catch_response=True,
                            name="格式錯誤JSON") as response:
            
            if 400 <= response.status_code < 500:
                response.success()
            else:
                response.failure(f"JSON 錯誤處理異常: {response.status_code}")
    
    @task(2)
    def large_payload(self):
        """大型 payload 測試"""
        large_text = "A" * 5000  # 5KB 訊息
        
        payload = {
            "events": [
                {
                    "type": "message",
                    "message": {
                        "type": "text",
                        "text": large_text
                    },
                    "source": {
                        "type": "user",
                        "userId": "stress_test_user"
                    },
                    "replyToken": "stress_test_token",
                    "timestamp": int(time.time() * 1000)
                }
            ]
        }
        
        with self.client.post("/webhook",
                            json=payload,
                            headers={"Content-Type": "application/json"},
                            catch_response=True,
                            name="大型Payload測試") as response:
            
            # 可能會被接受或因為大小限制被拒絕
            if response.status_code in [200, 400, 413]:
                response.success()
            else:
                response.failure(f"大型 payload 處理異常: {response.status_code}")
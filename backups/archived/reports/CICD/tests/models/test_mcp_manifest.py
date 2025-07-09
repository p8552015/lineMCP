"""
MCP Manifest 測試
測試 MCP 工具清單功能
"""


from src.models.mcp_manifest import get_mcp_manifest


class TestMCPManifest:
    """測試 MCP 工具清單"""

    def test_get_mcp_manifest_returns_dict(self):
        """測試 get_mcp_manifest 返回字典"""
        manifest = get_mcp_manifest()
        assert isinstance(manifest, dict)

    def test_manifest_contains_expected_tools(self):
        """測試清單包含預期的工具"""
        manifest = get_mcp_manifest()

        expected_tools = [
            "search_docs",
            "get_code_examples",
            "get_api_reference",
            "get_best_practices",
            "execute_query",
            "describe_table",
            "list_tables",
            "get_table_sample",
        ]

        for tool in expected_tools:
            assert tool in manifest, f"清單中缺少工具: {tool}"

    def test_manifest_tools_have_required_structure(self):
        """測試清單工具具有必需的結構"""
        manifest = get_mcp_manifest()

        for tool_name, tool_config in manifest.items():
            # 每個工具應該有 description 和 parameters
            assert "description" in tool_config, f"工具 {tool_name} 缺少 description"
            assert "parameters" in tool_config, f"工具 {tool_name} 缺少 parameters"

            # parameters 應該有 type 和 properties
            parameters = tool_config["parameters"]
            assert "type" in parameters, f"工具 {tool_name} 的 parameters 缺少 type"
            assert (
                "properties" in parameters
            ), f"工具 {tool_name} 的 parameters 缺少 properties"
            assert (
                "required" in parameters
            ), f"工具 {tool_name} 的 parameters 缺少 required"

    def test_search_docs_tool_structure(self):
        """測試 search_docs 工具結構"""
        manifest = get_mcp_manifest()
        search_docs = manifest["search_docs"]

        # 檢查描述
        assert isinstance(search_docs["description"], str)
        assert len(search_docs["description"]) > 0

        # 檢查參數
        params = search_docs["parameters"]
        assert params["type"] == "object"

        properties = params["properties"]
        assert "query" in properties
        assert "framework" in properties
        assert "language" in properties

        required = params["required"]
        assert "query" in required

    def test_execute_query_tool_structure(self):
        """測試 execute_query 工具結構"""
        manifest = get_mcp_manifest()
        execute_query = manifest["execute_query"]

        # 檢查描述包含 PostgreSQL
        assert "PostgreSQL" in execute_query["description"]

        # 檢查參數
        params = execute_query["parameters"]
        properties = params["properties"]
        assert "query" in properties

        required = params["required"]
        assert "query" in required

    def test_database_tools_present(self):
        """測試資料庫工具存在"""
        manifest = get_mcp_manifest()

        database_tools = [
            "execute_query",
            "describe_table",
            "list_tables",
            "get_table_sample",
        ]

        for tool in database_tools:
            assert tool in manifest, f"缺少資料庫工具: {tool}"

    def test_documentation_tools_present(self):
        """測試文檔工具存在"""
        manifest = get_mcp_manifest()

        doc_tools = [
            "search_docs",
            "get_code_examples",
            "get_api_reference",
            "get_best_practices",
        ]

        for tool in doc_tools:
            assert tool in manifest, f"缺少文檔工具: {tool}"

    def test_tool_descriptions_are_strings(self):
        """測試工具描述都是字符串"""
        manifest = get_mcp_manifest()

        for tool_name, tool_config in manifest.items():
            description = tool_config["description"]
            assert isinstance(description, str), f"工具 {tool_name} 的描述不是字符串"
            assert len(description) > 0, f"工具 {tool_name} 的描述為空"

    def test_tool_parameters_structure(self):
        """測試工具參數結構"""
        manifest = get_mcp_manifest()

        for tool_name, tool_config in manifest.items():
            params = tool_config["parameters"]

            # 檢查基本結構
            assert params["type"] == "object", f"工具 {tool_name} 參數 type 不是 object"
            assert isinstance(
                params["properties"], dict
            ), f"工具 {tool_name} 的 properties 不是字典"
            assert isinstance(
                params["required"], list
            ), f"工具 {tool_name} 的 required 不是列表"

    def test_required_parameters_exist_in_properties(self):
        """測試必需參數存在於屬性中"""
        manifest = get_mcp_manifest()

        for tool_name, tool_config in manifest.items():
            params = tool_config["parameters"]
            properties = params["properties"]
            required = params["required"]

            for req_param in required:
                assert (
                    req_param in properties
                ), f"工具 {tool_name} 的必需參數 {req_param} 不在 properties 中"

    def test_manifest_is_not_empty(self):
        """測試清單不為空"""
        manifest = get_mcp_manifest()
        assert len(manifest) > 0, "MCP 工具清單為空"
        assert len(manifest) >= 8, "MCP 工具清單工具數量不足"


class TestMCPManifestFunctionality:
    """測試 MCP 清單功能性"""

    def test_manifest_can_be_called_multiple_times(self):
        """測試清單可以多次調用"""
        manifest1 = get_mcp_manifest()
        manifest2 = get_mcp_manifest()

        # 應該返回相同的結構
        assert manifest1.keys() == manifest2.keys()
        assert manifest1 == manifest2

    def test_manifest_contains_context7_references(self):
        """測試清單包含 Context7 引用"""
        manifest = get_mcp_manifest()

        # search_docs 應該提到 Context7
        search_docs_desc = manifest["search_docs"]["description"]
        assert "Context7" in search_docs_desc

    def test_manifest_contains_postgresql_references(self):
        """測試清單包含 PostgreSQL 引用"""
        manifest = get_mcp_manifest()

        # 資料庫工具應該提到 PostgreSQL
        db_tools = [
            "execute_query",
            "describe_table",
            "list_tables",
            "get_table_sample",
        ]

        found_postgresql_ref = False
        for tool_name in db_tools:
            if tool_name in manifest:
                desc = manifest[tool_name]["description"]
                if "PostgreSQL" in desc:
                    found_postgresql_ref = True
                    break

        assert found_postgresql_ref, "資料庫工具中未找到 PostgreSQL 引用"

    def test_all_tools_have_non_empty_properties(self):
        """測試所有工具都有非空屬性（除了 list_tables）"""
        manifest = get_mcp_manifest()

        for tool_name, tool_config in manifest.items():
            properties = tool_config["parameters"]["properties"]

            # list_tables 可以有空屬性
            if tool_name == "list_tables":
                continue

            assert len(properties) > 0, f"工具 {tool_name} 沒有定義任何屬性"

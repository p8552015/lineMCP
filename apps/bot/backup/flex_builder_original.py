# FlexBuilder 原始檔案備份 - 安全隔離測試前備份
# 備份時間: 2025-06-19
# 用途: 安全隔離測試失敗時可以快速恢復

# 這個檔案是 src/services/flex_builder.py 的完整備份
# 如果隔離測試發現問題，可以使用以下命令恢復：
# cp backup/flex_builder_original.py src/services/flex_builder.py

import shutil
source = "/Users/yen/Desktop/lineMCP/apps/bot/src/services/flex_builder.py"
backup = "/Users/yen/Desktop/lineMCP/apps/bot/backup/flex_builder_original_content.py"
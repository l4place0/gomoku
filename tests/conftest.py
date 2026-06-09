import os
import sys
import pytest

# 设置环境变量，强迫 Pygame 在 headless 模式下运行（如果没有显示设备的话）
os.environ["SDL_VIDEODRIVER"] = "dummy"

@pytest.fixture(autouse=True)
def mock_pygame_display(monkeypatch):
    """
    一个自动应用的 fixture，用以在测试环境中防御性处理 Pygame。
    """
    # 可以在这里添加针对特定 GUI 组件的 Mock 逻辑
    pass

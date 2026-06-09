import pytest
from game.game_logic import (
    is_symmetric,
    is_symmetric_to_any,
    get_distance,
    choose_low_impact_candidates_for_black,
    BOARD_SIZE
)

class MockAIMove:
    def __init__(self, x, y, score):
        self.x = x
        self.y = y
        self.score = score

def test_is_symmetric_center():
    # 关于中心点 (7, 7) 对称的测试
    center = BOARD_SIZE // 2
    assert is_symmetric((center - 1, center - 1), (center + 1, center + 1))
    assert is_symmetric((center, center - 3), (center, center + 3))
    # 自身不对称，必须是两个不同位置
    assert not is_symmetric((center, center), (center, center))

def test_is_symmetric_axis():
    # 轴对称测试
    center = BOARD_SIZE // 2
    # 水平对称
    assert is_symmetric((3, center - 2), (3, center + 2))
    # 垂直对称
    assert is_symmetric((center - 4, 5), (center + 4, 5))
    # 对角线对称
    assert is_symmetric((center - 2, center - 2), (center + 2, center + 2))

def test_is_symmetric_to_any():
    # 测试 is_symmetric_to_any
    selected = [(7, 6), (6, 7)]
    assert is_symmetric_to_any((7, 8), selected)  # (7, 8) 关于 (7,7) 对称于 (7, 6)
    assert not is_symmetric_to_any((1, 1), selected)

def test_get_distance():
    assert get_distance((0, 0), (3, 4)) == 5.0
    assert get_distance((7, 7), (7, 7)) == 0.0

def test_choose_low_impact_candidates_for_black():
    # 测试低影响黑子开局点的选择，排除对称性
    # 传入一批候选位置
    candidates = [(7, 6), (7, 8), (6, 7), (8, 7), (3, 3)]
    
    # choose_low_impact_candidates_for_black 根据 rank_move_score_from_arr 升序排列（分越低，影响越低），次要关键字为距离中心越远（-distance 降序）
    # 构造模拟的 C++ 推荐点数组。注意：如果候选点不在 arr 中，默认返回的得分为 0，这样反而会排在最前面。
    # 故我们需要为所有 candidates 都在 arr 中指定分数。
    arr = [
        MockAIMove(7, 6, 10),   # 影响极低分，优先考虑
        MockAIMove(7, 8, 20),   # 垂直对称
        MockAIMove(6, 7, 30),   # 对角线对称
        MockAIMove(8, 7, 40),   # 对称
        MockAIMove(3, 3, 5)     # 极低分，但无对称
    ]
    # (3, 3) 最优得分 5
    # (7, 6) 次优得分 10
    # 其他与 (7, 6) 对称的被排除。
    selected = choose_low_impact_candidates_for_black(candidates, arr, len(arr), 2)
    assert (7, 6) in selected
    assert (3, 3) in selected
    assert len(selected) == 2

import math

# 常量定义
BOARD_SIZE = 15

def is_symmetric(pos1, pos2, center_x=BOARD_SIZE//2, center_y=BOARD_SIZE//2):
    """检查两个位置是否关于棋盘中心对称"""
    if pos1 == pos2:
        return False
    x1, y1 = pos1
    x2, y2 = pos2
    
    # 检查中心对称
    if (2*center_x - x1 == x2) and (2*center_y - y1 == y2):
        return True
    
    # 检查轴对称（水平、垂直、对角线）
    if x1 == x2 and abs(y1 - center_y) == abs(y2 - center_y) and y1 != y2:
        return True
    if y1 == y2 and abs(x1 - center_x) == abs(x2 - center_x) and x1 != x2:
        return True
    if abs(x1 - center_x) == abs(y1 - center_y) and abs(x2 - center_x) == abs(y2 - center_y):
        if (x1 - center_x) == (y1 - center_y) and (x2 - center_x) == (y2 - center_y):
            return True
        if (x1 - center_x) == -(y1 - center_y) and (x2 - center_x) == -(y2 - center_y):
            return True
    
    return False

def is_symmetric_to_any(pos, selected):
    return any(is_symmetric(prev, pos) for prev in selected)

def get_distance(pos1, pos2):
    """计算两点间距离"""
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

def rank_move_score_from_arr(arr, cnt, pos):
    return next((arr[i].score for i in range(cnt) if (arr[i].x, arr[i].y) == pos), 0)

def choose_low_impact_candidates_for_black(candidates, arr, cnt, n):
    ranked = sorted(
        candidates,
        key=lambda pos: (rank_move_score_from_arr(arr, cnt, pos), -get_distance(pos, (BOARD_SIZE // 2, BOARD_SIZE // 2)))
    )
    selected = []
    for pos in ranked:
        if pos not in selected and not is_symmetric_to_any(pos, selected):
            selected.append(pos)
        if len(selected) >= n:
            break
    for pos in ranked:
        if len(selected) >= n:
            break
        if pos not in selected:
            selected.append(pos)
    return selected[:n]

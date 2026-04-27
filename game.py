import sys
import ctypes
import pygame
from pygame.locals import *
import math

# -------------------------------------------------------------------
# DLL 接口封装
# -------------------------------------------------------------------
DLL_PATH = r"D:\coding\TheWayofCode\demo\mini-gomoko\GameEngine.dll"
dll = ctypes.CDLL(DLL_PATH)

class GameEngine(ctypes.Structure): pass
class AIMove(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("score", ctypes.c_int)]

# 原型定义
dll.GetGameEngine.restype = ctypes.POINTER(GameEngine)
dll.CheckWin.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.CheckWin.restype = ctypes.c_bool
dll.SwapHand.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_bool]
dll.DoMove.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.DoMove.restype = ctypes.c_bool
dll.UndoMove.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.UndoMove.restype = ctypes.c_bool
dll.GetTopMoves.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.POINTER(AIMove), ctypes.c_int]
dll.GetTopMoves.restype = ctypes.c_int
dll.GetBoardState.argtypes = [ctypes.POINTER(GameEngine), ctypes.POINTER(ctypes.c_int), ctypes.c_bool]
dll.ReleaseEngine.argtypes = [ctypes.POINTER(GameEngine)]

# -------------------------------------------------------------------
# 常量 & 初始化
# -------------------------------------------------------------------
BOARD_SIZE = 15
CELL = 40
MARGIN = 50
STATUS_H = 80
WIDTH = MARGIN + CELL * BOARD_SIZE + 20
HEIGHT = MARGIN + CELL * BOARD_SIZE + STATUS_H + 20
BLACK, WHITE = 0, 1

pygame.init(); pygame.font.init()
font = pygame.font.Font('LXGWZhenKaiGB-Regular.ttf', 24)
small_font = pygame.font.Font('LXGWZhenKaiGB-Regular.ttf', 18)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('五子棋')

# 引擎 & 缓存
env = dll.GetGameEngine()
board_buf = (ctypes.c_int * (BOARD_SIZE * BOARD_SIZE))()
history = []
current_role = BLACK
human_is_black = True
ai_first_done = False
asked_open = False
asked_three = False  # 三手交换标志
five_asked = False   # 五手两打标志
virtual_candidates = []
winner = None


# 五手二打虚拟棋盘状态
virtual_candidates = []  # 虚拟候选位置

# -------------------------------------------------------------------
# 辅助函数
# -------------------------------------------------------------------
def is_symmetric(pos1, pos2, center_x=BOARD_SIZE//2, center_y=BOARD_SIZE//2):
    """检查两个位置是否关于棋盘中心对称"""
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

def get_distance(pos1, pos2):
    """计算两点间距离"""
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

def filter_non_symmetric_pairs(candidates):
    """过滤掉对称的点对组合"""
    valid_pairs = []
    for i in range(len(candidates)):
        for j in range(i+1, len(candidates)):
            pos1, pos2 = candidates[i], candidates[j]
            if not is_symmetric(pos1, pos2) and get_distance(pos1, pos2) > 1:
                valid_pairs.append((pos1, pos2))
    return valid_pairs

def evaluate_virtual_move_for_white(x, y):
    """虚拟评估某步棋对白方的价值（不影响真实棋盘状态）"""
    # 临时下一个黑子
    if dll.DoMove(env, x, y, BLACK):
        # 获取白方的最佳应对
        arr = (AIMove * 5)()
        cnt = dll.GetTopMoves(env, WHITE, arr, 5)
        white_best_score = arr[0].score if cnt > 0 else 0
        
        # 立即撤销临时棋子
        dll.UndoMove(env, x, y, BLACK)
        
        # 返回白方的得分（越高对白方越有利）
        return white_best_score
    return -9999

# -------------------------------------------------------------------
# 坐标映射：origin at top-left x→down, y→right
# -------------------------------------------------------------------
def to_screen(x, y):
    px = MARGIN + y * CELL
    py = MARGIN + x * CELL
    return px, py

# -------------------------------------------------------------------
# 绘制棋盘与 UI
# -------------------------------------------------------------------
def draw():
    screen.fill((230,200,160))
    for i in range(BOARD_SIZE):
        txt = font.render(str(i), True, (0,0,0))
        screen.blit(txt, (MARGIN-30, MARGIN + i*CELL - txt.get_height()/2))
        screen.blit(txt, (MARGIN + i*CELL - txt.get_width()/2, MARGIN-30))
    for i in range(BOARD_SIZE+1):
        pygame.draw.line(screen, (0,0,0), (MARGIN, MARGIN + i*CELL), (MARGIN + BOARD_SIZE*CELL, MARGIN + i*CELL))
        pygame.draw.line(screen, (0,0,0), (MARGIN + i*CELL, MARGIN), (MARGIN + i*CELL, MARGIN + BOARD_SIZE*CELL))
    
    dll.GetBoardState(env, board_buf, human_is_black)
    for x in range(BOARD_SIZE):
        for y in range(BOARD_SIZE):
            v = board_buf[x * BOARD_SIZE + y]
            px, py = to_screen(x, y)
            if v == BLACK:
                pygame.draw.circle(screen, (0,0,0), (px, py), CELL//2-2)
            elif v == WHITE:
                pygame.draw.circle(screen, (255,255,255), (px, py), CELL//2-2)
                pygame.draw.circle(screen, (0,0,0), (px, py), CELL//2-2,1)
            elif v == 2:
                pygame.draw.circle(screen, (255,0,0), (px, py), 5)
    # 高亮最后一个落子点
    if history:
        lx, ly, _ = history[-1]
        px, py = to_screen(lx, ly)
        rect = pygame.Rect(px - CELL//2 + 2, py - CELL//2 + 2, CELL - 4, CELL - 4)
        dash_len = 5
        color = (255, 0, 0)
        # 上边虚线
        for x_off in range(0, rect.width, dash_len*2):
            start = (rect.x + x_off, rect.y)
            end   = (min(rect.x + x_off + dash_len, rect.x + rect.width), rect.y)
            pygame.draw.line(screen, color, start, end, 2)
        # 下边虚线
        for x_off in range(0, rect.width, dash_len*2):
            start = (rect.x + x_off, rect.y + rect.height)
            end   = (min(rect.x + x_off + dash_len, rect.x + rect.width), rect.y + rect.height)
            pygame.draw.line(screen, color, start, end, 2)
        # 左边虚线
        for y_off in range(0, rect.height, dash_len*2):
            start = (rect.x, rect.y + y_off)
            end   = (rect.x, min(rect.y + y_off + dash_len, rect.y + rect.height))
            pygame.draw.line(screen, color, start, end, 2)
        # 右边虚线
        for y_off in range(0, rect.height, dash_len*2):
            start = (rect.x + rect.width, rect.y + y_off)
            end   = (rect.x + rect.width, min(rect.y + y_off + dash_len, rect.y + rect.height))
            pygame.draw.line(screen, color, start, end, 2)

    # 绘制虚拟候选位置（五手二打阶段）
    if virtual_candidates:
        for cx, cy in virtual_candidates:
            px, py = to_screen(cx, cy)
            pygame.draw.circle(screen, (128, 128, 128), (px, py), CELL//2-2)  # 半透明显示
            pygame.draw.circle(screen, (255, 255, 0), (px, py), CELL//2-2, 2)  # 黄色边框
    
    if winner is not None:
        msg = f"{ '黑子' if winner==BLACK else '白子' } 胜利！"
        text = font.render(msg, True, (255,0,0))
        screen.blit(text, ((WIDTH-text.get_width())//2, HEIGHT-STATUS_H+20))
    else:
        text = font.render(f'当前手数: {len(history)}', True, (0,0,0))
        screen.blit(text, (20, HEIGHT-STATUS_H+20))
        
        # 显示当前轮次信息
        role_text = "黑子" if current_role == BLACK else "白子"
        player_text = "人类" if ((current_role == BLACK and human_is_black) or (current_role == WHITE and not human_is_black)) else "AI"
        info_text = f'{role_text} ({player_text}) 回合'
        text = small_font.render(info_text, True, (0,0,0))
        screen.blit(text, (20, HEIGHT-STATUS_H+45))
        
        # 五手两打提示
        if len(history) == 4 and current_role == BLACK:
            if virtual_candidates:
                tip_text = "五手二打：选择保留的位置"
            else:
                tip_text = "五手二打：需要放置两枚棋子"
            text = small_font.render(tip_text, True, (255,0,0))
            screen.blit(text, (200, HEIGHT-STATUS_H+45))
    
    btn = pygame.Rect(WIDTH-100, HEIGHT-STATUS_H+10, 80, 40)
    pygame.draw.rect(screen, (100,100,100), btn)
    screen.blit(font.render('悔棋', True, (255,255,255)), (btn.x+20, btn.y+10))
    return btn

# -------------------------------------------------------------------
# 弹窗
# -------------------------------------------------------------------
def confirm(prompt):
    w,h = 300,150; x=(WIDTH-w)//2; y=(HEIGHT-STATUS_H-h)//2
    r = pygame.Rect(x,y,w,h); dragging=False; off=(0,0)
    while True:
        draw(); pygame.draw.rect(screen,(255,255,255),r); pygame.draw.rect(screen,(0,0,0),r,2)
        screen.blit(font.render(prompt,True,(0,0,0)), (r.x+20, r.y+20))
        yb = pygame.Rect(r.x+40, r.y+80,80,40); nb = pygame.Rect(r.x+180,r.y+80,80,40)
        pygame.draw.rect(screen,(0,150,0),yb); pygame.draw.rect(screen,(150,0,0),nb)
        screen.blit(font.render('是',True,(255,255,255)), (yb.x+30,yb.y+10))
        screen.blit(font.render('否',True,(255,255,255)), (nb.x+30,nb.y+10))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==QUIT: pygame.quit(); sys.exit()
            if e.type==MOUSEBUTTONDOWN and e.button==1:
                if r.collidepoint(e.pos): dragging=True; off=(e.pos[0]-r.x,e.pos[1]-r.y)
                if yb.collidepoint(e.pos): return True
                if nb.collidepoint(e.pos): return False
            if e.type==MOUSEBUTTONUP and e.button==1: dragging=False
            if e.type==MOUSEMOTION and dragging: r.x, r.y = e.pos[0]-off[0], e.pos[1]-off[1]

# -------------------------------------------------------------------
# 主循环
# -------------------------------------------------------------------
asked_open=False; asked_three=False; run=True

while run:
    btn = draw(); pygame.display.flip()
    if winner is not None: 
        # 显示获胜信息后等待用户操作
        for ev in pygame.event.get():
            if ev.type == QUIT:
                run = False
        continue
    
    if not asked_open:
        asked_open=True
        if confirm('是否开局换手(默认您执黑)？'):
            human_is_black=not human_is_black; dll.SwapHand(env, human_is_black)
    
    if not ai_first_done and not human_is_black:
        dll.DoMove(env, BOARD_SIZE//2, BOARD_SIZE//2, BLACK)
        history.append((BOARD_SIZE//2,BOARD_SIZE//2,BLACK))
        if dll.CheckWin(env, BOARD_SIZE//2, BOARD_SIZE//2, BLACK): winner = BLACK
        current_role=WHITE; ai_first_done=True
        continue
    
    # 三手交换逻辑：人类执白时生效
    if len(history) == 3 and not asked_three and not human_is_black:
        asked_three = True
        if confirm('是否进行三手交换？'):
            human_is_black = True
            dll.SwapHand(env, human_is_black)
            print("[三手交换] 已交换，您执黑，AI执白")
        else:
            print("[三手交换] 未交换，继续执白")
        # 交换后直接进入下一轮，若 AI 执白则 AI 会在此后立即落子
        continue

    
    # 五手二打逻辑
    if len(history)==4 and not five_asked and current_role==BLACK:
        five_asked = True
        print(f"[五手二打] 开始，当前轮次：{current_role}（黑子）")
        
        # 获取AI推荐的前8个位置作为候选
        arr=(AIMove*15)()
        cnt=dll.GetTopMoves(env,BLACK,arr,15)
        candidates=[(m.x,m.y) for m in arr[:min(cnt,8)]]
        print(f"[五手二打] 候选位置：{candidates}")
        
        if human_is_black:
            # 人类执黑：让玩家选择两个非对称点位
            print("[五手二打] 人类执黑 - 玩家选择两个位置")
            selected=[]
            
            while len(selected) < 2:
                draw()
                
                # 高亮显示候选位置
                for cx, cy in candidates:
                    px, py = to_screen(cx, cy)
                    if (cx, cy) in selected:
                        pygame.draw.circle(screen, (0, 255, 0), (px, py), CELL//2, 3)  # 已选择 - 绿色
                    else:
                        pygame.draw.circle(screen, (255, 255, 0), (px, py), CELL//2, 3)  # 候选 - 黄色
                
                # 显示提示信息
                if len(selected) == 0:
                    tip = "请选择第一个位置"
                else:
                    tip = "请选择第二个位置（不能对称）"
                tip_surface = small_font.render(tip, True, (255, 0, 0))
                screen.blit(tip_surface, (20, 20))
                
                pygame.display.flip()
                
                for ev in pygame.event.get():
                    if ev.type == QUIT:
                        run = False
                        break
                    elif ev.type == MOUSEBUTTONDOWN and ev.button == 1:
                        gx = (ev.pos[1] - MARGIN + CELL//2) // CELL
                        gy = (ev.pos[0] - MARGIN + CELL//2) // CELL
                        
                        if (gx, gy) in candidates and (gx, gy) not in selected:
                            # 检查是否与已选位置对称
                            if len(selected) == 0:
                                selected.append((gx, gy))
                                print(f"[五手二打] 玩家选择第一个位置：{(gx, gy)}")
                            else:
                                if not is_symmetric(selected[0], (gx, gy)):
                                    selected.append((gx, gy))
                                    print(f"[五手二打] 玩家选择第二个位置：{(gx, gy)}")
                                else:
                                    # 显示对称警告
                                    print(f"[五手二打] 位置 {(gx, gy)} 与 {selected[0]} 对称，不允许选择")
                                    draw()
                                    warning = small_font.render("不能选择对称位置！", True, (255, 0, 0))
                                    screen.blit(warning, (20, 50))
                                    pygame.display.flip()
                                    pygame.time.wait(1000)
                
                if not run:
                    break
            
            if not run:
                break
                
            # 设置虚拟候选位置，供AI选择
            virtual_candidates = selected[:]
            print(f"[五手二打] 虚拟位置设置：{virtual_candidates}")
            
            # AI选择保留哪一个（选择对白方威胁最小的位置）
            scores = []
            for cx, cy in selected:
                # 虚拟评估这个位置对白方的价值
                white_value = evaluate_virtual_move_for_white(cx, cy)
                scores.append(((cx, cy), white_value))
                print(f"[五手二打] 位置 {(cx, cy)} 对白方价值：{white_value}")
            
            # AI选择对白方威胁最小的位置保留（白方价值最低的）
            keep_pos, keep_score = max(scores, key=lambda x: x[1]) # 为什么要用max呢？
            print(f"[五手二打] AI选择保留位置：{keep_pos}（白方价值：{keep_score}）")
            
            # 显示AI选择过程
            for step in range(20):
                draw()
                # 高亮所有虚拟位置
                for cx, cy in virtual_candidates:
                    px, py = to_screen(cx, cy)
                    if (cx, cy) == keep_pos:
                        # 被保留的位置闪烁绿色
                        color_intensity = int(128 + 127 * abs(step % 10 - 5) / 5)
                        pygame.draw.circle(screen, (0, color_intensity, 0), (px, py), CELL//2 + 5, 4)
                    else:
                        # 被移除的位置显示红色
                        pygame.draw.circle(screen, (255, 100, 100), (px, py), CELL//2, 3)
                
                tip_surface = small_font.render(f"AI保留位置: ({keep_pos[0]}, {keep_pos[1]})", True, (0, 150, 0))
                screen.blit(tip_surface, (20, 20))
                pygame.display.flip()
                pygame.time.wait(100)
            
            # 只在真实棋盘上放置被保留的棋子
            dll.DoMove(env, keep_pos[0], keep_pos[1], BLACK)
            history.append((keep_pos[0], keep_pos[1], BLACK))
            
            # 清空虚拟候选位置
            virtual_candidates = []
            
        else:
            # AI执黑：AI选择最佳的两个非对称位置
            print("[五手二打] AI执黑 - AI选择两个位置")
            
            # 获取所有有效的非对称点对
            valid_pairs = filter_non_symmetric_pairs(candidates)
            
            if not valid_pairs:
                # 如果没有非对称点对，随机选择两个距离较远的点
                if len(candidates) >= 2:
                    selected = [candidates[0], candidates[1]]
                    for i in range(2, len(candidates)):
                        if get_distance(candidates[0], candidates[i]) > get_distance(candidates[0], selected[1]):
                            selected[1] = candidates[i]
                else:
                    selected = candidates[:2] if len(candidates) >= 2 else candidates
            else:
                # 选择综合得分最高的点对
                best_pair = None
                best_score = float('-inf')
                
                for pair in valid_pairs[:10]:  # 只评估前10个点对避免计算过久
                    pos1, pos2 = pair
                    # 计算点对的综合得分
                    score1 = next((m.score for m in arr[:cnt] if (m.x, m.y) == pos1), 0)
                    score2 = next((m.score for m in arr[:cnt] if (m.x, m.y) == pos2), 0)
                    pair_score = score1 + score2
                    
                    if pair_score > best_score:
                        best_score = pair_score
                        best_pair = pair
                
                selected = list(best_pair) if best_pair else candidates[:2]
            
            print(f"[五手二打] AI选择的两个位置：{selected}")
            
            # 设置虚拟候选位置
            virtual_candidates = selected[:]
            
            # 显示AI的选择过程
            for step in range(30):  # 显示选择动画
                draw()
                for cx, cy in virtual_candidates:
                    px, py = to_screen(cx, cy)
                    alpha = (step % 10) / 10.0
                    color_intensity = int(255 * alpha)
                    pygame.draw.circle(screen, (color_intensity, 0, 255-color_intensity), (px, py), CELL//2, 3)
                
                tip_surface = small_font.render("AI正在进行五手二打...", True, (255, 0, 0))
                screen.blit(tip_surface, (20, 20))
                pygame.display.flip()
                pygame.time.wait(100)
            
            # 让玩家选择保留哪一个
            chosen = None
            while chosen is None:
                draw()
                for cx, cy in virtual_candidates:
                    px, py = to_screen(cx, cy)
                    pygame.draw.circle(screen, (0, 255, 0), (px, py), CELL//2, 3)
                
                tip_surface = small_font.render("请选择保留哪个黑子", True, (255, 0, 0))
                screen.blit(tip_surface, (20, 20))
                pygame.display.flip()
                
                for ev in pygame.event.get():
                    if ev.type == QUIT:
                        run = False
                        break
                    elif ev.type == MOUSEBUTTONDOWN and ev.button == 1:
                        gx = (ev.pos[1] - MARGIN + CELL//2) // CELL
                        gy = (ev.pos[0] - MARGIN + CELL//2) // CELL
                        if (gx, gy) in virtual_candidates:
                            chosen = (gx, gy)
                            print(f"[五手二打] 玩家选择保留位置：{chosen}")
                
                if not run:
                    break
            
            if not run:
                break
                
            # 只在真实棋盘上放置被选择保留的棋子
            dll.DoMove(env, chosen[0], chosen[1], BLACK) # type: ignore
            history.append((chosen[0], chosen[1], BLACK)) # type: ignore
            
            # 清空虚拟候选位置
            virtual_candidates = []
        
        # 检查是否获胜
        final_pos = None
        for x, y, role in reversed(history):
            if role == BLACK:
                final_pos = (x, y)
                break
        
        if final_pos and dll.CheckWin(env, final_pos[0], final_pos[1], BLACK):
            winner = BLACK
            print(f"[五手二打] 黑方获胜！")
        else:
            # 五手二打完成，轮到白方
            current_role = WHITE
            print(f"[五手二打] 完成，轮到白方")
        
        # 给玩家时间看清楚结果
        pygame.time.wait(1000)
        continue
    
    # 普通事件处理
    for ev in pygame.event.get():
        if ev.type == QUIT:
            run = False
        elif ev.type == MOUSEBUTTONDOWN and ev.button == 1:
            if btn.collidepoint(ev.pos) and history:
                # 悔棋逻辑
                if len(history) >= 2:  # 悔掉最近两步
                    for _ in range(min(2, len(history))):
                        x, y, r = history.pop()
                        dll.UndoMove(env, x, y, r)
                        current_role = r
                elif history:
                    x, y, r = history.pop()
                    dll.UndoMove(env, x, y, r)
                    current_role = r
                winner = None
                five_asked = False  # 重置五手两打标志
                virtual_candidates = []  # 清空虚拟候选位置
            else:
                # 正常下棋
                gx = (ev.pos[1] - MARGIN + CELL//2) // CELL
                gy = (ev.pos[0] - MARGIN + CELL//2) // CELL
                if 0 <= gx < BOARD_SIZE and 0 <= gy < BOARD_SIZE and winner is None:
                    # 确保是人类回合且不是五手两打阶段
                    is_human_turn = (current_role == BLACK and human_is_black) or (current_role == WHITE and not human_is_black)
                    is_five_move_phase = (len(history) == 4 and current_role == BLACK)
                    
                    if is_human_turn and not is_five_move_phase:
                        if dll.DoMove(env, gx, gy, current_role):
                            history.append((gx, gy, current_role))
                            print(f"[普通回合] 人类落子：{(gx, gy)}，角色：{'黑' if current_role == BLACK else '白'}")
                            if dll.CheckWin(env, gx, gy, current_role):
                                winner = current_role
                            current_role = 1 - current_role
    
    # AI 普通回合
    if winner is None and not (len(history) == 4 and current_role == BLACK):
        is_ai_turn = (current_role == BLACK and not human_is_black) or (current_role == WHITE and human_is_black)
        if is_ai_turn:
            arr = (AIMove * 10)()
            cnt = dll.GetTopMoves(env, current_role, arr, 10)
            if cnt > 0:
                m = arr[0]
                if dll.DoMove(env, m.x, m.y, current_role):
                    history.append((m.x, m.y, current_role))
                    print(f"[普通回合] AI落子：{(m.x, m.y)}，角色：{'黑' if current_role == BLACK else '白'}，评分：{m.score}")
                    if dll.CheckWin(env, m.x, m.y, current_role):
                        winner = current_role
                    current_role = 1 - current_role

# 退出清理
pygame.quit()
dll.ReleaseEngine(env)
sys.exit()
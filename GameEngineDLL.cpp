// ---- GameEngineDLL.cpp ----
#include "GameEngine.h"


struct AIMove {
    int x;
    int y;
    int score;
};

extern "C" {
// enum Role {NONE = -1,BLACK, WHITE};

// 默认人类执黑，如果想实现选边就开局交换
__declspec(dllexport) GameEngine* GetGameEngine() {
    LOG(INFO, "游戏开始，默认人类玩家执黑");
    return &GameEngine::getInstance();
}


__declspec(dllexport) bool CheckWin(GameEngine* engine, int x, int y, int role) {
    bool flag = engine->checkWin(x, y, (Role)role);
    if (flag) LOG(INFO, "玩家 [" << (role == Role::BLACK ? "黑子" : "白子") << "] 胜利");
    return flag;
}

// 开局选边 和 三手交换 可以使用 并返回一个 bool 表示当前电脑是否执黑* 1 为执黑 0 为执白
__declspec(dllexport) void SwapHand(GameEngine* engine, bool is_black) {
    engine->swapHand();
    is_black = engine->isBlack;
    LOG(INFO, "换手成功，当前执黑玩家" << (engine->isBlack == Role::BLACK ? "人类" : "电脑"));
}

__declspec(dllexport) bool DoMove(GameEngine* engine, int x, int y, int role) {
    bool flag = engine->doMove({x, y}, static_cast<Role>(role));
    LOG(INFO, ((role == Role::BLACK && !engine->isBlack) ? "人类" : "电脑") << "落子 [" << x << ", " << y << "] ");
    #ifdef DEBUG
    engine->printBoard();
    #endif
    return flag;
}

__declspec(dllexport) bool UndoMove(GameEngine* engine, int x, int y, int role) {
    bool flag = engine->undoMove({x, y}, static_cast<Role>(role));
    LOG(INFO, ((role == Role::BLACK && !engine->isBlack) ? "人类" : "电脑") << "撤销落子 [" << x << ", " << y << "] ");
    #ifdef DEBUG
    engine->printBoard();
    #endif
    return flag;
}

// 返回分数从大到小排序的着法序列
__declspec(dllexport) int GetTopMoves(GameEngine* engine, int role, AIMove* out_moves, int max_count) {
    LOG(INFO, "正在为当前玩家 " << ((Role)role == Role::BLACK ? "[黑子]" : "[白子]") << "生成推荐着法");
    auto moves = engine->getBestMoves(static_cast<Role>(role));
    int count = std::min(static_cast<int>(moves.size()), max_count);
    for (int i = 0; i < count; ++i) {
        LOG(INFO, "落子 [" << moves[i].first << ", " << moves[i].second << "] 评分: " << engine->board[moves[i].first][moves[i].second].moveScore);
        out_moves[i].x = moves[i].first;
        out_moves[i].y = moves[i].second;
        out_moves[i].score = engine->board[moves[i].first][moves[i].second].moveScore;
    }
    return count;
}

// 返回一个整型数组作为棋盘状态代表 -> -1 : 空 | 0 : 黑子 | 1 : 白子 | 2 : 禁手点 并返回一个 bool 表示当前电脑是否执黑* 1 为执黑 0 为执白
__declspec(dllexport) void GetBoardState(GameEngine* engine, int* out_board, bool is_black) {
    is_black = engine->isBlack;
    for (int i = 0; i < 15; ++i)
        for (int j = 0; j < 15; ++j) {
            if (engine->board[i][j].isForbidde) { 
                out_board[i * 15 + j] = 2;
                continue;
            }
            out_board[i * 15 + j] = static_cast<int>(engine->board[i][j].role);
        }
}

__declspec(dllexport) void ReleaseEngine(GameEngine* /*engine*/) {
    // nothing
}
}

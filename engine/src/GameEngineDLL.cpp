// ---- GameEngineDLL.cpp ----
#include "GameEngine.h"

#ifdef _WIN32
  #ifdef BUILDING_DLL
    #define DLLEXPORT DLLEXPORT
  #else
    #define DLLEXPORT __declspec(dllimport)
  #endif
#else
  #define DLLEXPORT __attribute__((visibility("default")))
#endif

struct AIMove {
    int x;
    int y;
    int score;
};

// --- KataGomo adapter (managed at DLL layer, transparent to GameEngine) ---
#ifdef ENABLE_KATAGOMO_CUDA
#include "KataInferenceAdapter.h"
#include <mutex>
static std::unique_ptr<KataInferenceAdapter> g_kataAdapter;
static std::mutex g_kataMutex;
#endif

extern "C" {

DLLEXPORT bool LoadKataModel(void* /*engine*/, const char* model_path, const char* config_path) {
#ifdef ENABLE_KATAGOMO_CUDA
    std::lock_guard<std::mutex> lock(g_kataMutex);
    if (!g_kataAdapter) g_kataAdapter = std::make_unique<KataInferenceAdapter>();
    return g_kataAdapter->loadModel(model_path ? model_path : "", config_path ? config_path : "");
#else
    (void)model_path; (void)config_path;
    return false;
#endif
}

DLLEXPORT void SetKataEnabled(void* /*engine*/, bool enabled) {
#ifdef ENABLE_KATAGOMO_CUDA
    std::lock_guard<std::mutex> lock(g_kataMutex);
    if (g_kataAdapter) g_kataAdapter->setEnabled(enabled);
#else
    (void)enabled;
#endif
}

DLLEXPORT bool IsKataReady(void* /*engine*/) {
#ifdef ENABLE_KATAGOMO_CUDA
    std::lock_guard<std::mutex> lock(g_kataMutex);
    return g_kataAdapter && g_kataAdapter->isReady() && g_kataAdapter->isEnabled();
#else
    return false;
#endif
}

DLLEXPORT void SetKataSearchParams(void* /*engine*/, int visits, double seconds, double policyBlend, double valueBlend) {
#ifdef ENABLE_KATAGOMO_CUDA
    std::lock_guard<std::mutex> lock(g_kataMutex);
    if (g_kataAdapter) g_kataAdapter->setSearchParams(visits, seconds, policyBlend, valueBlend);
#else
    (void)visits; (void)seconds; (void)policyBlend; (void)valueBlend;
#endif
}

// 默认人类执黑，如果想实现选边就开局交换
DLLEXPORT GameEngine* GetGameEngine() {
    LOG(INFO, "游戏开始，默认人类玩家执黑");
    return &GameEngine::getInstance();
}


DLLEXPORT bool CheckWin(GameEngine* engine, int x, int y, int role) {
    if (x < 0 || x >= 15 || y < 0 || y >= 15) return false;
    if (role < 0 || role > 1) return false;
    bool flag = engine->checkWin(x, y, (Role)role);
    if (flag) LOG(INFO, "玩家 [" << (role == Role::BLACK ? "黑子" : "白子") << "] 胜利");
    return flag;
}

// 开局选边 和 三手交换 可以使用，根据传入的 is_black (人类是否执黑) 精确设置电脑是否执黑 (AI_is_black = !is_black)
DLLEXPORT void SwapHand(GameEngine* engine, bool is_black) {
    engine->setAIBlack(!is_black);
    LOG(INFO, "换手成功，当前执黑玩家" << (engine->isBlack == Role::BLACK ? "人类" : "电脑"));
}

DLLEXPORT bool DoMove(GameEngine* engine, int x, int y, int role) {
    if (x < 0 || x >= 15 || y < 0 || y >= 15) return false;
    if (role < 0 || role > 1) return false;
    bool flag = engine->doMove({x, y}, static_cast<Role>(role));
    LOG(INFO, ((role == Role::BLACK && !engine->isBlack) ? "人类" : "电脑") << "落子 [" << x << ", " << y << "] ");
    #ifdef DEBUG
    engine->printBoard();
    #endif
    return flag;
}

DLLEXPORT bool UndoMove(GameEngine* engine, int x, int y, int role) {
    if (x < 0 || x >= 15 || y < 0 || y >= 15) return false;
    if (role < 0 || role > 1) return false;
    bool flag = engine->undoMove({x, y}, static_cast<Role>(role));
    LOG(INFO, ((role == Role::BLACK && !engine->isBlack) ? "人类" : "电脑") << "撤销落子 [" << x << ", " << y << "] ");
    #ifdef DEBUG
    engine->printBoard();
    #endif
    return flag;
}

// 返回分数从大到小排序的着法序列
DLLEXPORT int GetTopMoves(GameEngine* engine, int role, AIMove* out_moves, int max_count) {
    if (role < 0 || role > 1 || max_count <= 0) return 0;
#ifdef ENABLE_KATAGOMO_CUDA
    // Use KataGomo NN when enabled and ready
    {
        std::lock_guard<std::mutex> lock(g_kataMutex);
        if (g_kataAdapter && g_kataAdapter->isReady() && g_kataAdapter->isEnabled()) {
            LOG(INFO, "正在用 KataGomo 为 " << ((Role)role == Role::BLACK ? "[黑子]" : "[白子]") << " 推理着法");
            // Sync board state to adapter
            std::array<int, 15*15> boardArr;
            for (int i = 0; i < 15; ++i)
                for (int j = 0; j < 15; ++j) {
                    int v = static_cast<int>(engine->board[i][j].role);
                    boardArr[i * 15 + j] = (v == 1) ? 0 : ((v == 0) ? 1 : -1);
                }
            g_kataAdapter->setPosition(boardArr);
            // Build candidate list (non-empty neighbor positions)
            std::vector<std::pair<int,int>> candidates;
            for (int i = 0; i < 15; ++i)
                for (int j = 0; j < 15; ++j)
                    if (engine->board[i][j].role == Role::NONE && engine->board[i][j].neighborCnt > 0)
                        candidates.emplace_back(i, j);
            auto ranked = g_kataAdapter->rankMoves(candidates,
                role == static_cast<int>(Role::BLACK) ? KataRole::Black : KataRole::White);
            int count = std::min(static_cast<int>(ranked.size()), max_count);
            for (int i = 0; i < count; ++i) {
                out_moves[i].x = ranked[i].x;
                out_moves[i].y = ranked[i].y;
                out_moves[i].score = ranked[i].score;
            }
            return count;
        }
    }
#endif
    // Fallback: alpha-beta search
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
DLLEXPORT void GetBoardState(GameEngine* engine, int* out_board, bool is_black) {
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

DLLEXPORT void ReleaseEngine(GameEngine* /*engine*/) {
    // nothing
}
}

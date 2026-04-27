#pragma once
#include <string>
#include <utility>
#include <chrono>
#include <random>
#include <iostream>
#include <iomanip>
#include <algorithm>
#include <unordered_map>
#include <sstream>
#include <stack>


using namespace std;

#ifdef DEBUG
#define LOG(Level, S) std::cout << "[调试信息] : [" << #Level << "] : " << S << "  " << std::endl
#else
#define LOG(X, S)
#endif


#define BOARD_SIZE (int)(15)

enum PatternType {
    FIVE = 0,
    FOUR,
    BLOCKED_FOUR,
    THREE,
    BLOCKED_THREE,
    TWO,
    BLOCKED_TWO,
    PATTERN_TYPE_COUNT // 自动获取枚举数量
};

const int patternScore[PATTERN_TYPE_COUNT] = {
    100000,   // FIVE（必胜）
    10000,    // FOUR（活四）
    5000,     // BLOCKED_FOUR（冲四）
    1000,     // THREE（活三）
    500,      // BLOCKED_THREE（眠三）
    200,      // TWO（活二）
    100       // BLOCKED_TWO（眠二）
};


enum Role {
    NONE = -1,
    BLACK,
    WHITE
};

// 四个方向：横、竖、主对角线、副对角线
const int dx[4] = {1, 0, 1, 1};
const int dy[4] = {0, 1, 1, -1};

bool isLegalPoint (int x, int y) {
    return x >= 0 && x < BOARD_SIZE && y >= 0 && y < BOARD_SIZE;
}

class GameEngine {

public:
    static GameEngine& getInstance() {
        static GameEngine instance;
        return instance;
    }

    bool checkWin(int x, int y, Role r) {
        string pat;
        for (int d = 0; d < 4; ++d) {
            pat = getLinePattern(x, y, dx[d], dy[d], r);
            if (pat.find("11111") != string::npos) return true;
        }
        return false;
    }

    void swapHand() {
        isBlack ^= 1;
    }

    bool doMove(pair<int, int> m, Role r) {
        int updateR = 3, neighborUpdateR = 1;

        moveHistory.push(m);
        turn++;
        zobristHash ^= board[m.first][m.second].zobristHash[(int)r];
        board[m.first][m.second].role = r;
        for (int i = m.first - updateR; i <= m.first + updateR; ++i) {
            for (int j = m.second - updateR; j <= m.second + updateR; ++j) {
                if (isLegalPoint(i, j)) {
                    board[i][j].isForbidde = isForbiddenPoint(i, j);
                    if (i >= m.first - neighborUpdateR && i <= m.first + neighborUpdateR
                        && j >= m.second - neighborUpdateR && j <= m.second + neighborUpdateR)
                        board[i][j].neighborCnt++;
                }
            }
        }
        return true;
    }

    bool undoMove(pair<int, int> m, Role r) {
        int updateR = 3, neighborUpdateR = 1;

        moveHistory.pop();
        turn--;
        zobristHash ^= board[m.first][m.second].zobristHash[(int)r];
        board[m.first][m.second].role = Role::NONE;

        for (int i = m.first - updateR; i <= m.first + updateR; ++i) {
            for (int j = m.second - updateR; j <= m.second + updateR; ++j) {
                if (isLegalPoint(i, j)) {
                    board[i][j].isForbidde = isForbiddenPoint(i, j);
                    if (i >= m.first - neighborUpdateR && i <= m.first + neighborUpdateR
                        && j >= m.second - neighborUpdateR && j <= m.second + neighborUpdateR) {
                        board[i][j].neighborCnt = std::max(0, board[i][j].neighborCnt - 1);
                    }
                }
            }
        }

        return true;
    }

    vector<pair<int, int>> getBestMoves(Role role) {
        using namespace std::chrono;
        
        md = MoveData();
        int CurrentMaxDepth = decideSearchDepth();

        vector<pair<int, int>> moves = genMoves(role);

        auto startTime = steady_clock::now();
        for (int depth = 1, alpha = -INF, beta = INF; depth <= CurrentMaxDepth; ++depth) {
            md.maxDepth = maxDepth = depth;
            md.bestScore = INT_MIN;

            for (auto &mv : moves) {
                auto now = steady_clock::now();
                auto elapsed = duration_cast<milliseconds>(now - startTime).count();
                if (elapsed >= MAX_TIME_MS) {
                    goto TIMEOUT_EXIT;
                }

                doMove(mv, role);
                board[mv.first][mv.second].moveScore = -negaMax(0, alpha, beta, (Role)(role ^ 1));
                undoMove(mv, role);

            }
        }

    TIMEOUT_EXIT:
        sort(moves.begin(), moves.end(), [&](auto &a, auto &b) {
            if (board[a.first][a.second].moveScore != board[b.first][b.second].moveScore) 
                return board[a.first][a.second].moveScore > board[b.first][b.second].moveScore;
            return board[a.first][a.second].neighborCnt > board[b.first][b.second].neighborCnt;
        });
        clearHashTable();
        // md.bestScore = board[moves[0].first][moves[0].second].moveScore;
        // md.bestMove = moves[0];
        // md.summarize();
        
        return moves;
    }

// private:
    struct PointStatus {
        unsigned long long zobristHash[2] = { 0 };
        Role role;
        bool isForbidde =false;
        int neighborCnt {};
        int moveScore {};
        int score {};
    };

    struct HashItem {
        enum class Flag { F_NONE, F_EXACT, F_ALPHA, F_BETA };

        int depth = 0;
        int score = INT_MIN;
        std::pair<int, int> bestMove = {-1, -1};
        Flag flagType = Flag::F_NONE;

        HashItem() = default;
        HashItem(int d, int s) : depth(d), score(s) {}
        HashItem(int d, int s, Flag f) : depth(d), score(s), flagType(f) {}
    };
    struct MoveData {
        chrono::steady_clock::time_point startTime{chrono::steady_clock::now()};
        
        double evaluateMoveMaxTimeInMs = 0.0;
        double recognizePatternMaxTimeInMs = 0.0;
        double thinkingTimeInMs = 0.0;
        pair<int, int> bestMove = {-1, -1};
        int bestScore = INT_MIN;
        int alphaCutCnt = 0;
        int betaCutCnt = 0;
        int hashHitCnt = 0;
        int searchCnt = 0;
        int maxDepth = 0;

        void summarize() {
            thinkingTimeInMs = chrono::duration<double, milli>(
                chrono::steady_clock::now() - startTime).count();

            double hitRate = (searchCnt > 0) ? (100.0 * hashHitCnt / searchCnt) : 0.0;

            LOG(INFO, "===[统计信息]===");
            LOG(INFO, "思考时间(ms): " << thinkingTimeInMs);
            // LOG(INFO, "AI推荐着法: [" << bestMove.first << ", " << bestMove.second << "] ");
            // LOG(INFO, "AI推荐着法评分: " << bestScore);
            LOG(INFO, "总搜索次数: " << searchCnt);
            LOG(INFO, "最大搜索深度: " << maxDepth);
            LOG(INFO, "缓存命中率: " << fixed << setprecision(2) << hitRate << " %");
            LOG(INFO, "发生 Beta 截断数: " << betaCutCnt);
        }
    };

    unsigned long long zobristHash = 0ULL;
    const int UNK = 1e9 + 1;
    const int INF = 1e9;
    int MAX_DEPTH = 20;
    int MAX_TIME_MS = 1e5;
    stack<pair<int, int>> moveHistory;
    bool isBlack = false;
    int turn = 0;
    int maxDepth = 1;
    unordered_map<unsigned long long, HashItem> hashTable;
    PointStatus board[BOARD_SIZE][BOARD_SIZE];
    MoveData md;
    
    void printBoard() {
        LOG(INFO, "正在打印棋盘...");

        cout << "   ";
        for (int y = 0; y < BOARD_SIZE; ++y) {
            if (y < 10) cout << " " << y << " ";
            else cout << y << " ";
        }
        cout << endl;

        for (int x = 0; x < BOARD_SIZE; ++x) {
            if (x < 10) cout << " " << x << " ";
            else cout << x << " ";

            for (int y = 0; y < BOARD_SIZE; ++y) {
                char c = '.';
                if (!moveHistory.empty() && x == moveHistory.top().first && y == moveHistory.top().second) {
                    c = 'N';
                } else if (board[x][y].role == Role::BLACK) {
                    c = 'X';
                } else if (board[x][y].role == Role::WHITE) {
                    c = 'O';
                } else if (board[x][y].isForbidde) {
                    c = 'F';
                }
                cout << " " << c << " ";
            }
            cout << endl << endl;
        }
    }


    int decideSearchDepth() {
        int stones = turn;

        if (stones <= 4) return 2;              // 开局，快速启发判断
        else if (stones <= 8) return 4;         // 初期
        else if (stones <= 14) return 6;        // 中期
        else if (stones <= 22) return 8;        // 中后期
        else return MAX_DEPTH;              // 终局力争精准终结
    }

    int negaMax(int depth, int alpha, int beta, Role role) {
        md.searchCnt++;
        int val = probeHashHIt(depth, alpha, beta);
        if (val != UNK) return val;

        if (depth == maxDepth) return (hashTable[zobristHash] = HashItem(depth, evaluate(role), HashItem::Flag::F_EXACT)).score;

        for (auto &move : genMoves(role)) {
            doMove(move, role);
            alpha = max(alpha, -negaMax(depth + 1, -beta, -alpha, (Role)(role ^ 1)));
            undoMove(move, role);
        
            if (alpha >= beta) {
                md.betaCutCnt++;
                return (hashTable[zobristHash] = HashItem(depth, beta, HashItem::Flag::F_BETA)).score;
            }
        }
        return (hashTable[zobristHash] = HashItem(depth, alpha, HashItem::Flag::F_ALPHA)).score;
    }

    int probeHashHIt(int depth, int alpha, int beta) {
        auto it = hashTable.find(zobristHash);
        if (it != hashTable.end()) {
            md.hashHitCnt++;
            HashItem hi = it->second;
            if ((hi.flagType != HashItem::Flag::F_NONE) && (hi.depth <= depth)) {
                if (hi.flagType == HashItem::Flag::F_EXACT) return hi.score;
                if ((hi.flagType == HashItem::Flag::F_ALPHA) && (hi.score <= alpha)) return alpha;
                if ((hi.flagType == HashItem::Flag::F_BETA) && (hi.score >= beta)) return beta;
            }
        }
        return UNK;
    }

    int evaluate(Role role) {
        long long scoreCurr = 0;
        long long scoreEnemy = 0;
        for (int i = 0; i < BOARD_SIZE; ++i) {
            for (int j = 0; j < BOARD_SIZE; ++j) {
                if (board[i][j].role > -1) {
                    if (role == Role::BLACK && board[i][j].isForbidde) {
                        return -FIVE;
                    }
                    if (board[i][j].role == role) scoreCurr += evaluateMove({i, j}, board[i][j].role);
                    else scoreEnemy += evaluateMove({i, j}, board[i][j].role);
                }
            }
        }


        return static_cast<int>(scoreCurr - scoreEnemy);
    }

    int evaluateMove(pair<int, int> m, Role role) {
        // chrono::steady_clock::time_point evaluateMoveStartTime = chrono::steady_clock::now();
        int totalScore = 0;
        int x = m.first;
        int y = m.second;

        for (int dir = 0; dir < 4; ++dir) {
            totalScore += recognizePattern(getLinePattern(x, y, dx[dir], dy[dir], role));
        }

        // md.evaluateMoveMaxTimeInMs = max(md.evaluateMoveMaxTimeInMs, chrono::duration<double, milli>(chrono::steady_clock::now() - evaluateMoveStartTime).count());
        return totalScore;
    }


    int evaluatePoint(pair<int, int> p) {
        return board[p.first][p.second].neighborCnt;
    }

    int evaluatePoint(pair<int, int> p, Role r) {
        return evaluateMove(p, r);
    }

    // 可能需要修改
    vector<pair<int, int>> genMoves(Role r) {
        vector<pair<int ,int>> moves;
        for (int i = 0; i < BOARD_SIZE; ++i) {
            for (int j = 0; j < BOARD_SIZE; ++j) {
                if (board[i][j].role == Role::NONE && board[i][j].neighborCnt > 0 && !(r == Role::BLACK && board[i][j].isForbidde)) {
                    moves.emplace_back(i, j);
                    board[i][j].score = evaluatePoint({i, j}, r);
                }
            }
        }

        sort(moves.begin(), moves.end(), [&](const pair<int, int>& a, const pair<int, int>& b) {
            return board[a.first][a.second].score > board[b.first][b.second].score;
        });

        return moves;
    }
    
    string getLinePattern(int x, int y, int dx, int dy, Role role) {
        string pattern;
        for (int i = -4; i <= 4; ++i) {
            int nx = x + i * dx;
            int ny = y + i * dy;

            if (!isLegalPoint(nx, ny)) {
                pattern += 'B'; // 边界视为阻挡
            } else if (nx == x && ny == y) {
                pattern += '1'; // 假设当前点落子
            } else {
                Role r = board[nx][ny].role;
                if (r == Role::NONE) pattern += '0';
                else if (r == Role::BLACK && board[nx][ny].isForbidde) pattern += '2';
                else if (r == role) pattern += '1';
                else pattern += '2';
            }
        }
        return pattern;
    }

    int recognizePattern(const string& s) {
        // chrono::steady_clock::time_point recognizePatternStartTime = chrono::steady_clock::now();
        int score = 0;
        int count[PATTERN_TYPE_COUNT] = {0};

        // 检测各类模式出现次数
        if (s.find("11111") != string::npos) count[FIVE]++;
        
        // 活四
        for (const string& pat : {"011110"}) {
            size_t pos = s.find(pat);
            while (pos != string::npos) {
                count[FOUR]++;
                pos = s.find(pat, pos + 1);
            }
        }

        // 冲四
        for (const string& pat : {"011112", "211110", "10111", "11011", "11101"}) {
            size_t pos = s.find(pat);
            while (pos != string::npos) {
                count[BLOCKED_FOUR]++;
                pos = s.find(pat, pos + 1);
            }
        }

        // 活三
        for (const string& pat : {"01110", "010110", "011010"}) {
            size_t pos = s.find(pat);
            while (pos != string::npos) {
                count[THREE]++;
                pos = s.find(pat, pos + 1);
            }
        }

        // 眠三
        for (const string& pat : {"001112", "211100", "021110", "011012"}) {
            size_t pos = s.find(pat);
            while (pos != string::npos) {
                count[BLOCKED_THREE]++;
                pos = s.find(pat, pos + 1);
            }
        }

        // 活二
        for (const string& pat : {"00110", "01010", "01100", "00110"}) {
            size_t pos = s.find(pat);
            while (pos != string::npos) {
                count[TWO]++;
                pos = s.find(pat, pos + 1);
            }
        }

        // 眠二
        for (const string& pat : {"000112", "211000", "021100", "001102"}) {
            size_t pos = s.find(pat);
            while (pos != string::npos) {
                count[BLOCKED_TWO]++;
                pos = s.find(pat, pos + 1);
            }
        }

        // 组合所有得分
        for (int i = 0; i < PATTERN_TYPE_COUNT; ++i) {
            score += count[i] * patternScore[i];
        }
        // md.recognizePatternMaxTimeInMs = max(md.recognizePatternMaxTimeInMs, chrono::duration<double, milli>(chrono::steady_clock::now() - recognizePatternStartTime).count());
        return score;
    }

    bool isPatternMatch(const std::string& pattern, const std::vector<std::string>& rules) {
    for (const auto& rule : rules) {
        if (pattern.find(rule) != std::string::npos)
            return true;
    }
    return false;
}

    bool isForbiddenPoint(int x, int y) {
        if (!isLegalPoint(x, y) || board[x][y].role != Role::NONE)
            return false;

        int overlineCount = 0, openThree = 0, openFour = 0;

        board[x][y].role = Role::BLACK;  // 假设落子
        for (int d = 0; d < 4; ++d) {
            std::string pattern = getLinePattern(x, y, dx[d], dy[d], board[x][y].role);

            // 1. 长连检测（连续6个或以上己方）
            if (pattern.find("111111") != std::string::npos || pattern.find("1111111") != std::string::npos)
                overlineCount++;

            // 2. 活三（开放三）检测（可扩展规则）
            static const std::vector<std::string> liveThreePatterns = {
                "01110", "010110", "011010"
            };
            if (isPatternMatch(pattern, liveThreePatterns))
                openThree++;

            // 3. 活四检测（可扩展规则）
            static const std::vector<std::string> liveFourPatterns = {
                "011110", "101110", "011101", "110110"
            };
            if (isPatternMatch(pattern, liveFourPatterns))
                openFour++;
        }
        board[x][y].role = Role::NONE;  // 撤销落子

        return overlineCount > 0 || openThree >= 2 || openFour >= 2;
    }
    

    void clearHashTable() {
        LOG(INFO, "清理 [" << hashTable.size() <<"] 个缓存记录 ");
        hashTable.clear();
    }

private:
    GameEngine() {
        mt19937_64 rng(random_device{}());
        uniform_int_distribution<uint64_t> dist;

        zobristHash = dist(rng);
        for (int i = 0; i < BOARD_SIZE; ++i) {
            for (int j = 0; j < BOARD_SIZE; ++j) {
                board[i][j].role = Role::NONE;
                board[i][j].zobristHash[0] = dist(rng);
                board[i][j].zobristHash[1] = dist(rng);
            }
        }
    };

    ~GameEngine() = default;

    GameEngine(const GameEngine&) = delete;

    GameEngine& operator=(const GameEngine&) = delete;

};

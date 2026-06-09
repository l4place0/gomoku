#include "KataInferenceAdapter.h"

#include <algorithm>
#include <cmath>

#ifdef ENABLE_KATAGOMO_CUDA
#include "KataGomo/cpp/core/logger.h"
#include "KataGomo/cpp/game/board.h"
#include "KataGomo/cpp/game/boardhistory.h"
#include "KataGomo/cpp/neuralnet/nneval.h"
#include "KataGomo/cpp/neuralnet/nninputs.h"
#include "KataGomo/cpp/neuralnet/nninterface.h"
#include "KataGomo/cpp/search/reportedsearchvalues.h"
#include "KataGomo/cpp/search/search.h"
#include "KataGomo/cpp/search/searchparams.h"

#include <atomic>
#include <mutex>

struct KataInferenceAdapter::Impl {
    Logger logger;
    std::unique_ptr<NNEvaluator> nnEval;
    std::unique_ptr<Search> search;
    Board board;
    BoardHistory history;
    Rules rules;
    Player nextPlayer = P_BLACK;
    bool globalsInitialized = false;

    Impl()
        : logger(nullptr, false, false, true, false),
          board(KataInferenceAdapter::BoardSize, KataInferenceAdapter::BoardSize),
          rules(Rules::BASICRULE_RENJU, Rules::VCNRULE_NOVC, false, 0) {
        logger.setDisabled(true);
    }
};
#else
struct KataInferenceAdapter::Impl {};
#endif

KataInferenceAdapter::KataInferenceAdapter()
    : impl_(std::make_unique<Impl>()) {}

KataInferenceAdapter::~KataInferenceAdapter() = default;

bool KataInferenceAdapter::loadModel(const std::string& modelPath, const std::string& configPath) {
    modelPath_ = modelPath;
    configPath_ = configPath;

#ifdef ENABLE_KATAGOMO_CUDA
    try {
        static std::once_flag initFlag;
        std::call_once(initFlag, []() {
            Board::initHash();
            NeuralNet::globalInitialize();
        });
        impl_->globalsInitialized = true;

        const int maxBatchSize = 32;
        const int maxConcurrentEvals = 64;
        const int nnCacheSizePowerOfTwo = 16;
        const int nnMutexPoolSizePowerOfTwo = 8;
        const std::vector<int> gpuIdxByServerThread = {0};
        impl_->nnEval = std::make_unique<NNEvaluator>(
            "kata-gomoku",
            modelPath_,
            "",
            &impl_->logger,
            maxBatchSize,
            maxConcurrentEvals,
            BoardSize,
            BoardSize,
            true,
            true,
            nnCacheSizePowerOfTwo,
            nnMutexPoolSizePowerOfTwo,
            false,
            "",
            "",
            false,
            enabled_t::Auto,
            enabled_t::Auto,
            1,
            gpuIdxByServerThread,
            "gomoku-kata-adapter",
            true,
            NNInputs::SYMMETRY_NOTSPECIFIED
        );
        impl_->nnEval->spawnServerThreads();
        ready_ = true;
        status_ = "KataGomo CUDA model loaded";
        setPosition(board_);
    }
    catch(const std::exception& e) {
        impl_->search.reset();
        impl_->nnEval.reset();
        ready_ = false;
        status_ = std::string("KataGomo load failed: ") + e.what();
    }
#else
    ready_ = false;
    status_ = "Built without ENABLE_KATAGOMO_CUDA";
#endif
    return ready_;
}

void KataInferenceAdapter::setEnabled(bool enabled) {
    enabled_ = enabled;
}

bool KataInferenceAdapter::isEnabled() const {
    return enabled_;
}

bool KataInferenceAdapter::isReady() const {
    return ready_;
}

std::string KataInferenceAdapter::status() const {
    return status_;
}

void KataInferenceAdapter::setSearchParams(int visits, double seconds, double policyBlend, double valueBlend) {
    visits_ = std::max(1, visits);
    seconds_ = std::max(0.0, seconds);
    policyBlend_ = std::max(0.0, std::min(1.0, policyBlend));
    valueBlend_ = std::max(0.0, std::min(1.0, valueBlend));
}

int KataInferenceAdapter::visits() const {
    return visits_;
}

double KataInferenceAdapter::seconds() const {
    return seconds_;
}

double KataInferenceAdapter::policyBlend() const {
    return policyBlend_;
}

double KataInferenceAdapter::valueBlend() const {
    return valueBlend_;
}

void KataInferenceAdapter::setPosition(const BoardArray& board) {
    board_ = board;
#ifdef ENABLE_KATAGOMO_CUDA
    if(!ready_)
        return;
    try {
        impl_->board = Board(BoardSize, BoardSize);
        int blackCount = 0;
        int whiteCount = 0;
        for(int x = 0; x < BoardSize; ++x) {
            for(int y = 0; y < BoardSize; ++y) {
                int cell = board_[x * BoardSize + y];
                if(cell == 0) {
                    impl_->board.setStone(Location::getLoc(y, x, BoardSize), P_BLACK);
                    blackCount++;
                }
                else if(cell == 1) {
                    impl_->board.setStone(Location::getLoc(y, x, BoardSize), P_WHITE);
                    whiteCount++;
                }
            }
        }
        impl_->nextPlayer = blackCount <= whiteCount ? P_BLACK : P_WHITE;
        impl_->history = BoardHistory(impl_->board, impl_->nextPlayer, impl_->rules);
    }
    catch(const std::exception& e) {
        ready_ = false;
        status_ = std::string("KataGomo board sync failed: ") + e.what();
    }
#endif
}

bool KataInferenceAdapter::doMove(int x, int y, KataRole role) {
    if(x < 0 || x >= BoardSize || y < 0 || y >= BoardSize)
        return false;
    int& cell = board_[x * BoardSize + y];
    if(cell != -1)
        return false;
    cell = role == KataRole::Black ? 0 : 1;
    return true;
}

bool KataInferenceAdapter::undoMove(int x, int y) {
    if(x < 0 || x >= BoardSize || y < 0 || y >= BoardSize)
        return false;
    board_[x * BoardSize + y] = -1;
    return true;
}

std::vector<KataMoveScore> KataInferenceAdapter::rankMoves(
    const std::vector<std::pair<int, int>>& candidates,
    KataRole role
) {
#ifdef ENABLE_KATAGOMO_CUDA
    if(ready_ && enabled_ && impl_->nnEval != nullptr) {
        try {
            setPosition(board_);
            SearchParams params = SearchParams::forTestsV1();
            params.maxVisits = visits_;
            params.maxPlayouts = visits_;
            params.maxTime = seconds_ > 0.0 ? seconds_ : 1.0e20;
            params.numThreads = 1;
            params.rootNoiseEnabled = false;
            params.useVCFInput = true;
            params.useForbiddenInput = true;
            params.nnPolicyTemperature = 1.0f;
            Player pla = role == KataRole::Black ? P_BLACK : P_WHITE;

            impl_->search = std::make_unique<Search>(params, impl_->nnEval.get(), &impl_->logger, "gomoku-kata-search");
            impl_->search->setPosition(pla, impl_->board, impl_->history);
            impl_->search->runWholeSearch(pla);

            float policy[NNPos::MAX_NN_POLICY_SIZE];
            std::fill(policy, policy + NNPos::MAX_NN_POLICY_SIZE, -1.0f);
            impl_->search->getPolicy(policy);

            ReportedSearchValues values;
            bool hasValues = impl_->search->getRootValues(values);
            double rootValue = hasValues ? values.winLossValue : 0.0;
            if(pla == P_BLACK)
                rootValue = -rootValue;

            std::vector<KataMoveScore> ranked;
            ranked.reserve(candidates.size());
            for(const auto& candidate : candidates) {
                Loc loc = Location::getLoc(candidate.second, candidate.first, BoardSize);
                int pos = NNPos::locToPos(loc, BoardSize, BoardSize, BoardSize);
                double p = pos >= 0 && pos < NNPos::MAX_NN_POLICY_SIZE ? std::max(0.0f, policy[pos]) : 0.0;
                KataMoveScore item;
                item.x = candidate.first;
                item.y = candidate.second;
                item.policy = p;
                item.value = rootValue;
                item.score = static_cast<int>(std::round(p * 100000.0 + rootValue * 10000.0));
                ranked.push_back(item);
            }
            std::sort(ranked.begin(), ranked.end(), [](const KataMoveScore& a, const KataMoveScore& b) {
                return a.score > b.score;
            });
            return ranked;
        }
        catch(const std::exception& e) {
            ready_ = false;
            status_ = std::string("KataGomo inference failed: ") + e.what();
        }
    }
#endif

    std::vector<KataMoveScore> ranked;
    ranked.reserve(candidates.size());

    for(const auto& candidate : candidates) {
        KataMoveScore item;
        item.x = candidate.first;
        item.y = candidate.second;
        item.score = fallbackHeuristic(item.x, item.y, role);
        item.policy = std::max(0, item.score) / 1000.0;
        item.value = item.score / 1000.0;
        ranked.push_back(item);
    }

    std::sort(ranked.begin(), ranked.end(), [](const KataMoveScore& a, const KataMoveScore& b) {
        return a.score > b.score;
    });
    return ranked;
}

int KataInferenceAdapter::fallbackHeuristic(int x, int y, KataRole role) const {
    const double center = (BoardSize - 1) / 2.0;
    const double centerDistance = std::abs(x - center) + std::abs(y - center);
    int neighborCount = 0;
    for(int dx = -2; dx <= 2; ++dx) {
        for(int dy = -2; dy <= 2; ++dy) {
            if(dx == 0 && dy == 0)
                continue;
            int nx = x + dx;
            int ny = y + dy;
            if(nx < 0 || nx >= BoardSize || ny < 0 || ny >= BoardSize)
                continue;
            int cell = board_[nx * BoardSize + ny];
            if(cell == 0 || cell == 1)
                neighborCount += cell == static_cast<int>(role) ? 3 : 2;
        }
    }
    return static_cast<int>(std::round((BoardSize - centerDistance) * 8.0 + neighborCount * 12.0));
}

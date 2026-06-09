#pragma once

#include <array>
#include <memory>
#include <string>
#include <utility>
#include <vector>

enum class KataRole {
    Black = 0,
    White = 1,
};

struct KataMoveScore {
    int x = -1;
    int y = -1;
    double policy = 0.0;
    double value = 0.0;
    int score = 0;
};

class KataInferenceAdapter {
public:
    static constexpr int BoardSize = 15;
    using BoardArray = std::array<int, BoardSize * BoardSize>;

    KataInferenceAdapter();
    ~KataInferenceAdapter();

    bool loadModel(const std::string& modelPath, const std::string& configPath);
    void setEnabled(bool enabled);
    bool isEnabled() const;
    bool isReady() const;
    std::string status() const;

    void setSearchParams(int visits, double seconds, double policyBlend, double valueBlend);
    int visits() const;
    double seconds() const;
    double policyBlend() const;
    double valueBlend() const;

    void setPosition(const BoardArray& board);
    bool doMove(int x, int y, KataRole role);
    bool undoMove(int x, int y);
    std::vector<KataMoveScore> rankMoves(
        const std::vector<std::pair<int, int>>& candidates,
        KataRole role
    );

private:
    BoardArray board_{};
    bool enabled_ = false;
    bool ready_ = false;
    int visits_ = 64;
    double seconds_ = 0.0;
    double policyBlend_ = 0.25;
    double valueBlend_ = 0.35;
    std::string modelPath_;
    std::string configPath_;
    std::string status_ = "KataGomo disabled";
    struct Impl;
    std::unique_ptr<Impl> impl_;

    int fallbackHeuristic(int x, int y, KataRole role) const;
};

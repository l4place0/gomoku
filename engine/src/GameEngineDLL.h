// ---- GameEngineDLL.h ----
#pragma once

#ifdef _WIN32
  #ifdef BUILDING_DLL
    #define DLLEXPORT __declspec(dllexport)
  #else
    #define DLLEXPORT __declspec(dllimport)
  #endif
#else
  #define DLLEXPORT
#endif

#ifdef __cplusplus
extern "C" {
#endif

struct AIMove {
    int x;
    int y;
    int score;
};


DLLEXPORT void* GetGameEngine();
DLLEXPORT bool LoadModelWeights(void* engine, const char* path);
DLLEXPORT bool LoadKataModel(void* engine, const char* model_path, const char* config_path);
DLLEXPORT void SetKataEnabled(void* engine, bool enabled);
DLLEXPORT void SetKataSearchParams(void* engine, int visits, double seconds, double policy_blend, double value_blend);
DLLEXPORT bool IsKataReady(void* engine);
DLLEXPORT void  SwapHand(void* engine, bool is_black);
DLLEXPORT bool CheckWin(void* engine, int x, int y, int role);
DLLEXPORT bool  DoMove(void* engine, int x, int y, int role);
DLLEXPORT bool  UndoMove(void* engine, int x, int y, int role);
DLLEXPORT int GetTopMoves(void* engine, int role, AIMove* out_moves, int max_count);
DLLEXPORT int GetLastSearchLogJson(void* engine, char* out_json, int max_len);
DLLEXPORT void  ReleaseEngine(void* engine);
DLLEXPORT void GetBoardState(void* engine, int* out_board, bool is_black);

#ifdef __cplusplus
}
#endif

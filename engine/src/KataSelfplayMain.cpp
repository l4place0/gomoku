#include "KataGomo/cpp/core/global.h"
#include "KataGomo/cpp/main.h"
#include "KataGomo/cpp/vcfsolver/VCFsolver.h"

#include <iostream>

namespace Version {
std::string getKataGoVersion() {
  return "Gom2024 embedded";
}

std::string getKataGoVersionForHelp() {
  return getKataGoVersion();
}

std::string getKataGoVersionFullInfo() {
  return getKataGoVersion();
}

std::string getGitRevision() {
  return "unknown";
}

std::string getGitRevisionWithBackend() {
  return getGitRevision();
}
}

int main(int argc, const char* const* argv) {
  std::vector<std::string> args;
  args.emplace_back("selfplay");
  const int firstArg = (argc > 1 && std::string(argv[1]) == "selfplay") ? 2 : 1;
  for(int i = firstArg; i < argc; i++)
    args.emplace_back(argv[i]);

  try {
    VCFsolver::init();
    return MainCmds::selfplay(args);
  }
  catch(const StringError& err) {
    std::cerr << err.what() << std::endl;
    return 1;
  }
  catch(const std::exception& err) {
    std::cerr << err.what() << std::endl;
    return 1;
  }
}

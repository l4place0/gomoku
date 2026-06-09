# Contributing to Gomoku

## Branch Strategy

This project uses a **master/dev** two-branch model:

- **`master`** — Stable branch. Always buildable and runnable. Receives changes via squash merge from `dev`.
- **`dev`** — Development branch. All day-to-day commits happen here.

## Commit Convention

All commit messages MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): description
```

### Types

| Type       | When to use                          |
| ---------- | ------------------------------------ |
| `feat`     | New feature or capability            |
| `fix`      | Bug fix                              |
| `refactor` | Code restructuring (no behavior change) |
| `docs`     | Documentation only                   |
| `chore`    | Tooling, config, dependencies        |

### Scopes (optional)

`game`, `ml`, `tools`, `engine`, `tests`

### Examples

```
feat(game): add swap rule detection
fix(ml): correct training data shuffle
refactor(engine): extract board evaluation
docs: add contributing guidelines
chore: update pytest config
```

## Workflow

### Daily Development

1. Start from `dev`: `git checkout dev`
2. Make changes and commit following the convention above.
3. Push to remote: `git push`

### Releasing to Master

When a batch of changes on `dev` is ready:

```bash
# 1. Switch to master
git checkout master

# 2. Squash merge from dev
git merge dev --squash -m "merge: <summary of changes>"

# 3. Push master
git push

# 4. Reset dev to match master
git checkout dev
git reset --hard master
git push --force-with-lease
```

> **Important**: Always reset `dev` after squash merging. This keeps `dev` in sync with `master` and prevents divergence.

## Git Aliases

The following aliases are configured for filtering commit history:

| Alias         | Command                                              | Shows                    |
| ------------- | ---------------------------------------------------- | ------------------------ |
| `git log-code`  | `log --oneline --grep='^feat\|^fix\|^refactor'`    | Code-related commits     |
| `git log-docs`  | `log --oneline --grep='^docs'`                     | Documentation commits    |
| `git log-chore` | `log --oneline --grep='^chore'`                    | Chore/config commits     |

Usage:

```bash
git log-code   # View only code changes
git log-docs   # View only documentation changes
git log-chore  # View only chore changes
```

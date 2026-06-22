export const meta = {
  name: 'parallel-changes',
  description: 'Implement git-workflow-conventions and model-drive-backup in parallel',
  phases: [
    { title: 'Git Workflow', detail: 'Set up master/dev branches, aliases, CONTRIBUTING.md' },
    { title: 'Drive Backup', detail: 'Create sync_drive.py CLI tool with OAuth2 and incremental sync' },
  ],
}

// Phase 1: Git workflow conventions
const gitResult = await agent(
  `Implement the git-workflow-conventions change.

Read the change artifacts at openspec/changes/git-workflow-conventions/ (proposal.md, design.md, specs/git-workflow/spec.md, tasks.md).

Then implement ALL tasks:

1. Create dev branch from master: git checkout -b dev && git push -u origin dev
2. Configure git aliases:
   - git config alias.log-code "log --oneline --grep='^feat\\\\|^fix\\\\|^refactor'"
   - git config alias.log-docs "log --oneline --grep='^docs'"
   - git config alias.log-chore "log --oneline --grep='^chore'"
3. Create CONTRIBUTING.md at project root with:
   - Branch strategy (master/dev, squash merge)
   - Commit convention (feat/fix/refactor/docs/chore with scope)
   - Workflow steps (develop on dev, squash merge to master, reset dev)
   - Git alias usage
4. Update AGENTS.md to add a reference to CONTRIBUTING.md
5. Commit on dev: git add CONTRIBUTING.md AGENTS.md && git commit -m "docs: add CONTRIBUTING.md and git workflow conventions"
6. Squash merge to master: git checkout master && git merge dev --squash -m "merge: git workflow conventions"
7. Push master: git push
8. Reset dev: git checkout dev && git reset --hard master && git push --force-with-lease

IMPORTANT: Read AGENTS.md first before modifying it. Write CONTRIBUTING.md in English.
After completing, mark all tasks as done in openspec/changes/git-workflow-conventions/tasks.md by changing [ ] to [x].`,
  { label: 'git-workflow', phase: 'Git Workflow' }
)

// Phase 2: Model Drive backup (parallel with Phase 1)
const driveResult = await agent(
  `Implement the model-drive-backup change.

Read the change artifacts at openspec/changes/model-drive-backup/ (proposal.md, design.md, specs/drive-sync/spec.md, tasks.md).

Then implement ALL tasks:

1. Update pyproject.toml to add dependencies: google-api-python-client, google-auth-oauthlib, google-auth-httplib2
2. Create tools/sync_drive.py as a CLI tool with:
   - argparse CLI with subcommands: auth, sync, status
   - OAuth2 authentication flow (credentials at ~/.config/gomoku/credentials.json, token at ~/.config/gomoku/token.json)
   - Incremental sync: list Drive files, compare with local ml/data/models/, upload only new files
   - Registry overwrite: always upload model_registry.jsonl and plan_registry.jsonl
   - Plan docs sync: detect new dirs in docs/ml/plans/archive/ and upload
   - --dry-run flag for sync: show what would be uploaded without doing it
   - status subcommand: show local vs Drive diff
   - Drive folder structure: gomoku-models/models/, gomoku-models/plans/, root registry files
   - Use MediaFileUpload with resumable=True for large files
   - Handle token refresh automatically
3. Update ml/mlevo_cli.py to add 'sync' subcommand that calls tools/sync_drive.py via subprocess
4. Create tests/test_sync_drive.py with unit tests for diff logic and CLI structure
5. Update pyproject.toml testpaths if needed

IMPORTANT:
- Read ml/mlevo_cli.py first to understand the argparse structure before adding the sync subcommand
- Read pyproject.toml before modifying
- The tool should work standalone: python tools/sync_drive.py auth/sync/status
- Store credentials in ~/.config/gomoku/ (not in project directory)
- Write all code in English (comments, docstrings, variable names)

After completing, mark all tasks as done in openspec/changes/model-drive-backup/tasks.md by changing [ ] to [x].`,
  { label: 'drive-backup', phase: 'Drive Backup' }
)

return { gitResult, driveResult }

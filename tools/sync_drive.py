#!/usr/bin/env python3
"""sync_drive.py — Google Drive model backup CLI.

Syncs model files, registry, and plan docs to Google Drive incrementally.
Credentials stored at ~/.config/gomoku/.
"""

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "ml" / "data" / "models"
REGISTRY_PATH = PROJECT_ROOT / "ml" / "data" / "model_registry.jsonl"
PLANS_REGISTRY_PATH = PROJECT_ROOT / "ml" / "data" / "plan_registry.jsonl"
PLANS_DIR = PROJECT_ROOT / "docs" / "ml" / "plans" / "archive"

CONFIG_DIR = Path.home() / ".config" / "gomoku"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"
TOKEN_PATH = CONFIG_DIR / "token.json"

DRIVE_FOLDER = "gomoku-models"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def compute_model_diff(local_dir: Path, drive_models: set) -> list[str]:
    if not local_dir.exists():
        return []
    local = {f.name for f in local_dir.iterdir() if f.suffix == ".gz" and f.name.endswith(".bin.gz")}
    return sorted(local - drive_models)


def compute_plan_diff(local_dir: Path, drive_plans: set) -> list[str]:
    if not local_dir.exists():
        return []
    local = {d.name for d in local_dir.iterdir() if d.is_dir()}
    return sorted(local - drive_plans)


def compute_sync_plan(local_models, drive_models, local_plans, drive_plans) -> dict:
    return {
        "models_to_upload": local_models if isinstance(local_models, list) else list(local_models),
        "plans_to_upload": local_plans if isinstance(local_plans, list) else list(local_plans),
        "registry_overwrite": True,
    }


def _get_drive_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                print(f"Error: {CREDENTIALS_PATH} not found.", file=sys.stderr)
                print("Download OAuth2 client secret from Google Cloud Console", file=sys.stderr)
                print(f"and save to: {CREDENTIALS_PATH}", file=sys.stderr)
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds)


def _find_or_create_folder(service, name, parent_id=None):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        metadata["parents"] = [parent_id]
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def _list_drive_files(service, folder_id):
    files = []
    page_token = None
    while True:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(name)", pageToken=page_token,
        ).execute()
        files.extend(f["name"] for f in results.get("files", []))
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return files


def _upload_file(service, local_path, folder_id):
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(str(local_path), resumable=True)
    metadata = {"name": local_path.name, "parents": [folder_id]}
    request = service.files().create(body=metadata, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Uploaded {int(status.progress() * 100)}%")
    print(f"  Done: {local_path.name}")


def _overwrite_file(service, local_path, folder_id):
    from googleapiclient.http import MediaFileUpload
    query = f"name='{local_path.name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    existing = results.get("files", [])
    media = MediaFileUpload(str(local_path), resumable=True)
    if existing:
        service.files().update(fileId=existing[0]["id"], media_body=media).execute()
        print(f"  Overwritten: {local_path.name}")
    else:
        metadata = {"name": local_path.name, "parents": [folder_id]}
        service.files().create(body=metadata, media_body=media).execute()
        print(f"  Uploaded: {local_path.name}")


def cmd_auth(args):
    if not CREDENTIALS_PATH.exists():
        print(f"credentials.json not found at: {CREDENTIALS_PATH}")
        print("\nTo set up:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Create OAuth 2.0 Client ID (Desktop app)")
        print("3. Download JSON and save as:")
        print(f"   {CREDENTIALS_PATH}")
        return
    print("Starting OAuth2 flow...")
    _get_drive_service()
    print(f"Authentication successful! Token cached at: {TOKEN_PATH}")


def cmd_sync(args):
    dry_run = getattr(args, "dry_run", False)
    print("Computing sync plan...")
    service = _get_drive_service()
    root_id = _find_or_create_folder(service, DRIVE_FOLDER)
    models_folder_id = _find_or_create_folder(service, "models", root_id)
    plans_folder_id = _find_or_create_folder(service, "plans", root_id)
    drive_model_names = set(_list_drive_files(service, models_folder_id))
    drive_plan_names = set(_list_drive_files(service, plans_folder_id))
    models_to_upload = compute_model_diff(MODELS_DIR, drive_model_names)
    plans_to_upload = compute_plan_diff(PLANS_DIR, drive_plan_names)

    print("\nSync plan:")
    if models_to_upload:
        total = sum((MODELS_DIR / f).stat().st_size for f in models_to_upload)
        print(f"  Models: {len(models_to_upload)} to upload ({_human_size(total)})")
        for f in models_to_upload:
            print(f"    + {f} ({_human_size((MODELS_DIR / f).stat().st_size)})")
    else:
        print("  Models: up to date")
    print(f"  Registry: will overwrite ({REGISTRY_PATH.name}, {PLANS_REGISTRY_PATH.name})")
    if plans_to_upload:
        print(f"  Plans: {len(plans_to_upload)} to upload")
        for p in plans_to_upload:
            print(f"    + {p}/")
    else:
        print("  Plans: up to date")

    if dry_run:
        print("\nDry run — nothing uploaded.")
        return

    print("\nUploading models...")
    for f in models_to_upload:
        _upload_file(service, MODELS_DIR / f, models_folder_id)
    print("Uploading registry...")
    _overwrite_file(service, REGISTRY_PATH, root_id)
    _overwrite_file(service, PLANS_REGISTRY_PATH, root_id)
    if plans_to_upload:
        print("Uploading plans...")
        for plan_name in plans_to_upload:
            plan_dir = PLANS_DIR / plan_name
            plan_folder_id = _find_or_create_folder(service, plan_name, plans_folder_id)
            for f in plan_dir.iterdir():
                if f.is_file():
                    _upload_file(service, f, plan_folder_id)
    print("\nSync complete!")


def cmd_status(args):
    print("Checking Drive status...")
    service = _get_drive_service()
    root_id = _find_or_create_folder(service, DRIVE_FOLDER)
    models_folder_id = _find_or_create_folder(service, "models", root_id)
    plans_folder_id = _find_or_create_folder(service, "plans", root_id)
    drive_model_names = set(_list_drive_files(service, models_folder_id))
    drive_plan_names = set(_list_drive_files(service, plans_folder_id))
    models_to_upload = compute_model_diff(MODELS_DIR, drive_model_names)
    plans_to_upload = compute_plan_diff(PLANS_DIR, drive_plan_names)

    print("\nModels:")
    if models_to_upload:
        for f in models_to_upload:
            print(f"  + {f} ({_human_size((MODELS_DIR / f).stat().st_size)}) — local only")
    else:
        print("  All synced")
    local_model_names = set()
    if MODELS_DIR.exists():
        local_model_names = {f.name for f in MODELS_DIR.iterdir() if f.name.endswith(".bin.gz")}
    for f in sorted(drive_model_names - local_model_names):
        print(f"  - {f} — Drive only")

    print("\nPlans:")
    if plans_to_upload:
        for p in plans_to_upload:
            print(f"  + {p}/ — local only")
    else:
        print("  All synced")
    local_plan_names = set()
    if PLANS_DIR.exists():
        local_plan_names = {d.name for d in PLANS_DIR.iterdir() if d.is_dir()}
    for p in sorted(drive_plan_names - local_plan_names):
        print(f"  - {p}/ — Drive only")


def main():
    parser = argparse.ArgumentParser(description="Sync models and metadata to Google Drive")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("auth", help="Authenticate with Google Drive")
    sync_p = sub.add_parser("sync", help="Sync files to Drive")
    sync_p.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    sub.add_parser("status", help="Show local vs Drive status")
    args = parser.parse_args()
    {"auth": cmd_auth, "sync": cmd_sync, "status": cmd_status}.get(args.command, lambda a: parser.print_help())(args)


if __name__ == "__main__":
    main()

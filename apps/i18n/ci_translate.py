#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import polib

from _translator.base import BaseTranslateManager
from _translator.utils import build_translator


REPO_ROOT = Path(__file__).resolve().parents[2]
I18N_ROOT = Path(__file__).resolve().parent


def _run_git(args: list[str]) -> str:
    out = subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True)
    return out


def _git_show_text(rev: str, relpath: str) -> str | None:
    try:
        return _run_git(["show", f"{rev}:{relpath}"])
    except subprocess.CalledProcessError:
        return None


def _read_json_text(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_text_from_git(rev: str, relpath: str) -> dict:
    txt = _git_show_text(rev, relpath)
    if not txt:
        return {}
    return json.loads(txt)


def _read_po_from_text(txt: str) -> polib.POFile:
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".po", delete=False) as f:
        f.write(txt)
        f.flush()
        name = f.name
    try:
        return polib.pofile(name)
    finally:
        try:
            os.unlink(name)
        except OSError:
            pass


def _read_po_from_git(rev: str, relpath: str) -> polib.POFile | None:
    txt = _git_show_text(rev, relpath)
    if not txt:
        return None
    return _read_po_from_text(txt)


def _read_po_from_fs(path: Path) -> polib.POFile:
    return polib.pofile(str(path))


def _changed_keys_json(base: dict, head: dict) -> set[str]:
    changed: set[str] = set()
    for k, v in head.items():
        if not k:
            continue
        if k not in base or base.get(k) != v:
            changed.add(k)
    return changed


def _po_translated_dict(po: polib.POFile) -> dict[str, str]:
    return {e.msgid: e.msgstr for e in po.translated_entries()}


def _changed_msgids_po(base_po: polib.POFile | None, head_po: polib.POFile) -> set[str]:
    base = _po_translated_dict(base_po) if base_po else {}
    head = _po_translated_dict(head_po)
    changed: set[str] = set()
    for msgid, msgstr in head.items():
        if msgid not in base or base.get(msgid) != msgstr:
            changed.add(msgid)
    return changed


@dataclass(frozen=True)
class WorkItem:
    # For json: kind="json", src points to zh.json
    # For po: kind="po", src points to zh/LC_MESSAGES/{django.po|djangojs.po}
    kind: str
    src_relpath: str


class _BulkTranslator(BaseTranslateManager):
    # Reuse BaseTranslateManager.bulk_translate
    pass


async def _translate_json_item(
    translator,
    module_dir: Path,
    zh_relpath: str,
    changed_keys: set[str],
    overwrite: bool,
):
    zh_path = REPO_ROOT / zh_relpath
    zh_dict = _read_json_text(zh_path)
    if not zh_dict:
        return

    mgr = _BulkTranslator(str(module_dir), translator)
    for file_prefix, target_lang in mgr.LANG_MAPPER.items():
        file_prefix = file_prefix.lower()
        if file_prefix == "zh":
            continue

        target_path = module_dir / f"{file_prefix}.json"
        target_dict = _read_json_text(target_path)

        to_update: dict[str, str] = {}
        for k in changed_keys:
            if k not in zh_dict:
                continue
            if overwrite or k not in target_dict:
                to_update[k] = zh_dict[k]

        if not to_update:
            continue
        translated = await mgr.bulk_translate(to_update, target_lang)
        target_dict.update(translated)
        target_path.write_text(
            json.dumps(target_dict, ensure_ascii=False, sort_keys=True, indent=4) + "\n",
            encoding="utf-8",
        )


async def _translate_po_item(
    translator,
    module_dir: Path,
    po_name: str,
    zh_relpath: str,
    changed_msgids: set[str],
    overwrite: bool,
):
    zh_path = REPO_ROOT / zh_relpath
    if not zh_path.exists():
        return
    zh_po = _read_po_from_fs(zh_path)
    zh_dict = _po_translated_dict(zh_po)
    if not zh_dict:
        return

    mgr = _BulkTranslator(str(module_dir), translator)
    for file_prefix, target_lang in mgr.LANG_MAPPER.items():
        if file_prefix == "zh":
            continue

        target_path = module_dir / file_prefix / "LC_MESSAGES" / po_name
        if not target_path.exists():
            continue

        trans_po = _read_po_from_fs(target_path)
        to_update: dict[str, str] = {}

        for msgid in changed_msgids:
            if msgid not in zh_dict:
                continue
            entry = trans_po.find(msgid)
            if not entry:
                continue
            if overwrite or (not entry.msgstr) or ("fuzzy" in entry.flags):
                to_update[msgid] = zh_dict[msgid]

        if not to_update:
            continue
        translated = await mgr.bulk_translate(to_update, target_lang)
        for msgid, msgstr in translated.items():
            entry = trans_po.find(msgid)
            if not entry:
                continue
            entry.flags = []
            entry.previous_msgid = None
            entry.msgstr = msgstr
        trans_po.save(str(target_path))


def _discover_work_items_from_diff(base: str, head: str) -> list[WorkItem]:
    changed_files = _run_git(["diff", "--name-only", f"{base}..{head}"]).splitlines()

    items: list[WorkItem] = []
    for p in changed_files:
        if not p.startswith("apps/i18n/"):
            continue

        # json modules
        if p.endswith("/zh.json") and "/LC_MESSAGES/" not in p:
            items.append(WorkItem(kind="json", src_relpath=p))
            continue

        # gettext sources
        if p.endswith("/zh/LC_MESSAGES/django.po") or p.endswith("/zh/LC_MESSAGES/djangojs.po"):
            items.append(WorkItem(kind="po", src_relpath=p))
            continue

    # de-dup
    uniq: dict[tuple[str, str], WorkItem] = {(i.kind, i.src_relpath): i for i in items}
    return list(uniq.values())


async def run_pr(base: str, head: str, overwrite: bool):
    translator = build_translator()
    items = _discover_work_items_from_diff(base, head)
    if not items:
        print("No i18n source changes detected; skip.")
        return

    for item in items:
        if item.kind == "json":
            module_dir = (REPO_ROOT / item.src_relpath).parent
            base_dict = _read_json_text_from_git(base, item.src_relpath)
            head_dict = _read_json_text(REPO_ROOT / item.src_relpath)
            changed = _changed_keys_json(base_dict, head_dict)
            if not changed:
                continue
            await _translate_json_item(translator, module_dir, item.src_relpath, changed, overwrite=overwrite)
        elif item.kind == "po":
            src_path = REPO_ROOT / item.src_relpath
            # .../core/zh/LC_MESSAGES/django.po -> module_dir=.../core
            module_dir = src_path.parents[2]
            po_name = src_path.name
            base_po = _read_po_from_git(base, item.src_relpath)
            head_po = _read_po_from_fs(src_path)
            changed = _changed_msgids_po(base_po, head_po)
            if not changed:
                continue
            await _translate_po_item(
                translator,
                module_dir,
                po_name=po_name,
                zh_relpath=item.src_relpath,
                changed_msgids=changed,
                overwrite=overwrite,
            )


async def run_full():
    # Full run: reuse existing translate logic, but load by file path
    # to avoid name conflicts with any third-party "translate" package.
    import importlib.util

    translate_path = I18N_ROOT / "translate.py"
    spec = importlib.util.spec_from_file_location("jumpserver_i18n_translate", translate_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Failed to load translate module from {translate_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    translator = build_translator()
    manager = mod.Translate(translator)
    await manager.run()


def main(argv: Iterable[str] | None = None):
    parser = argparse.ArgumentParser(description="JumpServer i18n CI translator")
    parser.add_argument("--mode", choices=["full", "pr"], required=True)
    parser.add_argument("--base", help="Base git sha (PR only)")
    parser.add_argument("--head", help="Head git sha (PR only)", default="HEAD")
    parser.add_argument(
        "--overwrite",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Overwrite existing translations for changed source keys/msgids",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.mode == "full":
        asyncio.run(run_full())
        return

    if not args.base:
        raise SystemExit("--base is required for --mode pr")
    asyncio.run(run_pr(args.base, args.head, overwrite=args.overwrite))


if __name__ == "__main__":
    main()

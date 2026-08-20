"""A realistic use case: migrating a batch of files with an AI agent call
per file, resumable if the process dies partway through.

Run it, kill it (Ctrl+C) partway, run it again with the same command -
it picks up exactly where it left off instead of reprocessing everything.
No LLM calls here (kept dependency-free) - `convert_file` stands in for
whatever real per-file work you'd actually do (e.g. an Agent SDK call).
"""
import time

from caravanserai import resumable_iterate


def convert_file(filename: str) -> None:
    print(f"  converting {filename}...")
    time.sleep(1)  # stand-in for a real LLM call / slow operation


def all_js_files() -> list[str]:
    return [f"module_{i}.js" for i in range(1, 11)]


if __name__ == "__main__":
    for f in resumable_iterate(all_js_files(), run_id="js-to-ts-migration"):
        convert_file(f)
        print(f"  done: {f}")

    print("migration complete.")

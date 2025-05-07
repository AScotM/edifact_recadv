import os
import hashlib

def compute_blake2b(filepath):
    hasher = hashlib.blake2b(digest_size=32)  # 256-bit hash
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def check_folders_hash(folders=["output", "export"]):
    print(f"{'File Path':<60} | {'BLAKE2b-256 Hash'}")
    print("-" * 100)

    for folder in folders:
        if not os.path.isdir(folder):
            print(f"[!] Folder not found: {folder}")
            continue
        for root, _, files in os.walk(folder):
            for name in files:
                full_path = os.path.join(root, name)
                try:
                    hash_value = compute_blake2b(full_path)
                    print(f"{full_path:<60} | {hash_value}")
                except Exception as e:
                    print(f"[Error reading {full_path}]: {e}")

if __name__ == "__main__":
    check_folders_hash()

<div align="center">

# MiniFAT

A FAT-inspired virtual file system implemented from scratch in Python.  
Simulates a real disk using a binary image and exposes a full interactive shell.

<br/>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-brightgreen?style=flat-square)
![Dependencies](https://img.shields.io/badge/Dependencies-None-orange?style=flat-square)

</div>

---

## What is MiniFAT?

MiniFAT is a userspace implementation of a FAT-style file system. It stores everything inside a single binary file (`minifat.bin`) divided into fixed-size clusters. A FAT table tracks cluster chains, a directory manager handles 8.3-format entries, and a shell provides a familiar command-line interface — all written in pure Python with zero external dependencies.

---

## Quick Start

```bash
git clone https://github.com/your-username/minifat.git
cd minifat
python main.py
```

`minifat.bin` is created automatically on first run. The disk persists between sessions.

```
MiniFAT Shell initialized!

T:\> md docs
T:\> cd docs
T:\docs\> touch readme.txt
T:\docs\> echo "hello world" readme.txt
T:\docs\> cat readme.txt
hello world
T:\docs\> ls
<FILE>    readme.txt    11
```

---

## Architecture

```
             shell.py  ─── user commands
                 │
           FileSystem.py  ─── file & directory API
          /      │       \
 FatTableManager  DirectoryManager  Converter
          \      │       /
           VirtualDisk  ─── raw cluster I/O on minifat.bin
```

| Module | Role |
|--------|------|
| `shell.py` | CLI shell — input parsing and command dispatch |
| `FileSystem.py` | Orchestrates FAT, directory, and disk operations |
| `fat_table_manager.py` | Cluster allocation, chaining, FAT persistence |
| `directory_manager.py` | 8.3 directory entries — read, write, remove |
| `virtual_disk.py` | Low-level `ReadCluster` / `WriteCluster` on the binary file |
| `superblock_manager.py` | Superblock read/write |
| `Converter.py` | UTF-8 string ↔ bytes |
| `fs_constants.py` | Disk layout constants |

---

## Disk Layout

**Total size: 1 MB** (1024 clusters × 1024 bytes)

| Region | Clusters | Purpose |
|--------|----------|---------|
| Superblock | 0 | File system metadata |
| FAT Table | 1 – 4 | Cluster chain map |
| Root Directory | 5 | Top-level directory entries |
| Data | 6 – 1023 | File and subdirectory content |

Each FAT entry is a 4-byte signed integer: `0` = free, `-1` = end of chain, `N` = next cluster.  
Each directory entry is 32 bytes and uses the classic 8.3 filename format.

---

## Shell Commands

| Command | Description |
|---------|-------------|
| `ls [dir]` | List directory contents |
| `cd <dir>` / `cd ..` | Navigate directories |
| `md <dir>` | Create a directory |
| `rd <dir>` | Remove an empty directory |
| `touch <file>` | Create an empty file |
| `cat <file>` | Print file contents |
| `echo "text" <file>` | Write text to a file |
| `echo "text" <file> --append` | Append text to a file |
| `cp <src> <dst>` | Copy a file |
| `mv <src> <dst>` | Move or rename a file |
| `rm <file>` | Delete a file |
| `help` / `cls` / `exit` | Utility commands |

---

## Key Design Decisions

- **Immediate persistence** — every write is flushed with `os.fsync`. No write buffering; the disk is always consistent.
- **Dynamic directories** — a directory cluster chain grows automatically when its entries exceed capacity.
- **8.3 filenames** — names are uppercased and truncated to `FILENAME.EXT` format on write, with a warning printed if truncation occurs.
- **Chain integrity** — `FollowChain` detects cycles at runtime and raises a `RuntimeError` on corruption.

---

## Configuration

```python
# fs_constants.py
CLUSTER_SIZE  = 1024   # bytes per cluster
CLUSTER_COUNT = 1024   # number of clusters  →  1 MB disk

SUPERBLOCK_CLUSTER     = 0
FAT_START_CLUSTER      = 1
FAT_END_CLUSTER        = 4
ROOT_DIR_FIRST_CLUSTER = 5
CONTENT_START_CLUSTER  = 6
```

To scale the disk, increase `CLUSTER_COUNT` and extend `FAT_END_CLUSTER` so the FAT region fits `CLUSTER_COUNT × 4` bytes.

---

## License

[MIT](LICENSE)

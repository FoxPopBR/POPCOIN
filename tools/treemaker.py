# treemaker.py

import os
import pathlib
from tools.config_treemaker import get_config, get_icon_for_extension, get_folder_icon

PIPE = "│"
ELBOW = "└──"
TEE = "├──"
PIPE_PREFIX = "│   "
SPACE_PREFIX = "    "

class TreeGenerator:
    def __init__(self, root_dir):
        self.root_dir = pathlib.Path(root_dir)
        self.config = get_config()

    def generate_tree(self):
        tree = [f"{get_folder_icon({'name': self.root_dir.name, 'files': list(self.root_dir.iterdir())}, root=True)} {self.root_dir.name}/"]
        self._generate_tree_body(self.root_dir, "", tree)
        return tree

    def _generate_tree_body(self, directory, prefix, tree):
        entries = list(directory.iterdir())
        # Filtragem para remover diretórios e extensões ignorados, além de arquivos especificados
        entries = [entry for entry in entries if not any(entry.name.endswith(ext) for ext in self.config['ignore_exts']) and entry.name not in self.config['ignore_dirs'] and entry.name not in self.config.get('ignore_files', [])]

        entries.sort(key=lambda entry: (entry.is_dir(), os.path.splitext(entry.name)[1], entry.name))
        entries_count = len(entries)

        for index, entry in enumerate(entries):
            connector = ELBOW if index == entries_count - 1 else TEE
            if entry.is_dir():
                folder_info = {'name': entry.name, 'files': list(entry.iterdir())}
                icon = get_folder_icon(folder_info)
                tree.append(f"{prefix}{connector} {icon} {entry.name}/")
                new_prefix = f"{prefix}{PIPE_PREFIX if index != entries_count - 1 else SPACE_PREFIX}"
                self._generate_tree_body(entry, new_prefix, tree)
            else:
                file_ext = os.path.splitext(entry.name)[1]
                icon = get_icon_for_extension(file_ext)
                tree.append(f"{prefix}{connector} {icon} {entry.name}")

if __name__ == "__main__":
    root_dir = pathlib.Path(__file__).resolve().parent
    generator = TreeGenerator(root_dir)
    tree = generator.generate_tree()
    print("\n".join(tree))

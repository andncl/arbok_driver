import importlib
import sys
import pkgutil
from types import ModuleType
from typing import Any, Dict, List


class _NamespaceNode:
    """Container for dynamically attached attributes."""

    def __init__(self) -> None:
        self.__dict__: Dict[str, Any] = {}

    def __repr__(self) -> str:
        return f"<NamespaceNode {list(self.__dict__.keys())}>"


class Ekans:
    """
    Ekans object providing a dynamic, reloadable view of a package.

    Attributes from submodules are flattened one level up, enabling:

        ekans.analysis.DecayFit

    instead of:

        ekans.analysis.decay_fit.DecayFit

    The module hierarchy is preserved internally using namespace nodes.
    """

    _root_module: ModuleType

    def __init__(self, root_module: ModuleType) -> None:
        if not isinstance(root_module, ModuleType):
            raise TypeError(
                f"root_module must be a Python module, got {type(root_module)}"
            )
        self._root_module = root_module
        self.reload_modules()

    def reload_modules(self) -> None:
        """Reload all modules and rebuild the attribute tree."""
        module_names: List[str] = self._collect_module_names()
        module_names.sort(key=lambda name: name.count("."), reverse=True)
        # Module name order is reversed to reload leaf modules first, root last
        self._import_or_reload_modules(module_names)
        self._build_attribute_tree(module_names)

    def _collect_module_names(self) -> List[str]:
        root = self._root_module
        module_names: List[str] = [root.__name__]

        if hasattr(root, "__path__"):
            for module_info in pkgutil.walk_packages(
                root.__path__, prefix=root.__name__ + "."
            ):
                module_names.append(module_info.name)
        return module_names

    def _import_or_reload_modules(self, module_names: List[str]) -> None:
        """Walks through module names and imports/ reloads all"""
        for name in module_names:
            try:
                if name in sys.modules:
                    module = sys.modules[name]
                    if getattr(module, "__spec__", None) is not None:
                        importlib.reload(module)
                else:
                    importlib.import_module(name)

            except Exception as e:
                print(f"Error importing {name}: {e}")
                raise e

    def _build_attribute_tree(self, module_names: List[str]) -> None:
        """
        Build namespace in two phases:
        1. Create full tree (packages + modules)
        2. Attach __all__ exports
        """

        # --- 1. Clear existing public attributes ---
        for key in list(self.__dict__.keys()):
            if not key.startswith("_"):
                delattr(self, key)

        root_name = self._root_module.__name__
        root_prefix = root_name + "."

        # Keep track of nodes for second pass
        node_map: Dict[str, Any] = {}

        # --- 2. First pass: build structure only ---
        for full_name in module_names:
            module = sys.modules.get(full_name)
            if not isinstance(module, ModuleType):
                continue

            if full_name == root_name:
                parts: List[str] = []
            else:
                parts = full_name[len(root_prefix):].split(".")

            parent: Any = self

            for part in parts[:-1]:
                if not hasattr(parent, part):
                    setattr(parent, part, _NamespaceNode())
                parent = getattr(parent, part)

            if not parts:
                node = self
                node_map[full_name] = node
                continue

            name = parts[-1]

            if hasattr(module, "__path__"):
                if not hasattr(parent, name):
                    setattr(parent, name, _NamespaceNode())
                node = getattr(parent, name)
            else:
                # attach leaf module
                setattr(parent, name, module)
                node = module  # not used for exports

            node_map[full_name] = node

        # --- 3. Second pass: attach __all__ exports ---
        for full_name, node in node_map.items():
            module = sys.modules.get(full_name)
            if not isinstance(module, ModuleType):
                continue

            # Only attach to namespace nodes (i.e. packages)
            if not hasattr(module, "__path__") and full_name != root_name:
                continue

            public_names = getattr(module, "__all__", [])

            for attr_name in public_names:
                try:
                    value = getattr(module, attr_name)
                except AttributeError:
                    continue

                setattr(node, attr_name, value)

    def _attach_module_attributes(self, node, module):
        # Only respect explicit API
        public_names = getattr(module, "__all__", [])

        for attr_name in public_names:
            try:
                value = getattr(module, attr_name)
            except AttributeError:
                continue
            setattr(node, attr_name, value)

    def _get_submodules(self, module: ModuleType) -> List[ModuleType]:
        """Gets submodules"""
        prefix = module.__name__ + "."
        return [
            m for name, m in sys.modules.items()
            if name.startswith(prefix)
            and isinstance(m, ModuleType)
            and name.count(".") == prefix.count(".")  # direct children only
        ]
"""Repeatable static project inventory (no third-party static analyser required).

Run: python tools/audit_project.py --output results/audit/project_metrics.json
This is an architecture diagnostic, not proof of correctness or security.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from pathlib import Path
import json


def inventory(root: Path) -> dict:
    package = root / 'biosphere'
    python_files = sorted(package.glob('*.py'))
    modules = {f.stem for f in python_files}
    dependencies: dict[str, list[str]] = {}
    stats: list[dict] = []
    for file in python_files:
        contents = file.read_text(encoding='utf-8')
        tree = ast.parse(contents, filename=str(file))
        edges = set()
        def import_edges(node):
            # Type-only imports are not runtime cycles.
            if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == 'TYPE_CHECKING':
                return
            if isinstance(node, ast.ImportFrom) and node.level and node.module:
                root_name = node.module.split('.')[0]
                if root_name in modules:
                    edges.add(root_name)
            for child in ast.iter_child_nodes(node):
                import_edges(child)
        import_edges(tree)
        dependencies[file.stem] = sorted(edges)
        functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        large = [dict(name=node.name, line=node.lineno, lines=node.end_lineno - node.lineno + 1)
                 for node in functions if node.end_lineno - node.lineno + 1 > 75]
        stats.append({'module': file.name, 'lines': len(contents.splitlines()),
                      'functions': len(functions), 'large_functions': large})
    cycles = []
    # DFS detects graph cycles beyond immediate mutually importing pairs.
    visited, active = set(), set()
    def walk(module: str, path: list[str]):
        if module in active:
            cycle = path[path.index(module):]
            if cycle not in cycles:
                cycles.append(cycle)
            return
        if module in visited: return
        active.add(module)
        for dep in dependencies[module]:
            walk(dep, path + [dep])
        active.remove(module)
        visited.add(module)
    for module in sorted(modules): walk(module, [module])
    paths = [p for p in root.rglob('*') if p.is_file() and not any(part in
             ('__pycache__', '.pytest_cache', '.venv') for part in p.relative_to(root).parts)]
    results = root / 'results'
    return {
        'source_files': len(python_files),
        'package_loc': sum(item['lines'] for item in stats),
        'test_files': len(list((root / 'tests').glob('test_*.py'))),
        'source_modules': stats,
        'package_dependencies': dependencies,
        'import_cycles': cycles,
        'historical_results_bytes': sum(p.stat().st_size for p in results.rglob('*') if p.is_file())
            if results.exists() else 0,
        'python_source_bytes': sum(p.stat().st_size for p in python_files),
        'repo_total_bytes_excluding_cache': sum(p.stat().st_size for p in paths),
        'has_git_repository': (root / '.git').is_dir(),
        'note': 'Static AST and file-size inventory. Coverage and graphical QA run separately.'
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = inventory(root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('source_files', 'package_loc',
        'test_files', 'import_cycles', 'historical_results_bytes',
        'python_source_bytes', 'has_git_repository')}, indent=2))


if __name__ == '__main__':
    main()

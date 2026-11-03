import sys
import json
from pathlib import Path
from project_infra import cli  # Include the console command in the shared frozen module archive.
from project_infra.desktop import main, load_recent, application_directory

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--check-ui':
        # Optional portable-runtime diagnostic, without selecting a project or opening a browser.
        def ready(root, shutdown):
            from project_infra.reviewer_runtime import environment
            from project_infra.store import Store
            recent = load_recent(application_directory())
            Path(sys.argv[2]).write_text(json.dumps({'title': root.title(), 'visible': bool(root.winfo_viewable()),
                'tk': str(root.tk.call('info', 'patchlevel')),
                'projects': [str(p) for p in recent],
                'reviewer_environment': environment(Store(recent[0])) if recent else None}), encoding='utf-8')
            shutdown()
        main(startup=False, on_ready=ready)
    else:
        main()

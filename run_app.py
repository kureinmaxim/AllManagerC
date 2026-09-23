#!/usr/bin/env python3
"""Launch AllManagerC from its project directory using the shared GUI entry point."""
import os
from pathlib import Path
import runpy


def main():
    project = Path(__file__).resolve().parent
    os.chdir(project)
    runpy.run_path(str(project / 'app.py'), run_name='__main__')


if __name__ == '__main__':
    main()

"""
main.py
=======
Entry point for the Dynamic Pathfinding Agent.

Run:
    python main.py

This module only owns the console prompt and launches the App.
All logic lives in: constants.py · grid.py · algorithms.py · button.py · app.py
"""

from app import App


def get_grid_dimensions() -> tuple:
    print("\n╔════════════════════════════════════╗")
    print("║   Dynamic Pathfinding Agent  v1.0  ║")
    print("╠════════════════════════════════════╣")
    print("║  Algorithms : GBFS  |  A*          ║")
    print("║  Heuristics : Manhattan | Euclidean ║")
    print("╚════════════════════════════════════╝\n")
    while True:
        try:
            rows = int(input("  Enter number of ROWS    (5–60): ").strip())
            cols = int(input("  Enter number of COLUMNS (5–60): ").strip())
            if 5 <= rows <= 60 and 5 <= cols <= 60:
                return rows, cols
            print("  ⚠  Values must be between 5 and 60.\n")
        except ValueError:
            print("  ⚠  Please enter whole numbers.\n")


def main():
    rows, cols = get_grid_dimensions()
    print(f"\n  ✓ Launching {rows} × {cols} grid …\n")
    App(rows, cols).run()


if __name__ == "__main__":
    main()

import cProfile
import pstats
import io
import sys
from main_gui2 import main  # Replace 'your_app_module' with your actual module name

def profile_app():
    pr = cProfile.Profile()
    pr.enable()
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
    pr.disable()
    s = io.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    with open('profile_output.txt', 'w') as f:
        f.write(s.getvalue())

if __name__ == "__main__":
    profile_app()

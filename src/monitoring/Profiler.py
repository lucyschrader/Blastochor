import cProfile
import pstats
from datetime import datetime

profiler = cProfile.Profile()


def output_profile():
    profile_stats = pstats.Stats(profiler)
    profile_stats.strip_dirs()
    now = datetime.now().strftime("%Y%m%d-%H_%M_%S")
    profile_stats.dump_stats("src/logging/{}.prof".format(now))

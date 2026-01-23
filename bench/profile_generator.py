import cProfile
import pstats
from io import StringIO

from uaforge.core.generator import UserAgentGenerator


def profile(n=2000):
    gen = UserAgentGenerator()
    # warmup
    for _ in range(100):
        gen.generate()

    pr = cProfile.Profile()
    pr.enable()
    for _ in range(n):
        gen.generate()
    pr.disable()

    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumtime')
    ps.print_stats(40)
    print(s.getvalue())

if __name__ == '__main__':
    profile(5000)

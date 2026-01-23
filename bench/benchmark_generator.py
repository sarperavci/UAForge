import time
import argparse
from statistics import mean

from uaforge.core.generator import UserAgentGenerator


def run_benchmark(n: int, seed: int = None):
    gen = UserAgentGenerator(seed=seed)
    # warmup
    for _ in range(100):
        gen.generate()

    times = []
    t0 = time.perf_counter()
    for _ in range(n):
        s = time.perf_counter()
        gen.generate()
        e = time.perf_counter()
        times.append((e - s) * 1000)
    t1 = time.perf_counter()

    print(f"Total: {(t1-t0)*1000:.2f} ms for {n} runs")
    print(f"Mean per-call: {mean(times):.4f} ms (min: {min(times):.4f} ms, max: {max(times):.4f} ms)")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('-n', type=int, default=1000)
    p.add_argument('--seed', type=int, default=None)
    args = p.parse_args()
    run_benchmark(args.n, args.seed)

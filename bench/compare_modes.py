import time
from statistics import mean

from uaforge.core.generator import UserAgentGenerator


def benchmark_with_seed(seed: int, n: int):
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
    
    print(f"\nSeed {seed if seed is not None else 'None'}:")
    print(f"  Total: {(t1-t0)*1000:.2f} ms for {n} runs")
    print(f"  Mean:  {mean(times):.4f} ms per call")
    print(f"  Min:   {min(times):.4f} ms")
    print(f"  Max:   {max(times):.4f} ms")
    
    return mean(times)


if __name__ == '__main__':
    n = 10000
    
    print("Testing performance across different seeds:")
    print("="*50)
    
    times = []
    for seed in [None, 42, 123, 999]:
        t = benchmark_with_seed(seed, n)
        times.append(t)
    
    avg_time = mean(times)
    print(f"\n{'='*50}")
    print(f"Average: {avg_time:.4f} ms per call")
    print(f"Throughput: ~{int(1000/avg_time):,} user agents/second")
    print(f"{'='*50}")

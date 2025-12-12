from collections import Counter
from uaforge.core.generator import UserAgentGenerator
import sys
import os
 
def run_distribution_check():
    print("Running Statistical Validation (n=10,000)...")
    generator = UserAgentGenerator()
    
    stats = Counter()
    total = 10000
    
    for _ in range(total):
        ua = generator.generate()
        stats[ua.meta_browser.value] += 1

    print(f"\n{'BROWSER':<15} | {'COUNT':<8} | {'SHARE %':<8}")
    print("-" * 40)
    
    for browser, count in stats.most_common():
        percentage = (count / total) * 100
        print(f"{browser:<15} | {count:<8} | {percentage:.2f}%")

    print("\nCompare these % values with your market_share.json inputs.")
    print("Chrome/Android Chrome should dominate (~65%+ combined).")

if __name__ == "__main__":
    run_distribution_check()

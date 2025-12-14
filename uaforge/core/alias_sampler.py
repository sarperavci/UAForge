import random
from typing import List


class AliasSampler:
    """
    O(1) weighted random sampler using Vose's Alias Method.
    
    Usage:
        sampler = AliasSampler(weights, rng)
        index = sampler.sample()  # O(1) per call
    """
    
    def __init__(self, weights: List[float], rng=None):
        """
        Preprocess weights into alias table.
        
        Args:
            weights: List of weights (need not sum to 1, will be normalized)
            rng: Random instance to use (defaults to random module)
        """
        self.rng = rng if rng is not None else random
        n = len(weights)
        
        if n == 0:
            raise ValueError("Cannot create AliasSampler with empty weights")
        
        self.n = n
        
        # Normalize weights
        total = sum(weights)
        if total <= 0:
            raise ValueError("Sum of weights must be positive")
        
        # probabilities normalized to sum to n (for the algorithm)
        prob = [w * n / total for w in weights]
        
        # Alias tables
        self.prob = [0.0] * n
        self.alias = [0] * n
        
        # Partition into small and large
        small = []
        large = []
        
        for i, p in enumerate(prob):
            if p < 1.0:
                small.append(i)
            else:
                large.append(i)
        
        # Build alias table
        while small and large:
            l = small.pop()
            g = large.pop()
            
            self.prob[l] = prob[l]
            self.alias[l] = g
            
            prob[g] = prob[g] + prob[l] - 1.0
            
            if prob[g] < 1.0:
                small.append(g)
            else:
                large.append(g)
        
        # Remaining items (due to floating point, both could have leftovers)
        while large:
            g = large.pop()
            self.prob[g] = 1.0
        
        while small:
            l = small.pop()
            self.prob[l] = 1.0
    
    def sample(self) -> int:
        """Sample an index in O(1) time."""
        # Generate fair die roll
        i = self.rng.randrange(self.n)
        # Flip biased coin
        if self.rng.random() < self.prob[i]:
            return i
        else:
            return self.alias[i]
    
    def sample_n(self, n: int) -> List[int]:
        """Sample n indices efficiently."""
        return [self.sample() for _ in range(n)]

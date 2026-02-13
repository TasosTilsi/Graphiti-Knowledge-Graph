"""Batch accumulator for grouping items before processing.

Accumulates items until batch_size is reached, then returns the full batch.
Used for both git commit batching (10 commits at a time) and conversation
capture (10 turns at a time).

Default batch size is 10 per user decision.
"""

from typing import Any, Optional


class BatchAccumulator:
    """Generic batch accumulator that groups items until batch_size reached.
    
    Accumulates items and returns them in batches when batch_size is reached.
    Supports partial flush for shutdown/timeout scenarios.
    
    Example:
        >>> accumulator = BatchAccumulator(batch_size=3)
        >>> accumulator.add("item1")  # Returns None
        >>> accumulator.add("item2")  # Returns None
        >>> batch = accumulator.add("item3")  # Returns ["item1", "item2", "item3"]
        >>> len(accumulator)  # 0 (cleared after batch returned)
    """
    
    def __init__(self, batch_size: int = 10):
        """Initialize batch accumulator.
        
        Args:
            batch_size: Number of items to accumulate before returning batch.
                Default: 10 (per user decision from Phase 6 context)
        """
        self.batch_size = batch_size
        self._items: list[Any] = []
    
    def add(self, item: Any) -> Optional[list[Any]]:
        """Add item to batch.
        
        Returns full batch list when batch_size is reached, None otherwise.
        Clears internal list after returning batch.
        
        Args:
            item: Item to add to batch
        
        Returns:
            List of batch_size items when batch is ready, None otherwise
        
        Example:
            >>> acc = BatchAccumulator(batch_size=2)
            >>> acc.add("a")  # None
            >>> acc.add("b")  # ["a", "b"]
        """
        self._items.append(item)
        
        if len(self._items) >= self.batch_size:
            batch = self._items
            self._items = []
            return batch
        
        return None
    
    def flush(self) -> list[Any]:
        """Force-flush partial batch.
        
        Returns current items and clears internal list. Used for shutdown
        or timeout scenarios where you need to process remaining items
        even if batch isn't full.
        
        Returns:
            List of current items (may be empty or partial)
        
        Example:
            >>> acc = BatchAccumulator(batch_size=10)
            >>> acc.add("a")
            >>> acc.add("b")
            >>> acc.flush()  # ["a", "b"] (partial batch)
        """
        batch = self._items
        self._items = []
        return batch
    
    def __len__(self) -> int:
        """Current number of items in accumulator.
        
        Returns:
            Number of items waiting to form a batch
        """
        return len(self._items)
    
    def is_empty(self) -> bool:
        """Check if accumulator has no items.
        
        Returns:
            True if accumulator is empty, False otherwise
        """
        return len(self._items) == 0
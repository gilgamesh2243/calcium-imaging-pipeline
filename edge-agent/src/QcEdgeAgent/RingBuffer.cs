using System.Collections.Concurrent;

namespace QcEdgeAgent;

/// <summary>
/// Thread-safe bounded ring buffer for frames.
/// When full, the oldest frame is dropped (never blocks the producer).
/// </summary>
public sealed class RingBuffer<T>
{
    private readonly ConcurrentQueue<T> _queue = new();
    private readonly int _capacity;
    private int _droppedCount;

    public RingBuffer(int capacity)
    {
        if (capacity <= 0) throw new ArgumentOutOfRangeException(nameof(capacity));
        _capacity = capacity;
    }

    public int Count => _queue.Count;
    public int DroppedCount => _droppedCount;

    /// <summary>Enqueue an item; drops the oldest if at capacity.</summary>
    public void Enqueue(T item)
    {
        // If full, drop the oldest item
        while (_queue.Count >= _capacity)
        {
            _queue.TryDequeue(out _);
            Interlocked.Increment(ref _droppedCount);
        }
        _queue.Enqueue(item);
    }

    /// <summary>Try to dequeue; returns false if empty.</summary>
    public bool TryDequeue(out T? item) => _queue.TryDequeue(out item);

    /// <summary>Try to peek at the next item without removing it.</summary>
    public bool TryPeek(out T? item) => _queue.TryPeek(out item);
}

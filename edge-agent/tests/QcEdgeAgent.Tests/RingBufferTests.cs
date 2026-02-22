using Xunit;
using QcEdgeAgent;

namespace QcEdgeAgent.Tests;

public class RingBufferTests
{
    [Fact]
    public void Enqueue_BelowCapacity_AllItemsPresent()
    {
        var buf = new RingBuffer<int>(5);
        buf.Enqueue(1);
        buf.Enqueue(2);
        buf.Enqueue(3);

        Assert.Equal(3, buf.Count);
        Assert.Equal(0, buf.DroppedCount);
    }

    [Fact]
    public void Enqueue_AtCapacity_OldestDropped()
    {
        var buf = new RingBuffer<int>(3);
        buf.Enqueue(1);
        buf.Enqueue(2);
        buf.Enqueue(3);
        buf.Enqueue(4); // should drop 1

        Assert.Equal(3, buf.Count);
        Assert.True(buf.DroppedCount >= 1);
    }

    [Fact]
    public void TryDequeue_EmptyBuffer_ReturnsFalse()
    {
        var buf = new RingBuffer<int>(5);
        Assert.False(buf.TryDequeue(out _));
    }

    [Fact]
    public void TryDequeue_NonEmpty_ReturnsItem()
    {
        var buf = new RingBuffer<int>(5);
        buf.Enqueue(42);
        var ok = buf.TryDequeue(out var item);
        Assert.True(ok);
        Assert.Equal(42, item);
    }

    [Fact]
    public void NeverBlocks_WhenFull_ProducerContinues()
    {
        var buf = new RingBuffer<int>(10);
        // Enqueue 100 items into a buffer of size 10 – should never throw
        for (int i = 0; i < 100; i++)
            buf.Enqueue(i);

        Assert.Equal(10, buf.Count);
        Assert.True(buf.DroppedCount > 0);
    }
}

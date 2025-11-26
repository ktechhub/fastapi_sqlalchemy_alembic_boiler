# Redis Streams Implementation Guide

## Overview

This implementation migrates the Redis message queue system from Lists/Sorted Sets to Redis Streams with proper message acknowledgements and consumer groups.

## Key Changes

### 1. **Message Publishing (`redis_push.py`)**

**Before (Lists/Sorted Sets):**
- Immediate messages: `LPUSH` to Redis Lists
- Delayed messages: `ZADD` to Sorted Sets with timestamp scores

**After (Redis Streams):**
- Immediate messages: `XADD` with auto-generated IDs
- Delayed messages: `XADD` with timestamp-based IDs (format: `{timestamp_ms}-0`)

**Example:**
```python
# Immediate message
await redis_push_async(message, delay_seconds=0)

# Delayed message (5 minutes)
await redis_push_async(message, delay_seconds=300)
```

### 2. **Message Consumption (`redis_main.py`)**

**Before:**
- Used `BRPOP` to block and pop from Lists
- No acknowledgements - messages lost if consumer crashes
- Manual load balancing with multiple consumers

**After:**
- Uses `XREADGROUP` with consumer groups
- Automatic load balancing across consumers
- Messages acknowledged with `XACK` after successful processing
- Pending Entry List (PEL) for failed message retries

**Key Features:**
- **Consumer Groups**: Automatic load balancing
- **Acknowledgements**: Messages only removed after `XACK`
- **Pending Messages**: Failed messages stay in PEL for retry
- **Timestamp Validation**: Skips future-dated messages automatically

### 3. **Delayed Message Processing (`delayed_msgs.py`)**

**Before:**
- Polled Sorted Sets with `ZRANGEBYSCORE`
- Moved ready messages back to Lists

**After:**
- Monitors Redis Streams for ready delayed messages
- Uses `XRANGE` to find messages with timestamps <= current time
- Messages are automatically consumed by main consumer when ready

### 4. **Consumer Group Management (`stream_consumer_groups.py`)**

New utility module for managing consumer groups:
- `ensure_consumer_group()`: Creates consumer groups on startup
- `initialize_consumer_groups()`: Sets up groups for all queues
- `get_pending_messages()`: Retrieves unacknowledged messages
- `claim_pending_messages()`: Claims idle messages from failed consumers
- `get_consumer_group_info()`: Gets group statistics

## How It Works

### Message Flow

1. **Producer** calls `redis_push_async(message, delay_seconds=0)`
   - Message added to stream: `{queue_name}:stream`
   - For delayed messages, ID format: `{future_timestamp_ms}-0`

2. **Consumer** reads with `XREADGROUP`
   - Reads from consumer group: `main-group`
   - Each consumer has unique name: `{hostname}-{pid}`
   - Messages distributed across consumers automatically

3. **Processing**
   - Consumer validates message timestamp (skips future messages)
   - Processes message
   - On success: `XACK` removes from PEL
   - On failure: Message stays in PEL for retry

4. **Pending Messages**
   - Background task checks PEL every 60 seconds
   - Claims messages idle > 60 seconds
   - Retries processing

### Stream Structure

```
Stream Name: {queue_name}:stream
Consumer Group: main-group
Consumer Names: {hostname}-{pid}

Message Format:
{
  "data": "{json_encoded_message}",
  ...
}

Message ID Format:
- Immediate: Auto-generated (e.g., "1234567890123-0")
- Delayed: Timestamp-based (e.g., "1234567895000-0")
```

## Benefits

### 1. **Message Durability**
- Messages persist until acknowledged
- No message loss on consumer crashes
- Automatic retry via PEL

### 2. **Load Balancing**
- Consumer groups automatically distribute messages
- No manual queue assignment needed
- Easy horizontal scaling

### 3. **Observability**
- Track pending messages per consumer
- Monitor consumer group health
- Better debugging capabilities

### 4. **Performance**
- More efficient than Lists for high throughput
- Better memory usage than Sorted Sets
- Supports batch operations

## Migration Notes

### Backward Compatibility

The old `redis_lpush()` function still works but now uses Streams internally. However, you should migrate to `redis_push_async()` for async operations.

### Consumer Group Initialization

Consumer groups are automatically created on first startup. If you need to reset:
```python
# Delete and recreate consumer group
await redis_client.xgroup_destroy(stream_name, group_name)
await ensure_consumer_group(stream_name, group_name)
```

### Monitoring

Check consumer group status:
```python
from app.services.stream_consumer_groups import get_consumer_group_info

info = await get_consumer_group_info("notifications:stream", "main-group")
print(f"Pending: {info['pending']}, Consumers: {info['consumers']}")
```

## Configuration

No configuration changes needed. The system uses existing `QUEUE_NAMES` setting.

## Testing

1. **Test Immediate Messages:**
```python
message = {
    "queue_name": "notifications",
    "operation": "send_email",
    "data": {...}
}
await redis_push_async(message)
```

2. **Test Delayed Messages:**
```python
await redis_push_async(message, delay_seconds=60)
```

3. **Check Pending Messages:**
```python
from app.services.stream_consumer_groups import get_pending_messages

pending = await get_pending_messages("notifications:stream", "main-group")
```

## Troubleshooting

### Messages Not Being Processed

1. Check consumer group exists:
   ```python
   await ensure_consumer_group("queue:stream", "main-group")
   ```

2. Check for pending messages:
   ```python
   pending = await get_pending_messages("queue:stream", "main-group")
   ```

3. Claim and retry pending messages:
   ```python
   claimed = await claim_pending_messages("queue:stream", "main-group", "consumer-1")
   ```

### High Memory Usage

Streams can grow large. Consider:
- Setting `MAXLEN` when adding messages (not implemented yet)
- Periodic cleanup of old messages
- Monitoring stream length with `XLEN`

## Future Enhancements

1. **Stream Trimming**: Auto-trim old messages with `XADD ... MAXLEN`
2. **Dead Letter Queue**: Move failed messages after max retries
3. **Metrics**: Add Prometheus metrics for monitoring
4. **Stream Replication**: Support for Redis Cluster


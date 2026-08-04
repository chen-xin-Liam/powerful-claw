# LAN AI Computing Power Sharing System

## 📋 Overview 

This system implements GPU resource sharing and distributed execution of AI model inference tasks among multiple computers within a LAN. Through automatic discovery, intelligent scheduling, and secure transmission mechanisms, all available GPU resources within the LAN are integrated into a unified computing power pool, enabling efficient distributed computing.

## 🏗️ Architecture Design

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LAN Cluster Architecture                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                │
│   │   Node A    │    │   Node B    │    │   Node C    │   ...          │
│   │ (Leader)    │    │ (Worker)    │    │ (Worker)    │                │
│   └─────┬─────┘    └─────┬─────┘    └─────┬─────┘                │
│         │                │                │                              │
│         ↓                ↓                ↓                              │
│   ┌──────────────────────────────────────────────────────┐              │
│   │              LAN Network (UDP/TCP)                   │              │
│   │  Port 15300: Node Discovery  Port 15301: Main Comm   │              │
│   │  Port 15302: Task Dispatch  Port 15303: Data Transfer│              │
│   │  Port 15304: Status Monitor Port 15305: REST API     │              │
│   └──────────────────────────────────────────────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component                 | File                       | Responsibility                                                  |
| ------------------------- | -------------------------- | --------------------------------------------------------------- |
| **GPU Detection**         | `gpu_detector.py`          | Detect GPU model, memory, temperature and other information     |
| **Node Communication**    | `lan_node.py`              | LAN node discovery, connection management, heartbeat monitoring |
| **Task Scheduling**       | `task_scheduler.py`        | Task distribution and load balancing                            |
| **Secure Transport**      | `secure_transport.py`      | Data encryption and signature verification                      |
| **Cluster Monitoring**    | `cluster_monitor.py`       | Real-time status monitoring and statistics                      |
| **Distributed Inference** | `distributed_inference.py` | AI model distributed inference                                  |
| **REST API**              | `cluster_api.py`           | External API interface                                          |
| **Cluster Management**    | `__init__.py`              | Integration of all components                                   |

## 🔌 Port Allocation

| Port      | Protocol | Purpose                   |
| --------- | -------- | ------------------------- |
| **15300** | UDP      | Node discovery broadcast  |
| **15301** | TCP      | Master node communication |
| **15302** | TCP      | Task distribution         |
| **15303** | TCP      | Data transfer             |
| **15304** | UDP      | Status monitoring         |
| **15305** | HTTP     | REST API                  |

## 🧠 Core Principles

### 1. Node Discovery Mechanism

**Principle**: Use UDP broadcast to achieve automatic node discovery within the LAN

```
┌─────────────────────────────────────────────────────────────┐
│                    Node Discovery Flow                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Node Startup → Send UDP Broadcast(255.255.255.255:15300)  │
│                    ↓                                        │
│   Other nodes receive broadcast → Parse node info → Add to  │
│   node list                                                 │
│                    ↓                                        │
│   Periodically send heartbeat → Update node status → Detect │
│   offline nodes                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Technical Points**:

- Broadcast interval: 3 seconds
- Heartbeat timeout: 15 seconds
- Offline determination: No response for two consecutive heartbeat cycles

### 2. GPU Resource Detection

**Detection Methods**:

| Method     | Description                                           |
| ---------- | ----------------------------------------------------- |
| nvidia-smi | Get detailed GPU information on Windows/Linux systems |
| PyTorch    | Fallback solution, detect via torch.cuda              |

**Detection Content**:

- GPU model and quantity
- Total/used/available memory
- GPU utilization
- Temperature
- Compute capability version

### 3. Load Balancing Algorithm

**Node Scoring Formula**:

```
Score = (Memory Adequacy × 50) + (GPU Count × 10) + (Load Ratio × 30) + (Priority Bonus × 10)
```

**Scoring Factors**:

| Factor          | Weight | Description                             |
| --------------- | ------ | --------------------------------------- |
| Memory Adequacy | 50%    | Available memory / Total memory         |
| GPU Count       | 10%    | Number of GPUs in the node              |
| Load Ratio      | 30%    | (Max tasks - Current tasks) / Max tasks |
| Priority Bonus  | 10%    | Extra points for HIGH/URGENT tasks      |

### 4. Distributed Inference Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   Distributed Inference Flow                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   User Request → Check Local Model → Available Locally?     │
│       ↓                      ↓                              │
│      Yes                     No                             │
│       ↓                      ↓                              │
│   Local Inference        Select Optimal Node                │
│       ↓                      ↓                              │
│   Return Result      Send Inference Request → Execute       │
│   Inference → Return Result                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5. Secure Transmission Mechanism

**Encryption Scheme**:

| Type                  | Algorithm    | Purpose                        |
| --------------------- | ------------ | ------------------------------ |
| Symmetric Encryption  | Fernet       | Data transmission encryption   |
| Asymmetric Encryption | RSA-2048     | Key exchange                   |
| Digital Signature     | SHA256 + PSS | Message integrity verification |

**Security Features**:

- ✅ End-to-end encryption
- ✅ Message signature verification
- ✅ Data integrity check
- ✅ Replay attack prevention

## 🚀 Quick Start

### 1. Start Cluster Service

```python
from src.services.cluster import ClusterManager

# Create cluster manager
cluster = ClusterManager()

# Start cluster
cluster.start()

print("Cluster service started")
```

### 2. Integrate Local Model

```python
from src.services.local_model_service import LocalModelService

# Create local model service
local_model = LocalModelService()

# Connect to cluster
cluster.set_local_model_service(local_model)

# Load model
local_model.load_model("Qwen2-0.5B")
```

### 3. Execute Inference

```python
# Synchronous inference
result = cluster.chat("Help me write a poem")
print(result)

# Streaming inference
for chunk in cluster.chat_stream("Tell a story"):
    print(chunk, end="", flush=True)
```

### 4. Access via API

```bash
# Get cluster status
curl http://localhost:15305/api/cluster/summary

# Get node list
curl http://localhost:15305/api/cluster/nodes

# Get task list
curl http://localhost:15305/api/cluster/tasks

# Submit task
curl -X POST http://localhost:15305/api/cluster/task \
  -H "Content-Type: application/json" \
  -d '{"type": "ai_inference", "data": {"prompt": "Hello"}, "priority": 2}'
```

## 📊 API Interface

### GET /api/cluster/stats

Get cluster statistics

**Response Example**:

```json
{
  "status": "active",
  "total_nodes": 3,
  "active_nodes": 3,
  "total_gpus": 4,
  "total_memory_gb": 48.0,
  "available_memory_gb": 32.0,
  "active_tasks": 2,
  "completed_tasks": 100,
  "failed_tasks": 2
}
```

### GET /api/cluster/nodes

Get node list

### GET /api/cluster/tasks

Get task list

### GET /api/cluster/summary

Get cluster summary

### GET /api/cluster/self

Get current node information

### POST /api/cluster/task

Submit new task

### POST /api/cluster/task/cancel

Cancel task

## ⚙️ Configuration

### Environment Variables

| Variable         | Default Value | Description                  |
| ---------------- | ------------- | ---------------------------- |
| CLUSTER\_ENABLED | true          | Enable cluster functionality |
| DISCOVERY\_PORT  | 15300         | Discovery service port       |
| MAIN\_PORT       | 15301         | Main communication port      |
| TASK\_PORT       | 15302         | Task port                    |
| DATA\_PORT       | 15303         | Data port                    |
| MONITOR\_PORT    | 15304         | Monitor port                 |
| API\_PORT        | 15305         | API port                     |

### Configuration Example (.env)

```ini
# Cluster Configuration
CLUSTER_ENABLED=true
DISCOVERY_PORT=15300
MAIN_PORT=15301
TASK_PORT=15302
DATA_PORT=15303
MONITOR_PORT=15304
API_PORT=15305

# Task Configuration
MAX_TASKS_PER_NODE=10
HEARTBEAT_INTERVAL=5
HEARTBEAT_TIMEOUT=15
```

## 🔍 Troubleshooting

### Common Issues

| Issue                  | Cause                           | Solution                 |
| ---------------------- | ------------------------------- | ------------------------ |
| Cannot discover nodes  | Firewall blocking UDP broadcast | Allow UDP port 15300     |
| Connection refused     | Target port not open            | Check port usage         |
| GPU detection failed   | nvidia-smi not available        | Install NVIDIA driver    |
| Task assignment failed | Node offline                    | Check network connection |

### Log Description

```
[LANNode] Node abc12345 started, IP: 192.168.1.100
[LANNode] Discovered new node: def67890 (192.168.1.101)
[TaskScheduler] Task 12345678 assigned to node def67890
[DistributedInference] Received inference request: abcdef12
[ClusterMonitor] Cluster status: active
```

## 📈 Performance Optimization

### Optimization Strategies

1. **Local Priority**: Prioritize using local GPU to reduce network overhead
2. **Memory Awareness**: Select appropriate nodes based on model size
3. **Batch Tasks**: Combine small tasks to reduce network round trips
4. **Async Transfer**: Use async IO to improve concurrent processing capability

### Performance Metrics

| Metric                  | Description                              | Target Value         |
| ----------------------- | ---------------------------------------- | -------------------- |
| Node discovery latency  | From startup to discovering all nodes    | < 5 seconds          |
| Task assignment latency | From submission to assignment completion | < 100ms              |
| Inference latency       | Network transfer + computation time      | Depends on model     |
| Throughput              | Tasks processed per second               | Depends on GPU count |

## 🤝 Extensibility

### Supported Model Types

- ✅ Large Language Models (LLM)
- ✅ Image Generation Models
- ✅ Speech Recognition Models
- ✅ Computer Vision Models

### Future Extensions

- [ ] Distributed training support
- [ ] Model parallel computing
- [ ] Dynamic load balancing
- [ ] Fault tolerance and recovery
- [ ] Resource reservation mechanism

## 📝 License

This system is released under the MIT License, see LICENSE file for details.

***

*Document Version: 1.0*\
*Last Updated: May 2026 *

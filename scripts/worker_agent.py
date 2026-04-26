#!/usr/bin/env python
"""Worker agent — run on remote PCs to report resources to the main server.

Usage:
    python worker_agent.py --server http://MAIN_SERVER:8000 --name my-gpu-pc --port 11434

The agent:
1. Registers itself with the main server
2. Polls local Ollama for available models
3. Reads GPU stats via nvidia-smi and RAM via psutil
4. Sends heartbeat every 15 seconds
"""

import argparse
import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Install: pip install requests")
    sys.exit(1)

try:
    import psutil
except ImportError:
    psutil = None
    print("WARNING: psutil not found, RAM metrics will be unavailable. Install: pip install psutil")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker_agent")


def get_gpu_stats() -> dict:
    """Get GPU stats via nvidia-smi."""
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return {}
    
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return {}
        
        line = result.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]
        
        if len(parts) >= 4:
            return {
                "gpu_name": parts[0],
                "vram_total_mb": int(float(parts[1])),
                "vram_used_mb": int(float(parts[2])),
                "vram_free_mb": int(float(parts[3])),
            }
    except Exception as e:
        logger.warning(f"nvidia-smi error: {e}")
    
    return {}


def get_ram_stats() -> dict:
    """Get RAM stats via psutil."""
    if not psutil:
        return {}
    
    mem = psutil.virtual_memory()
    return {
        "ram_total_mb": int(mem.total / 1024 / 1024),
        "ram_used_mb": int(mem.used / 1024 / 1024),
        "ram_free_mb": int(mem.available / 1024 / 1024),
        "cpu_percent": psutil.cpu_percent(interval=0.5),
    }


def get_ollama_models(ollama_url: str) -> list:
    """Get list of available models from local Ollama."""
    try:
        resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


def get_local_ip() -> str:
    """Get the local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def register_worker(server_url: str, name: str, host: str, port: int, api_type: str) -> int:
    """Register this worker with the main server. Returns worker ID."""
    url = f"{server_url}/api/workers/register"
    payload = {
        "name": name,
        "host": host,
        "port": port,
        "api_type": api_type,
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        worker_id = data["id"]
        logger.info(f"Registered as worker ID {worker_id}: {name} @ {host}:{port}")
        return worker_id
    except requests.RequestException as e:
        logger.error(f"Failed to register: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Response: {e.response.text[:300]}")
        sys.exit(1)


def send_heartbeat(server_url: str, worker_id: int, ollama_url: str) -> bool:
    """Send heartbeat with resource metrics."""
    gpu = get_gpu_stats()
    ram = get_ram_stats()
    models = get_ollama_models(ollama_url)
    
    payload = {
        **gpu,
        **ram,
        "models_available": models,
    }
    
    try:
        resp = requests.post(f"{server_url}/api/workers/{worker_id}/heartbeat", json=payload, timeout=10)
        resp.raise_for_status()
        
        # Compact log
        vram_info = f"VRAM: {gpu.get('vram_used_mb', '?')}/{gpu.get('vram_total_mb', '?')}MB" if gpu else "No GPU"
        ram_info = f"RAM: {ram.get('ram_used_mb', '?')}/{ram.get('ram_total_mb', '?')}MB" if ram else "No RAM info"
        logger.info(f"♥ Heartbeat OK | {vram_info} | {ram_info} | Models: {len(models)}")
        return True
    except requests.RequestException as e:
        logger.warning(f"Heartbeat failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Worker agent for Threads Automation")
    parser.add_argument("--server", required=True, help="Main server URL (e.g. http://192.168.1.100:8000)")
    parser.add_argument("--name", default=platform.node(), help="Worker name (default: hostname)")
    parser.add_argument("--host", default=None, help="Worker IP (default: auto-detect)")
    parser.add_argument("--port", type=int, default=11434, help="Ollama port (default: 11434)")
    parser.add_argument("--api-type", default="ollama", choices=["ollama", "openai"], help="API type")
    parser.add_argument("--interval", type=int, default=15, help="Heartbeat interval in seconds")
    args = parser.parse_args()
    
    host = args.host or get_local_ip()
    ollama_url = f"http://localhost:{args.port}"
    
    logger.info(f"Worker Agent starting: {args.name} @ {host}:{args.port}")
    logger.info(f"Main server: {args.server}")
    logger.info(f"Ollama URL: {ollama_url}")
    
    # Register
    worker_id = register_worker(args.server, args.name, host, args.port, args.api_type)
    
    # Heartbeat loop
    logger.info(f"Starting heartbeat loop (every {args.interval}s)...")
    fail_count = 0
    
    while True:
        ok = send_heartbeat(args.server, worker_id, ollama_url)
        if ok:
            fail_count = 0
        else:
            fail_count += 1
            if fail_count >= 10:
                logger.error("Too many heartbeat failures, re-registering...")
                worker_id = register_worker(args.server, args.name, host, args.port, args.api_type)
                fail_count = 0
        
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

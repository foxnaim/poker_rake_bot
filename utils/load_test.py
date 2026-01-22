#!/usr/bin/env python3
"""
Load testing script для проверки производительности API под нагрузкой

Использование:
    python -m utils.load_test --api http://localhost:8000 --requests 1000 --concurrent 10
"""

import argparse
import asyncio
import time
import statistics
from typing import List, Dict, Any
import httpx


async def make_decide_request(
    client: httpx.AsyncClient,
    api_url: str,
    request_id: int,
    table_key: str = "table_1"
) -> Dict[str, Any]:
    """Отправляет запрос /decide"""
    request_data = {
        "hand_id": f"load_test_{request_id}",
        "table_id": table_key,
        "limit_type": "NL10",
        "street": "preflop",
        "hero_position": 0,
        "dealer": 5,
        "hero_cards": "AsKh",
        "board_cards": "",
        "stacks": {str(i): 100.0 for i in range(6)},
        "bets": {str(i): 0.0 for i in range(6)},
        "total_bets": {str(i): 0.0 for i in range(6)},
        "active_players": [0, 1, 2, 3, 4, 5],
        "pot": 1.5,
        "current_player": 0,
        "last_raise_amount": 0.0,
        "small_blind": 0.5,
        "big_blind": 1.0
    }
    
    start_time = time.time()
    try:
        response = await client.post(
            f"{api_url}/api/v1/decide",
            json=request_data,
            timeout=5.0
        )
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "success": response.status_code == 200,
            "latency_ms": latency_ms,
            "status_code": response.status_code,
            "error": None
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "latency_ms": latency_ms,
            "status_code": None,
            "error": str(e)
        }


async def run_load_test(
    api_url: str,
    total_requests: int,
    concurrent: int,
    table_key: str = "table_1"
) -> Dict[str, Any]:
    """Запускает нагрузочный тест"""
    print(f"\n🚀 Load Test Started")
    print(f"   API: {api_url}")
    print(f"   Total requests: {total_requests}")
    print(f"   Concurrent: {concurrent}")
    print(f"   Table key: {table_key}\n")
    
    async with httpx.AsyncClient() as client:
        # Проверяем health
        try:
            health_response = await client.get(f"{api_url}/api/v1/health", timeout=2.0)
            if health_response.status_code != 200:
                print(f"❌ API health check failed: {health_response.status_code}")
                return {"error": "Health check failed"}
            print("✅ API health check passed")
        except Exception as e:
            print(f"❌ API not reachable: {e}")
            return {"error": f"API not reachable: {e}"}
        
        # Запускаем нагрузочный тест
        results: List[Dict[str, Any]] = []
        start_time = time.time()
        
        semaphore = asyncio.Semaphore(concurrent)
        
        async def bounded_request(request_id: int):
            async with semaphore:
                return await make_decide_request(client, api_url, request_id, table_key)
        
        # Создаём задачи
        tasks = [bounded_request(i) for i in range(total_requests)]
        
        # Выполняем все запросы
        print(f"📊 Sending {total_requests} requests...")
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Анализируем результаты
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        if not successful:
            print("❌ All requests failed!")
            return {
                "total_requests": total_requests,
                "successful": 0,
                "failed": len(failed),
                "error": "All requests failed"
            }
        
        latencies = [r["latency_ms"] for r in successful]
        
        stats = {
            "total_requests": total_requests,
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / total_requests * 100,
            "total_time_seconds": total_time,
            "requests_per_second": total_requests / total_time,
            "latency": {
                "min": min(latencies),
                "max": max(latencies),
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies),
                "p95": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else statistics.median(latencies),
                "p99": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
            }
        }
        
        # Выводим результаты
        print(f"\n📊 Load Test Results:")
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Successful: {stats['successful']} ({stats['success_rate']:.1f}%)")
        print(f"   Failed: {stats['failed']}")
        print(f"   Total time: {stats['total_time_seconds']:.2f}s")
        print(f"   Requests/sec: {stats['requests_per_second']:.1f}")
        print(f"\n⏱️  Latency (ms):")
        print(f"   Min: {stats['latency']['min']:.2f}")
        print(f"   Max: {stats['latency']['max']:.2f}")
        print(f"   Mean: {stats['latency']['mean']:.2f}")
        print(f"   Median: {stats['latency']['median']:.2f}")
        print(f"   P95: {stats['latency']['p95']:.2f}")
        print(f"   P99: {stats['latency']['p99']:.2f}")
        
        # Проверяем требования
        print(f"\n✅ Requirements Check:")
        p95_ok = stats['latency']['p95'] < 200
        p99_ok = stats['latency']['p99'] < 500
        success_rate_ok = stats['success_rate'] >= 95
        
        print(f"   P95 < 200ms: {'✅' if p95_ok else '❌'} ({stats['latency']['p95']:.2f}ms)")
        print(f"   P99 < 500ms: {'✅' if p99_ok else '❌'} ({stats['latency']['p99']:.2f}ms)")
        print(f"   Success rate >= 95%: {'✅' if success_rate_ok else '❌'} ({stats['success_rate']:.1f}%)")
        
        if p95_ok and p99_ok and success_rate_ok:
            print(f"\n✅ Load test PASSED")
        else:
            print(f"\n⚠️  Load test has warnings")
        
        if failed:
            print(f"\n❌ Failed requests ({len(failed)}):")
            for i, fail in enumerate(failed[:5]):  # Показываем первые 5
                print(f"   {i+1}. Status: {fail.get('status_code', 'N/A')}, Error: {fail.get('error', 'N/A')}")
        
        return stats


def main():
    parser = argparse.ArgumentParser(description="Load test for Poker Bot API")
    parser.add_argument("--api", default="http://localhost:8000", help="API URL")
    parser.add_argument("--requests", type=int, default=1000, help="Total number of requests")
    parser.add_argument("--concurrent", type=int, default=10, help="Concurrent requests")
    parser.add_argument("--table-key", default="table_1", help="Table key for requests")
    
    args = parser.parse_args()
    
    try:
        stats = asyncio.run(run_load_test(
            api_url=args.api,
            total_requests=args.requests,
            concurrent=args.concurrent,
            table_key=args.table_key
        ))
        
        if "error" in stats:
            exit(1)
        
        # Exit code 0 если все требования выполнены
        p95_ok = stats['latency']['p95'] < 200
        p99_ok = stats['latency']['p99'] < 500
        success_rate_ok = stats['success_rate'] >= 95
        
        exit(0 if (p95_ok and p99_ok and success_rate_ok) else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Load test interrupted")
        exit(1)
    except Exception as e:
        print(f"\n❌ Load test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()

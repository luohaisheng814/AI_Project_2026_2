"""CLI 终端版（保留，方便调试）"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core_api import ask
import time

def main():
    print("=" * 60)
    print("  🌏 釜山沙下区文旅问答系统 (CLI)")
    print("=" * 60)
    
    session_id = "cli_user"
    t0 = time.time()
    
    while True:
        q = input("\n🙋 提问（exit 退出 / stats 统计）：").strip()
        if not q:
            continue
        if q.lower() == "exit":
            print("👋 再见")
            break
        if q.lower() == "stats":
            from core_api import get_session_stats
            stats = get_session_stats(session_id)
            print(f"📊 提问 {stats['count']} 次，耗时 {int(time.time()-t0)}s")
            continue
        
        result = ask(q, session_id=session_id)
        print(f"\n{result['reply']}")
        if result["recommendation"]:
            print(f"\n💡 {result['recommendation']}")
        if result["prediction"]:
            print(f"\n🔮 {result['prediction']}")

if __name__ == "__main__":
    main()
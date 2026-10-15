"""직접 구현한 자료구조로 만드는 대화형 Redis 스타일 문자열 저장소."""

import shlex
import sys
import time

from doubly_linked_list import DoublyLinkedList
from hash_map import HashMap
from min_heap import MinHeap


class MiniRedis:
    """해시맵, LRU 리스트, 만료 최소 힙과 UTF-8 메모리 제한을 함께 관리한다."""

    def __init__(self):
        """값 저장소와 LRU/TTL 인덱스를 만들고 메모리·퇴출 카운터를 초기화한다."""
        self.data = HashMap()
        self.lru = DoublyLinkedList()
        self.lru_nodes = HashMap()  # key -> linked-list node handle
        self.expirations = HashMap()  # key -> monotonic deadline
        self.expiry_heap = MinHeap()  # lazy stale entries are discarded when they reach root
        self.used_memory = 0
        self.maxmemory = 0
        self.evicted_keys = 0

    @staticmethod
    def _bytes(key, value):
        """명세의 공식에 따라 키와 값의 UTF-8 바이트 수 합을 계산한다."""
        return len(key.encode("utf-8")) + len(value.encode("utf-8"))

    def _delete(self, key):
        """키를 데이터, 메모리 카운터, LRU와 TTL 인덱스에서 일관되게 제거한다."""
        value = self.data.remove(key)
        if value is None:
            return False
        self.used_memory -= self._bytes(key, value)
        node = self.lru_nodes.remove(key)
        if node is not None:
            self.lru.remove_node(node)
        self.expirations.remove(key)
        # Heap entries are intentionally left stale; _purge_expired validates them lazily.
        return True

    def _purge_expired(self):
        """기한이 지난 힙 레코드를 제거하되 현재 TTL과 일치하는 레코드의 키만 만료시킨다."""
        now = time.monotonic()
        while self.expiry_heap.peek() is not None and self.expiry_heap.peek()[0] <= now:
            deadline, key = self.expiry_heap.pop()
            if self.expirations.get(key) == deadline:
                self._delete(key)

    def _ensure_live(self, key):
        """만료된 레코드를 먼저 정리한 뒤 요청 키가 살아 있는지 확인한다."""
        self._purge_expired()
        return self.data.contains(key)

    def _touch(self, key):
        """성공한 조회의 키 노드를 리스트 맨 앞으로 옮겨 최근 사용으로 표시한다."""
        node = self.lru_nodes.get(key)
        if node is not None:
            self.lru.move_to_front(node)

    def _evict_to_limit(self):
        """양수 메모리 제한을 만족할 때까지 가장 오래된 키부터 지우고 횟수를 누적한다."""
        while self.maxmemory > 0 and self.used_memory > self.maxmemory:
            oldest = self.lru.remove_back()
            if oldest is None:
                break
            key = oldest
            self.lru_nodes.remove(key)
            value = self.data.remove(key)
            if value is not None:
                self.used_memory -= self._bytes(key, value)
                self.expirations.remove(key)
                self.evicted_keys += 1

    def set(self, key, value):
        """값을 설정하며 기존 TTL을 지운다. 단일 항목 OOM은 거부하고 초과분은 LRU 퇴출한다."""
        self._purge_expired()
        entry_size = self._bytes(key, value)
        if self.maxmemory > 0 and entry_size > self.maxmemory:
            return "(error) OOM command not allowed when used_memory > 'maxmemory'"
        if self.data.contains(key):
            self._delete(key)
        self.data.put(key, value)
        self.used_memory += entry_size
        node = self.lru.insert_front(key)
        self.lru_nodes.put(key, node)
        self._evict_to_limit()
        return "OK"

    def execute(self, parts):
        """토큰화된 명령의 인자 수와 값을 검증한 뒤 실행하고 Redis 스타일 응답을 만든다."""
        if not parts:
            return None
        command = parts[0].upper()
        args = parts[1:]
        # A conditional chain avoids using a built-in mapping for command dispatch.
        if command == "SET" or command == "EXPIRE":
            expected = 2
        elif command == "GET" or command == "DEL" or command == "EXISTS" or command == "TTL":
            expected = 1
        elif command == "DBSIZE" or command == "KEYS":
            expected = 0
        else:
            expected = None
        if command == "CONFIG":
            if len(args) != 3 or args[0].upper() != "SET" or args[1].lower() != "maxmemory":
                return "(error) ERR wrong number of arguments for 'config' command"
            try:
                amount = int(args[2], 10)
            except ValueError:
                return "(error) ERR value is not an integer or out of range"
            if amount < 0:
                return "(error) ERR value is not an integer or out of range"
            self.maxmemory = amount
            self._evict_to_limit()
            return "OK"
        if command == "INFO":
            if len(args) != 1 or args[0].lower() != "memory":
                return "(error) ERR wrong number of arguments for 'info' command"
            return ("# Memory\r\n" f"used_memory:{self.used_memory}\r\n"
                    f"maxmemory:{self.maxmemory}\r\n" f"evicted_keys:{self.evicted_keys}")
        if expected is None:
            return f"(error) ERR unknown command '{parts[0]}'"
        if len(args) != expected:
            return f"(error) ERR wrong number of arguments for '{command.lower()}' command"
        if command == "SET":
            return self.set(args[0], args[1])
        if command == "GET":
            key = args[0]
            if not self._ensure_live(key):
                return "(nil)"
            value = self.data.get(key)
            self._touch(key)
            return f'"{value}"'
        if command == "DEL":
            self._ensure_live(args[0])
            return f"(integer) {int(self._delete(args[0]))}"
        if command == "EXISTS":
            return f"(integer) {int(self._ensure_live(args[0]))}"
        if command == "DBSIZE":
            self._purge_expired()
            return f"(integer) {self.data.size()}"
        if command == "KEYS":
            self._purge_expired()
            keys = self.data.keys()
            return "(empty array)" if not keys else "\n".join(f'{i}. "{key}"' for i, key in enumerate(keys, 1))
        if command == "EXPIRE":
            key = args[0]
            try:
                seconds = int(args[1], 10)
            except ValueError:
                return "(error) ERR value is not an integer or out of range"
            if not self._ensure_live(key):
                return "(integer) 0"
            if seconds <= 0:
                self._delete(key)
                return "(integer) 1"
            deadline = time.monotonic() + seconds
            self.expirations.put(key, deadline)
            self.expiry_heap.push((deadline, key))
            return "(integer) 1"
        if command == "TTL":
            key = args[0]
            if not self._ensure_live(key):
                return "(integer) -2"
            deadline = self.expirations.get(key)
            return "(integer) -1" if deadline is None else f"(integer) {max(0, int(deadline - time.monotonic()))}"


def main():
    """mini-redis 프롬프트를 표시하고, 따옴표를 지원하는 shlex 파서로 입력을 실행한다."""
    server = MiniRedis()
    while True:
        try:
            line = input("mini-redis> ")
        except EOFError:
            print()
            break
        if line.strip().lower() in ("exit", "quit"):
            break
        try:
            parts = shlex.split(line)
        except ValueError:
            print("(error) ERR syntax error")
            continue
        output = server.execute(parts)
        if output is not None:
            print(output)


if __name__ == "__main__":
    main()

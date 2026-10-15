"""파이썬 내장 매핑 자료형 없이 체이닝으로 구현한 해시맵."""

from doubly_linked_list import DoublyLinkedList


class HashMap:
    """사용자 정의 해시와 이중 연결 리스트 버킷을 이용하는 문자열 키 해시맵."""

    def __init__(self, capacity=8):
        """최소 두 개의 버킷과 항목 수 카운터로 빈 해시맵을 준비한다."""
        self._capacity = max(2, capacity)
        self._buckets = [DoublyLinkedList() for _ in range(self._capacity)]
        self._size = 0

    def _hash(self, key):
        """문자 코드에 FNV 계열 다항 해시를 적용해 버킷 인덱스를 직접 계산한다."""
        value = 2166136261
        for character in key:
            value = ((value ^ ord(character)) * 16777619) & 0xFFFFFFFF
        return value % self._capacity

    def _find(self, key):
        """해시 버킷 하나만 순회해 키의 노드를 찾고, 없으면 (버킷, None)을 돌려준다."""
        bucket = self._buckets[self._hash(key)]
        for node in self._nodes(bucket):
            if node.data[0] == key:
                return bucket, node
        return bucket, None

    @staticmethod
    def _nodes(bucket):
        """버킷의 감시 노드를 제외하고 실제 노드 핸들을 차례로 생성한다."""
        node = bucket._head.next
        while node is not bucket._tail:
            yield node
            node = node.next

    def _resize(self):
        """버킷 수를 두 배로 늘리고 모든 항목을 새 해시 인덱스에 다시 연결한다."""
        old_buckets = self._buckets
        self._capacity *= 2
        self._buckets = [DoublyLinkedList() for _ in range(self._capacity)]
        for bucket in old_buckets:
            for key, value in bucket:
                self._buckets[self._hash(key)].insert_back((key, value))

    def put(self, key, value):
        """키를 추가하거나 값을 교체한다. 추가 후 적재율이 0.75를 넘으면 두 배 확장한다."""
        bucket, node = self._find(key)
        if node is not None:
            previous = node.data[1]
            node.data = (key, value)
            return previous
        bucket.insert_back((key, value))
        self._size += 1
        if self._size / self._capacity > 0.75:
            self._resize()
        return None

    def get(self, key, default=None):
        """해당 체인에서 값을 찾아 반환하고, 키가 없으면 지정한 기본값을 반환한다."""
        _, node = self._find(key)
        return default if node is None else node.data[1]

    def contains(self, key):
        """해당 키가 존재하는지 체인 검색으로 확인한다."""
        _, node = self._find(key)
        return node is not None

    def remove(self, key):
        """키가 있으면 체인에서 노드를 제거하고 값을 반환하며 없으면 None을 반환한다."""
        bucket, node = self._find(key)
        if node is None:
            return None
        value = bucket.remove_node(node)[1]
        self._size -= 1
        return value

    def keys(self):
        """모든 버킷 체인을 훑어 키 목록을 만든다. 순서는 버킷 배치에 따른다."""
        result = []
        for bucket in self._buckets:
            for key, _ in bucket:
                result.append(key)
        return result

    def size(self):
        """저장된 항목 수를 상수 시간에 반환한다."""
        return self._size

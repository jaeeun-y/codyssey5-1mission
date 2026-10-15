"""캐시의 LRU 순서와 해시 버킷 체인에 공용으로 쓰는 이중 연결 리스트."""


class Node:
    """리스트 노드. 양방향 링크를 저장하므로 노드 핸들로 제거할 때 O(1)이다."""

    def __init__(self, data):
        """아직 리스트에 연결되지 않은 노드를 만들고 사용자 데이터를 보관한다."""
        self.prev = None
        self.next = None
        self.data = data


class DoublyLinkedList:
    """양 끝 감시 노드를 사용해 경계 처리를 단순화한 이중 연결 리스트."""

    def __init__(self):
        """head와 tail 감시 노드를 서로 연결해 빈 리스트 상태를 초기화한다."""
        self._head = Node(None)
        self._tail = Node(None)
        self._head.next = self._tail
        self._tail.prev = self._head
        self._size = 0

    def __len__(self):
        """별도 크기 카운터를 반환하므로 리스트 순회 없이 O(1)에 계산한다."""
        return self._size

    def _insert_between(self, node, left, right):
        """서로 이웃인 left와 right 사이에 node를 연결하고 크기를 갱신한다."""
        node.prev, node.next = left, right
        left.next, right.prev = node, node
        self._size += 1

    def insert_front(self, data):
        """맨 앞에 새 노드를 삽입하고, 이후 O(1) 이동/삭제에 쓸 노드 핸들을 반환한다."""
        node = Node(data)
        self._insert_between(node, self._head, self._head.next)
        return node

    def insert_back(self, data):
        """맨 뒤에 새 노드를 삽입한다. 끝 감시 노드 덕분에 빈 상태도 같은 절차다."""
        node = Node(data)
        self._insert_between(node, self._tail.prev, self._tail)
        return node

    def remove_node(self, node):
        """소속 리스트에 연결된 노드만 양옆에서 끊어 제거하고 데이터 값을 반환한다."""
        if node is self._head or node is self._tail or node.prev is None:
            raise ValueError("node is not linked in this list")
        node.prev.next = node.next
        node.next.prev = node.prev
        value = node.data
        node.prev = node.next = None
        self._size -= 1
        return value

    def remove_front(self):
        """첫 실제 노드를 제거해 반환하며, 비어 있으면 None을 반환한다."""
        if self._size == 0:
            return None
        return self.remove_node(self._head.next)

    def remove_back(self):
        """마지막 실제 노드를 제거해 반환하며, 비어 있으면 None을 반환한다."""
        if self._size == 0:
            return None
        return self.remove_node(self._tail.prev)

    def move_to_front(self, node):
        """기존 노드의 링크만 바꿔 맨 앞으로 이동한다. 새 노드를 만들지 않는다."""
        if node is self._head or node is self._tail or node.prev is None:
            raise ValueError("node is not linked in this list")
        if node.prev is self._head:
            return
        node.prev.next = node.next
        node.next.prev = node.prev
        first = self._head.next
        node.prev, node.next = self._head, first
        self._head.next = node
        first.prev = node

    def __iter__(self):
        """감시 노드는 감추고 실제 데이터만 앞에서 뒤 순서로 순회한다."""
        node = self._head.next
        while node is not self._tail:
            yield node.data
            node = node.next
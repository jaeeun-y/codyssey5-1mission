"""(만료 시각, 키) 레코드를 빠른 만료 순으로 꺼내는 배열 기반 최소 힙."""


class MinHeap:
    """원소 비교 순서를 이용해 최소 원소를 루트에 유지하는 이진 힙."""

    def __init__(self):
        """완전 이진 트리의 레벨 순서를 배열로 표현할 빈 힙을 만든다."""
        self._items = []

    def size(self):
        """배열 길이를 반환해 힙 크기를 O(1)에 제공한다."""
        return len(self._items)

    def peek(self):
        """루트의 최소 원소를 제거하지 않고 반환하며, 빈 힙이면 None을 반환한다."""
        return self._items[0] if self._items else None

    def push(self, item):
        """배열 끝에 원소를 추가한 뒤 부모와 비교하며 위로 올려 힙 조건을 복구한다."""
        self._items.append(item)
        self._heapify_up(len(self._items) - 1)

    def pop(self):
        """최솟값을 반환하고 마지막 원소를 루트로 옮긴 뒤 아래로 내려 조건을 복구한다."""
        if not self._items:
            return None
        if len(self._items) == 1:
            return self._items.pop()
        smallest = self._items[0]
        self._items[0] = self._items.pop()
        self._heapify_down(0)
        return smallest

    def _heapify_up(self, index):
        """삽입된 위치에서 시작해 부모가 더 작거나 같아질 때까지 교환한다."""
        while index > 0:
            parent = (index - 1) // 2
            if self._items[parent] <= self._items[index]:
                break
            self._items[parent], self._items[index] = self._items[index], self._items[parent]
            index = parent

    def _heapify_down(self, index):
        """두 자식 중 더 작은 쪽과 교환하며 힙 조건이 만족될 때까지 내려간다."""
        count = len(self._items)
        while True:
            left = 2 * index + 1
            right = left + 1
            smallest = index
            if left < count and self._items[left] < self._items[smallest]:
                smallest = left
            if right < count and self._items[right] < self._items[smallest]:
                smallest = right
            if smallest == index:
                return
            self._items[index], self._items[smallest] = self._items[smallest], self._items[index]
            index = smallest

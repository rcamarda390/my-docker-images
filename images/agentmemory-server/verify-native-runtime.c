/* verify-native-runtime.c: exercise the actual runtime libc and zlib. */
#define _GNU_SOURCE
#include <assert.h>
#include <resolv.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

int main(void)
{
    /* Previously an oversized LOCALDOMAIN could abort in resolver setup. */
    char domain[4096];
    memset(domain, 'a', sizeof domain - 1);
    domain[sizeof domain - 1] = '\0';
    assert(setenv("LOCALDOMAIN", domain, 1) == 0);
    assert(res_init() == 0);
    strcpy(domain, "example.org ");
    memset(domain + 12, 'a', sizeof domain - 13);
    domain[sizeof domain - 1] = '\0';
    assert(setenv("LOCALDOMAIN", domain, 1) == 0);
    assert(res_init() == 0);

    assert(strcmp(zlibVersion(), "1.3.2") == 0);
    const unsigned char input[] = "AgentMemory runtime compression";
    unsigned char compressed[128], restored[128];
    uLongf compressed_size = sizeof compressed, restored_size = sizeof restored;
    assert(compress(compressed, &compressed_size, input, sizeof input) == Z_OK);
    assert(uncompress(restored, &restored_size, compressed, compressed_size) == Z_OK);
    assert(restored_size == sizeof input);
    assert(memcmp(input, restored, sizeof input) == 0);
    return 0;
}
